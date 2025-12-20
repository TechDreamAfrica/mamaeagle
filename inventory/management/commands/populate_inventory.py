"""
Management command to populate inventory with sample products
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import Company
from inventory.models import Category, Product, Supplier, Warehouse, StockMovement
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'Populate inventory with sample products for testing and demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing inventory data before populating',
        )
        parser.add_argument(
            '--company',
            type=str,
            help='Company ID to populate inventory for (optional)',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing inventory data...')
            Product.objects.all().delete()
            Category.objects.all().delete()
            Supplier.objects.all().delete()
            StockMovement.objects.all().delete()

        # Get company
        company = None
        if options['company']:
            try:
                company = Company.objects.get(id=options['company'])
            except Company.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Company with ID {options["company"]} not found'))
                return
        else:
            company = Company.objects.first()
            if not company:
                self.stdout.write(self.style.ERROR('No companies found. Create a company first.'))
                return

        self.stdout.write(f'Populating inventory for company: {company.name}')

        with transaction.atomic():
            # Create warehouse
            warehouse, created = Warehouse.objects.get_or_create(
                code='MAIN',
                defaults={
                    'name': 'Main Warehouse',
                    'address': 'Main warehouse location, Accra',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created warehouse: {warehouse.name}')

            # Create suppliers
            suppliers_data = [
                {
                    'name': 'Plumbing Supplies Ghana Ltd',
                    'contact_person': 'Kwame Asante',
                    'email': 'kwame@plumbingghana.com',
                    'phone': '+233244567890',
                    'payment_terms': 'Net 30',
                    'lead_time_days': 7,
                    'rating': 5
                },
                {
                    'name': 'Industrial Hardware Co.',
                    'contact_person': 'Ama Osei',
                    'email': 'ama@industrialhw.com',
                    'phone': '+233201234567',
                    'payment_terms': 'Net 15',
                    'lead_time_days': 5,
                    'rating': 4
                },
                {
                    'name': 'Building Materials Direct',
                    'contact_person': 'Kojo Mensah',
                    'email': 'kojo@buildingmaterials.com',
                    'phone': '+233275678901',
                    'payment_terms': 'COD',
                    'lead_time_days': 3,
                    'rating': 4
                }
            ]

            suppliers = []
            for supplier_data in suppliers_data:
                supplier, created = Supplier.objects.get_or_create(
                    company=company,
                    name=supplier_data['name'],
                    defaults=supplier_data
                )
                suppliers.append(supplier)
                if created:
                    self.stdout.write(f'Created supplier: {supplier.name}')

            # Create categories
            categories_data = [
                {'name': 'Plumbing Pipes', 'description': 'Various types of plumbing pipes'},
                {'name': 'Pipe Fittings', 'description': 'Connectors and fittings for pipes'},
                {'name': 'Valves & Taps', 'description': 'Water control valves and taps'},
                {'name': 'Bathroom Fixtures', 'description': 'Toilets, sinks, and bathroom accessories'},
                {'name': 'Tools & Equipment', 'description': 'Plumbing tools and equipment'},
                {'name': 'Adhesives & Sealants', 'description': 'PVC cement, thread sealants, etc.'}
            ]

            categories = {}
            for cat_data in categories_data:
                category, created = Category.objects.get_or_create(
                    company=company,
                    name=cat_data['name'],
                    defaults=cat_data
                )
                categories[cat_data['name']] = category
                if created:
                    self.stdout.write(f'Created category: {category.name}')

            # Create products
            products_data = [
                {
                    'sku': 'PVC-PIPE-25MM',
                    'name': 'PVC Pipe 25mm (1 inch)',
                    'description': 'High-quality PVC pipe for plumbing installations',
                    'category': 'Plumbing Pipes',
                    'cost_price': Decimal('12.50'),
                    'selling_price': Decimal('18.75'),
                    'minimum_stock_level': 50,
                    'reorder_point': 25,
                    'reorder_quantity': 100,
                    'unit_type': 'meter'
                },
                {
                    'sku': 'PVC-PIPE-50MM',
                    'name': 'PVC Pipe 50mm (2 inch)',
                    'description': 'Heavy-duty PVC pipe for larger installations',
                    'category': 'Plumbing Pipes',
                    'cost_price': Decimal('25.00'),
                    'selling_price': Decimal('37.50'),
                    'minimum_stock_level': 30,
                    'reorder_point': 15,
                    'reorder_quantity': 50,
                    'unit_type': 'meter'
                },
                {
                    'sku': 'ELBOW-25MM-90',
                    'name': '90° Elbow 25mm',
                    'description': '90-degree elbow fitting for 25mm pipes',
                    'category': 'Pipe Fittings',
                    'cost_price': Decimal('2.50'),
                    'selling_price': Decimal('4.00'),
                    'minimum_stock_level': 100,
                    'reorder_point': 50,
                    'reorder_quantity': 200,
                    'unit_type': 'piece'
                },
                {
                    'sku': 'TEE-25MM',
                    'name': 'T-Junction 25mm',
                    'description': 'T-junction fitting for 25mm pipes',
                    'category': 'Pipe Fittings',
                    'cost_price': Decimal('3.50'),
                    'selling_price': Decimal('5.25'),
                    'minimum_stock_level': 75,
                    'reorder_point': 40,
                    'reorder_quantity': 150,
                    'unit_type': 'piece'
                },
                {
                    'sku': 'BALL-VALVE-25MM',
                    'name': 'Ball Valve 25mm',
                    'description': 'High-quality ball valve for water control',
                    'category': 'Valves & Taps',
                    'cost_price': Decimal('15.00'),
                    'selling_price': Decimal('22.50'),
                    'minimum_stock_level': 20,
                    'reorder_point': 10,
                    'reorder_quantity': 40,
                    'unit_type': 'piece'
                },
                {
                    'sku': 'TOILET-SEAT-STD',
                    'name': 'Standard Toilet Seat',
                    'description': 'Durable plastic toilet seat with fittings',
                    'category': 'Bathroom Fixtures',
                    'cost_price': Decimal('35.00'),
                    'selling_price': Decimal('52.50'),
                    'minimum_stock_level': 10,
                    'reorder_point': 5,
                    'reorder_quantity': 20,
                    'unit_type': 'piece'
                },
                {
                    'sku': 'PIPE-WRENCH-12',
                    'name': 'Pipe Wrench 12 inch',
                    'description': 'Heavy-duty pipe wrench for plumbing work',
                    'category': 'Tools & Equipment',
                    'cost_price': Decimal('45.00'),
                    'selling_price': Decimal('67.50'),
                    'minimum_stock_level': 5,
                    'reorder_point': 3,
                    'reorder_quantity': 10,
                    'unit_type': 'piece'
                },
                {
                    'sku': 'PVC-CEMENT-250ML',
                    'name': 'PVC Cement 250ml',
                    'description': 'High-strength PVC pipe cement',
                    'category': 'Adhesives & Sealants',
                    'cost_price': Decimal('8.50'),
                    'selling_price': Decimal('12.75'),
                    'minimum_stock_level': 25,
                    'reorder_point': 15,
                    'reorder_quantity': 50,
                    'unit_type': 'bottle'
                }
            ]

            products_created = 0
            for product_data in products_data:
                category = categories.get(product_data.pop('category'))
                
                product, created = Product.objects.get_or_create(
                    company=company,
                    sku=product_data['sku'],
                    defaults={
                        **product_data,
                        'category': category,
                        'product_type': 'physical',
                        'is_active': True
                    }
                )
                
                if created:
                    products_created += 1
                    self.stdout.write(f'Created product: {product.name}')
                    
                    # Add initial stock
                    initial_stock = random.randint(
                        product.minimum_stock_level * 2,
                        product.maximum_stock_level
                    )
                    
                    StockMovement.objects.create(
                        company=company,
                        product=product,
                        warehouse=warehouse,
                        movement_type='initial',
                        quantity_change=initial_stock,
                        unit_cost=product.cost_price,
                        total_cost=product.cost_price * initial_stock,
                        reference_number='INIT-001',
                        notes='Initial inventory setup'
                    )
                    
                    self.stdout.write(f'  Added initial stock: {initial_stock} units')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated inventory with {products_created} products for {company.name}'
            )
        )