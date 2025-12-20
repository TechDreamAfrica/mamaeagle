"""
Management command to update categories to plumbing-related ones
"""
from django.core.management.base import BaseCommand
from website.models import ProductCategory


class Command(BaseCommand):
    help = 'Update categories to plumbing-related categories'

    def handle(self, *args, **options):
        self.stdout.write('Updating categories to plumbing-related categories...')
        
        # Delete existing categories
        ProductCategory.objects.all().delete()
        
        # Create plumbing-related categories
        plumbing_categories = [
            {
                'name': 'Pipes & Fittings',
                'slug': 'pipes-fittings',
                'description': 'PVC, copper, steel pipes, elbows, joints, couplings, and all pipe fittings',
                'is_active': True,
                'parent': None
            },
            {
                'name': 'Bathroom Fixtures',
                'slug': 'bathroom-fixtures', 
                'description': 'Toilets, sinks, bathtubs, shower heads, faucets, and bathroom accessories',
                'is_active': True,
                'parent': None
            },
            {
                'name': 'Kitchen Plumbing',
                'slug': 'kitchen-plumbing',
                'description': 'Kitchen sinks, garbage disposals, kitchen faucets, and water filtration systems',
                'is_active': True,
                'parent': None
            },
            {
                'name': 'Water Heaters',
                'slug': 'water-heaters',
                'description': 'Electric, gas, solar water heaters, boilers, and water heating accessories',
                'is_active': True,
                'parent': None
            },
            {
                'name': 'Pumps & Motors',
                'slug': 'pumps-motors',
                'description': 'Water pumps, submersible pumps, pressure pumps, and motor accessories',
                'is_active': True,
                'parent': None
            },
            {
                'name': 'Tools & Equipment',
                'slug': 'tools-equipment',
                'description': 'Plumbing tools, pipe cutters, wrenches, drain snakes, and professional equipment',
                'is_active': True,
                'parent': None
            },
            {
                'name': 'Drainage Systems',
                'slug': 'drainage-systems',
                'description': 'Drain pipes, manholes, septic tanks, and drainage accessories',
                'is_active': True,
                'parent': None
            },
            {
                'name': 'Water Storage',
                'slug': 'water-storage',
                'description': 'Water tanks, reservoirs, storage containers, and related accessories',
                'is_active': True,
                'parent': None
            }
        ]
        
        for cat_data in plumbing_categories:
            category, created = ProductCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
            else:
                # Update existing category
                for key, value in cat_data.items():
                    setattr(category, key, value)
                category.save()
                self.stdout.write(self.style.WARNING(f'Updated category: {category.name}'))
        
        self.stdout.write(self.style.SUCCESS('Successfully updated all plumbing categories!'))