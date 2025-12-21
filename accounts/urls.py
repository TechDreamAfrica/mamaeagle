from django.urls import path
from . import views
from . import team_views
from . import company_views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    
    # Profile Management URLs
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/password/', views.change_password, name='change_password'),
    path('profile/notifications/', views.notification_preferences, name='notification_preferences'),
    path('profile/preferences/', views.user_preferences, name='user_preferences'),
    path('profile/activity/', views.profile_activity, name='profile_activity'),
    path('profile/avatar/delete/', views.delete_avatar, name='delete_avatar'),
    
    # Company Management URLs
    path('companies/', company_views.company_list, name='company_list'),
    path('companies/create/', company_views.create_company, name='create_company'),
    path('companies/<int:company_id>/', company_views.company_detail, name='company_detail'),
    path('companies/<int:company_id>/delete/', company_views.company_delete, name='company_delete'),
    path('companies/switch/<int:company_id>/', company_views.switch_company, name='switch_company'),
    path('companies/switcher/', company_views.company_switcher, name='company_switcher'),
    
    # Company User Management URLs
    path('companies/<int:company_id>/users/', company_views.company_users, name='company_users'),
    path('companies/<int:company_id>/users/assign/', company_views.assign_user_to_company, name='assign_user_to_company'),
    path('companies/<int:company_id>/users/create/', company_views.create_user_for_company, name='create_user_for_company'),
    path('companies/<int:company_id>/users/<int:user_company_id>/update-role/', company_views.update_user_role_in_company, name='update_user_role'),
    path('companies/<int:company_id>/users/<int:user_company_id>/remove/', company_views.remove_user_from_company, name='remove_user_from_company'),
    
    # User Management URLs (Super Admin only)
    path('users/', company_views.user_list, name='user_list'),
    
    # Team Management URLs
    path('team/', team_views.team_dashboard, name='team_dashboard'),
    path('team/invite/', team_views.invite_user, name='invite_user'),
    path('team/invite/bulk/', team_views.bulk_invite, name='bulk_invite'),
    path('team/accept/<str:token>/', team_views.accept_invitation, name='accept_invitation'),
    path('team/invitation/<int:invitation_id>/cancel/', team_views.cancel_invitation, name='cancel_invitation'),
    path('team/member/<int:user_id>/role/', team_views.change_user_role, name='change_user_role'),
    path('team/member/<int:user_id>/deactivate/', team_views.deactivate_user, name='deactivate_user'),
    path('team/member/<int:user_id>/activate/', team_views.activate_user, name='activate_user'),
    path('team/member/<int:user_id>/permissions/', team_views.manage_permissions, name='manage_permissions'),
    # path('team/member/<int:user_id>/branches/', team_views.user_branch_assignments, name='user_branch_assignments'),
    # Branch management URLs - DISABLED
    # path('team/branches/assign/', team_views.assign_user_branches, name='assign_user_branches'),
    # path('team/branches/assign/<int:user_id>/', team_views.assign_user_branches, name='assign_user_branches_user'),
    path('team/roles/', team_views.role_templates, name='role_templates'),
    path('team/roles/create/', team_views.create_role_template, name='create_role_template'),
    
    # Password Reset URLs
    path('password-reset/', views.DreamBizPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.DreamBizPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', views.DreamBizPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', views.DreamBizPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # API endpoints
    path('api/companies/', views.user_companies, name='user_companies'),
]
