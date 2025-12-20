"""
Django signals for inventory management
Automatically updates stock levels when invoices are created/updated
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db import transaction
from invoicing.models import Invoice, InvoiceItem
from .models import StockMovement, Product
from .utils import update_inventory_from_invoice, check_and_alert_low_stock
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Invoice)
def handle_invoice_stock_update(sender, instance, created, **kwargs):
    """
    Update inventory when invoice is saved
    """
    try:
        if instance.status in ['paid', 'sent'] and instance.invoice_type == 'sale':
            # Only deduct stock for sales invoices that are sent or paid
            with transaction.atomic():
                update_inventory_from_invoice(instance)
                
                # Check for low stock alerts after updating
                affected_products = []
                for item in instance.invoiceitem_set.all():
                    if hasattr(item, 'product') and item.product:
                        affected_products.append(item.product)
                
                # Check low stock for affected products
                for product in affected_products:
                    if product.is_low_stock():
                        product.send_low_stock_alert()
                        
            logger.info(f"Inventory updated for invoice {instance.invoice_number}")
            
    except Exception as e:
        logger.error(f"Error updating inventory for invoice {instance.id}: {str(e)}")


@receiver(post_save, sender=InvoiceItem)
def handle_invoice_item_stock_update(sender, instance, created, **kwargs):
    """
    Update inventory when individual invoice items are modified
    """
    try:
        if instance.invoice.status in ['paid', 'sent'] and instance.invoice.invoice_type == 'sale':
            if hasattr(instance, 'product') and instance.product:
                with transaction.atomic():
                    # Get or create a default warehouse
                    warehouse, created = instance.invoice.company.warehouses.get_or_create(
                        code='MAIN',
                        defaults={'name': 'Main Warehouse', 'is_active': True}
                    )
                    
                    # Create stock movement for this specific item
                    StockMovement.objects.create(
                        company=instance.invoice.company,
                        product=instance.product,
                        warehouse=warehouse,
                        movement_type='sale',
                        quantity_change=-abs(instance.quantity),  # Negative for sales
                        unit_cost=instance.product.cost_price,
                        total_cost=instance.product.cost_price * abs(instance.quantity),
                        reference_number=instance.invoice.invoice_number,
                        notes=f'Sale to {instance.invoice.customer_name if hasattr(instance.invoice, "customer_name") else "Customer"}'
                    )
                    
                    # Check if product is now low stock
                    if instance.product.is_low_stock():
                        instance.product.send_low_stock_alert()
                        
                logger.info(f"Stock updated for product {instance.product.sku} from invoice item {instance.id}")
                
    except Exception as e:
        logger.error(f"Error updating stock for invoice item {instance.id}: {str(e)}")


@receiver(post_delete, sender=InvoiceItem)
def handle_invoice_item_deletion(sender, instance, **kwargs):
    """
    Restore inventory when invoice items are deleted
    """
    try:
        if instance.invoice.status in ['paid', 'sent'] and instance.invoice.invoice_type == 'sale':
            if hasattr(instance, 'product') and instance.product:
                with transaction.atomic():
                    # Get or create a default warehouse
                    warehouse, created = instance.invoice.company.warehouses.get_or_create(
                        code='MAIN',
                        defaults={'name': 'Main Warehouse', 'is_active': True}
                    )
                    
                    # Create stock movement to restore inventory
                    StockMovement.objects.create(
                        company=instance.invoice.company,
                        product=instance.product,
                        warehouse=warehouse,
                        movement_type='adjustment',
                        quantity_change=abs(instance.quantity),  # Positive to restore stock
                        unit_cost=instance.product.cost_price,
                        total_cost=instance.product.cost_price * abs(instance.quantity),
                        reference_number=f"REV-{instance.invoice.invoice_number}",
                        notes=f'Stock restored from deleted invoice item'
                    )
                    
                logger.info(f"Stock restored for product {instance.product.sku} from deleted invoice item")
                
    except Exception as e:
        logger.error(f"Error restoring stock for deleted invoice item: {str(e)}")


@receiver(pre_save, sender=Invoice)
def track_invoice_status_changes(sender, instance, **kwargs):
    """
    Track when invoice status changes to handle stock movements appropriately
    """
    if instance.pk:
        try:
            old_instance = Invoice.objects.get(pk=instance.pk)
            
            # If invoice status changed from draft to paid/sent, deduct stock
            if (old_instance.status in ['draft', 'pending'] and 
                instance.status in ['paid', 'sent'] and 
                instance.invoice_type == 'sale'):
                
                # Stock will be deducted by post_save signal
                logger.info(f"Invoice {instance.invoice_number} status changed to {instance.status} - stock will be updated")
                
            # If invoice status changed from paid/sent back to draft, restore stock
            elif (old_instance.status in ['paid', 'sent'] and 
                  instance.status in ['draft', 'pending'] and 
                  instance.invoice_type == 'sale'):
                
                with transaction.atomic():
                    # Get or create a default warehouse
                    warehouse, created = instance.company.warehouses.get_or_create(
                        code='MAIN',
                        defaults={'name': 'Main Warehouse', 'is_active': True}
                    )
                    
                    for item in instance.invoiceitem_set.all():
                        if hasattr(item, 'product') and item.product:
                            # Create stock movement to restore inventory
                            StockMovement.objects.create(
                                company=instance.company,
                                product=item.product,
                                warehouse=warehouse,
                                movement_type='adjustment',
                                quantity_change=abs(item.quantity),  # Positive to restore
                                unit_cost=item.product.cost_price,
                                total_cost=item.product.cost_price * abs(item.quantity),
                                reference_number=f"REST-{instance.invoice_number}",
                                notes=f'Stock restored due to status change to {instance.status}'
                            )
                            
                logger.info(f"Stock restored for invoice {instance.invoice_number} due to status change")
                
        except Invoice.DoesNotExist:
            # New invoice, will be handled by post_save
            pass
        except Exception as e:
            logger.error(f"Error tracking invoice status change for {instance.id}: {str(e)}")


# Scheduled task function (can be called by Celery or cron)
def check_low_stock_daily():
    """
    Function to be called daily to check for low stock across all products
    Can be integrated with Celery for automated execution
    """
    try:
        check_and_alert_low_stock()
        logger.info("Daily low stock check completed")
    except Exception as e:
        logger.error(f"Error during daily low stock check: {str(e)}")