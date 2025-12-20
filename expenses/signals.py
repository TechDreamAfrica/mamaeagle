from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from decimal import Decimal
from .models import Expense


@receiver(post_save, sender=Expense)
def create_journal_entry_for_expense(sender, instance, created, **kwargs):
    """
    Automatically create journal entry when expense is approved
    Debit: Expense Account
    Credit: Cash/Bank Account (or Accounts Payable if not paid)
    """
    from reports.models import JournalEntry, JournalEntryLine, Account
    
    # Only create journal entry if expense is approved and doesn't already have one
    if instance.status in ['approved', 'paid']:
        # Check if journal entry already exists for this expense
        existing_entry = JournalEntry.objects.filter(
            user=instance.user,
            reference_type='expense',
            reference_id=instance.id
        ).first()
        
        if existing_entry:
            # Update existing entry if status changed to paid
            if instance.status == 'paid' and existing_entry.description.find('(Paid)') == -1:
                existing_entry.description = f"Expense: {instance.description} (Paid)"
                existing_entry.save()
            return
        
        # Get or create expense account
        expense_account = get_or_create_expense_account(instance)
        
        # Get or create cash/bank account
        cash_account = get_or_create_cash_account(instance.user, instance.payment_method)
        
        if not expense_account or not cash_account:
            return
        
        # Create journal entry
        journal_entry = JournalEntry.objects.create(
            user=instance.user,
            entry_date=instance.date,
            reference_type='expense',
            reference_id=instance.id,
            description=f"Expense: {instance.description}" + (" (Paid)" if instance.status == 'paid' else ""),
            status='posted'
        )
        
        # Debit expense account (increases expense)
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=expense_account,
            debit=instance.total_amount,
            credit=Decimal('0'),
            description=f"Expense: {instance.description}"
        )
        
        # Credit cash/bank account (decreases asset)
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=cash_account,
            debit=Decimal('0'),
            credit=instance.total_amount,
            description=f"Payment for: {instance.description}"
        )


def get_or_create_expense_account(expense):
    """Get or create appropriate expense account based on category"""
    from reports.models import Account, AccountType
    
    # Try to find existing expense account for this category
    if expense.category:
        account_name = f"{expense.category.name} Expense"
    else:
        account_name = "General Expenses"
    
    # Try to find existing account
    account = Account.objects.filter(
        user=expense.user,
        account_name__iexact=account_name,
        account_type__category='expense'
    ).first()
    
    if account:
        return account
    
    # Get or create expense account type
    account_type = AccountType.objects.filter(
        category='expense',
        name='Operating Expenses'
    ).first()
    
    if not account_type:
        # Create a default expense account type
        account_type, created = AccountType.objects.get_or_create(
            code='EXP-OPS',
            defaults={
                'category': 'expense',
                'name': 'Operating Expenses',
                'description': 'Day-to-day business operating expenses'
            }
        )
    
    # Create new expense account
    # Get next account number (6000-6999 for expenses)
    last_expense_account = Account.objects.filter(
        user=expense.user,
        account_type__category='expense'
    ).order_by('-account_number').first()
    
    if last_expense_account and last_expense_account.account_number:
        try:
            next_number = str(int(last_expense_account.account_number) + 1)
        except ValueError:
            next_number = '6000'
    else:
        next_number = '6000'
    
    account = Account.objects.create(
        user=expense.user,
        account_type=account_type,
        account_number=next_number,
        account_name=account_name,
        description=f"Automatically created for {expense.category.name if expense.category else 'expenses'}",
        opening_balance=Decimal('0'),
        is_active=True
    )
    
    return account


def get_or_create_cash_account(user, payment_method):
    """Get or create appropriate cash/bank account based on payment method"""
    from reports.models import Account, AccountType
    
    # Map payment methods to account names
    account_name_map = {
        'cash': 'Cash',
        'petty_cash': 'Petty Cash',
        'credit_card': 'Credit Card',
        'debit_card': 'Checking Account',
        'bank_transfer': 'Checking Account',
        'check': 'Checking Account',
        'other': 'Cash',
    }
    
    account_name = account_name_map.get(payment_method, 'Cash')
    
    # Try to find existing account
    account = Account.objects.filter(
        user=user,
        account_name__iexact=account_name,
        account_type__category='asset'
    ).first()
    
    if account:
        return account
    
    # Get or create asset account type
    if payment_method in ['credit_card']:
        # Credit card is actually a liability
        account_type, created = AccountType.objects.get_or_create(
            code='LIAB-CC',
            defaults={
                'category': 'liability',
                'name': 'Credit Card',
                'subtype': 'current_liability',
                'description': 'Credit card liabilities'
            }
        )
    else:
        # Cash and bank accounts are assets
        account_type, created = AccountType.objects.get_or_create(
            code='ASSET-CURR',
            defaults={
                'category': 'asset',
                'name': 'Current Assets',
                'subtype': 'current_asset',
                'description': 'Current assets including cash and bank accounts'
            }
        )
    
    # Create new account
    # Get next account number (1000-1999 for assets, 2000-2999 for liabilities)
    if payment_method in ['credit_card']:
        base_number = 2000
        category = 'liability'
    else:
        base_number = 1000
        category = 'asset'
    
    last_account = Account.objects.filter(
        user=user,
        account_type__category=category
    ).order_by('-account_number').first()
    
    if last_account and last_account.account_number:
        try:
            next_number = str(int(last_account.account_number) + 1)
        except ValueError:
            next_number = str(base_number)
    else:
        next_number = str(base_number)
    
    account = Account.objects.create(
        user=user,
        account_type=account_type,
        account_number=next_number,
        account_name=account_name,
        description=f"Automatically created for {payment_method} payments",
        opening_balance=Decimal('0'),
        is_active=True
    )
    
    return account
