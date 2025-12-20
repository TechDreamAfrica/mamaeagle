"""
Team Management Models
Handles user invitations, team member permissions, and role management
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.crypto import get_random_string
import datetime

User = get_user_model()


class UserInvitation(models.Model):
    """
    Handles secure user invitations with email links
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    email = models.EmailField()
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='invitations')
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_invitations')
    
    # Role assignment
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES, default='employee')
    department = models.CharField(max_length=100, blank=True)
    
    # Invitation details
    token = models.CharField(max_length=64, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Permissions
    permissions = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    # Personal message
    message = models.TextField(blank=True, help_text="Optional welcome message")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'status']),
            models.Index(fields=['token']),
        ]
    
    def __str__(self):
        return f"Invitation for {self.email} to {self.company.name}"
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = get_random_string(64)
        if not self.expires_at:
            self.expires_at = timezone.now() + datetime.timedelta(days=7)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if invitation is still valid"""
        return (
            self.status == 'pending' and
            self.expires_at > timezone.now()
        )
    
    def accept(self, user):
        """Mark invitation as accepted"""
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.save()
        
        # Create UserCompany relationship
        from .models import UserCompany
        UserCompany.objects.create(
            user=user,
            company=self.company,
            role=self.role,
            permissions=self.permissions
        )
    
    def cancel(self):
        """Cancel invitation"""
        self.status = 'cancelled'
        self.save()
    
    def check_expiry(self):
        """Check and update expired status"""
        if self.status == 'pending' and self.expires_at <= timezone.now():
            self.status = 'expired'
            self.save()
            return True
        return False


class TeamMember(models.Model):
    """
    Extended team member information with detailed permissions
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='team_members')
    
    # Access control
    is_active = models.BooleanField(default=True)
    can_invite_users = models.BooleanField(default=False)
    can_manage_roles = models.BooleanField(default=False)
    
    # Module permissions
    module_permissions = models.JSONField(
        default=dict,
        help_text="Granular permissions for each module"
    )
    
    # Activity tracking
    last_active = models.DateTimeField(null=True, blank=True)
    login_count = models.IntegerField(default=0)
    
    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'company']
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.company.name}"
    
    def get_default_permissions(self):
        """Get default permissions based on role"""
        role = self.user.role
        
        permissions = {
            'admin': {
                'dashboard': {'view': True, 'edit': True, 'delete': True},
                'invoicing': {'view': True, 'create': True, 'edit': True, 'delete': True},
                'expenses': {'view': True, 'create': True, 'edit': True, 'delete': True},
                'inventory': {'view': True, 'create': True, 'edit': True, 'delete': True},
                'hr': {'view': True, 'create': True, 'edit': True, 'delete': True},
                'reports': {'view': True, 'create': True, 'edit': True, 'delete': True},
                'sales': {'view': True, 'create': True, 'edit': True, 'delete': True},
                'bank_reconciliation': {'view': True, 'create': True, 'edit': True},
                'ai_insights': {'view': True},
                'welfare': {'view': True, 'create': True, 'edit': True},
            },
            'accountant': {
                'dashboard': {'view': True},
                'invoicing': {'view': True, 'create': True, 'edit': True},
                'expenses': {'view': True, 'create': True, 'edit': True},
                'inventory': {'view': True},
                'hr': {'view': True},
                'reports': {'view': True, 'create': True},
                'sales': {'view': True},
                'bank_reconciliation': {'view': True, 'create': True, 'edit': True},
                'ai_insights': {'view': True},
                'welfare': {'view': True},
            },
            'manager': {
                'dashboard': {'view': True},
                'invoicing': {'view': True, 'create': True},
                'expenses': {'view': True, 'create': True, 'edit': True},
                'inventory': {'view': True, 'create': True},
                'hr': {'view': True, 'create': True},
                'reports': {'view': True},
                'sales': {'view': True, 'create': True},
                'bank_reconciliation': {'view': True},
                'ai_insights': {'view': True},
                'welfare': {'view': True, 'create': True},
            },
            'employee': {
                'dashboard': {'view': True},
                'invoicing': {'view': False},
                'expenses': {'view': True, 'create': True},
                'inventory': {'view': True},
                'hr': {'view': False},
                'reports': {'view': False},
                'sales': {'view': False},
                'bank_reconciliation': {'view': False},
                'ai_insights': {'view': False},
                'welfare': {'view': True},
            },
        }
        
        return permissions.get(role, permissions['employee'])
    
    def has_module_permission(self, module, action='view'):
        """Check if user has permission for a module action"""
        if not self.is_active:
            return False
        
        if not self.module_permissions:
            self.module_permissions = self.get_default_permissions()
            self.save()
        
        module_perms = self.module_permissions.get(module, {})
        return module_perms.get(action, False)


class RoleTemplate(models.Model):
    """
    Custom role templates for companies
    """
    name = models.CharField(max_length=100)
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='role_templates')
    description = models.TextField(blank=True)
    
    # Permissions
    permissions = models.JSONField(default=dict)
    
    # Settings
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['name', 'company']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.company.name}"
