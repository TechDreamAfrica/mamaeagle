from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from invoicing.models import Customer, Product, Invoice, InvoiceItem
from datetime import date, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample invoicing data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username to create data for',
            required=True
        )

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options['user'])
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User {options["user"]} does not exist')
            )
            return

        # Create sample customers
        customers_data = [
            {
                'name': 'Acme Corporation',
                'email': 'billing@acme.com',
                'phone': '+1-555-0101',
                'address': '123 Business Ave\nSuite 100\nNew York, NY 10001'
            },
            {
                'name': 'Tech Solutions LLC',
                'email': 'accounts@techsolutions.com',
                'phone': '+1-555-0102',
                'address': '456 Innovation Dr\nSan Francisco, CA 94105'
            },
            {
                'name': 'Global Enterprises Inc',
                'email': 'finance@globalent.com',
                'phone': '+1-555-0103',
                'address': '789 Corporate Blvd\nChicago, IL 60601'
            }
        ]

        customers = []
        for customer_data in customers_data:
            customer, created = Customer.objects.get_or_create(
                user=user,
                name=customer_data['name'],
                defaults=customer_data
            )
            customers.append(customer)
            if created:
                self.stdout.write(f'Created customer: {customer.name}')

        # Create sample products
        products_data = [
            {
                'name': 'Web Development Service',
                'description': 'Custom web application development',
                'unit_price': 150.00,
                'tax_rate': 8.25
            },
            {
                'name': 'SEO Consultation',
                'description': 'Search engine optimization consultation',
                'unit_price': 125.00,
                'tax_rate': 8.25
            },
            {
                'name': 'Graphic Design',
                'description': 'Logo and brand design services',
                'unit_price': 100.00,
                'tax_rate': 8.25
            },
            {
                'name': 'Technical Support',
                'description': 'Monthly technical support package',
                'unit_price': 75.00,
                'tax_rate': 8.25
            }
        ]

        products = []
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                user=user,
                name=product_data['name'],
                defaults=product_data
            )
            products.append(product)
            if created:
                self.stdout.write(f'Created product: {product.name}')

        # Create sample invoices
        statuses = ['draft', 'sent', 'paid']
        
        for i in range(5):
            customer = random.choice(customers)
            status = random.choice(statuses)
            
            # Generate invoice number
            invoice_number = f"INV-{1000 + i:05d}"
            
            # Create dates
            created_date = date.today() - timedelta(days=random.randint(1, 30))
            due_date = created_date + timedelta(days=30)
            
            invoice = Invoice.objects.create(
                user=user,
                customer=customer,
                invoice_number=invoice_number,
                date_created=created_date,
                date_due=due_date,
                status=status,
                notes=f'Thank you for your business, {customer.name}!',
                terms='Payment is due within 30 days of invoice date.',
                total_amount=0  # Will be calculated from line items
            )

            # Add 1-4 random line items
            num_items = random.randint(1, 4)
            subtotal = 0
            tax_total = 0

            for j in range(num_items):
                product = random.choice(products)
                quantity = random.randint(1, 5)
                
                item = InvoiceItem.objects.create(
                    invoice=invoice,
                    product=product,
                    description=product.description,
                    quantity=quantity,
                    unit_price=product.unit_price,
                    tax_rate=product.tax_rate
                )
                
                line_total = item.total
                line_tax = line_total * (item.tax_rate / 100)
                subtotal += line_total
                tax_total += line_tax

            # Update invoice totals
            invoice.subtotal = subtotal
            invoice.tax_amount = tax_total
            invoice.total_amount = subtotal + tax_total
            invoice.save()

            self.stdout.write(f'Created invoice: {invoice.invoice_number} for {customer.name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created sample data for user: {user.username}'
            )
        )
