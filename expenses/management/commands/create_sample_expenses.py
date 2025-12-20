from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from expenses.models import Expense, ExpenseCategory, Vendor
from decimal import Decimal
from datetime import date, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates sample expense data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID to create expenses for'
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with ID {user_id} does not exist')
                )
                return
        else:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.first()
            
            if not user:
                self.stdout.write(
                    self.style.ERROR('No users found in the database')
                )
                return

        # Create sample categories
        categories_data = [
            {'name': 'Office Supplies', 'description': 'Pens, paper, etc.', 'color': '#8B5CF6'},
            {'name': 'Travel', 'description': 'Business travel expenses', 'color': '#3B82F6'},
            {'name': 'Meals & Entertainment', 'description': 'Business meals', 'color': '#10B981'},
            {'name': 'Software', 'description': 'Software subscriptions', 'color': '#6366F1'},
            {'name': 'Utilities', 'description': 'Internet, phone, etc.', 'color': '#F59E0B'},
            {'name': 'Marketing', 'description': 'Advertising and marketing', 'color': '#EF4444'},
        ]

        categories = []
        for cat_data in categories_data:
            category, created = ExpenseCategory.objects.get_or_create(
                user=user,
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'color': cat_data['color'],
                    'is_tax_deductible': True
                }
            )
            categories.append(category)
            if created:
                self.stdout.write(f'Created category: {category.name}')

        # Create sample vendors
        vendors_data = [
            {'name': 'Staples', 'email': 'business@staples.com'},
            {'name': 'Amazon Business', 'email': 'support@amazon.com'},
            {'name': 'Microsoft', 'email': 'billing@microsoft.com'},
            {'name': 'Uber', 'email': 'business@uber.com'},
            {'name': 'Delta Airlines', 'email': 'corporate@delta.com'},
            {'name': 'Marriott Hotels', 'email': 'corporate@marriott.com'},
            {'name': 'Zoom', 'email': 'billing@zoom.us'},
            {'name': 'Adobe', 'email': 'billing@adobe.com'},
        ]

        vendors = []
        for vendor_data in vendors_data:
            vendor, created = Vendor.objects.get_or_create(
                user=user,
                name=vendor_data['name'],
                defaults={
                    'email': vendor_data['email'],
                    'is_active': True
                }
            )
            vendors.append(vendor)
            if created:
                self.stdout.write(f'Created vendor: {vendor.name}')

        # Create sample expenses
        expenses_data = [
            {
                'description': 'Office supplies - pens and notebooks',
                'amount': Decimal('89.99'),
                'category': 'Office Supplies',
                'vendor': 'Staples',
                'status': 'approved',
                'payment_method': 'credit_card',
                'days_ago': 5
            },
            {
                'description': 'Business lunch with potential client',
                'amount': Decimal('125.50'),
                'category': 'Meals & Entertainment',
                'vendor': None,
                'status': 'pending',
                'payment_method': 'credit_card',
                'days_ago': 3
            },
            {
                'description': 'Uber ride to airport for business trip',
                'amount': Decimal('45.00'),
                'category': 'Travel',
                'vendor': 'Uber',
                'status': 'approved',
                'payment_method': 'credit_card',
                'days_ago': 7
            },
            {
                'description': 'Microsoft Office 365 subscription',
                'amount': Decimal('99.99'),
                'category': 'Software',
                'vendor': 'Microsoft',
                'status': 'paid',
                'payment_method': 'credit_card',
                'days_ago': 1
            },
            {
                'description': 'Hotel stay for conference',
                'amount': Decimal('280.00'),
                'category': 'Travel',
                'vendor': 'Marriott Hotels',
                'status': 'approved',
                'payment_method': 'credit_card',
                'days_ago': 12
            },
            {
                'description': 'Zoom Pro subscription',
                'amount': Decimal('14.99'),
                'category': 'Software',
                'vendor': 'Zoom',
                'status': 'paid',
                'payment_method': 'credit_card',
                'days_ago': 2
            },
            {
                'description': 'Business cards printing',
                'amount': Decimal('75.00'),
                'category': 'Marketing',
                'vendor': None,
                'status': 'draft',
                'payment_method': 'cash',
                'days_ago': 1
            },
            {
                'description': 'Flight to client meeting',
                'amount': Decimal('420.00'),
                'category': 'Travel',
                'vendor': 'Delta Airlines',
                'status': 'pending',
                'payment_method': 'credit_card',
                'days_ago': 8
            },
        ]

        expenses_created = 0
        for exp_data in expenses_data:
            # Get category
            category = None
            if exp_data['category']:
                category = next((c for c in categories if c.name == exp_data['category']), None)
            
            # Get vendor
            vendor = None
            if exp_data['vendor']:
                vendor = next((v for v in vendors if v.name == exp_data['vendor']), None)
            
            # Calculate date
            expense_date = date.today() - timedelta(days=exp_data['days_ago'])
            
            expense, created = Expense.objects.get_or_create(
                user=user,
                description=exp_data['description'],
                date=expense_date,
                defaults={
                    'amount': exp_data['amount'],
                    'category': category,
                    'vendor': vendor,
                    'status': exp_data['status'],
                    'payment_method': exp_data['payment_method'],
                    'tax_amount': exp_data['amount'] * Decimal('0.08'),  # 8% tax
                }
            )
            
            if created:
                expenses_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {expenses_created} expenses for user {user.username}'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Created {len(categories)} categories and {len(vendors)} vendors'
            )
        )
