"""
Mixins and Decorators for Company-Based Access Control
"""
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


class CompanyAccessMixin:
    """
    Mixin for class-based views to ensure company-based access control.
    Automatically filters querysets by current company.
    """
    
    def get_queryset(self):
        """Override to filter by company"""
        queryset = super().get_queryset()
        
        # If model has a company field, filter by it
        if hasattr(queryset.model, 'company'):
            company = getattr(self.request, 'company', None)
            if company:
                queryset = queryset.filter(company=company)
            elif not self.request.user.is_superuser:
                # No company and not superuser = no access
                queryset = queryset.none()
        
        return queryset
    
    def dispatch(self, request, *args, **kwargs):
        """Check company access before dispatching"""
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        # Superusers can access everything
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        # Regular users must have a company
        if not getattr(request, 'company', None):
            messages.error(request, 'You must be associated with a company to access this resource.')
            return redirect('dashboard:home')
        
        return super().dispatch(request, *args, **kwargs)


class MultiCompanyAccessMixin(CompanyAccessMixin):
    """
    Mixin for views that support multi-company access.
    Used for consolidated reports, super admin views, etc.
    """
    
    def get_accessible_companies(self):
        """Get all companies the user has access to"""
        from accounts.models import UserCompany
        
        if self.request.user.is_superuser:
            from accounts.models import Company
            return Company.objects.all()
        
        return UserCompany.objects.filter(
            user=self.request.user,
            is_active=True
        ).values_list('company', flat=True)


def require_company_access(view_func):
    """
    Decorator for function-based views to ensure company access.
    Usage: @require_company_access
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        if not getattr(request, 'company', None):
            messages.error(request, 'You must be associated with a company to access this resource.')
            return redirect('dashboard:home')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def company_admin_required(view_func):
    """
    Decorator to require admin role in the current company.
    Usage: @company_admin_required
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Check if user is admin in current company
        from accounts.models import UserCompany
        company = getattr(request, 'company', None)
        
        if not company:
            messages.error(request, 'No active company found.')
            return redirect('dashboard:home')
        
        try:
            user_company = UserCompany.objects.get(user=request.user, company=company)
            if user_company.role not in ['admin', 'owner']:
                raise PermissionDenied('You must be a company administrator to access this resource.')
        except UserCompany.DoesNotExist:
            raise PermissionDenied('You do not have access to this company.')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
