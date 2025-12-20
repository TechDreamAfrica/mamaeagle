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
    """Check if user can create another company - unlimited in Mama Eagle Enterprise"""
    if user.is_superuser:
        return True
    
    # Mama Eagle Enterprise allows unlimited companies
    return True


@register.simple_tag
def get_company_limit_info(user):
    """Get information about company limits - unlimited in Mama Eagle Enterprise"""
    if user.is_superuser:
        return {'current': 0, 'max': -1, 'can_create': True}
    
    company_count = UserCompany.objects.filter(
        user=user,
        role__in=['owner', 'admin'],
        is_active=True
    ).count()
    
    # Mama Eagle Enterprise allows unlimited companies
    return {
        'current': company_count,
        'max': -1,  # -1 means unlimited
        'can_create': True
    }
