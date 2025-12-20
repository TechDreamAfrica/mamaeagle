from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from dashboard.models import DashboardWidget, QuickAction
from invoicing.models import Customer, Product, Invoice, InvoiceItem
from expenses.models import ExpenseCategory, Expense
from decimal import Decimal
import random
from datetime import date, timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate the database with sample data for demonstration'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating sample data...'))
        
        # Create a demo user if it doesn't exist
        user, created = User.objects.get_or_create(
            username='demo',
            defaults={
                'email': 'demo@accuflow.com',
                'first_name': 'Demo',
                'last_name': 'User',
                'is_staff': False,
            }
        )
        if created:
            user.set_password('demo123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created demo user: {user.username}'))

        # Create sample customers
        customers_data = [
            {'name': 'Acme Corporation', 'email': 'billing@acmecorp.com', 'company': 'Acme Corp'},
            {'name': 'TechStart Inc', 'email': 'finance@techstart.com', 'company': 'TechStart Inc'},
            {'name': 'Global Solutions', 'email': 'accounts@globalsolutions.com', 'company': 'Global Solutions LLC'},
            {'name': 'Creative Agency', 'email': 'billing@creativeagency.com', 'company': 'Creative Agency Co'},
        ]
        
        for customer_data in customers_data:
            customer, created = Customer.objects.get_or_create(
                user=user,
                email=customer_data['email'],
                defaults=customer_data
            )
            if created:
                self.stdout.write(f'Created customer: {customer.name}')

        # Create sample products/services
        products_data = [
            {'name': 'Web Development', 'description': 'Custom web development services', 'unit_price': Decimal('150.00')},
            {'name': 'Consulting Services', 'description': 'Business consulting and strategy', 'unit_price': Decimal('200.00')},
            {'name': 'Design Services', 'description': 'UI/UX design and branding', 'unit_price': Decimal('125.00')},
            {'name': 'Maintenance Package', 'description': 'Monthly website maintenance', 'unit_price': Decimal('500.00')},
        ]
        
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                user=user,
                name=product_data['name'],
                defaults=product_data
            )
            if created:
                self.stdout.write(f'Created product: {product.name}')

        # Create sample expense categories
        categories_data = [
            {'name': 'Office Supplies', 'color': '#10B981'},
            {'name': 'Travel & Transportation', 'color': '#3B82F6'},
            {'name': 'Marketing & Advertising', 'color': '#8B5CF6'},
            {'name': 'Software & Subscriptions', 'color': '#F59E0B'},
            {'name': 'Meals & Entertainment', 'color': '#EF4444'},
        ]
        
        for category_data in categories_data:
            category, created = ExpenseCategory.objects.get_or_create(
                user=user,
                name=category_data['name'],
                defaults=category_data
            )
            if created:
                self.stdout.write(f'Created expense category: {category.name}')

        # Create sample invoices
        customers = Customer.objects.filter(user=user)
        products = Product.objects.filter(user=user)
        
        if customers.exists() and products.exists():
            for i in range(10):
                customer = random.choice(customers)
                invoice = Invoice.objects.create(
                    user=user,
                    customer=customer,
                    invoice_number=f'INV-{1000 + i:05d}',
                    date_due=date.today() + timedelta(days=30),
                    status=random.choice(['draft', 'sent', 'paid']),
                    total_amount=Decimal('0')
                )
                
                # Add random line items
                for j in range(random.randint(1, 3)):
                    product = random.choice(products)
                    quantity = random.randint(1, 10)
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product=product,
                        description=product.description,
                        quantity=quantity,
                        unit_price=product.unit_price
                    )
                
                invoice.calculate_totals()
                self.stdout.write(f'Created invoice: {invoice.invoice_number}')

        # Create sample expenses
        categories = ExpenseCategory.objects.filter(user=user)
        
        if categories.exists():
            expenses_data = [
                {'description': 'Office chair and desk supplies', 'amount': Decimal('245.99')},
                {'description': 'Business lunch with client', 'amount': Decimal('89.50')},
                {'description': 'Adobe Creative Suite subscription', 'amount': Decimal('52.99')},
                {'description': 'Uber rides for business meetings', 'amount': Decimal('127.30')},
                {'description': 'Google Ads campaign', 'amount': Decimal('350.00')},
            ]
            
            for expense_data in expenses_data:
                Expense.objects.create(
                    user=user,
                    category=random.choice(categories),
                    description=expense_data['description'],
                    amount=expense_data['amount'],
                    date=date.today() - timedelta(days=random.randint(1, 30)),
                    payment_method='credit_card',
                    status='approved'
                )
                self.stdout.write(f'Created expense: {expense_data["description"]}')

        # Create default dashboard widgets
        default_widgets = [
            {'widget_type': 'revenue_chart', 'title': 'Revenue Trend', 'position_x': 0, 'position_y': 0, 'width': 8, 'height': 4},
            {'widget_type': 'kpi_metrics', 'title': 'Key Metrics', 'position_x': 8, 'position_y': 0, 'width': 4, 'height': 4},
            {'widget_type': 'recent_transactions', 'title': 'Recent Activity', 'position_x': 0, 'position_y': 4, 'width': 6, 'height': 4},
            {'widget_type': 'ai_insights', 'title': 'AI Insights', 'position_x': 6, 'position_y': 4, 'width': 6, 'height': 4},
        ]
        
        for widget_data in default_widgets:
            widget, created = DashboardWidget.objects.get_or_create(
                user=user,
                widget_type=widget_data['widget_type'],
                defaults=widget_data
            )
            if created:
                self.stdout.write(f'Created dashboard widget: {widget.title}')

        # Create quick actions
        quick_actions_data = [
            {'name': 'Create Invoice', 'url': '/invoicing/invoices/create/', 'icon': 'fas fa-file-invoice', 'color': 'blue'},
            {'name': 'Add Expense', 'url': '/expenses/create/', 'icon': 'fas fa-receipt', 'color': 'green'},
            {'name': 'Add Customer', 'url': '/invoicing/customers/create/', 'icon': 'fas fa-user-plus', 'color': 'purple'},
            {'name': 'View Reports', 'url': '/reports/', 'icon': 'fas fa-chart-bar', 'color': 'orange'},
        ]
        
        for i, action_data in enumerate(quick_actions_data):
            action, created = QuickAction.objects.get_or_create(
                user=user,
                name=action_data['name'],
                defaults={**action_data, 'order': i}
            )
            if created:
                self.stdout.write(f'Created quick action: {action.name}')

        self.stdout.write(
            self.style.SUCCESS(
                'Sample data created successfully!\n\n'
                'You can now login with:\n'
                'Username: demo\n'
                'Password: demo123\n\n'
                'Or use the admin user you created.'
            )
        )
