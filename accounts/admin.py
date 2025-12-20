from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Company, UserCompany, Branch, UserBranch
from .team_models import UserInvitation, TeamMember, RoleTemplate


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'manager_name', 'city', 'country', 'is_active', 'is_head_office', 'created_at']
    list_filter = ['is_active', 'is_head_office', 'country', 'created_at']
    search_fields = ['name', 'code', 'manager_name', 'city', 'email']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'manager_name', 'is_active', 'is_head_office')
        }),
        ('Address', {
            'fields': ('address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email')
        }),
        ('Settings', {
            'fields': ('settings',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class UserBranchInline(admin.TabularInline):
    model = UserBranch
    fk_name = 'user'
    extra = 0
    fields = ['branch', 'role', 'is_active', 'assigned_by']
    readonly_fields = ['assigned_by']


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'full_name', 'role', 'current_branch', 'department', 'is_active_employee', 'hire_date']
    list_filter = ['role', 'current_branch', 'department', 'is_active', 'is_active_employee', 'hire_date', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'employee_id']
    readonly_fields = ['date_joined', 'last_login', 'created_at', 'updated_at']
    inlines = [UserBranchInline]
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Employee Information', {
            'fields': ('employee_id', 'hire_date', 'department', 'salary', 'phone_number', 'date_of_birth')
        }),
        ('Role & Branch Assignment', {
            'fields': ('role', 'current_branch', 'can_access_all_branches', 'is_active_employee')
        }),
        ('Profile', {
            'fields': ('avatar',),
            'classes': ('collapse',)
        }),
        ('AI Preferences', {
            'fields': ('ai_insights_enabled', 'notification_preferences'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def full_name(self, obj):
        return obj.get_full_name()
    full_name.short_description = 'Full Name'


@admin.register(UserBranch)
class UserBranchAdmin(admin.ModelAdmin):
    list_display = ['user', 'branch', 'role', 'is_active', 'assigned_by', 'created_at']
    list_filter = ['role', 'is_active', 'branch', 'created_at']
    search_fields = ['user__username', 'user__email', 'branch__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'country', 'fiscal_year_start', 'currency', 'created_at']
    list_filter = ['country', 'currency', 'created_at']
    search_fields = ['name', 'email', 'registration_number', 'tax_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'registration_number', 'tax_id', 'email', 'phone', 'website')
        }),
        ('Address', {
            'fields': ('address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Financial Settings', {
            'fields': ('fiscal_year_start', 'currency', 'timezone')
        }),
        ('Branding', {
            'fields': ('logo', 'primary_color'),
            'classes': ('collapse',)
        }),
        ('Advanced Settings', {
            'fields': ('settings',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserCompany)
class UserCompanyAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'company__name']
    autocomplete_fields = ['user', 'company']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Assignment', {
            'fields': ('user', 'company', 'role', 'is_active')
        }),
        ('Permissions', {
            'fields': ('permissions',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserInvitation)
class UserInvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'company', 'role', 'status', 'invited_by', 'created_at', 'expires_at']
    list_filter = ['status', 'role', 'created_at']
    search_fields = ['email', 'company__name', 'invited_by__username']
    readonly_fields = ['token', 'created_at', 'accepted_at']
    autocomplete_fields = ['company', 'invited_by']
    
    fieldsets = (
        ('Invitation Details', {
            'fields': ('email', 'company', 'invited_by', 'role', 'department')
        }),
        ('Status', {
            'fields': ('status', 'token', 'expires_at', 'accepted_at')
        }),
        ('Permissions', {
            'fields': ('permissions',),
            'classes': ('collapse',)
        }),
        ('Message', {
            'fields': ('message',),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        # Allow deletion of expired or cancelled invitations
        if obj and obj.status in ['expired', 'cancelled']:
            return True
        return super().has_delete_permission(request, obj)


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'is_active', 'can_invite_users', 'can_manage_roles', 'joined_at']
    list_filter = ['is_active', 'can_invite_users', 'can_manage_roles', 'joined_at']
    search_fields = ['user__username', 'user__email', 'company__name']
    readonly_fields = ['joined_at', 'updated_at', 'last_active', 'login_count']
    autocomplete_fields = ['user', 'company']
    
    fieldsets = (
        ('Team Member', {
            'fields': ('user', 'company', 'is_active')
        }),
        ('Permissions', {
            'fields': ('can_invite_users', 'can_manage_roles', 'module_permissions')
        }),
        ('Activity', {
            'fields': ('last_active', 'login_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('joined_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RoleTemplate)
class RoleTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'is_default', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_default', 'is_active', 'created_at']
    search_fields = ['name', 'company__name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['company', 'created_by']
    
    fieldsets = (
        ('Role Template', {
            'fields': ('name', 'company', 'description')
        }),
        ('Settings', {
            'fields': ('is_default', 'is_active')
        }),
        ('Permissions', {
            'fields': ('permissions',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
