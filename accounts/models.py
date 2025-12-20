from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class Branch(models.Model):
    """
    Branch model for Mama Eagle Enterprise
    Supports unlimited branches for multi-location business
    """
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    
    # Address information
    address_line_1 = models.CharField(max_length=200, blank=True)
    address_line_2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='Ghana')
    
    # Contact information
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    manager_name = models.CharField(max_length=200, blank=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    is_head_office = models.BooleanField(default=False)
    settings = models.JSONField(default=dict, blank=True)
    
    # Audit fields
    created_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_branches')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name_plural = "Branches"
        ordering = ['name']

    def save(self, *args, **kwargs):
        # Ensure only one head office
        if self.is_head_office:
            Branch.objects.filter(is_head_office=True).update(is_head_office=False)
        super().save(*args, **kwargs)


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    Enhanced for Mama Eagle Enterprise with branch assignment
    """
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('branch_manager', 'Branch Manager'),
        ('accountant', 'Accountant'),
        ('manager', 'Manager'),
        ('employee', 'Employee'),
        ('client', 'Client'),
    ]
    
    email = models.EmailField(unique=True)
    phone_number = models.CharField(
        max_length=17,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')],
        blank=True
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    department = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    is_active_employee = models.BooleanField(default=True)
    employee_id = models.CharField(max_length=20, blank=True, null=True, unique=True)
    hire_date = models.DateField(blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Branch assignment - users can be assigned to specific branches
    current_branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_users')
    can_access_all_branches = models.BooleanField(default=False, help_text="Admin privilege to access all branches")
    
    # AI preferences
    ai_insights_enabled = models.BooleanField(default=True)
    notification_preferences = models.JSONField(default=dict, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    def get_accessible_branches(self):
        """
        Get branches the user can access
        """
        if self.can_access_all_branches or self.role == 'admin':
            return Branch.objects.filter(is_active=True)
        elif self.current_branch:
            # Users assigned to branches through UserBranch model
            return Branch.objects.filter(
                id__in=self.branch_assignments.filter(is_active=True).values_list('branch_id', flat=True)
            )
        return Branch.objects.none()
    
    @property
    def company(self):
        """
        Get the user's primary company (first active company they belong to)
        """
        from accounts.models import UserCompany
        user_company = UserCompany.objects.filter(user=self, is_active=True).first()
        return user_company.company if user_company else None


class Company(models.Model):
    """
    Company model for multi-tenancy - Mama Eagle Enterprise
    Unlimited companies vs QuickBooks' limitations
    """
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=50, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    
    # Address
    address_line_1 = models.CharField(max_length=200, blank=True)
    address_line_2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='Ghana')
    
    # Financial settings
    fiscal_year_start = models.DateField()
    currency = models.CharField(max_length=3, default='GHS')
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Logo and branding
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#0ea5e9')
    
    # Settings
    settings = models.JSONField(default=dict)
    
    # Audit fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_companies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Companies"


class UserCompany(models.Model):
    """
    Many-to-many relationship between Users and Companies
    Supports unlimited users per company - removed subscription limits
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, default='employee')
    is_active = models.BooleanField(default=True)
    permissions = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.company.name}"

    class Meta:
        unique_together = ['user', 'company']


class UserBranch(models.Model):
    """
    Many-to-many relationship between Users and Branches
    Allows users to be assigned to multiple branches
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='branch_assignments')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='user_assignments')
    role = models.CharField(max_length=50, default='employee')
    is_active = models.BooleanField(default=True)
    permissions = models.JSONField(default=list)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='branch_assignments_made')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.branch.name}"

    class Meta:
        unique_together = ['user', 'branch']
        verbose_name = "User Branch Assignment"
        verbose_name_plural = "User Branch Assignments"
