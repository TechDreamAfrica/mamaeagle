from .team_models import TeamMember
from .models import UserCompany

# Default role -> module permissions mapping
ROLE_DEFAULTS = {
    'admin': {
        'dashboard': ['view', 'create', 'edit', 'delete'],
        'invoicing': ['view', 'create', 'edit', 'delete'],
        'expenses': ['view', 'create', 'edit', 'delete'],
        'inventory': ['view', 'create', 'edit', 'delete'],
        'hr': ['view', 'create', 'edit', 'delete'],
        'reports': ['view', 'create', 'edit'],
        'sales': ['view', 'create', 'edit', 'delete'],
        'bank_reconciliation': ['view', 'create', 'edit'],
        'ai_insights': ['view'],
        'welfare': ['view', 'create', 'edit'],
    },
    'accountant': {
        'dashboard': ['view'],
        'invoicing': ['view', 'create', 'edit'],
        'expenses': ['view', 'create', 'edit'],
        'inventory': ['view'],
        'hr': ['view'],
        'reports': ['view', 'create'],
        'sales': ['view'],
        'bank_reconciliation': ['view', 'create', 'edit'],
        'ai_insights': ['view'],
        'welfare': ['view'],
    },
    'manager': {
        'dashboard': ['view'],
        'invoicing': ['view'],
        'expenses': ['view'],
        'inventory': ['view'],
        'hr': ['view', 'create', 'edit'],
        'reports': ['view', 'create'],
        'sales': ['view', 'create', 'edit'],
        'bank_reconciliation': ['view'],
        'ai_insights': ['view'],
        'welfare': ['view', 'create'],
    },
    'employee': {
        'dashboard': ['view'],
        'invoicing': ['view'],
        'expenses': ['view', 'create'],
        'inventory': ['view'],
        'hr': [],
        'reports': [],
        'sales': [],
        'bank_reconciliation': [],
        'ai_insights': [],
        'welfare': [],
    },
    'viewer': {
        'dashboard': ['view'],
        'invoicing': ['view'],
        'expenses': ['view'],
        'inventory': ['view'],
        'hr': ['view'],
        'reports': ['view'],
        'sales': ['view'],
        'bank_reconciliation': ['view'],
        'ai_insights': ['view'],
        'welfare': ['view'],
    }
}


def team_permissions(request):
    """Context processor that returns effective team permissions for the current user.

    Returns:
        {'team_permissions': {module: [actions,...]}, 'can_invite_users': bool, 'can_manage_roles': bool}
    """
    if not request.user.is_authenticated:
        return {}

    user = request.user
    
    # Superusers and staff get full access to everything
    if user.is_superuser or user.is_staff:
        full_permissions = {
            'dashboard': ['view', 'create', 'edit', 'delete'],
            'invoicing': ['view', 'create', 'edit', 'delete'],
            'expenses': ['view', 'create', 'edit', 'delete'],
            'inventory': ['view', 'create', 'edit', 'delete'],
            'hr': ['view', 'create', 'edit', 'delete'],
            'reports': ['view', 'create', 'edit', 'delete'],
            'sales': ['view', 'create', 'edit', 'delete'],
            'bank_reconciliation': ['view', 'create', 'edit', 'delete'],
            'ai_insights': ['view'],
            'welfare': ['view', 'create', 'edit', 'delete'],
        }
        return {
            'team_permissions': full_permissions,
            'can_invite_users': True,
            'can_manage_roles': True,
        }
    
    company = getattr(user, 'company', None)

    module_permissions = {}
    can_invite = False
    can_manage_roles = False

    try:
        tm = TeamMember.objects.filter(user=user, company=company).first()
    except Exception:
        tm = None

    if tm:
        # use team_member explicit permissions
        module_permissions = tm.module_permissions or {}
        can_invite = bool(tm.can_invite_users)
        can_manage_roles = bool(tm.can_manage_roles)
    else:
        # fallback to role defaults
        role = getattr(user, 'role', 'viewer')
        module_permissions = ROLE_DEFAULTS.get(role, ROLE_DEFAULTS['viewer']).copy()
        # promote to minimal booleans
        can_invite = False
        can_manage_roles = (role == 'admin')

    return {
        'team_permissions': module_permissions,
        'can_invite_users': can_invite,
        'can_manage_roles': can_manage_roles,
    }
