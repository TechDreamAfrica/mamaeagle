from django.core.management.base import BaseCommand
from website.models import ProductCategory


class Command(BaseCommand):
    help = 'Populate the database with multi-purpose e-commerce categories'

    def handle(self, *args, **options):
        categories = [
            {
                'name': 'Electronics',
                'slug': 'electronics',
                'description': 'Smartphones, laptops, tablets, cameras, and all electronic gadgets',
                'sort_order': 1
            },
            {
                'name': 'Fashion',
                'slug': 'fashion',
                'description': 'Clothing, shoes, accessories for men, women, and children',
                'sort_order': 2
            },
            {
                'name': 'Home & Garden',
                'slug': 'home-garden',
                'description': 'Furniture, home decor, gardening tools, kitchen appliances',
                'sort_order': 3
            },
            {
                'name': 'Sports & Outdoors',
                'slug': 'sports-outdoors',
                'description': 'Sporting goods, fitness equipment, outdoor gear, recreational items',
                'sort_order': 4
            },
            {
                'name': 'Beauty & Health',
                'slug': 'beauty-health',
                'description': 'Cosmetics, skincare, personal care, health supplements',
                'sort_order': 5
            },
            {
                'name': 'Books & Media',
                'slug': 'books-media',
                'description': 'Books, magazines, movies, music, educational materials',
                'sort_order': 6
            },
            {
                'name': 'Automotive',
                'slug': 'automotive',
                'description': 'Car parts, accessories, tools, motor oil, car care products',
                'sort_order': 7
            },
            {
                'name': 'Toys & Games',
                'slug': 'toys-games',
                'description': 'Toys for all ages, board games, video games, educational toys',
                'sort_order': 8
            },
            {
                'name': 'Kitchen & Dining',
                'slug': 'kitchen-dining',
                'description': 'Cookware, utensils, dining sets, kitchen appliances',
                'sort_order': 9
            },
            {
                'name': 'Baby & Kids',
                'slug': 'baby-kids',
                'description': 'Baby gear, kids clothing, strollers, toys, child safety products',
                'sort_order': 10
            },
            {
                'name': 'Office Supplies',
                'slug': 'office-supplies',
                'description': 'Stationery, office furniture, business equipment, desk accessories',
                'sort_order': 11
            },
            {
                'name': 'Pet Supplies',
                'slug': 'pet-supplies',
                'description': 'Pet food, toys, grooming supplies, pet accessories',
                'sort_order': 12
            }
        ]

        created_count = 0
        for category_data in categories:
            category, created = ProductCategory.objects.get_or_create(
                slug=category_data['slug'],
                defaults=category_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {category.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Category already exists: {category.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new categories')
        )