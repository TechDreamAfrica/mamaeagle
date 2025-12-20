from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.managers import CompanyManager

User = get_user_model()


class SalesTerritory(models.Model):
    """
    Sales territory management for geographic sales organization
    """
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='sales_territories')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    region = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='United States')
    
    # Territory boundaries (can store GeoJSON)
    boundaries = models.JSONField(default=dict, blank=True)
    
    # Performance targets
    monthly_target = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    quarterly_target = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    annual_target = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyManager()

    def __str__(self):
        return f"{self.name} - {self.region}"

    class Meta:
        verbose_name_plural = "Sales Territories"
        indexes = [
            models.Index(fields=['company', 'is_active']),
        ]


class SalesRep(models.Model):
    """
    Sales representative model with territory and performance tracking
    """
    COMMISSION_TYPES = [
        ('percentage', 'Percentage'),
        ('flat_rate', 'Flat Rate'),
        ('tiered', 'Tiered'),
        ('custom', 'Custom'),
    ]
    
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='sales_reps')
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=20)
    territory = models.ForeignKey(SalesTerritory, on_delete=models.SET_NULL, null=True, blank=True)
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Commission structure
    commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPES, default='percentage')
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage or flat amount
    commission_tiers = models.JSONField(default=list, blank=True)  # For tiered commissions
    
    # Performance targets
    monthly_quota = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    quarterly_quota = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    annual_quota = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Contact information
    phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"

    @property
    def full_name(self):
        return self.user.get_full_name()

    objects = CompanyManager()

    class Meta:
        verbose_name = "Sales Representative"
        unique_together = ['company', 'employee_id']
        indexes = [
            models.Index(fields=['company', 'is_active']),
        ]


class Lead(models.Model):
    """
    Sales lead management with advanced tracking
    """
    LEAD_SOURCES = [
        ('website', 'Website'),
        ('referral', 'Referral'),
        ('cold_call', 'Cold Call'),
        ('email_campaign', 'Email Campaign'),
        ('social_media', 'Social Media'),
        ('trade_show', 'Trade Show'),
        ('advertising', 'Advertising'),
        ('partner', 'Partner'),
        ('other', 'Other'),
    ]
    
    LEAD_STATUS = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('proposal', 'Proposal Sent'),
        ('negotiation', 'Negotiation'),
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('nurturing', 'Nurturing'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='leads')
    # Basic information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    company_name = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=100, blank=True)
    
    # Contact information
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    
    # Address
    address_line_1 = models.CharField(max_length=200, blank=True)
    address_line_2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='United States')
    
    # Lead tracking
    source = models.CharField(max_length=20, choices=LEAD_SOURCES)
    status = models.CharField(max_length=20, choices=LEAD_STATUS, default='new')
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='medium')
    
    # Assignment
    assigned_to = models.ForeignKey(SalesRep, on_delete=models.SET_NULL, null=True, blank=True)
    territory = models.ForeignKey(SalesTerritory, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Opportunity details
    estimated_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    probability = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    expected_close_date = models.DateField(null=True, blank=True)
    
    # Lead scoring
    lead_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    scoring_factors = models.JSONField(default=dict, blank=True)
    
    # Notes and additional info
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # AI insights
    ai_recommendations = models.JSONField(default=dict, blank=True)
    conversion_probability = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.company_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'assigned_to']),
        ]


class Opportunity(models.Model):
    """
    Sales opportunity with detailed tracking and forecasting
    """
    OPPORTUNITY_STAGES = [
        ('qualification', 'Qualification'),
        ('needs_analysis', 'Needs Analysis'),
        ('proposal', 'Proposal'),
        ('negotiation', 'Negotiation'),
        ('closed_won', 'Closed Won'),
        ('closed_lost', 'Closed Lost'),
    ]
    
    # Basic information
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, null=True, blank=True)
    
    # Customer information (if not from lead)
    customer_name = models.CharField(max_length=200, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_company = models.CharField(max_length=200, blank=True)
    
    # Opportunity details
    stage = models.CharField(max_length=20, choices=OPPORTUNITY_STAGES, default='qualification')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    probability = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    expected_close_date = models.DateField()
    actual_close_date = models.DateField(null=True, blank=True)
    
    # Assignment
    sales_rep = models.ForeignKey(SalesRep, on_delete=models.SET_NULL, null=True)
    territory = models.ForeignKey(SalesTerritory, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Competition and decision factors
    competitors = models.JSONField(default=list, blank=True)
    decision_factors = models.JSONField(default=list, blank=True)
    decision_makers = models.JSONField(default=list, blank=True)
    
    # Financial details
    cost_of_sale = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    margin = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
    
    # Tracking
    next_step = models.CharField(max_length=500, blank=True)
    next_step_date = models.DateField(null=True, blank=True)
    
    # AI predictions
    ai_forecast = models.JSONField(default=dict, blank=True)
    churn_risk = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - GH₵{self.amount:,.2f}"

    @property
    def weighted_amount(self):
        from decimal import Decimal
        return self.amount * (Decimal(self.probability) / Decimal(100))

    class Meta:
        verbose_name_plural = "Opportunities"
        ordering = ['-expected_close_date']


class SalesActivity(models.Model):
    """
    Track all sales activities and interactions
    """
    ACTIVITY_TYPES = [
        ('call', 'Phone Call'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('demo', 'Product Demo'),
        ('proposal', 'Proposal'),
        ('follow_up', 'Follow Up'),
        ('note', 'Note'),
        ('task', 'Task'),
    ]
    
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    
    # Related objects
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, null=True, blank=True)
    sales_rep = models.ForeignKey(SalesRep, on_delete=models.CASCADE)
    
    # Activity details
    activity_date = models.DateTimeField()
    duration = models.DurationField(null=True, blank=True)
    outcome = models.CharField(max_length=500, blank=True)
    
    # Follow-up
    requires_follow_up = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    follow_up_completed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.activity_type} - {self.subject}"

    class Meta:
        verbose_name_plural = "Sales Activities"
        ordering = ['-activity_date']


class Commission(models.Model):
    """
    Commission calculations and payments
    """
    sales_rep = models.ForeignKey(SalesRep, on_delete=models.CASCADE)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, null=True, blank=True)
    
    # Commission details
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    base_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Timing
    earned_date = models.DateField()
    payment_date = models.DateField(null=True, blank=True)
    
    # Status
    is_paid = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # Additional details
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.sales_rep.full_name} - GH₵{self.commission_amount:,.2f}"

    class Meta:
        ordering = ['-earned_date']
