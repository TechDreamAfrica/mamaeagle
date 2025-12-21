"""
Authorization decorators for view-level security enforcement.
Provides decorators for permissions, roles, audit logging, and access control.
"""

from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from typing import Optional, List, Callable, Any

from .models import Company
from .authorization import AuthorizationService, Permission, Action


def require_permissions(permissions: List[Permission], company_param: str = None):
    """
    Decorator to require specific permissions for a view
    
    Args:
        permissions: List of required permissions
        company_param: Name of the parameter/attribute that contains the company
                      (e.g., 'company_id' for URL parameter, 'company' for object)
    
    Usage:
        @require_permissions([Permission.CREATE_USER], company_param='company_id')
        def create_user_view(request, company_id):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Get company if specified
            company = None
            if company_param:
                if company_param in kwargs:
                    # Company ID from URL parameter
                    company_id = kwargs[company_param]
                    company = get_object_or_404(Company, id=company_id, is_active=True)
                elif hasattr(request, company_param):
                    # Company from request attribute
                    company = getattr(request, company_param)
            
            # Check all required permissions
            auth_service = AuthorizationService()
            for permission in permissions:
                auth_service.enforce_permission(request.user, permission, company)
            
            # Add company to request if found
            if company:
                request.company = company
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def require_company_access(company_param: str = 'company_id'):
    """
    Decorator to ensure user has access to the specified company
    
    Args:
        company_param: Name of the URL parameter containing company ID
    
    Usage:
        @require_company_access('company_id')
        def company_detail_view(request, company_id):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            company_id = kwargs.get(company_param)
            if not company_id:
                raise PermissionDenied("Company ID not provided")
            
            company = get_object_or_404(Company, id=company_id, is_active=True)
            
            auth_service = AuthorizationService()
            if not auth_service.can_access_company(request.user, company):
                raise PermissionDenied("Access denied to this company")
            
            # Add company to request and kwargs for convenience
            request.company = company
            kwargs['company'] = company
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def super_admin_required(view_func):
    """
    Decorator to require super admin privileges
    
    Usage:
        @super_admin_required
        def admin_only_view(request):
            pass
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        auth_service = AuthorizationService()
        if not auth_service.is_super_admin(request.user):
            raise PermissionDenied("Super admin privileges required")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def company_admin_required(company_param: str = 'company_id'):
    """
    Decorator to require company admin role
    
    Args:
        company_param: Name of parameter containing company
    
    Usage:
        @company_admin_required('company_id')
        def admin_view(request, company_id):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            company_id = kwargs.get(company_param)
            if not company_id:
                raise PermissionDenied("Company ID not provided")
            
            company = get_object_or_404(Company, id=company_id, is_active=True)
            
            auth_service = AuthorizationService()
            if not auth_service.is_super_admin(request.user):
                user_company = auth_service.get_user_role_in_company(request.user, company)
                if not user_company or user_company.role != 'admin':
                    raise PermissionDenied("Company admin privileges required")
            
            request.company = company
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def audit_sensitive_action(action: Action, resource_type: str):
    """
    Decorator for sensitive actions that require extra audit logging
    
    Usage:
        @audit_sensitive_action(Action.DELETE, 'company')
        def delete_company_view(request, company_id):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            auth_service = AuthorizationService()
            
            # Log the attempt before execution
            auth_service.log_action(
                user=request.user,
                action=action,
                resource_type=resource_type,
                details={
                    'view_name': view_func.__name__,
                    'args': list(args),
                    'kwargs': {k: v for k, v in kwargs.items() if not callable(v)}
                },
                is_security_event=True
            )
            
            try:
                response = view_func(request, *args, **kwargs)
                return response
                
            except Exception as e:
                # Log failed execution
                auth_service.log_action(
                    user=request.user,
                    action=action,
                    resource_type=resource_type,
                    details={
                        'view_name': view_func.__name__,
                        'error': str(e),
                        'error_type': type(e).__name__
                    },
                    is_security_event=True,
                    is_failed_attempt=True
                )
                raise
        return _wrapped_view
    return decorator


def api_require_permissions(permissions: List[Permission], company_param: str = None):
    """
    API version of require_permissions that returns JSON responses
    
    Usage:
        @api_require_permissions([Permission.VIEW_REPORTS], company_param='company_id')
        def api_reports_view(request, company_id):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            try:
                # Get company if specified
                company = None
                if company_param and company_param in kwargs:
                    company_id = kwargs[company_param]
                    company = Company.objects.get(id=company_id, is_active=True)
                
                # Check all required permissions
                auth_service = AuthorizationService()
                for permission in permissions:
                    auth_service.enforce_permission(request.user, permission, company)
                
                # Add company to request if found
                if company:
                    request.company = company
                
                return view_func(request, *args, **kwargs)
                
            except PermissionDenied as e:
                return JsonResponse({
                    'error': 'Permission denied',
                    'message': str(e)
                }, status=403)
            except Company.DoesNotExist:
                return JsonResponse({
                    'error': 'Company not found'
                }, status=404)
            except Exception as e:
                return JsonResponse({
                    'error': 'Internal error',
                    'message': str(e)
                }, status=500)
        return _wrapped_view
    return decorator