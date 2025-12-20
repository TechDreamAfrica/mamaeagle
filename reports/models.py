from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import date

User = get_user_model()


class AccountType(models.Model):
    """
    Chart of Accounts - Account Types
    Following GAAP/IFRS standards
    """
    ACCOUNT_CATEGORIES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ]
    
    ASSET_SUBTYPES = [
        ('current_asset', 'Current Asset'),
        ('fixed_asset', 'Fixed Asset'),
        ('other_asset', 'Other Asset'),
    ]
    
    LIABILITY_SUBTYPES = [
        ('current_liability', 'Current Liability'),
        ('long_term_liability', 'Long-term Liability'),
        ('other_liability', 'Other Liability'),
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    category = models.CharField(max_length=20, choices=ACCOUNT_CATEGORIES)
    subtype = models.CharField(max_length=50, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['code', 'name']
        verbose_name = 'Account Type'
        verbose_name_plural = 'Account Types'
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Account(models.Model):
    """
    General Ledger Accounts
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account_type = models.ForeignKey(AccountType, on_delete=models.PROTECT)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Balance tracking
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    opening_balance_date = models.DateField(null=True, blank=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    is_system_account = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['account_number', 'account_name']
        unique_together = ['user', 'account_number']
    
    def __str__(self):
        return f"{self.account_number} - {self.account_name}"


class JournalEntry(models.Model):
    """
    Journal Entries for double-entry bookkeeping
    """
    ENTRY_TYPES = [
        ('standard', 'Standard Entry'),
        ('adjusting', 'Adjusting Entry'),
        ('closing', 'Closing Entry'),
        ('reversing', 'Reversing Entry'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('void', 'Void'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    entry_number = models.CharField(max_length=50)
    entry_date = models.DateField()
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES, default='standard')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    reference = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    
    # Reference tracking for automatic entries
    reference_type = models.CharField(max_length=50, blank=True)  # 'expense', 'invoice', etc.
    reference_id = models.IntegerField(null=True, blank=True)
    
    # Related documents
    invoice = models.ForeignKey('invoicing.Invoice', on_delete=models.SET_NULL, null=True, blank=True)
    expense = models.ForeignKey('expenses.Expense', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Audit
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='posted_entries')
    posted_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-entry_date', '-created_at']
        verbose_name = 'Journal Entry'
        verbose_name_plural = 'Journal Entries'
    
    def __str__(self):
        return f"{self.entry_number} - {self.entry_date}"


class JournalEntryLine(models.Model):
    """
    Individual lines in a journal entry (debits and credits)
    """
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    description = models.CharField(max_length=500, blank=True)
    
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.account.account_name} - Dr: {self.debit} Cr: {self.credit}"


class FinancialPeriod(models.Model):
    """
    Financial reporting periods (months, quarters, years)
    """
    PERIOD_TYPES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPES)
    
    start_date = models.DateField()
    end_date = models.DateField()
    
    is_closed = models.BooleanField(default=False)
    closed_date = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='closed_periods')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        unique_together = ['user', 'start_date', 'end_date', 'period_type']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"


class FinancialStatement(models.Model):
    """
    Generated financial statements storage
    """
    STATEMENT_TYPES = [
        ('balance_sheet', 'Balance Sheet'),
        ('income_statement', 'Income Statement'),
        ('cash_flow', 'Cash Flow Statement'),
        ('equity_statement', 'Statement of Changes in Equity'),
        ('comprehensive', 'Comprehensive Financial Statement'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    statement_type = models.CharField(max_length=30, choices=STATEMENT_TYPES)
    period = models.ForeignKey(FinancialPeriod, on_delete=models.CASCADE)
    
    generated_date = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='generated_statements')
    
    # Statement data (JSON format for flexibility)
    statement_data = models.JSONField()
    
    # Metadata
    notes = models.TextField(blank=True)
    accounting_standard = models.CharField(max_length=20, default='GAAP', choices=[('GAAP', 'GAAP'), ('IFRS', 'IFRS')])
    
    class Meta:
        ordering = ['-generated_date']
    
    def __str__(self):
        return f"{self.get_statement_type_display()} - {self.period.name}"
