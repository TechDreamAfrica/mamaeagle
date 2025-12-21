"""
Company-Aware Model Managers and Mixins
Provides automatic company-scoped data filtering for multi-tenant models
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from .middleware import get_current_company

User = get_user_model()


class CompanyScopedManager(models.Manager):
    """
    Manager that automatically filters querysets by company context
    Ensures data isolation between companies
    """
    
    def get_queryset(self):
        """Filter queryset by current company context"""
        queryset = super().get_queryset()
        
        # Get current company from thread-local storage (set by middleware)
        current_company = get_current_company()
        
        if current_company:
            # Filter by current company
            queryset = queryset.filter(company=current_company)
        
        return queryset
    
    def for_company(self, company):
        """Explicitly get objects for a specific company"""
        return super().get_queryset().filter(company=company)
    
    def all_companies(self):
        """Get objects from all companies (for super admin use)"""
        return super().get_queryset()


class UserScopedManager(models.Manager):
    """Manager that filters querysets by user's accessible companies"""
    
    def for_user(self, user):
        """Get objects accessible to a specific user"""
        from .authorization import AuthorizationService
        
        if AuthorizationService.is_super_admin(user):
            return super().get_queryset()
        
        # Get user's accessible companies
        accessible_companies = AuthorizationService.get_user_companies(user)
        return super().get_queryset().filter(company__in=accessible_companies)


class UserCompanyManager(models.Manager):
    """
    Manager for UserCompany relationships.
    Handles user access to multiple companies.
    """
    
    def for_user(self, user):
        """Get all company assignments for a user"""
        return self.filter(user=user, is_active=True)
    
    def for_company(self, company):
        """Get all user assignments for a company"""
        return self.filter(company=company, is_active=True)
    
    def active_assignments(self):
        """Get all active user-company assignments"""
        return self.filter(is_active=True)


class CompanyScopedMixin(models.Model):
    """Mixin for models that should be scoped to a company"""
    
    company = models.ForeignKey(
        'accounts.Company', 
        on_delete=models.CASCADE, 
        related_name='%(app_label)s_%(class)s_set'
    )
    
    # Default manager filters by company
    objects = CompanyScopedManager()
    
    # Manager for user-specific access
    user_objects = UserScopedManager()
    
    # Unfiltered manager for admin/system use
    all_objects = models.Manager()
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """Ensure company is set when saving"""
        if not self.company_id:
            # Try to get company from current context
            current_company = get_current_company()
            if current_company:
                self.company = current_company
            else:
                raise ValidationError("Company must be specified for this model")
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate company assignment"""
        super().clean()
        if not self.company_id:
            raise ValidationError("Company is required")


class AuditMixin(models.Model):
    """Mixin to add audit fields to models"""
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_%(app_label)s_%(class)s_set'
    )
    updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='updated_%(app_label)s_%(class)s_set'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """Mixin to add soft delete functionality"""
    
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='deleted_%(app_label)s_%(class)s_set'
    )
    
    class Meta:
        abstract = True
    
    def delete(self, *args, **kwargs):
        """Soft delete instead of hard delete"""
        from django.utils import timezone
        
        self.is_deleted = True
        self.deleted_at = timezone.now()
        
        # Try to get current user from context if available
        current_user = getattr(self, '_current_user', None)
        if current_user:
            self.deleted_by = current_user
        
        self.save()
    
    def restore(self):
        """Restore soft deleted object"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()


class SoftDeleteManager(models.Manager):
    """Manager that excludes soft-deleted objects by default"""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def deleted(self):
        """Get soft-deleted objects"""
        return super().get_queryset().filter(is_deleted=True)
    
    def with_deleted(self):
        """Get all objects including soft-deleted ones"""
        return super().get_queryset()


class CompanyAwareSoftDeleteManager(CompanyScopedManager):
    """Manager that combines company scoping with soft delete filtering"""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def deleted(self):
        """Get soft-deleted objects for current company"""
        return super().get_queryset().filter(is_deleted=True)
    
    def with_deleted(self):
        """Get all objects for current company including soft-deleted ones"""
        return super().get_queryset()


class SecureModelMixin(CompanyScopedMixin, AuditMixin, SoftDeleteMixin):
    """Complete mixin that combines company scoping, audit trails, and soft delete"""
    
    objects = CompanyAwareSoftDeleteManager()
    all_objects = models.Manager()
    
    class Meta:
        abstract = True


# Utility functions for authorization checks in models
def validate_user_company_access(user, company, action="access"):
    """Validate that user can access the specified company"""
    from .authorization import AuthorizationService
    
    if not AuthorizationService.can_access_company(user, company):
        raise ValidationError(
            f"User {user.username} does not have {action} permission for company {company.name}"
        )


def validate_user_permission(user, permission, company=None):
    """Validate that user has the specified permission"""
    from .authorization import AuthorizationService
    
    if not AuthorizationService.has_permission(user, permission, company):
        raise ValidationError(
            f"User {user.username} does not have permission {permission.value}"
            f"{f' for company {company.name}' if company else ''}"
        )


# Custom field for company-aware foreign keys
class CompanyAwareForeignKey(models.ForeignKey):
    """Foreign key that validates related object belongs to same company"""
    
    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        
        if value and hasattr(model_instance, 'company') and hasattr(value, 'company'):
            if model_instance.company != value.company:
                raise ValidationError(
                    f"Related object must belong to the same company ({model_instance.company})"
                )


# Backward compatibility aliases
CompanyManager = CompanyScopedManager


# For models that already use UserCompanyManager  
class UserCompanyManager(models.Manager):
    """
    Manager for UserCompany relationships.
    Handles user access to multiple companies.
    """
    
    def for_user(self, user):
        """Get all company assignments for a user"""
        return self.filter(user=user, is_active=True)
    
    def for_company(self, company):
        """Get all user assignments for a company"""
        return self.filter(company=company, is_active=True)
    
    def active_assignments(self):
        """Get all active user-company assignments"""
        return self.filter(is_active=True)
        """Get all companies accessible by a user"""
        return self.filter(user=user)
    
    def active_for_user(self, user):
        """Get active company relationships for a user"""
        return self.filter(user=user, is_active=True)
    
    def can_access_company(self, user, company):
        """Check if user has access to a specific company"""
        return self.filter(user=user, company=company, is_active=True).exists()
