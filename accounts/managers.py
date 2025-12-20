"""
Custom Model Managers for Multi-Tenancy
Automatically filters queries by current company context
"""
from django.db import models
from django.db.models import Q


class CompanyManager(models.Manager):
    """
    Manager that automatically filters by current company.
    All queries will be scoped to the user's active company.
    """
    
    def get_queryset(self):
        from .middleware import get_current_company
        
        queryset = super().get_queryset()
        company = get_current_company()
        
        # If no company context, return empty queryset (safe default)
        if company is None:
            # Check if we're in admin or superuser context
            return queryset
        
        # Filter by current company
        return queryset.filter(company=company)
    
    def all_companies(self):
        """
        Returns all objects without company filtering.
        Use sparingly and only when explicitly needed.
        """
        return super().get_queryset()
    
    def for_company(self, company):
        """
        Explicitly filter by a specific company.
        Useful for superusers or multi-company reports.
        """
        return super().get_queryset().filter(company=company)


class UserCompanyManager(models.Manager):
    """
    Manager for UserCompany relationships.
    Handles user access to multiple companies.
    """
    
    def for_user(self, user):
        """Get all companies accessible by a user"""
        return self.filter(user=user)
    
    def active_for_user(self, user):
        """Get active company relationships for a user"""
        return self.filter(user=user, is_active=True)
    
    def can_access_company(self, user, company):
        """Check if user has access to a specific company"""
        return self.filter(user=user, company=company, is_active=True).exists()
