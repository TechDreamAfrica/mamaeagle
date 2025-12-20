from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary by key
    Usage: {{ my_dict|get_item:my_key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def has_permission(permissions_dict, module_action):
    """
    Check if a module has a specific permission
    Usage: {{ team_permissions|has_permission:'invoicing:view' }}
    """
    if not permissions_dict:
        return False
    
    try:
        module, action = module_action.split(':')
        module_perms = permissions_dict.get(module, [])
        return action in module_perms
    except (ValueError, AttributeError):
        return False
