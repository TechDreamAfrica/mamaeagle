from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal
from .models import Payment


@receiver(post_save, sender=Payment)
def create_journal_entry_for_payment(sender, instance, created, **kwargs):
    """
    Automatically create journal entry when payment is recorded for an invoice
    Debit: Cash/Bank Account (increases asset)
    Credit: Accounts Receivable or Revenue Account (decreases receivable or increases revenue)
    """
    from reports.models import JournalEntry, JournalEntryLine, Account
    
    # Only create journal entry for new payments
    if created:
        # Check if journal entry already exists for this payment
        existing_entry = JournalEntry.objects.filter(
            user=instance.invoice.user,
            reference_type='payment',
            reference_id=instance.id
        ).first()
        
        if existing_entry:
            return
        
        # Get or create revenue account
        revenue_account = get_or_create_revenue_account(instance.invoice.user)
        
        # Get or create cash/bank account based on payment method
        cash_account = get_or_create_cash_account(instance.invoice.user, instance.payment_method)
        
        if not revenue_account or not cash_account:
            return
        
        # Create journal entry
        journal_entry = JournalEntry.objects.create(
            user=instance.invoice.user,
            entry_date=instance.payment_date,
            reference_type='payment',
            reference_id=instance.id,
            invoice=instance.invoice,
            description=f"Payment received for Invoice {instance.invoice.invoice_number}",
            status='posted'
        )
        
        # Debit cash/bank account (increases asset)
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=cash_account,
            debit=instance.amount,
            credit=Decimal('0'),
            description=f"Payment for Invoice {instance.invoice.invoice_number}"
        )
        
        # Credit revenue account (increases revenue)
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=revenue_account,
            debit=Decimal('0'),
            credit=instance.amount,
            description=f"Revenue from Invoice {instance.invoice.invoice_number}"
        )


@receiver(post_delete, sender=Payment)
def delete_journal_entry_for_payment(sender, instance, **kwargs):
    """
    Delete associated journal entry when payment is deleted
    """
    from reports.models import JournalEntry
    
    # Find and delete the journal entry associated with this payment
    JournalEntry.objects.filter(
        user=instance.invoice.user,
        reference_type='payment',
        reference_id=instance.id
    ).delete()


def get_or_create_revenue_account(user):
    """Get or create revenue account for invoice payments"""
    from reports.models import Account, AccountType
    
    account_name = "Sales Revenue"
    
    # Try to find existing account
    account = Account.objects.filter(
        user=user,
        account_name__iexact=account_name,
        account_type__category='revenue'
    ).first()
    
    if account:
        return account
    
    # Get or create revenue account type
    account_type = AccountType.objects.filter(
        category='revenue',
        name='Sales Revenue'
    ).first()
    
    if not account_type:
        # Create a default revenue account type
        account_type, created = AccountType.objects.get_or_create(
            code='REV-SALES',
            defaults={
                'category': 'revenue',
                'name': 'Sales Revenue',
                'description': 'Revenue from sales of products and services'
            }
        )
    
    # Create new revenue account
    # Get next account number (4000-4999 for revenue)
    last_revenue_account = Account.objects.filter(
        user=user,
        account_type__category='revenue'
    ).order_by('-account_number').first()
    
    if last_revenue_account and last_revenue_account.account_number:
        try:
            next_number = str(int(last_revenue_account.account_number) + 1)
        except ValueError:
            next_number = '4000'
    else:
        next_number = '4000'
    
    account = Account.objects.create(
        user=user,
        account_type=account_type,
        account_number=next_number,
        account_name=account_name,
        description="Automatically created for invoice revenue",
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
        'check': 'Checking Account',
        'credit_card': 'Credit Card Payments',
        'bank_transfer': 'Checking Account',
        'paypal': 'PayPal Account',
        'stripe': 'Stripe Account',
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
    
    # Get or create asset account type for cash/bank accounts
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
    # Get next account number (1000-1999 for assets)
    base_number = 1000
    
    last_account = Account.objects.filter(
        user=user,
        account_type__category='asset'
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
