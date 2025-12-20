from django.core.management.base import BaseCommand
from django.utils.text import slugify
from website.models import ProductCategory, Product, ProductImage
from accounts.models import Branch, User
from decimal import Decimal


class Command(BaseCommand):
    help = 'Setup initial data for Mama Eagle Enterprise'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up initial data for Mama Eagle Enterprise...'))
        
        # Create default branches
        self.create_branches()
        
        # Create product categories
        self.create_categories()
        
        # Create sample products
        self.create_products()
        
        self.stdout.write(self.style.SUCCESS('Initial data setup completed successfully!'))

    def create_branches(self):
        """Create default branches"""
        branches_data = [
            {
                'name': 'Head Office - Accra',
                'code': 'HQ001',
                'description': 'Main head office located in Accra',
                'city': 'Accra',
                'state': 'Greater Accra',
                'country': 'Ghana',
                'phone': '+233 XXX XXX XXX',
                'email': 'accra@mamaeagle.com',
                'manager_name': 'Head Office Manager',
                'is_head_office': True,
            },
            {
                'name': 'Kumasi Branch',
                'code': 'KSI001',
                'description': 'Kumasi regional branch office',
                'city': 'Kumasi',
                'state': 'Ashanti',
                'country': 'Ghana',
                'phone': '+233 XXX XXX XXX',
                'email': 'kumasi@mamaeagle.com',
                'manager_name': 'Kumasi Branch Manager',
                'is_head_office': False,
            },
            {
                'name': 'Takoradi Branch',
                'code': 'TAK001',
                'description': 'Western region branch office',
                'city': 'Takoradi',
                'state': 'Western',
                'country': 'Ghana',
                'phone': '+233 XXX XXX XXX',
                'email': 'takoradi@mamaeagle.com',
                'manager_name': 'Takoradi Branch Manager',
                'is_head_office': False,
            },
        ]
        
        for branch_data in branches_data:
            branch, created = Branch.objects.get_or_create(
                code=branch_data['code'],
                defaults=branch_data
            )
            if created:
                self.stdout.write(f'Created branch: {branch.name}')
            else:
                self.stdout.write(f'Branch already exists: {branch.name}')

    def create_categories(self):
        """Create plumbing product categories"""
        categories_data = [
            {
                'name': 'Pipes & Fittings',
                'description': 'PVC, copper, and steel pipes with joints and fittings',
            },
            {
                'name': 'Bathroom Fixtures',
                'description': 'Toilets, sinks, bathtubs, and shower fixtures',
            },
            {
                'name': 'Kitchen Plumbing',
                'description': 'Kitchen sinks, faucets, and disposal systems',
            },
            {
                'name': 'Water Heaters',
                'description': 'Electric, gas, and solar water heating systems',
            },
            {
                'name': 'Pumps & Motors',
                'description': 'Water pumps, pressure tanks, and motor systems',
            },
            {
                'name': 'Tools & Equipment',
                'description': 'Professional plumbing tools and equipment',
            },
            {
                'name': 'Valves & Controls',
                'description': 'Shut-off valves, ball valves, and flow controllers',
            },
            {
                'name': 'Drainage Systems',
                'description': 'Drain pipes, manholes, and sewage systems',
            },
        ]
        
        for cat_data in categories_data:
            category, created = ProductCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'slug': slugify(cat_data['name']),
                    'description': cat_data['description'],
                }
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')

    def create_products(self):
        """Create plumbing products"""
        pipes_fittings = ProductCategory.objects.get(name='Pipes & Fittings')
        bathroom = ProductCategory.objects.get(name='Bathroom Fixtures')
        kitchen = ProductCategory.objects.get(name='Kitchen Plumbing')
        water_heaters = ProductCategory.objects.get(name='Water Heaters')
        pumps = ProductCategory.objects.get(name='Pumps & Motors')
        tools = ProductCategory.objects.get(name='Tools & Equipment')
        valves = ProductCategory.objects.get(name='Valves & Controls')
        
        products_data = [
            {
                'name': 'PVC Pipe 4" x 6m',
                'category': pipes_fittings,
                'price': Decimal('45.00'),
                'compare_at_price': Decimal('55.00'),
                'description': 'High-quality PVC pipe suitable for water supply and drainage systems. Durable and corrosion-resistant.',
                'short_description': 'PVC Pipe 4" x 6m - Water supply grade',
                'sku': 'PVC-4IN-6M',
                'stock_quantity': 150,
                'is_featured': True,
            },
            {
                'name': 'Water Closet - Modern Design',
                'category': bathroom,
                'price': Decimal('380.00'),
                'compare_at_price': Decimal('450.00'),
                'description': 'Modern water closet with dual flush system. Water-efficient and stylish design for contemporary bathrooms.',
                'short_description': 'Modern Water Closet - Dual flush system',
                'sku': 'WC-MOD-001',
                'stock_quantity': 25,
                'is_featured': True,
            },
            {
                'name': 'Kitchen Sink - Stainless Steel',
                'category': kitchen,
                'price': Decimal('220.00'),
                'description': 'Premium stainless steel kitchen sink with double bowl design. Includes drain fittings.',
                'short_description': 'Stainless Steel Kitchen Sink - Double bowl',
                'sku': 'KS-SS-DBL',
                'stock_quantity': 40,
                'is_featured': True,
            },
            {
                'name': 'Electric Water Heater 50L',
                'category': water_heaters,
                'price': Decimal('850.00'),
                'compare_at_price': Decimal('950.00'),
                'description': 'Energy-efficient 50-liter electric water heater with temperature control and safety features.',
                'short_description': 'Electric Water Heater 50L - Energy efficient',
                'sku': 'WH-ELC-50L',
                'stock_quantity': 15,
                'is_featured': True,
            },
            {
                'name': 'Submersible Water Pump 1HP',
                'category': pumps,
                'price': Decimal('1200.00'),
                'description': 'Heavy-duty submersible water pump suitable for boreholes and deep wells. 1HP motor with auto-start.',
                'short_description': 'Submersible Water Pump 1HP - Auto-start',
                'sku': 'PUMP-SUB-1HP',
                'stock_quantity': 12,
                'is_featured': False,
            },
            {
                'name': 'Pipe Wrench Set Professional',
                'category': tools,
                'price': Decimal('120.00'),
                'compare_at_price': Decimal('150.00'),
                'description': 'Professional pipe wrench set with multiple sizes. Chrome vanadium steel construction.',
                'short_description': 'Professional Pipe Wrench Set - Multi-size',
                'sku': 'TOOL-WRN-SET',
                'stock_quantity': 30,
                'is_featured': False,
            },
            {
                'name': 'Ball Valve 2" Brass',
                'category': valves,
                'price': Decimal('65.00'),
                'description': 'Heavy-duty brass ball valve with full port design. Suitable for high-pressure applications.',
                'short_description': 'Brass Ball Valve 2" - Heavy-duty',
                'sku': 'VALVE-BALL-2IN',
                'stock_quantity': 80,
                'is_featured': True,
            },
            {
                'name': 'Shower Head - Rain Style',
                'category': bathroom,
                'price': Decimal('95.00'),
                'compare_at_price': Decimal('120.00'),
                'description': 'Modern rain-style shower head with adjustable flow settings. Chrome finish.',
                'short_description': 'Rain Style Shower Head - Adjustable flow',
                'sku': 'SH-RAIN-CHR',
                'stock_quantity': 60,
                'is_featured': True,
            },
            {
                'name': 'PVC Elbow Joint 4"',
                'category': pipes_fittings,
                'price': Decimal('12.00'),
                'description': '90-degree PVC elbow joint for 4-inch pipes. High-quality molded construction.',
                'short_description': 'PVC Elbow Joint 4" - 90 degree',
                'sku': 'PVC-ELB-4IN',
                'stock_quantity': 200,
                'is_featured': False,
            },
            {
                'name': 'Basin Tap - Single Handle',
                'category': bathroom,
                'price': Decimal('75.00'),
                'description': 'Single handle basin tap with ceramic cartridge. Chrome plated finish.',
                'short_description': 'Single Handle Basin Tap - Chrome plated',
                'sku': 'TAP-BAS-SNG',
                'stock_quantity': 45,
                'is_featured': False,
            },
        ]
        
        for prod_data in products_data:
            product, created = Product.objects.get_or_create(
                sku=prod_data['sku'],
                defaults={
                    'name': prod_data['name'],
                    'slug': slugify(prod_data['name']),
                    'category': prod_data['category'],
                    'price': prod_data['price'],
                    'compare_at_price': prod_data.get('compare_at_price'),
                    'description': prod_data['description'],
                    'short_description': prod_data['short_description'],
                    'stock_quantity': prod_data['stock_quantity'],
                    'is_featured': prod_data['is_featured'],
                }
            )
            if created:
                self.stdout.write(f'Created product: {product.name}')