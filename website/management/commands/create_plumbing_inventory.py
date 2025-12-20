"""
Django management command to create comprehensive plumbing categories and products
Usage: python manage.py create_plumbing_inventory
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from website.models import ProductCategory, Product, ProductImage
from decimal import Decimal
import uuid


class Command(BaseCommand):
    help = 'Create plumbing categories and products for Mama Eagle Enterprise'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing products and categories before creating new ones',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing products and categories...')
            Product.objects.all().delete()
            ProductCategory.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared existing data'))

        self.stdout.write('Creating plumbing categories and products...')
        
        # Create categories and products
        self.create_categories()
        self.create_products()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {ProductCategory.objects.count()} categories '
                f'and {Product.objects.count()} products'
            )
        )

    def create_categories(self):
        """Create plumbing product categories"""
        categories_data = [
            {
                'name': 'Pipes & Fittings',
                'description': 'PVC, HDPE, steel pipes and various fittings for all plumbing needs',
                'subcategories': [
                    {'name': 'PVC Pipes', 'description': 'Durable PVC pipes for water supply and drainage'},
                    {'name': 'HDPE Pipes', 'description': 'High-density polyethylene pipes for underground applications'},
                    {'name': 'Steel Pipes', 'description': 'Galvanized and stainless steel pipes'},
                    {'name': 'Pipe Fittings', 'description': 'Elbows, tees, reducers, and connectors'},
                ]
            },
            {
                'name': 'Bathroom Fixtures',
                'description': 'Complete bathroom solutions including toilets, sinks, and accessories',
                'subcategories': [
                    {'name': 'Toilets & Bidets', 'description': 'Water closets, bidets, and toilet accessories'},
                    {'name': 'Bathroom Sinks', 'description': 'Washbasins, pedestals, and vanity units'},
                    {'name': 'Bathtubs & Showers', 'description': 'Bathtubs, shower trays, and enclosures'},
                    {'name': 'Bathroom Accessories', 'description': 'Towel rails, soap dispensers, mirrors'},
                ]
            },
            {
                'name': 'Kitchen Plumbing',
                'description': 'Kitchen sinks, faucets, and plumbing accessories',
                'subcategories': [
                    {'name': 'Kitchen Sinks', 'description': 'Stainless steel and ceramic kitchen sinks'},
                    {'name': 'Kitchen Faucets', 'description': 'Modern and traditional kitchen taps'},
                    {'name': 'Water Filters', 'description': 'Kitchen water filtration systems'},
                ]
            },
            {
                'name': 'Water Heaters',
                'description': 'Electric, gas, and solar water heating solutions',
                'subcategories': [
                    {'name': 'Electric Water Heaters', 'description': 'Instant and storage electric water heaters'},
                    {'name': 'Gas Water Heaters', 'description': 'LPG and natural gas water heaters'},
                    {'name': 'Solar Water Heaters', 'description': 'Eco-friendly solar water heating systems'},
                ]
            },
            {
                'name': 'Pumps & Motors',
                'description': 'Water pumps, pressure tanks, and motor accessories',
                'subcategories': [
                    {'name': 'Submersible Pumps', 'description': 'Borehole and well water pumps'},
                    {'name': 'Surface Pumps', 'description': 'Centrifugal and pressure pumps'},
                    {'name': 'Pressure Tanks', 'description': 'Water storage and pressure tanks'},
                ]
            },
            {
                'name': 'Tools & Equipment',
                'description': 'Professional plumbing tools and equipment',
                'subcategories': [
                    {'name': 'Pipe Cutting Tools', 'description': 'Pipe cutters, saws, and threading tools'},
                    {'name': 'Wrenches & Spanners', 'description': 'Pipe wrenches and adjustable spanners'},
                    {'name': 'Testing Equipment', 'description': 'Pressure testing and leak detection tools'},
                ]
            }
        ]

        for cat_data in categories_data:
            # Create main category
            main_cat, created = ProductCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'slug': slugify(cat_data['name']),
                    'description': cat_data['description'],
                    'is_active': True,
                    'sort_order': categories_data.index(cat_data) + 1
                }
            )
            
            if created:
                self.stdout.write(f'Created category: {main_cat.name}')

            # Create subcategories
            for i, subcat_data in enumerate(cat_data.get('subcategories', [])):
                subcat, created = ProductCategory.objects.get_or_create(
                    name=subcat_data['name'],
                    defaults={
                        'slug': slugify(subcat_data['name']),
                        'description': subcat_data['description'],
                        'parent': main_cat,
                        'is_active': True,
                        'sort_order': i + 1
                    }
                )
                
                if created:
                    self.stdout.write(f'  Created subcategory: {subcat.name}')

    def create_products(self):
        """Create plumbing products"""
        
        # Get categories for product assignment
        categories = {cat.name: cat for cat in ProductCategory.objects.all()}
        
        products_data = [
            # PVC Pipes
            {
                'name': 'PVC Pipe 20mm x 6m',
                'category': 'PVC Pipes',
                'price': Decimal('15.50'),
                'compare_at_price': Decimal('18.00'),
                'description': 'High-quality PVC pipe suitable for cold water supply and waste applications. Lightweight and easy to install.',
                'short_description': '20mm diameter PVC pipe, 6-meter length',
                'stock_quantity': 150,
                'sku': 'PVC-20-6M',
                'weight': Decimal('1.2'),
                'dimensions': '20mm x 6000mm',
                'is_featured': True
            },
            {
                'name': 'PVC Pipe 25mm x 6m',
                'category': 'PVC Pipes',
                'price': Decimal('22.50'),
                'compare_at_price': Decimal('25.00'),
                'description': 'Durable PVC pipe for residential and commercial plumbing installations.',
                'short_description': '25mm diameter PVC pipe, 6-meter length',
                'stock_quantity': 120,
                'sku': 'PVC-25-6M',
                'weight': Decimal('1.8'),
                'dimensions': '25mm x 6000mm'
            },
            {
                'name': 'PVC Pipe 32mm x 6m',
                'category': 'PVC Pipes',
                'price': Decimal('35.00'),
                'description': 'Heavy-duty PVC pipe for main water supply lines and drainage systems.',
                'short_description': '32mm diameter PVC pipe, 6-meter length',
                'stock_quantity': 80,
                'sku': 'PVC-32-6M',
                'weight': Decimal('2.5'),
                'dimensions': '32mm x 6000mm'
            },
            
            # Pipe Fittings
            {
                'name': 'PVC Elbow 90° - 20mm',
                'category': 'Pipe Fittings',
                'price': Decimal('3.50'),
                'description': 'Standard 90-degree PVC elbow fitting for 20mm pipes.',
                'short_description': '90° elbow fitting for 20mm PVC pipes',
                'stock_quantity': 200,
                'sku': 'ELBOW-90-20',
                'weight': Decimal('0.05'),
                'is_featured': True
            },
            {
                'name': 'PVC Tee Joint - 25mm',
                'category': 'Pipe Fittings',
                'price': Decimal('5.75'),
                'description': 'T-junction fitting for branching 25mm PVC pipes.',
                'short_description': 'Tee joint fitting for 25mm PVC pipes',
                'stock_quantity': 150,
                'sku': 'TEE-25',
                'weight': Decimal('0.08')
            },
            {
                'name': 'PVC Reducer 32mm to 25mm',
                'category': 'Pipe Fittings',
                'price': Decimal('4.25'),
                'description': 'Reducer fitting to connect 32mm pipe to 25mm pipe.',
                'short_description': 'Reducer from 32mm to 25mm',
                'stock_quantity': 100,
                'sku': 'REDUCER-32-25',
                'weight': Decimal('0.06')
            },
            
            # Toilets & Bidets
            {
                'name': 'Ceramic Wall-Hung Toilet',
                'category': 'Toilets & Bidets',
                'price': Decimal('450.00'),
                'compare_at_price': Decimal('520.00'),
                'description': 'Modern wall-mounted toilet with soft-close seat and dual-flush mechanism.',
                'short_description': 'Wall-hung toilet with dual flush',
                'stock_quantity': 25,
                'sku': 'WC-WALL-001',
                'weight': Decimal('35.0'),
                'dimensions': '540mm x 360mm x 350mm',
                'is_featured': True
            },
            {
                'name': 'Close-Coupled Toilet Suite',
                'category': 'Toilets & Bidets',
                'price': Decimal('320.00'),
                'description': 'Traditional close-coupled toilet with ceramic cistern and standard seat.',
                'short_description': 'Close-coupled toilet with cistern',
                'stock_quantity': 15,
                'sku': 'WC-CC-001',
                'weight': Decimal('42.0'),
                'dimensions': '665mm x 360mm x 780mm'
            },
            
            # Kitchen Sinks
            {
                'name': 'Stainless Steel Kitchen Sink - Single Bowl',
                'category': 'Kitchen Sinks',
                'price': Decimal('180.00'),
                'compare_at_price': Decimal('210.00'),
                'description': '304-grade stainless steel single bowl kitchen sink with drainer.',
                'short_description': 'Single bowl stainless steel sink',
                'stock_quantity': 30,
                'sku': 'SINK-SS-SB',
                'weight': Decimal('8.5'),
                'dimensions': '860mm x 500mm x 180mm',
                'is_featured': True
            },
            {
                'name': 'Stainless Steel Kitchen Sink - Double Bowl',
                'category': 'Kitchen Sinks',
                'price': Decimal('275.00'),
                'description': '304-grade stainless steel double bowl kitchen sink with central drainer.',
                'short_description': 'Double bowl stainless steel sink',
                'stock_quantity': 20,
                'sku': 'SINK-SS-DB',
                'weight': Decimal('12.0'),
                'dimensions': '1160mm x 500mm x 180mm'
            },
            
            # Electric Water Heaters
            {
                'name': 'Electric Instant Water Heater 12kW',
                'category': 'Electric Water Heaters',
                'price': Decimal('650.00'),
                'compare_at_price': Decimal('750.00'),
                'description': 'High-efficiency instant electric water heater with digital temperature control.',
                'short_description': '12kW instant electric water heater',
                'stock_quantity': 12,
                'sku': 'WH-ELE-12K',
                'weight': Decimal('8.5'),
                'dimensions': '320mm x 520mm x 110mm',
                'is_featured': True
            },
            {
                'name': 'Electric Storage Water Heater 50L',
                'category': 'Electric Water Heaters',
                'price': Decimal('420.00'),
                'description': '50-liter electric storage water heater with insulation and thermostat.',
                'short_description': '50L electric storage water heater',
                'stock_quantity': 18,
                'sku': 'WH-STO-50L',
                'weight': Decimal('25.0'),
                'dimensions': '440mm x 440mm x 500mm'
            },
            
            # Submersible Pumps
            {
                'name': 'Submersible Water Pump 1HP',
                'category': 'Submersible Pumps',
                'price': Decimal('850.00'),
                'description': 'Heavy-duty 1HP submersible pump for borehole and well applications.',
                'short_description': '1HP submersible water pump',
                'stock_quantity': 8,
                'sku': 'PUMP-SUB-1HP',
                'weight': Decimal('15.0'),
                'dimensions': '180mm x 180mm x 800mm',
                'is_featured': True
            },
            {
                'name': 'Submersible Water Pump 0.5HP',
                'category': 'Submersible Pumps',
                'price': Decimal('580.00'),
                'description': 'Reliable 0.5HP submersible pump for residential water supply.',
                'short_description': '0.5HP submersible water pump',
                'stock_quantity': 12,
                'sku': 'PUMP-SUB-05HP',
                'weight': Decimal('12.0'),
                'dimensions': '160mm x 160mm x 700mm'
            },
            
            # Pipe Cutting Tools
            {
                'name': 'Professional Pipe Cutter 15-67mm',
                'category': 'Pipe Cutting Tools',
                'price': Decimal('125.00'),
                'description': 'Professional-grade pipe cutter for copper and plastic pipes.',
                'short_description': 'Pipe cutter for 15-67mm pipes',
                'stock_quantity': 25,
                'sku': 'TOOL-CUT-67',
                'weight': Decimal('1.2'),
                'is_featured': True
            },
            {
                'name': 'PVC Pipe Saw 300mm',
                'category': 'Pipe Cutting Tools',
                'price': Decimal('35.00'),
                'description': 'Sharp-toothed saw specifically designed for cutting PVC pipes.',
                'short_description': '300mm PVC pipe saw',
                'stock_quantity': 40,
                'sku': 'TOOL-SAW-300',
                'weight': Decimal('0.8')
            }
        ]

        for product_data in products_data:
            category_name = product_data.pop('category')
            category = categories.get(category_name)
            
            if not category:
                self.stdout.write(self.style.WARNING(f'Category not found: {category_name}'))
                continue

            # Generate unique SKU if not provided or if it already exists
            sku = product_data.get('sku', str(uuid.uuid4())[:8].upper())
            counter = 1
            original_sku = sku
            while Product.objects.filter(sku=sku).exists():
                sku = f"{original_sku}-{counter}"
                counter += 1

            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    **product_data,
                    'slug': slugify(product_data['name']),
                    'category': category,
                    'is_active': True,
                    'track_inventory': True,
                    'meta_title': product_data['name'][:60],
                    'meta_description': product_data['short_description'][:160]
                }
            )
            
            if created:
                self.stdout.write(f'Created product: {product.name}')
            else:
                self.stdout.write(f'Product already exists: {product.name}')