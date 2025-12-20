from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
from accounts.managers import CompanyManager

User = get_user_model()


class ExpenseCategory(models.Model):
    """
    Expense categories for better organization
    More flexible than QuickBooks' categories
    """
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='expense_categories')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#6B7280')  # Hex color
    
    # Tax settings
    is_tax_deductible = models.BooleanField(default=True)
    tax_category = models.CharField(max_length=100, blank=True)
    
    # AI insights
    budget_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ai_spending_pattern = models.JSONField(default=dict)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CompanyManager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Expense Categories"
        unique_together = ['company', 'user', 'name']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['company', 'user']),
        ]


class Vendor(models.Model):
    """
    Vendor management for expense tracking
    Better vendor management than QuickBooks
    """
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='vendors')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    
    # Address
    address_line_1 = models.CharField(max_length=200, blank=True)
    address_line_2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='Ghana')
    
    # Financial
    tax_id = models.CharField(max_length=50, blank=True)
    payment_terms = models.CharField(max_length=50, blank=True)
    
    # AI insights
    reliability_score = models.IntegerField(default=50)  # 0-100
    payment_history = models.JSONField(default=dict)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyManager()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['company', 'name']),
        ]


class Expense(models.Model):
    """
    Expense model with receipt management and AI features
    Advanced expense tracking vs QuickBooks
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ]
    
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('check', 'Check'),
        ('bank_transfer', 'Bank Transfer'),
        ('petty_cash', 'Petty Cash'),
        ('other', 'Other'),
    ]
    
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='expenses')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Basic details
    description = models.CharField(max_length=500)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    
    # Payment details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    reference_number = models.CharField(max_length=100, blank=True)
    
    # Status and approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_expenses'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Tax information
    is_billable = models.BooleanField(default=False)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Receipt management
    receipt = models.ImageField(upload_to='receipts/', blank=True, null=True)
    receipt_processed = models.BooleanField(default=False)
    
    # AI extracted data from receipt
    ai_extracted_data = models.JSONField(default=dict)
    ai_confidence_score = models.FloatField(default=0)
    
    # Additional details
    notes = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.description} - GH₵{self.amount}"

    def get_absolute_url(self):
        return reverse('expenses:expense_detail', kwargs={'pk': self.pk})

    @property
    def total_amount(self):
        return self.amount + self.tax_amount

    objects = CompanyManager()

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'date']),
            models.Index(fields=['company', 'user']),
        ]


class ExpenseReport(models.Model):
    """
    Expense report for grouping and submission
    Advanced reporting vs QuickBooks
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ]
    
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='expense_reports')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Date range
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_expense_reports'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Totals
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.user.get_full_name()}"

    def calculate_totals(self):
        """Calculate totals from associated expenses"""
        # Get expenses through the ExpenseReportItem relationship
        expense_items = self.expenses.all()
        self.total_amount = sum(item.expense.amount for item in expense_items)
        self.total_tax = sum(item.expense.tax_amount for item in expense_items)
        self.save()

    objects = CompanyManager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'user']),
        ]


class ExpenseReportItem(models.Model):
    """
    Link between expense reports and individual expenses
    """
    report = models.ForeignKey(ExpenseReport, on_delete=models.CASCADE, related_name='expenses')
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['report', 'expense']


class MileageLog(models.Model):
    """
    Mileage tracking for business travel
    Better than QuickBooks' basic mileage tracking
    """
    PURPOSE_CHOICES = [
        ('business', 'Business'),
        ('medical', 'Medical'),
        ('charity', 'Charity'),
        ('moving', 'Moving'),
    ]
    
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='mileage_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Trip details
    date = models.DateField()
    start_location = models.CharField(max_length=200)
    end_location = models.CharField(max_length=200)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default='business')
    description = models.CharField(max_length=500)
    
    # Mileage
    miles = models.DecimalField(max_digits=8, decimal_places=2)
    rate_per_mile = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal('0.585'))  # 2023 IRS rate
    
    # Vehicle info
    vehicle = models.CharField(max_length=100, blank=True)
    
    # AI features
    gps_verified = models.BooleanField(default=False)
    route_data = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_amount(self):
        return self.miles * self.rate_per_mile

    def __str__(self):
        return f"{self.start_location} to {self.end_location} - {self.miles} miles"

    objects = CompanyManager()

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['company', 'date']),
            models.Index(fields=['company', 'user']),
        ]
