"""
Inventory utility functions including SMS notifications for low stock alerts
"""
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_low_stock_sms(phone, product_name, current_stock, minimum_stock):
    """
    Send SMS alert for low stock levels
    
    Args:
        phone (str): Phone number to send SMS to
        product_name (str): Name of the product
        current_stock (int): Current stock level
        minimum_stock (int): Minimum stock level
    """
    message = (
        f"🚨 LOW STOCK ALERT!\n"
        f"Product: {product_name}\n"
        f"Current Stock: {current_stock}\n"
        f"Minimum Stock: {minimum_stock}\n"
        f"Please create a purchase order immediately.\n"
        f"- Mama Eagle Inventory System"
    )
    
    try:
        # For now, we'll log the SMS message
        # In production, integrate with SMS service like Twilio, Arkesel, etc.
        logger.info(f"SMS Alert to {phone}: {message}")
        
        # TODO: Integrate with actual SMS service
        # Example for Twilio:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # client.messages.create(
        #     body=message,
        #     from_=settings.TWILIO_PHONE_NUMBER,
        #     to=phone
        # )
        
        # For Ghana, you might use Arkesel or similar service
        # import requests
        # response = requests.post('https://sms.arkesel.com/api/v2/sms/send', {
        #     'api_key': settings.ARKESEL_API_KEY,
        #     'to': phone,
        #     'message': message,
        #     'sender': 'MamaEagle'
        # })
        
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone}: {str(e)}")
        return False


def check_and_alert_low_stock():
    """
    Check all products for low stock and send alerts
    This function can be called by a scheduled task (cron job)
    """
    from .models import Product
    
    low_stock_products = Product.objects.filter(
        is_active=True
    ).select_related('company').prefetch_related('company__users')
    
    alert_count = 0
    
    for product in low_stock_products:
        if product.is_low_stock:
            product.send_low_stock_alert()
            alert_count += 1
            logger.info(f"Low stock alert sent for product: {product.name}")
    
    return alert_count


def update_inventory_from_invoice(invoice_item):
    """
    Update inventory when an invoice item is created or updated
    
    Args:
        invoice_item: InvoiceItem instance
    """
    from .models import Product, StockMovement, Warehouse
    
    try:
        # Find corresponding inventory product
        inventory_product = Product.objects.get(
            company=invoice_item.invoice.company,
            sku=invoice_item.product_sku
        )
        
        # Get or create a default warehouse
        warehouse, created = Warehouse.objects.get_or_create(
            company=invoice_item.invoice.company,
            code='MAIN',
            defaults={'name': 'Main Warehouse', 'is_active': True}
        )
        
        # Create stock movement for sale
        stock_movement = StockMovement.objects.create(
            company=invoice_item.invoice.company,
            product=inventory_product,
            warehouse=warehouse,
            movement_type='sale',
            quantity_change=-invoice_item.quantity,  # Negative for sale
            unit_cost=inventory_product.cost_price,
            total_cost=inventory_product.cost_price * abs(invoice_item.quantity),
            reference_number=invoice_item.invoice.invoice_number,
            notes=f"Sale via invoice {invoice_item.invoice.invoice_number}"
        )
        
        # Check if stock is now low and send alert
        if inventory_product.is_low_stock():
            inventory_product.send_low_stock_alert()
        
        logger.info(f"Updated inventory for {inventory_product.name}, new stock: {inventory_product.current_stock}")
        return True
        
    except Product.DoesNotExist:
        logger.warning(f"Product with SKU {invoice_item.product_sku} not found in inventory")
        return False
    except Exception as e:
        logger.error(f"Failed to update inventory: {str(e)}")
        return False