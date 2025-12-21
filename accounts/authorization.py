"""
Authorization Service for Multi-Tenant Company Management
Handles role-based access control, permissions, and audit logging
"""
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from typing import Optional, List, Dict, Any
from enum import Enum
import logging

from .models import Company, UserCompany, AuditLog

User = get_user_model()
logger = logging.getLogger(__name__)


class Permission(Enum):
    """Enum for granular permissions"""
    # Company Management
    CREATE_COMPANY = "create_company"
    UPDATE_COMPANY = "update_company"
    DEACTIVATE_COMPANY = "deactivate_company"
    DELETE_COMPANY = "delete_company"
    VIEW_COMPANY = "view_company"
    
    # User Management
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DEACTIVATE_USER = "deactivate_user"
    DELETE_USER = "delete_user"
    VIEW_USER = "view_user"
    ASSIGN_USER_TO_COMPANY = "assign_user_to_company"
    REMOVE_USER_FROM_COMPANY = "remove_user_from_company"
    
    # Role Management
    ASSIGN_ROLE = "assign_role"
    UPDATE_ROLE = "update_role"
    VIEW_ROLES = "view_roles"
    
    # Data Access
    VIEW_ACCOUNTING_DATA = "view_accounting_data"
    CREATE_ACCOUNTING_DATA = "create_accounting_data"
    UPDATE_ACCOUNTING_DATA = "update_accounting_data"
    DELETE_ACCOUNTING_DATA = "delete_accounting_data"
    
    # Reports
    VIEW_REPORTS = "view_reports"
    EXPORT_REPORTS = "export_reports"
    
    # System Administration
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_SYSTEM_SETTINGS = "manage_system_settings"


class Action(Enum):
    """Enum for audit log actions"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    SWITCH_COMPANY = "switch_company"
    ASSIGN_ROLE = "assign_role"
    REVOKE_ACCESS = "revoke_access"


class AuthorizationService:
    """
    Service class for handling authorization logic, permissions, and audit logging
    """
    
    # Role hierarchy and default permissions
    ROLE_PERMISSIONS = {
        'super_admin': [
            # Super Admin has all permissions
            Permission.CREATE_COMPANY, Permission.UPDATE_COMPANY, Permission.DEACTIVATE_COMPANY,
            Permission.DELETE_COMPANY, Permission.VIEW_COMPANY,
            Permission.CREATE_USER, Permission.UPDATE_USER, Permission.DEACTIVATE_USER,
            Permission.DELETE_USER, Permission.VIEW_USER, Permission.ASSIGN_USER_TO_COMPANY,
            Permission.REMOVE_USER_FROM_COMPANY, Permission.ASSIGN_ROLE, Permission.UPDATE_ROLE,
            Permission.VIEW_ROLES, Permission.VIEW_ACCOUNTING_DATA, Permission.CREATE_ACCOUNTING_DATA,
            Permission.UPDATE_ACCOUNTING_DATA, Permission.DELETE_ACCOUNTING_DATA,
            Permission.VIEW_REPORTS, Permission.EXPORT_REPORTS, Permission.VIEW_AUDIT_LOGS,
            Permission.MANAGE_SYSTEM_SETTINGS
        ],
        'admin': [
            # Company Admin - limited to their company
            Permission.VIEW_COMPANY, Permission.UPDATE_COMPANY,
            Permission.CREATE_USER, Permission.UPDATE_USER, Permission.DEACTIVATE_USER,
            Permission.VIEW_USER, Permission.ASSIGN_USER_TO_COMPANY, Permission.REMOVE_USER_FROM_COMPANY,
            Permission.ASSIGN_ROLE, Permission.UPDATE_ROLE, Permission.VIEW_ROLES,
            Permission.VIEW_ACCOUNTING_DATA, Permission.CREATE_ACCOUNTING_DATA,
            Permission.UPDATE_ACCOUNTING_DATA, Permission.DELETE_ACCOUNTING_DATA,
            Permission.VIEW_REPORTS, Permission.EXPORT_REPORTS
        ],
        'manager': [
            Permission.VIEW_COMPANY, Permission.VIEW_USER, Permission.VIEW_ACCOUNTING_DATA,
            Permission.CREATE_ACCOUNTING_DATA, Permission.UPDATE_ACCOUNTING_DATA,
            Permission.VIEW_REPORTS, Permission.EXPORT_REPORTS
        ],
        'accountant': [
            Permission.VIEW_COMPANY, Permission.VIEW_USER, Permission.VIEW_ACCOUNTING_DATA,
            Permission.CREATE_ACCOUNTING_DATA, Permission.UPDATE_ACCOUNTING_DATA, Permission.VIEW_REPORTS
        ],
        'employee': [
            Permission.VIEW_COMPANY, Permission.VIEW_USER, Permission.VIEW_ACCOUNTING_DATA, Permission.VIEW_REPORTS
        ],
        'client': [
            Permission.VIEW_COMPANY, Permission.VIEW_ACCOUNTING_DATA
        ]
    }

    @classmethod
    def is_super_admin(cls, user: User) -> bool:
        """Check if user is a super administrator"""
        return user.is_authenticated and (
            user.is_superuser or 
            (hasattr(user, 'role') and user.role == 'super_admin')
        )

    @classmethod
    def get_user_companies(cls, user: User) -> List[Company]:
        """Get all companies user has access to"""
        if cls.is_super_admin(user):
            return list(Company.objects.filter(is_active=True))
        
        return [uc.company for uc in UserCompany.objects.filter(
            user=user, is_active=True
        ).select_related('company')]

    @classmethod
    def get_user_role_in_company(cls, user: User, company: Company) -> Optional[str]:
        """Get user's role in a specific company"""
        if cls.is_super_admin(user):
            return 'super_admin'
        
        try:
            user_company = UserCompany.objects.get(
                user=user, company=company, is_active=True
            )
            return user_company.role
        except UserCompany.DoesNotExist:
            return None

    @classmethod
    def has_permission(cls, user: User, permission: Permission, company: Company = None) -> bool:
        """
        Check if user has a specific permission
        For company-scoped permissions, company parameter is required
        """
        if not user.is_authenticated:
            return False
        
        # Super admin bypasses all restrictions
        if cls.is_super_admin(user):
            return True
        
        # For company-scoped permissions, check user's role in that company
        if company:
            role = cls.get_user_role_in_company(user, company)
            if not role:
                return False
            
            permissions = cls.ROLE_PERMISSIONS.get(role, [])
            return permission in permissions
        
        # For global permissions (like creating companies), check global role
        permissions = cls.ROLE_PERMISSIONS.get(user.role, [])
        return permission in permissions

    @classmethod
    def enforce_permission(cls, user: User, permission: Permission, company: Company = None):
        """Enforce a permission or raise PermissionDenied"""
        if not cls.has_permission(user, permission, company):
            cls.log_security_event(
                user, Action.READ, 'permission_denied',
                {'permission': permission.value, 'company_id': company.id if company else None}
            )
            raise PermissionDenied(
                f"User {user.username} does not have permission {permission.value}"
                f"{f' for company {company.name}' if company else ''}"
            )

    @classmethod
    def can_access_company(cls, user: User, company: Company) -> bool:
        """Check if user can access a specific company"""
        if cls.is_super_admin(user):
            return True
        
        return UserCompany.objects.filter(
            user=user, company=company, is_active=True
        ).exists()

    @classmethod
    def enforce_company_access(cls, user: User, company: Company):
        """Enforce company access or raise PermissionDenied"""
        if not cls.can_access_company(user, company):
            cls.log_security_event(
                user, Action.READ, 'company_access_denied',
                {'company_id': company.id, 'company_name': company.name}
            )
            raise PermissionDenied(
                f"User {user.username} does not have access to company {company.name}"
            )

    @classmethod
    def can_manage_user(cls, manager: User, target_user: User, company: Company) -> bool:
        """Check if manager can manage target user in the given company"""
        # Super admin can manage anyone
        if cls.is_super_admin(manager):
            return True
        
        # Check if manager has admin role in the company
        manager_role = cls.get_user_role_in_company(manager, company)
        if manager_role not in ['admin', 'manager']:
            return False
        
        # Check if target user is in the same company
        target_role = cls.get_user_role_in_company(target_user, company)
        if not target_role:
            return False
        
        # Company admin can manage users but not other admins (unless they're super admin)
        if manager_role == 'admin' and target_role == 'admin' and not cls.is_super_admin(manager):
            return False
        
        return True

    @classmethod
    @transaction.atomic
    def assign_user_to_company(
        cls, 
        assigner: User, 
        target_user: User, 
        company: Company, 
        role: str,
        permissions: List[str] = None
    ) -> UserCompany:
        """Assign a user to a company with proper authorization checks"""
        
        # Check if assigner can assign users to this company
        cls.enforce_permission(assigner, Permission.ASSIGN_USER_TO_COMPANY, company)
        
        # Create or update user company assignment
        user_company, created = UserCompany.objects.update_or_create(
            user=target_user,
            company=company,
            defaults={
                'role': role,
                'is_active': True,
                'assigned_by': assigner,
                'permissions': permissions or []
            }
        )
        
        # Log the action
        cls.log_action(
            assigner, Action.ASSIGN_ROLE if not created else Action.CREATE,
            'user_company_assignment',
            {
                'target_user_id': target_user.id,
                'target_username': target_user.username,
                'company_id': company.id,
                'company_name': company.name,
                'role': role,
                'created': created
            },
            company
        )
        
        return user_company

    @classmethod
    @transaction.atomic
    def remove_user_from_company(
        cls,
        remover: User,
        target_user: User,
        company: Company
    ):
        """Remove a user from a company with proper authorization checks"""
        
        # Check if remover can remove users from this company
        cls.enforce_permission(remover, Permission.REMOVE_USER_FROM_COMPANY, company)
        
        # Check if remover can manage this specific user
        if not cls.can_manage_user(remover, target_user, company):
            raise PermissionDenied(f"Cannot manage user {target_user.username}")
        
        try:
            user_company = UserCompany.objects.get(
                user=target_user, company=company, is_active=True
            )
            user_company.is_active = False
            user_company.save()
            
            # Log the action
            cls.log_action(
                remover, Action.REVOKE_ACCESS, 'user_company_removal',
                {
                    'target_user_id': target_user.id,
                    'target_username': target_user.username,
                    'company_id': company.id,
                    'company_name': company.name,
                    'previous_role': user_company.role
                },
                company
            )
            
        except UserCompany.DoesNotExist:
            raise ValueError(f"User {target_user.username} is not assigned to company {company.name}")

    @classmethod
    def log_action(
        cls,
        user: User,
        action: Action,
        resource_type: str,
        details: Dict[str, Any],
        company: Company = None
    ):
        """Log user actions for audit trail"""
        try:
            AuditLog.objects.create(
                user=user,
                company=company,
                action=action.value,
                resource_type=resource_type,
                details=details,
                ip_address=getattr(user, '_request_ip', None),
                user_agent=getattr(user, '_request_user_agent', None),
                timestamp=timezone.now()
            )
        except Exception as e:
            logger.error(f"Failed to log action: {e}")

    @classmethod
    def log_security_event(
        cls,
        user: User,
        action: Action,
        event_type: str,
        details: Dict[str, Any]
    ):
        """Log security-related events"""
        try:
            AuditLog.objects.create(
                user=user,
                action=action.value,
                resource_type='security_event',
                details={
                    'event_type': event_type,
                    **details
                },
                ip_address=getattr(user, '_request_ip', None),
                user_agent=getattr(user, '_request_user_agent', None),
                timestamp=timezone.now(),
                is_security_event=True
            )
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    @classmethod
    def get_filtered_queryset(cls, user: User, queryset, company_field='company'):
        """
        Filter queryset based on user's company access
        This enforces company-scoped data access
        """
        if cls.is_super_admin(user):
            # Super admin can see all data
            return queryset
        
        # Get user's accessible companies
        accessible_companies = [uc.company for uc in UserCompany.objects.filter(
            user=user, is_active=True
        ).select_related('company')]
        
        if not accessible_companies:
            return queryset.none()
        
        # Filter by accessible companies
        filter_kwargs = {f'{company_field}__in': accessible_companies}
        return queryset.filter(**filter_kwargs)

    @classmethod
    def validate_company_scoped_request(cls, user: User, company_id: int) -> Company:
        """
        Validate that a user can access data for the specified company
        Returns the company if valid, raises PermissionDenied otherwise
        """
        try:
            company = Company.objects.get(id=company_id, is_active=True)
        except Company.DoesNotExist:
            raise PermissionDenied("Company not found or inactive")
        
        cls.enforce_company_access(user, company)
        return company