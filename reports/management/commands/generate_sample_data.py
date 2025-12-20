"""
Sample Data Generator for Financial Statements
This script creates sample account types, accounts, and journal entries for testing
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta
from reports.models import AccountType, Account, JournalEntry, JournalEntryLine

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate sample financial data for testing'

    def handle(self, *args, **kwargs):
        self.stdout.write('Generating sample financial data...')
        
        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User',
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created test user: {user.username}'))
        
        # Create Account Types
        self.stdout.write('Creating account types...')
        account_types_data = [
            # Assets
            {'code': '1000', 'name': 'Cash and Cash Equivalents', 'category': 'asset', 'subtype': 'current_asset'},
            {'code': '1100', 'name': 'Accounts Receivable', 'category': 'asset', 'subtype': 'current_asset'},
            {'code': '1200', 'name': 'Inventory', 'category': 'asset', 'subtype': 'current_asset'},
            {'code': '1500', 'name': 'Property, Plant & Equipment', 'category': 'asset', 'subtype': 'fixed_asset'},
            {'code': '1600', 'name': 'Accumulated Depreciation', 'category': 'asset', 'subtype': 'fixed_asset'},
            
            # Liabilities
            {'code': '2000', 'name': 'Accounts Payable', 'category': 'liability', 'subtype': 'current_liability'},
            {'code': '2100', 'name': 'Accrued Expenses', 'category': 'liability', 'subtype': 'current_liability'},
            {'code': '2500', 'name': 'Long-term Debt', 'category': 'liability', 'subtype': 'long_term_liability'},
            
            # Equity
            {'code': '3000', 'name': 'Common Stock', 'category': 'equity', 'subtype': ''},
            {'code': '3100', 'name': 'Retained Earnings', 'category': 'equity', 'subtype': ''},
            
            # Revenue
            {'code': '4000', 'name': 'Sales Revenue', 'category': 'revenue', 'subtype': ''},
            {'code': '4100', 'name': 'Service Revenue', 'category': 'revenue', 'subtype': ''},
            
            # Expenses
            {'code': '5000', 'name': 'Cost of Goods Sold', 'category': 'expense', 'subtype': ''},
            {'code': '6000', 'name': 'Salaries & Wages', 'category': 'expense', 'subtype': ''},
            {'code': '6100', 'name': 'Rent Expense', 'category': 'expense', 'subtype': ''},
            {'code': '6200', 'name': 'Utilities Expense', 'category': 'expense', 'subtype': ''},
            {'code': '6300', 'name': 'Office Supplies', 'category': 'expense', 'subtype': ''},
            {'code': '6400', 'name': 'Depreciation Expense', 'category': 'expense', 'subtype': ''},
        ]
        
        account_types = {}
        for data in account_types_data:
            at, created = AccountType.objects.get_or_create(
                code=data['code'],
                defaults=data
            )
            account_types[data['code']] = at
            if created:
                self.stdout.write(f'  Created account type: {at.code} - {at.name}')
        
        # Create Accounts
        self.stdout.write('Creating accounts...')
        accounts_data = [
            {'account_type': '1000', 'number': '1000-01', 'name': 'Cash - Operating', 'opening_balance': 50000},
            {'account_type': '1100', 'number': '1100-01', 'name': 'Accounts Receivable', 'opening_balance': 25000},
            {'account_type': '1200', 'number': '1200-01', 'name': 'Inventory', 'opening_balance': 30000},
            {'account_type': '1500', 'number': '1500-01', 'name': 'Equipment', 'opening_balance': 100000},
            {'account_type': '1600', 'number': '1600-01', 'name': 'Accumulated Depreciation - Equipment', 'opening_balance': -20000},
            {'account_type': '2000', 'number': '2000-01', 'name': 'Accounts Payable', 'opening_balance': 15000},
            {'account_type': '2100', 'number': '2100-01', 'name': 'Accrued Salaries', 'opening_balance': 5000},
            {'account_type': '2500', 'number': '2500-01', 'name': 'Bank Loan', 'opening_balance': 50000},
            {'account_type': '3000', 'number': '3000-01', 'name': 'Common Stock', 'opening_balance': 75000},
            {'account_type': '3100', 'number': '3100-01', 'name': 'Retained Earnings', 'opening_balance': 40000},
            {'account_type': '4000', 'number': '4000-01', 'name': 'Product Sales', 'opening_balance': 0},
            {'account_type': '4100', 'number': '4100-01', 'name': 'Consulting Services', 'opening_balance': 0},
            {'account_type': '5000', 'number': '5000-01', 'name': 'Cost of Goods Sold', 'opening_balance': 0},
            {'account_type': '6000', 'number': '6000-01', 'name': 'Salaries Expense', 'opening_balance': 0},
            {'account_type': '6100', 'number': '6100-01', 'name': 'Rent Expense', 'opening_balance': 0},
            {'account_type': '6200', 'number': '6200-01', 'name': 'Utilities Expense', 'opening_balance': 0},
            {'account_type': '6300', 'number': '6300-01', 'name': 'Office Supplies Expense', 'opening_balance': 0},
            {'account_type': '6400', 'number': '6400-01', 'name': 'Depreciation Expense', 'opening_balance': 0},
        ]
        
        accounts = {}
        for data in accounts_data:
            acc, created = Account.objects.get_or_create(
                user=user,
                account_number=data['number'],
                defaults={
                    'account_type': account_types[data['account_type']],
                    'account_name': data['name'],
                    'opening_balance': Decimal(str(data['opening_balance'])),
                    'current_balance': Decimal(str(data['opening_balance'])),
                    'opening_balance_date': date(2024, 1, 1),
                }
            )
            accounts[data['number']] = acc
            if created:
                self.stdout.write(f'  Created account: {acc.account_number} - {acc.account_name}')
        
        # Create Sample Journal Entries
        self.stdout.write('Creating sample journal entries...')
        
        entries_data = [
            # Entry 1: Sales Revenue
            {
                'number': 'JE-2024-001',
                'date': date(2024, 11, 1),
                'description': 'Record product sales for November',
                'lines': [
                    {'account': '1000-01', 'debit': 15000, 'credit': 0},
                    {'account': '4000-01', 'debit': 0, 'credit': 15000},
                ]
            },
            # Entry 2: COGS
            {
                'number': 'JE-2024-002',
                'date': date(2024, 11, 1),
                'description': 'Record cost of goods sold',
                'lines': [
                    {'account': '5000-01', 'debit': 9000, 'credit': 0},
                    {'account': '1200-01', 'debit': 0, 'credit': 9000},
                ]
            },
            # Entry 3: Service Revenue
            {
                'number': 'JE-2024-003',
                'date': date(2024, 11, 5),
                'description': 'Consulting services provided',
                'lines': [
                    {'account': '1100-01', 'debit': 8000, 'credit': 0},
                    {'account': '4100-01', 'debit': 0, 'credit': 8000},
                ]
            },
            # Entry 4: Salary Expense
            {
                'number': 'JE-2024-004',
                'date': date(2024, 11, 10),
                'description': 'Pay salaries',
                'lines': [
                    {'account': '6000-01', 'debit': 12000, 'credit': 0},
                    {'account': '1000-01', 'debit': 0, 'credit': 12000},
                ]
            },
            # Entry 5: Rent Expense
            {
                'number': 'JE-2024-005',
                'date': date(2024, 11, 1),
                'description': 'Monthly rent payment',
                'lines': [
                    {'account': '6100-01', 'debit': 3000, 'credit': 0},
                    {'account': '1000-01', 'debit': 0, 'credit': 3000},
                ]
            },
            # Entry 6: Utilities
            {
                'number': 'JE-2024-006',
                'date': date(2024, 11, 8),
                'description': 'Utility bills',
                'lines': [
                    {'account': '6200-01', 'debit': 800, 'credit': 0},
                    {'account': '1000-01', 'debit': 0, 'credit': 800},
                ]
            },
            # Entry 7: Office Supplies
            {
                'number': 'JE-2024-007',
                'date': date(2024, 11, 3),
                'description': 'Purchase office supplies',
                'lines': [
                    {'account': '6300-01', 'debit': 500, 'credit': 0},
                    {'account': '1000-01', 'debit': 0, 'credit': 500},
                ]
            },
            # Entry 8: Depreciation
            {
                'number': 'JE-2024-008',
                'date': date(2024, 11, 30),
                'description': 'Monthly depreciation',
                'lines': [
                    {'account': '6400-01', 'debit': 1000, 'credit': 0},
                    {'account': '1600-01', 'debit': 0, 'credit': 1000},
                ]
            },
        ]
        
        for entry_data in entries_data:
            entry, created = JournalEntry.objects.get_or_create(
                user=user,
                entry_number=entry_data['number'],
                defaults={
                    'entry_date': entry_data['date'],
                    'entry_type': 'standard',
                    'status': 'posted',
                    'description': entry_data['description'],
                    'posted_by': user,
                    'posted_date': entry_data['date'],
                }
            )
            
            if created:
                self.stdout.write(f'  Created journal entry: {entry.entry_number}')
                
                # Create lines
                for line_data in entry_data['lines']:
                    JournalEntryLine.objects.create(
                        journal_entry=entry,
                        account=accounts[line_data['account']],
                        debit=Decimal(str(line_data['debit'])),
                        credit=Decimal(str(line_data['credit'])),
                    )
        
        self.stdout.write(self.style.SUCCESS('\nSample data generated successfully!'))
        self.stdout.write(self.style.SUCCESS(f'Test User: username=testuser, password=testpass123'))
        self.stdout.write(self.style.SUCCESS('You can now generate financial statements for November 2024'))
