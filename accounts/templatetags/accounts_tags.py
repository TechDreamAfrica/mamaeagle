"""
Template tags for accounts app
"""
from django import template
from accounts.models import UserCompany

register = template.Library()


@register.simple_tag
def get_user_companies(user):
    """Get all companies a user has access to"""
    return UserCompany.objects.filter(user=user, is_active=True).select_related('company')


@register.simple_tag
def can_create_company(user):
    """Check if user can create another company - only super admins"""
    if user.is_superuser or user.is_super_admin or user.role == 'super_admin':
        return True
    
    # Only super admins can create companies
    return False


@register.simple_tag
def get_company_limit_info(user):
    """Get information about company limits - only super admins can create"""
    if user.is_superuser or user.is_super_admin or user.role == 'super_admin':
        company_count = UserCompany.objects.filter(
            user=user,
            role__in=['owner', 'admin'],
            is_active=True
        ).count()
        
        return {
            'current': company_count,
            'max': -1,  # -1 means unlimited for super admins
            'can_create': True
        }
    
    # Non-super admins cannot create companies
    return {
        'current': 0,
        'max': 0,
        'can_create': False
    }
