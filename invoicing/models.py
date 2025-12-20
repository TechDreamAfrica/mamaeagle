from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
from django.core.validators import MinValueValidator
import uuid
from accounts.managers import CompanyManager

User = get_user_model()


class Customer(models.Model):
    """
    Customer model with enhanced features
    Better customer management than QuickBooks
    """
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='customers')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    company_name = models.CharField(max_length=200, blank=True, help_text="Customer's company name")
    
    # Address
    billing_address_line_1 = models.CharField(max_length=200, blank=True)
    billing_address_line_2 = models.CharField(max_length=200, blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_state = models.CharField(max_length=100, blank=True)
    billing_postal_code = models.CharField(max_length=20, blank=True)
    billing_country = models.CharField(max_length=100, default='United States')
    
    # Financial info
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_terms = models.CharField(max_length=50, default='Net 30')
    tax_id = models.CharField(max_length=50, blank=True)
    
    # Preferences
    preferred_payment_method = models.CharField(max_length=50, blank=True)
    currency = models.CharField(max_length=3, default='GHS')
    language = models.CharField(max_length=10, default='en')
    
    # AI insights
    ai_insights = models.JSONField(default=dict, blank=True, null=True)
    risk_score = models.IntegerField(default=50)  # 0-100
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CompanyManager()  # Auto-filter by company

    def __str__(self):
        return f"{self.name} ({self.company_name})" if self.company_name else self.name

    class Meta:
        indexes = [
            models.Index(fields=['company', 'created_at']),
            models.Index(fields=['company', 'is_active']),
        ]
    def get_absolute_url(self):
        return reverse('invoicing:customer_detail', kwargs={'pk': self.pk})

    class Meta:
        ordering = ['name']


class Product(models.Model):
    """
    Product/Service model with inventory tracking
    Enhanced product management vs QuickBooks
    """
    PRODUCT_TYPES = [
        ('product', 'Product'),
        ('service', 'Service'),
        ('subscription', 'Subscription'),
    ]
    
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='products')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=100, blank=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='product')
    
    # Pricing
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Inventory (for products only)
    track_inventory = models.BooleanField(default=False)
    current_stock = models.IntegerField(default=0)
    minimum_stock = models.IntegerField(default=0)
    
    # Tax and categorization
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    category = models.CharField(max_length=100, blank=True)
    
    # AI insights
    demand_forecast = models.JSONField(default=dict)
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CompanyManager()  # Auto-filter by company

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.track_inventory and self.current_stock <= self.minimum_stock

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['company', 'sku']),
        ]


class Invoice(models.Model):
    """
    Invoice model with advanced features
    Superior to QuickBooks' basic invoicing
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('viewed', 'Viewed'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='invoices')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    
    # Invoice details
    invoice_number = models.CharField(max_length=50)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    
    # Dates
    date_created = models.DateField(auto_now_add=True)
    date_due = models.DateField()
    date_sent = models.DateTimeField(null=True, blank=True)
    date_paid = models.DateTimeField(null=True, blank=True)
    
    # Status and workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Financial
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    objects = CompanyManager()  # Auto-filter by company
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Additional info
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    payment_instructions = models.TextField(blank=True)
    
    # AI features
    ai_payment_prediction = models.JSONField(default=dict)
    risk_assessment = models.JSONField(default=dict)
    
    # Tracking
    view_count = models.IntegerField(default=0)
    last_viewed = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer.name}"

    def get_absolute_url(self):
        return reverse('invoicing:invoice_detail', kwargs={'pk': self.pk})

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.status in ['sent', 'viewed'] and self.date_due < timezone.now().date()

    @property
    def days_overdue(self):
        if self.is_overdue:
            from django.utils import timezone
            return (timezone.now().date() - self.date_due).days
        return 0

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid

    class Meta:
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'date_created']),
            models.Index(fields=['company', 'customer']),
        ]
        unique_together = [['company', 'invoice_number']]
    def calculate_totals(self):
        """Calculate invoice totals from line items"""
        items = self.invoiceitem_set.all()
        self.subtotal = sum(item.total for item in items)
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.save()

    class Meta:
        ordering = ['-date_created']


class InvoiceItem(models.Model):
    """
    Invoice line items
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total(self):
        if self.quantity is None or self.unit_price is None:
            return Decimal('0')
        return self.quantity * self.unit_price

    @property
    def tax_amount(self):
        if self.tax_rate is None:
            return Decimal('0')
        return self.total * (self.tax_rate / 100)

    @property
    def total_with_tax(self):
        return self.total + self.tax_amount

    def __str__(self):
        return f"{self.description} - {self.invoice.invoice_number}"

    class Meta:
        ordering = ['id']


class Payment(models.Model):
    """
    Payment tracking model
    Enhanced payment management vs QuickBooks
    """
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('other', 'Other'),
    ]
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_date = models.DateField()
    
    # Payment details
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # Bank/Card details (for record keeping)
    bank_account = models.CharField(max_length=100, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.amount} for {self.invoice.invoice_number}"

    class Meta:
        ordering = ['-payment_date']
