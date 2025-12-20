from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from expenses.models import ExpenseCategory, Vendor

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample data for expense management'

    def handle(self, *args, **options):
        # Get or create a superuser
        try:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.create_superuser(
                    username='admin',
                    email='admin@accuflow.com',
                    password='admin123'
                )
                self.stdout.write(f'Created superuser: {user.username}')
        except Exception as e:
            self.stdout.write(f'Error creating user: {e}')
            return

        # Create sample categories
        categories = [
            {'name': 'Office Supplies', 'description': 'Pens, paper, office equipment', 'color': '#3B82F6', 'is_tax_deductible': True},
            {'name': 'Travel', 'description': 'Business travel expenses', 'color': '#10B981', 'is_tax_deductible': True},
            {'name': 'Meals & Entertainment', 'description': 'Business meals and entertainment', 'color': '#F59E0B', 'is_tax_deductible': True},
            {'name': 'Software & Subscriptions', 'description': 'Software licenses and subscriptions', 'color': '#8B5CF6', 'is_tax_deductible': True},
            {'name': 'Marketing & Advertising', 'description': 'Marketing campaigns and ads', 'color': '#EF4444', 'is_tax_deductible': True},
            {'name': 'Equipment & Hardware', 'description': 'Computer equipment and hardware', 'color': '#6B7280', 'is_tax_deductible': True},
            {'name': 'Professional Services', 'description': 'Legal, consulting, and professional services', 'color': '#14B8A6', 'is_tax_deductible': True},
            {'name': 'Utilities', 'description': 'Phone, internet, electricity', 'color': '#F97316', 'is_tax_deductible': True},
        ]

        for cat_data in categories:
            category, created = ExpenseCategory.objects.get_or_create(
                user=user,
                name=cat_data['name'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')

        # Create sample vendors
        vendors = [
            {
                'name': 'Amazon Business',
                'email': 'business@amazon.com',
                'website': 'https://business.amazon.com',
                'city': 'Seattle',
                'state': 'WA',
                'country': 'United States',
                'payment_terms': 'Net 30'
            },
            {
                'name': 'Staples',
                'email': 'orders@staples.com',
                'website': 'https://staples.com',
                'city': 'Framingham',
                'state': 'MA',
                'country': 'United States',
                'payment_terms': 'Net 15'
            },
            {
                'name': 'FedEx',
                'email': 'business@fedex.com',
                'website': 'https://fedex.com',
                'city': 'Memphis',
                'state': 'TN',
                'country': 'United States',
                'payment_terms': 'COD'
            },
            {
                'name': 'Microsoft',
                'email': 'licensing@microsoft.com',
                'website': 'https://microsoft.com',
                'city': 'Redmond',
                'state': 'WA',
                'country': 'United States',
                'payment_terms': 'Net 30'
            },
            {
                'name': 'Google Workspace',
                'email': 'support@google.com',
                'website': 'https://workspace.google.com',
                'city': 'Mountain View',
                'state': 'CA',
                'country': 'United States',
                'payment_terms': 'Monthly'
            }
        ]

        for vendor_data in vendors:
            vendor, created = Vendor.objects.get_or_create(
                user=user,
                name=vendor_data['name'],
                defaults=vendor_data
            )
            if created:
                self.stdout.write(f'Created vendor: {vendor.name}')

        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
