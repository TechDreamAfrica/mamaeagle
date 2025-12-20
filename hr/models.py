from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from accounts.managers import CompanyManager

User = get_user_model()


class Employee(models.Model):
    """
    Employee model extending User
    Advanced HR management vs QuickBooks' basic employee records
    """
    EMPLOYMENT_TYPES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('intern', 'Intern'),
        ('temporary', 'Temporary'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('terminated', 'Terminated'),
        ('on_leave', 'On Leave'),
    ]
    
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='employees')
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Employment details
    employee_id = models.CharField(max_length=20)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPES, default='full_time')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Job information
    job_title = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Dates
    hire_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)
    
    # Compensation
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Tax information
    tax_id = models.CharField(max_length=20, blank=True)
    tax_exemptions = models.IntegerField(default=0)
    
    # Benefits
    health_insurance = models.BooleanField(default=False)
    dental_insurance = models.BooleanField(default=False)
    vision_insurance = models.BooleanField(default=False)
    retirement_plan = models.BooleanField(default=False)
    
    # Emergency contact
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)
    
    # AI insights
    performance_score = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    predicted_turnover_risk = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyManager()

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"

    @property
    def full_name(self):
        return self.user.get_full_name()

    class Meta:
        ordering = ['user__last_name', 'user__first_name']
        unique_together = ['company', 'employee_id']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'department']),
        ]


class PayrollPeriod(models.Model):
    """
    Payroll period management
    Better payroll handling than QuickBooks
    """
    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-weekly'),
        ('semi_monthly', 'Semi-monthly'),
        ('monthly', 'Monthly'),
    ]
    
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='payroll_periods')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    pay_date = models.DateField()
    
    is_processed = models.BooleanField(default=False)
    processed_date = models.DateTimeField(null=True, blank=True)

    objects = CompanyManager()
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payroll {self.start_date} to {self.end_date}"

    class Meta:
        ordering = ['-start_date']


class Payroll(models.Model):
    """
    Individual payroll record
    Advanced payroll processing vs QuickBooks
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    payroll_period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE)
    
    # Hours and earnings
    regular_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    vacation_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    sick_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Earnings
    regular_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    overtime_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Pre-tax deductions
    health_insurance_deduction = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    dental_insurance_deduction = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    retirement_contribution = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Taxes
    federal_tax = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    state_tax = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    social_security_tax = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    medicare_tax = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Post-tax deductions
    garnishments = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Calculated fields
    gross_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    is_processed = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_totals(self):
        """Calculate gross and net pay"""
        # Calculate gross pay
        self.gross_pay = (
            self.regular_pay + 
            self.overtime_pay + 
            self.bonus + 
            self.commission
        )
        
        # Calculate total deductions
        pre_tax_deductions = (
            self.health_insurance_deduction +
            self.dental_insurance_deduction +
            self.retirement_contribution
        )
        
        taxes = (
            self.federal_tax +
            self.state_tax +
            self.social_security_tax +
            self.medicare_tax
        )
        
        post_tax_deductions = self.garnishments
        
        # Calculate net pay
        self.net_pay = self.gross_pay - pre_tax_deductions - taxes - post_tax_deductions
        self.save()

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.payroll_period}"

    class Meta:
        unique_together = ['employee', 'payroll_period']
        ordering = ['-payroll_period__start_date']


class TimeEntry(models.Model):
    """
    Time tracking for hourly employees
    Better time tracking than QuickBooks
    """
    ENTRY_TYPES = [
        ('regular', 'Regular'),
        ('overtime', 'Overtime'),
        ('vacation', 'Vacation'),
        ('sick', 'Sick Leave'),
        ('personal', 'Personal Time'),
        ('holiday', 'Holiday'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES, default='regular')
    
    # Time details
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    break_duration = models.DurationField(null=True, blank=True)
    total_hours = models.DecimalField(max_digits=6, decimal_places=2)
    
    # Project/task tracking
    project = models.CharField(max_length=200, blank=True)
    task_description = models.TextField(blank=True)
    
    # Approval
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_time_entries'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # AI features
    gps_location = models.JSONField(default=dict, blank=True)
    is_gps_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.date} ({self.total_hours}h)"

    class Meta:
        ordering = ['-date', '-start_time']


class LeaveRequest(models.Model):
    """
    Employee leave request management
    Advanced leave management vs QuickBooks
    """
    LEAVE_TYPES = [
        ('vacation', 'Vacation'),
        ('sick', 'Sick Leave'),
        ('personal', 'Personal'),
        ('maternity', 'Maternity'),
        ('paternity', 'Paternity'),
        ('bereavement', 'Bereavement'),
        ('jury_duty', 'Jury Duty'),
        ('military', 'Military'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    
    # Date range
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.DecimalField(max_digits=5, decimal_places=1)
    
    # Request details
    reason = models.TextField()
    is_paid = models.BooleanField(default=True)
    
    # Approval workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leave_requests'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    denial_reason = models.TextField(blank=True)
    
    # AI insights
    approval_probability = models.FloatField(default=0.5)
    similar_requests = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.leave_type} ({self.start_date} to {self.end_date})"

    class Meta:
        ordering = ['-created_at']


class PerformanceReview(models.Model):
    """
    Employee performance review system
    Advanced HR features not in QuickBooks
    """
    REVIEW_TYPES = [
        ('annual', 'Annual Review'),
        ('quarterly', 'Quarterly Review'),
        ('probationary', 'Probationary Review'),
        ('project', 'Project Review'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conducted_reviews')
    
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPES)
    review_period_start = models.DateField()
    review_period_end = models.DateField()
    
    # Ratings (1-5 scale)
    overall_rating = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    technical_skills = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    communication = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    teamwork = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    leadership = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    # Comments
    strengths = models.TextField()
    areas_for_improvement = models.TextField()
    goals = models.TextField()
    
    # Employee feedback
    employee_comments = models.TextField(blank=True)
    employee_signature_date = models.DateTimeField(null=True, blank=True)
    
    # AI insights
    ai_performance_analysis = models.JSONField(default=dict)
    recommended_training = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.review_type} ({self.review_period_end})"

    class Meta:
        ordering = ['-review_period_end']
