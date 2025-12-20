from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.db.models import Q, F
from invoicing.models import InvoiceItem
import logging

logger = logging.getLogger(__name__)


def deduct_inventory_for_invoice(invoice_item):
    """
    Deduct inventory from website product when invoice item is added
    This ensures real-time inventory tracking between invoice and website
    """
    try:
        if not invoice_item.product:
            return False
            
        # Find corresponding website product by SKU
        from .models import Product
        
        sku = invoice_item.product.sku
        if sku and sku.startswith('WEB-'):
            # Extract website product ID from SKU
            website_product_id = sku.replace('WEB-', '')
            try:
                website_product = Product.objects.get(id=website_product_id)
            except Product.DoesNotExist:
                return False
        else:
            # Try to find by SKU or name
            website_product = Product.objects.filter(
                Q(sku=sku) | Q(name=invoice_item.product.name)
            ).first()
            
        if not website_product:
            return False
            
        # Check if we have enough stock
        if website_product.stock_quantity < invoice_item.quantity:
            return False
            
        # Deduct the quantity using atomic transaction
        with transaction.atomic():
            website_product.stock_quantity = F('stock_quantity') - invoice_item.quantity
            website_product.save()
            
            # Update the invoice product stock as well
            invoice_item.product.current_stock = F('current_stock') - invoice_item.quantity
            invoice_item.product.save()
            
        return True
        
    except Exception as e:
        logger.error(f"Error deducting inventory for invoice item {invoice_item.id}: {e}")
        return False


@receiver(post_save, sender=InvoiceItem)
def sync_inventory_on_invoice_item_save(sender, instance, created, **kwargs):
    """
    Signal to automatically deduct inventory when invoice items are created or updated
    This ensures real-time inventory tracking between invoice and website
    """
    if created:  # Only for new invoice items
        try:
            # Deduct inventory from website product
            success = deduct_inventory_for_invoice(instance)
            
            if not success:
                logger.warning(
                    f"Failed to deduct inventory for invoice item {instance.id}. "
                    f"Product: {instance.product.name if instance.product else 'N/A'}, "
                    f"Quantity: {instance.quantity}"
                )
            else:
                logger.info(
                    f"Successfully deducted inventory for invoice item {instance.id}. "
                    f"Product: {instance.product.name if instance.product else 'N/A'}, "
                    f"Quantity: {instance.quantity}"
                )
                
        except Exception as e:
            logger.error(f"Error in inventory sync signal for invoice item {instance.id}: {e}")


@receiver(post_delete, sender=InvoiceItem)
def restore_inventory_on_invoice_item_delete(sender, instance, **kwargs):
    """
    Signal to restore inventory when invoice items are deleted
    This handles cases where invoice items are removed
    """
    try:
        if not instance.product:
            return
            
        # Find corresponding website product
        from .models import Product
        
        sku = instance.product.sku
        if sku and sku.startswith('WEB-'):
            # Extract website product ID from SKU
            website_product_id = sku.replace('WEB-', '')
            try:
                website_product = Product.objects.get(id=website_product_id)
            except Product.DoesNotExist:
                return
        else:
            # Try to find by SKU or name
            website_product = Product.objects.filter(
                Q(sku=sku) | Q(name=instance.product.name)
            ).first()
            
        if not website_product:
            return
            
        # Restore the quantity using atomic transaction
        with transaction.atomic():
            website_product.stock_quantity = F('stock_quantity') + instance.quantity
            website_product.save()
            
            # Update the invoice product stock as well
            instance.product.current_stock = F('current_stock') + instance.quantity
            instance.product.save()
            
        logger.info(
            f"Restored inventory for deleted invoice item. "
            f"Product: {instance.product.name}, "
            f"Quantity: {instance.quantity}"
        )
            
    except Exception as e:
        logger.error(f"Error restoring inventory for deleted invoice item: {e}")