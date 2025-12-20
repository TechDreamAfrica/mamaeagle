from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone

User = get_user_model()


class BankAccount(models.Model):
    """
    Model representing a bank account for reconciliation.
    """
    ACCOUNT_TYPES = [
        ('checking', 'Checking'),
        ('savings', 'Savings'),
        ('money_market', 'Money Market'),
        ('credit_card', 'Credit Card'),
        ('line_of_credit', 'Line of Credit'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50, unique=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='checking')
    bank_name = models.CharField(max_length=200)
    routing_number = models.CharField(max_length=20, blank=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_reconciled_date = models.DateField(null=True, blank=True)
    last_reconciled_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_bank_accounts')
    
    class Meta:
        db_table = 'bank_reconciliation_bankaccount'
        verbose_name = 'Bank Account'
        verbose_name_plural = 'Bank Accounts'
        ordering = ['bank_name', 'name']
    
    def __str__(self):
        return f"{self.bank_name} - {self.name} ({self.account_number[-4:]})"
    
    @property
    def masked_account_number(self):
        """Return account number with all but last 4 digits masked."""
        if len(self.account_number) <= 4:
            return self.account_number
        return '*' * (len(self.account_number) - 4) + self.account_number[-4:]


class BankStatement(models.Model):
    """
    Model representing a bank statement for a specific period.
    """
    STATUS_CHOICES = [
        ('imported', 'Imported'),
        ('processing', 'Processing'),
        ('reconciled', 'Reconciled'),
        ('partially_reconciled', 'Partially Reconciled'),
        ('discrepancy', 'Discrepancy Found'),
    ]
    
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='statements')
    statement_date = models.DateField()
    beginning_balance = models.DecimalField(max_digits=12, decimal_places=2)
    ending_balance = models.DecimalField(max_digits=12, decimal_places=2)
    statement_period_start = models.DateField()
    statement_period_end = models.DateField()
    total_deposits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_withdrawals = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='imported')
    reconciliation_date = models.DateTimeField(null=True, blank=True)
    reconciled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reconciled_statements')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bank_reconciliation_bankstatement'
        verbose_name = 'Bank Statement'
        verbose_name_plural = 'Bank Statements'
        ordering = ['-statement_date']
        unique_together = ['bank_account', 'statement_date']
    
    def __str__(self):
        return f"{self.bank_account.name} - {self.statement_date}"
    
    @property
    def transaction_count(self):
        """Return the number of transactions in this statement."""
        return self.transactions.count()
    
    @property
    def unreconciled_count(self):
        """Return the number of unreconciled transactions."""
        return self.transactions.filter(reconciliation_status='unreconciled').count()


class BankTransaction(models.Model):
    """
    Model representing individual bank transactions from statements.
    """
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer', 'Transfer'),
        ('fee', 'Fee'),
        ('interest', 'Interest'),
        ('dividend', 'Dividend'),
        ('check', 'Check'),
        ('debit_card', 'Debit Card'),
        ('ach', 'ACH'),
        ('wire', 'Wire Transfer'),
        ('other', 'Other'),
    ]
    
    RECONCILIATION_STATUS = [
        ('unreconciled', 'Unreconciled'),
        ('matched', 'Matched'),
        ('cleared', 'Cleared'),
        ('disputed', 'Disputed'),
        ('void', 'Void'),
    ]
    
    bank_statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE, related_name='transactions')
    transaction_date = models.DateField()
    description = models.CharField(max_length=500)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    running_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    check_number = models.CharField(max_length=20, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    reconciliation_status = models.CharField(max_length=20, choices=RECONCILIATION_STATUS, default='unreconciled')
    reconciled_date = models.DateTimeField(null=True, blank=True)
    reconciled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reconciled_transactions')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bank_reconciliation_banktransaction'
        verbose_name = 'Bank Transaction'
        verbose_name_plural = 'Bank Transactions'
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['transaction_date']),
            models.Index(fields=['reconciliation_status']),
            models.Index(fields=['amount']),
        ]
    
    def __str__(self):
        return f"{self.transaction_date} - {self.description[:50]} - GH₵{self.amount}"
    
    @property
    def is_debit(self):
        """Return True if transaction is a debit (negative amount)."""
        return self.amount < 0
    
    @property
    def is_credit(self):
        """Return True if transaction is a credit (positive amount)."""
        return self.amount > 0


class ReconciliationRule(models.Model):
    """
    Model for automatic reconciliation rules to match transactions.
    """
    RULE_TYPES = [
        ('description_contains', 'Description Contains'),
        ('description_exact', 'Description Exact Match'),
        ('amount_exact', 'Amount Exact Match'),
        ('amount_range', 'Amount Range'),
        ('check_number', 'Check Number'),
        ('reference_number', 'Reference Number'),
        ('combined', 'Combined Criteria'),
    ]
    
    name = models.CharField(max_length=200)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    description_pattern = models.CharField(max_length=500, blank=True)
    amount_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    amount_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    check_number_pattern = models.CharField(max_length=50, blank=True)
    reference_pattern = models.CharField(max_length=100, blank=True)
    auto_match = models.BooleanField(default=False)
    confidence_threshold = models.IntegerField(default=80, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_reconciliation_rules')
    
    class Meta:
        db_table = 'bank_reconciliation_reconciliationrule'
        verbose_name = 'Reconciliation Rule'
        verbose_name_plural = 'Reconciliation Rules'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ReconciliationSession(models.Model):
    """
    Model representing a reconciliation session for tracking reconciliation progress.
    """
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
        ('error', 'Error'),
    ]
    
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='reconciliation_sessions')
    bank_statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE, related_name='reconciliation_sessions')
    session_name = models.CharField(max_length=200)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    starting_book_balance = models.DecimalField(max_digits=12, decimal_places=2)
    ending_book_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    statement_balance = models.DecimalField(max_digits=12, decimal_places=2)
    difference = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transactions_matched = models.IntegerField(default=0)
    transactions_unmatched = models.IntegerField(default=0)
    adjustments_made = models.IntegerField(default=0)
    reconciled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reconciliation_sessions')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bank_reconciliation_reconciliationsession'
        verbose_name = 'Reconciliation Session'
        verbose_name_plural = 'Reconciliation Sessions'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.session_name} - {self.bank_account.name} ({self.start_date.strftime('%Y-%m-%d')})"
    
    @property
    def duration(self):
        """Return the duration of the reconciliation session."""
        if self.end_date:
            return self.end_date - self.start_date
        return timezone.now() - self.start_date
    
    @property
    def is_balanced(self):
        """Return True if the reconciliation is balanced (difference is zero)."""
        return self.difference == 0


class ReconciliationAdjustment(models.Model):
    """
    Model for tracking adjustments made during reconciliation.
    """
    ADJUSTMENT_TYPES = [
        ('bank_error', 'Bank Error'),
        ('book_error', 'Book Error'),
        ('outstanding_check', 'Outstanding Check'),
        ('deposit_in_transit', 'Deposit in Transit'),
        ('bank_fee', 'Bank Fee'),
        ('interest_earned', 'Interest Earned'),
        ('nsf_check', 'NSF Check'),
        ('other', 'Other'),
    ]
    
    reconciliation_session = models.ForeignKey(ReconciliationSession, on_delete=models.CASCADE, related_name='adjustments')
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPES)
    description = models.CharField(max_length=500)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    affects_bank_balance = models.BooleanField(default=False)
    affects_book_balance = models.BooleanField(default=True)
    reference_transaction = models.ForeignKey(BankTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='adjustments')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_adjustments')
    
    class Meta:
        db_table = 'bank_reconciliation_reconciliationadjustment'
        verbose_name = 'Reconciliation Adjustment'
        verbose_name_plural = 'Reconciliation Adjustments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.adjustment_type} - {self.description[:50]} - GH₵{self.amount}"
