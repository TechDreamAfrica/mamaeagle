"""
Team Management Views
Views for managing team members, invitations, roles, and permissions
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.urls import reverse

from .team_models import UserInvitation, TeamMember, RoleTemplate
from .team_forms import (
    InviteUserForm, BulkInviteForm, ChangeRoleForm, 
    PermissionsForm, RoleTemplateForm, TeamMemberFilterForm
)
from .models import Company, UserCompany
from .company_views import is_company_admin, is_super_admin

User = get_user_model()
DEBUG = settings.DEBUG


def is_admin_user(user):
    """Check if user is admin or super admin (backward compatibility)"""
    return user.is_authenticated and (user.is_super_admin or user.role == 'super_admin' or user.is_superuser)


@login_required
def team_dashboard(request):
    """
    Main team management dashboard - Company Admin or Super Admin Only
    """
    # Get current company from session or user's primary company
    company_id = request.session.get('active_company_id')
    if company_id:
        company = get_object_or_404(Company, id=company_id)
    else:
        company = request.user.company
    
    if not company:
        messages.error(request, "You must be associated with a company to manage team members.")
        return redirect('dashboard:home')
    
    # Check if user can manage this company
    if not is_company_admin(request.user, company):
        messages.error(request, 'You do not have permission to manage team members for this company.')
        return redirect('dashboard:home')
    
    # Get all team members
    user_companies = UserCompany.objects.filter(company=company).select_related('user')
    
    # Apply filters
    filter_form = TeamMemberFilterForm(request.GET)
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        role = filter_form.cleaned_data.get('role')
        department = filter_form.cleaned_data.get('department')
        status = filter_form.cleaned_data.get('status')
        
        if search:
            user_companies = user_companies.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search)
            )
        if role:
            user_companies = user_companies.filter(user__role=role)
        if department:
            user_companies = user_companies.filter(user__department__icontains=department)
        if status == 'active':
            user_companies = user_companies.filter(user__is_active_employee=True)
        elif status == 'inactive':
            user_companies = user_companies.filter(user__is_active_employee=False)
    
    # Get pending invitations
    pending_invitations = UserInvitation.objects.filter(
        company=company,
        status='pending'
    ).order_by('-created_at')
    
    # Import Branch and UserBranch models
    from .models import Branch, UserBranch
    
    # Get statistics
    stats = {
        'total_members': user_companies.count(),
        'active_members': user_companies.filter(user__is_active_employee=True).count(),
        'pending_invitations': pending_invitations.count(),
        'admins': user_companies.filter(role='admin').count(),
        'total_branches': Branch.objects.filter(is_active=True).count(),
        'members_with_branches': UserBranch.objects.filter(is_active=True).values('user').distinct().count(),
    }
    
    context = {
        'company': company,
        'team_members': user_companies,
        'pending_invitations': pending_invitations,
        'stats': stats,
        'filter_form': filter_form,
    }
    
    return render(request, 'accounts/team/dashboard.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def invite_user(request):
    """
    Invite a new user to the company - Company Admin or Super Admin Only
    """
    # Get current company from session or user's primary company
    company_id = request.session.get('active_company_id')
    if company_id:
        company = get_object_or_404(Company, id=company_id)
    else:
        company = request.user.company
    
    if not company:
        messages.error(request, "You must be associated with a company to invite users.")
        return redirect('dashboard:home')
    
    # Check if user can manage this company
    if not is_company_admin(request.user, company):
        messages.error(request, 'You do not have permission to invite users to this company.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = InviteUserForm(request.POST, company=company)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.company = company
            invitation.invited_by = request.user
            invitation.save()
            
            # Send invitation email
            send_invitation_email(invitation, request)
            
            messages.success(request, f"Invitation sent to {invitation.email}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Invitation sent to {invitation.email}'
                })
            
            return redirect('accounts:team_dashboard')
    else:
        form = InviteUserForm(company=company)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'accounts/team/invite_form.html', {'form': form})
    
    return render(request, 'accounts/team/invite.html', {'form': form})


@login_required
@require_http_methods(["POST"])
def bulk_invite(request):
    """
    Invite multiple users at once - Company Admin or Super Admin Only
    """
    # Get current company from session or user's primary company
    company_id = request.session.get('active_company_id')
    if company_id:
        company = get_object_or_404(Company, id=company_id)
    else:
        company = request.user.company
    
    if not company:
        return JsonResponse({'success': False, 'message': 'No company associated'}, status=400)
    
    # Check if user can manage this company
    if not is_company_admin(request.user, company):
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    form = BulkInviteForm(request.POST)
    if form.is_valid():
        emails = form.cleaned_data['emails']
        role = form.cleaned_data['role']
        department = form.cleaned_data.get('department', '')
        
        invited_count = 0
        skipped = []
        
        for email in emails:
            # Check if already invited or member
            if UserInvitation.objects.filter(email=email, company=company, status='pending').exists():
                skipped.append(f"{email} (already invited)")
                continue
            
            existing_user = User.objects.filter(email=email).first()
            if existing_user and UserCompany.objects.filter(user=existing_user, company=company).exists():
                skipped.append(f"{email} (already a member)")
                continue
            
            # Create invitation
            invitation = UserInvitation.objects.create(
                email=email,
                company=company,
                invited_by=request.user,
                role=role,
                department=department
            )
            
            # Send invitation email
            send_invitation_email(invitation, request)
            invited_count += 1
        
        message = f"Sent {invited_count} invitation(s)."
        if skipped:
            message += f" Skipped: {', '.join(skipped)}"
        
        messages.success(request, message)
        return JsonResponse({'success': True, 'message': message})
    
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


def accept_invitation(request, token):
    """
    Accept an invitation and create account
    """
    invitation = get_object_or_404(UserInvitation, token=token)
    
    # Check if invitation is valid
    if not invitation.is_valid():
        invitation.check_expiry()
        messages.error(request, "This invitation has expired or is no longer valid.")
        return redirect('accounts:login')
    
    # If user is logged in
    if request.user.is_authenticated:
        # Check if email matches
        if request.user.email != invitation.email:
            messages.error(request, "This invitation is for a different email address.")
            return redirect('dashboard:home')
        
        # Accept invitation
        invitation.accept(request.user)
        messages.success(request, f"Welcome to {invitation.company.name}!")
        return redirect('dashboard:home')
    
    # If user not logged in, redirect to registration with pre-filled data
    request.session['invitation_token'] = token
    request.session['invitation_email'] = invitation.email
    request.session['invitation_role'] = invitation.role
    request.session['invitation_company'] = invitation.company.id
    
    messages.info(request, "Please create your account to accept the invitation.")
    return redirect('accounts:register')


@login_required
@require_http_methods(["POST"])
def cancel_invitation(request, invitation_id):
    """
    Cancel a pending invitation
    """
    invitation = get_object_or_404(UserInvitation, id=invitation_id)
    
    # Check permission
    if invitation.company != request.user.company:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    invitation.cancel()
    messages.success(request, f"Invitation to {invitation.email} has been cancelled.")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('accounts:team_dashboard')


@login_required
@require_http_methods(["GET", "POST"])
def change_user_role(request, user_id):
    """
    Change a user's role and department - Company Admin or Super Admin Only
    """
    # Get current company from session or user's primary company
    company_id = request.session.get('active_company_id')
    if company_id:
        company = get_object_or_404(Company, id=company_id)
    else:
        company = request.user.company
    
    if not company:
        messages.error(request, "You must be associated with a company.")
        return redirect('dashboard:home')
    
    # Check if user can manage this company
    if not is_company_admin(request.user, company):
        messages.error(request, 'You do not have permission to manage users in this company.')
        return redirect('dashboard:home')
    
    user_company = get_object_or_404(UserCompany, user_id=user_id, company=company)
    
    if request.method == 'POST':
        form = ChangeRoleForm(request.POST)
        if form.is_valid():
            user = user_company.user
            user.role = form.cleaned_data['role']
            user.department = form.cleaned_data.get('department', '')
            user.save()
            
            user_company.role = form.cleaned_data['role']
            user_company.save()
            
            messages.success(request, f"Role updated for {user.get_full_name()}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            
            return redirect('accounts:team_dashboard')
    else:
        form = ChangeRoleForm(initial={
            'role': user_company.user.role,
            'department': user_company.user.department
        })
    
    return render(request, 'accounts/team/change_role.html', {
        'form': form,
        'user_company': user_company
    })


@login_required
@require_http_methods(["POST"])
def deactivate_user(request, user_id):
    """
    Deactivate a team member - Company Admin or Super Admin Only
    """
    # Get current company from session or user's primary company
    company_id = request.session.get('active_company_id')
    if company_id:
        company = get_object_or_404(Company, id=company_id)
    else:
        company = request.user.company
    
    if not company:
        return JsonResponse({'success': False, 'message': 'No company associated'}, status=400)
    
    # Check if user can manage this company
    if not is_company_admin(request.user, company):
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    user_company = get_object_or_404(UserCompany, user_id=user_id, company=company)
    
    # Prevent self-deactivation
    if user_company.user == request.user:
        return JsonResponse({'success': False, 'message': 'You cannot deactivate yourself'}, status=400)
    
    user = user_company.user
    user.is_active_employee = False
    user.save()
    
    user_company.is_active = False
    user_company.save()
    
    messages.success(request, f"{user.get_full_name()} has been deactivated.")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('accounts:team_dashboard')


@login_required
@require_http_methods(["POST"])
def activate_user(request, user_id):
    """
    Reactivate a team member - Company Admin or Super Admin Only
    """
    # Get current company from session or user's primary company
    company_id = request.session.get('active_company_id')
    if company_id:
        company = get_object_or_404(Company, id=company_id)
    else:
        company = request.user.company
    
    if not company:
        return JsonResponse({'success': False, 'message': 'No company associated'}, status=400)
    
    # Check if user can manage this company
    if not is_company_admin(request.user, company):
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    user_company = get_object_or_404(UserCompany, user_id=user_id, company=company)
    
    user = user_company.user
    user.is_active_employee = True
    user.save()
    
    user_company.is_active = True
    user_company.save()
    
    messages.success(request, f"{user.get_full_name()} has been reactivated.")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('accounts:team_dashboard')


@login_required
def manage_permissions(request, user_id):
    """
    Manage user permissions - Company Admin or Super Admin Only
    """
    # Get current company from session or user's primary company
    company_id = request.session.get('active_company_id')
    if company_id:
        company = get_object_or_404(Company, id=company_id)
    else:
        company = request.user.company
    
    if not company:
        messages.error(request, "You must be associated with a company.")
        return redirect('dashboard:home')
    
    # Check if user can manage this company
    if not is_company_admin(request.user, company):
        messages.error(request, 'You do not have permission to manage permissions in this company.')
        return redirect('dashboard:home')
    
    user_company = get_object_or_404(UserCompany, user_id=user_id, company=company)
    
    # Get or create TeamMember
    team_member, created = TeamMember.objects.get_or_create(
        user=user_company.user,
        company=company,
        defaults={'module_permissions': {}}
    )
    
    if request.method == 'POST':
        try:

            
            form = PermissionsForm(request.POST, instance=team_member)
            
            # Build module_permissions from checkbox inputs
            module_permissions = {}
            for module, _ in PermissionsForm.MODULES:
                permissions = []
                for action, _ in PermissionsForm.ACTIONS:
                    checkbox_name = f'permission_{module}_{action}'
                    if request.POST.get(checkbox_name):
                        permissions.append(action)

                if permissions:
                    module_permissions[module] = permissions
            

            
            # Validate form for can_invite_users and can_manage_roles
            if form.is_valid():
                # Update team_member permissions using form cleaned data
                team_member.can_invite_users = form.cleaned_data.get('can_invite_users', False)
                team_member.can_manage_roles = form.cleaned_data.get('can_manage_roles', False)
                team_member.module_permissions = module_permissions
                team_member.save()
                

                
                messages.success(request, f"Permissions updated for {user_company.user.get_full_name()}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'redirect': reverse('accounts:team_dashboard')
                    })
                
                return redirect('accounts:team_dashboard')
            else:
                # Form validation failed

                error_msg = f"Please correct the errors in the form on the role permission assignment. Form validation errors: {form.errors}"
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_msg,
                        'form_errors': form.errors
                    }, status=400)
                
                messages.error(request, error_msg)
        except Exception as e:
            import traceback
            error_msg = f"Error updating permissions: {str(e)}"
            error_trace = traceback.format_exc()

            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg,
                    'details': error_trace if DEBUG else None
                }, status=500)
            
            messages.error(request, error_msg)
            return redirect('accounts:team_dashboard')
    else:
        form = PermissionsForm(instance=team_member)
    
    # Get default permissions for the role
    default_permissions = team_member.get_default_permissions()
    
    # Prepare modules list with icons and colors for template
    modules_with_details = [
        ('dashboard', 'Dashboard', 'tachometer-alt', 'blue'),
        ('invoicing', 'Invoicing', 'file-invoice-dollar', 'green'),
        ('expenses', 'Expenses', 'receipt', 'red'),
        ('inventory', 'Inventory', 'boxes', 'orange'),
        ('hr', 'Human Resources', 'users', 'teal'),
        ('reports', 'Reports', 'chart-bar', 'purple'),
        ('sales', 'Sales & CRM', 'shopping-cart', 'indigo'),
        ('bank_reconciliation', 'Bank Reconciliation', 'university', 'cyan'),
        ('ai_insights', 'AI Insights', 'brain', 'pink'),
        ('welfare', 'Employee Welfare', 'heart', 'rose'),
    ]
    
    context = {
        'form': form,
        'user_company': user_company,
        'team_member': team_member,
        'default_permissions': default_permissions,
        'current_permissions': team_member.module_permissions,
        'modules': modules_with_details,
        'actions': PermissionsForm.ACTIONS,
    }
    
    return render(request, 'accounts/team/permissions.html', context)


@login_required
def role_templates(request):
    """
    Manage custom role templates - Company Admin or Super Admin Only
    """
    # Get current company from session or user's primary company
    company_id = request.session.get('active_company_id')
    if company_id:
        company = get_object_or_404(Company, id=company_id)
    else:
        company = request.user.company
    
    if not company:
        messages.error(request, "You must be associated with a company.")
        return redirect('dashboard:home')
    
    # Check if user can manage this company
    if not is_company_admin(request.user, company):
        messages.error(request, 'You do not have permission to manage role templates in this company.')
        return redirect('dashboard:home')
    
    templates = RoleTemplate.objects.filter(company=company)
    
    context = {
        'templates': templates,
    }
    
    return render(request, 'accounts/team/role_templates.html', context)


@login_required
def create_role_template(request):
    """
    Create a new role template - Company Admin or Super Admin Only
    """
    # Get current company from session or user's primary company
    company_id = request.session.get('active_company_id')
    if company_id:
        company = get_object_or_404(Company, id=company_id)
    else:
        company = request.user.company
    
    if not company:
        messages.error(request, "You must be associated with a company.")
        return redirect('dashboard:home')
    
    # Check if user can manage this company
    if not is_company_admin(request.user, company):
        messages.error(request, 'You do not have permission to create role templates for this company.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = RoleTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.company = company
            template.created_by = request.user
            template.save()
            
            messages.success(request, f"Role template '{template.name}' created successfully.")
            return redirect('accounts:role_templates')
    else:
        form = RoleTemplateForm()
    
    return render(request, 'accounts/team/create_role_template.html', {'form': form})


def send_invitation_email(invitation, request):
    """
    Send invitation email to user
    """
    # Build invitation URL
    invitation_url = request.build_absolute_uri(
        f"/accounts/team/accept/{invitation.token}/"
    )
    
    # Render email template
    html_message = render_to_string('accounts/emails/invitation.html', {
        'invitation': invitation,
        'invitation_url': invitation_url,
        'company': invitation.company,
        'invited_by': invitation.invited_by,
    })
    plain_message = strip_tags(html_message)
    
    # Send email
    send_mail(
        subject=f"You've been invited to join {invitation.company.name} on DreamBiz",
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invitation.email],
        html_message=html_message,
        fail_silently=False,
    )


@login_required
def assign_user_branches(request, user_id=None):
    """
    Branch management functionality disabled - redirecting to team dashboard
    """
    messages.info(request, "Branch management functionality has been disabled.")
    return redirect('accounts:team_dashboard')


@login_required
def user_branch_assignments(request, user_id):
    """
    Branch management functionality disabled - redirecting to team dashboard
    """
    messages.info(request, "Branch management functionality has been disabled.")
    return redirect('accounts:team_dashboard')
