"""
Multi-Company Management Views for Mama Eagle Enterprise
Handles company switching, creation, and branch management - subscription limits removed
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q

from .models import Company, UserCompany
from .forms import CompanyCreationForm, UserCompanyAssignmentForm, CreateUserForCompanyForm, UserRoleUpdateForm


@login_required
def company_switcher(request):
    """
    View for switching between companies (for users with multi-company access)
    """
    # Get all companies user has access to
    user_companies = UserCompany.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('company')
    
    current_company = getattr(request, 'company', None)
    
    context = {
        'user_companies': user_companies,
        'current_company': current_company,
    }
    
    return render(request, 'accounts/company_switcher.html', context)


@login_required
def switch_company(request, company_id):
    """
    Switch active company context (Super Admin only)
    """
    # Only super admins can switch between companies
    if not (request.user.is_super_admin or request.user.role == 'super_admin' or request.user.is_superuser):
        messages.error(request, 'Only super administrators can switch between companies.')
        return redirect('dashboard:home')
    
    # Verify user has access to this company
    try:
        user_company = UserCompany.objects.get(
            user=request.user,
            company_id=company_id,
            is_active=True
        )
        
        # Set as active company in session
        request.session['active_company_id'] = company_id
        request.session.modified = True  # Force session save
        
        # Also update the current request object for immediate display
        request.company = user_company.company
        
        messages.success(request, f'Switched to {user_company.company.name}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'company_name': user_company.company.name
            })
        
        return redirect('dashboard:home')
        
    except UserCompany.DoesNotExist:
        messages.error(request, 'You do not have access to that company.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Access denied'
            }, status=403)
        
        return redirect('dashboard:home')


@login_required
def create_company(request):
    """
    Create a new company with proper role-based management
    Only super admins can create companies
    """
    # Check if user can create companies - only super admins
    if not (request.user.is_super_admin or request.user.role == 'super_admin' or request.user.is_superuser):
        messages.error(request, 'Only super administrators can create companies. Contact your system administrator.')
        return redirect('dashboard:home')
    
    # Calculate company limits for context
    owned_companies = UserCompany.objects.filter(
        user=request.user,
        role__in=['owner', 'admin'],
        is_active=True
    ).count()
    
    # Mama Eagle Enterprise allows unlimited companies for super admins
    company_limit = -1  # -1 means unlimited
    
    if request.method == 'POST':
        form = CompanyCreationForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.created_by = request.user
            company.save()
            
            # Get the selected user from the form
            assigned_user = form.cleaned_data['assign_to_user']
            
            # Add selected user as company manager or admin based on their role
            company_role = 'admin' if assigned_user.role in ['admin', 'super_admin'] else 'manager'
            
            UserCompany.objects.create(
                user=assigned_user,
                company=company,
                role=company_role,
                assigned_by=request.user,
                is_active=True
            )
            
            messages.success(
                request, 
                f'Company "{company.name}" created successfully and assigned to {assigned_user.get_full_name() or assigned_user.username} as {company_role}!'
            )
            
            # Switch to new company via session only if assigning to current user
            if assigned_user == request.user:
                request.session['active_company_id'] = company.id
            
            return redirect('accounts:company_users', company_id=company.id)
    else:
        # Initialize form with current user as default selection
        form = CompanyCreationForm(initial={'assign_to_user': request.user})
    
    context = {
        'form': form,
        'company_limit': company_limit,
        'owned_companies': owned_companies,
        'can_create': owned_companies < company_limit or request.user.is_superuser,
    }
    
    return render(request, 'accounts/create_company.html', context)


@login_required
def company_list(request):
    """
    List all companies user has access to - no subscription limits in Mama Eagle Enterprise
    """
    user_companies = UserCompany.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('company').order_by('-created_at')

    companies_with_info = []
    for uc in user_companies:
        companies_with_info.append({
            'user_company': uc,
            'is_current': uc.company == request.company,
        })

    context = {
        'companies': companies_with_info,
    }

    return render(request, 'accounts/company_list.html', context)


@login_required
def company_detail(request, company_id):
    """
    View and edit company details
    """
    # Verify user has access to this company
    try:
        user_company = UserCompany.objects.get(
            user=request.user,
            company_id=company_id,
            is_active=True
        )
    except UserCompany.DoesNotExist:
        messages.error(request, 'You do not have access to that company.')
        return redirect('accounts:company_list')

    company = user_company.company

    # Handle form submission
    if request.method == 'POST' and user_company.role in ['owner', 'admin']:
        # Update company fields
        company.name = request.POST.get('name', company.name)
        company.registration_number = request.POST.get('registration_number', '')
        company.tax_id = request.POST.get('tax_id', '')
        company.email = request.POST.get('email', company.email)
        company.phone = request.POST.get('phone', '')
        company.website = request.POST.get('website', '')

        # Update address
        company.address_line_1 = request.POST.get('address_line_1', '')
        company.address_line_2 = request.POST.get('address_line_2', '')
        company.city = request.POST.get('city', '')
        company.state = request.POST.get('state', '')
        company.postal_code = request.POST.get('postal_code', '')
        company.country = request.POST.get('country', 'Ghana')

        # Update financial settings
        company.currency = request.POST.get('currency', 'GHS')
        fiscal_year = request.POST.get('fiscal_year_start')
        if fiscal_year:
            company.fiscal_year_start = fiscal_year
        company.timezone = request.POST.get('timezone', 'UTC')

        # Update branding
        if 'logo' in request.FILES:
            company.logo = request.FILES['logo']
        company.primary_color = request.POST.get('primary_color', '#0ea5e9')

        company.save()
        messages.success(request, f'Company "{company.name}" updated successfully!')
        return redirect('accounts:company_detail', company_id=company.id)

    # Get team members
    team_members = UserCompany.objects.filter(
        company=company,
        is_active=True
    ).select_related('user').order_by('-role', 'created_at')

    context = {
        'company': company,
        'user_company': user_company,
        'team_members': team_members,
        'can_manage_company': request.user.is_super_admin or request.user.can_manage_company(company),
    }

    return render(request, 'accounts/company_detail.html', context)


@login_required
def company_delete(request, company_id):
    """
    Delete a company (owner only)
    """
    try:
        user_company = UserCompany.objects.get(
            user=request.user,
            company_id=company_id,
            role='owner',
            is_active=True
        )
    except UserCompany.DoesNotExist:
        messages.error(request, 'Only the company owner can delete a company.')
        return redirect('accounts:company_list')

    company = user_company.company
    company_name = company.name

    if request.method == 'POST':
        # Delete the company (cascade will handle related objects)
        company.delete()

        # Clear session if this was the active company
        if request.session.get('active_company_id') == company_id:
            del request.session['active_company_id']

        messages.success(request, f'Company "{company_name}" has been deleted successfully.')
        return redirect('accounts:company_list')

    context = {
        'company': company,
    }

    return render(request, 'accounts/company_confirm_delete.html', context)


@login_required
def company_users(request, company_id):
    """List all users in a company."""
    company = get_object_or_404(Company, id=company_id)
    
    # Check permissions
    if not request.user.is_super_admin and not request.user.can_manage_company(company):
        messages.error(request, 'You do not have permission to view users for this company.')
        return redirect('accounts:company_list')
    
    users = UserCompany.objects.filter(company=company).select_related('user')
    
    context = {
        'company': company,
        'users': users,
    }
    
    return render(request, 'accounts/company_users.html', context)


@login_required
def assign_user_to_company(request, company_id):
    """Assign a user to a company with a role."""
    company = get_object_or_404(Company, id=company_id)
    
    # Check permissions
    if not request.user.is_super_admin and not request.user.can_manage_company(company):
        messages.error(request, 'You do not have permission to assign users to this company.')
        return redirect('accounts:company_list')
    
    if request.method == 'POST':
        form = UserCompanyAssignmentForm(request.POST, company=company, manager=request.user)
        if form.is_valid():
            user_company = form.save(commit=False)
            user_company.company = company
            user_company.assigned_by = request.user
            user_company.save()
            
            messages.success(request, f'User "{user_company.user.get_full_name() or user_company.user.username}" has been assigned to "{company.name}" as {user_company.role}.')
            return redirect('accounts:company_users', company_id=company.id)
    else:
        form = UserCompanyAssignmentForm(company=company, manager=request.user)
    
    context = {
        'form': form,
        'company': company,
    }
    
    return render(request, 'accounts/assign_user_to_company.html', context)


@login_required
def create_user_for_company(request, company_id):
    """Create a new user and assign them to a company."""
    company = get_object_or_404(Company, id=company_id)
    
    # Check permissions
    if not request.user.is_super_admin and not request.user.can_manage_company(company):
        messages.error(request, 'You do not have permission to create users for this company.')
        return redirect('accounts:company_list')
    
    if request.method == 'POST':
        form = CreateUserForCompanyForm(request.POST, company=company, manager=request.user)
        if form.is_valid():
            user, user_company = form.save(company=company, assigned_by=request.user)
            
            messages.success(request, f'User "{user.get_full_name() or user.username}" has been created and assigned to "{company.name}" as {user_company.role}.')
            return redirect('accounts:company_users', company_id=company.id)
    else:
        form = CreateUserForCompanyForm(company=company, manager=request.user)
    
    context = {
        'form': form,
        'company': company,
    }
    
    return render(request, 'accounts/create_user_for_company.html', context)


@login_required
def update_user_role_in_company(request, company_id, user_company_id):
    """Update a user's role in a company."""
    company = get_object_or_404(Company, id=company_id)
    user_company = get_object_or_404(UserCompany, id=user_company_id, company=company)
    
    # Check permissions
    if not request.user.is_super_admin and not request.user.can_manage_company(company):
        messages.error(request, 'You do not have permission to update user roles in this company.')
        return redirect('accounts:company_list')
    
    # Prevent managers from updating their own role or other managers' roles
    if not request.user.is_super_admin:
        if user_company.user == request.user:
            messages.error(request, 'You cannot update your own role.')
            return redirect('accounts:company_users', company_id=company.id)
        
        if user_company.role in ['MANAGER', 'ADMIN'] and not request.user.is_super_admin:
            messages.error(request, 'You do not have permission to update this user\'s role.')
            return redirect('accounts:company_users', company_id=company.id)
    
    if request.method == 'POST':
        form = UserRoleUpdateForm(request.POST, instance=user_company, manager=request.user)
        if form.is_valid():
            form.save()
            
            messages.success(request, f'Role for "{user_company.user.get_full_name() or user_company.user.username}" has been updated to {user_company.role}.')
            return redirect('accounts:company_users', company_id=company.id)
    else:
        form = UserRoleUpdateForm(instance=user_company, manager=request.user)
    
    context = {
        'form': form,
        'company': company,
        'user_company': user_company,
    }
    
    return render(request, 'accounts/update_user_role.html', context)


@login_required
def remove_user_from_company(request, company_id, user_company_id):
    """Remove a user from a company."""
    company = get_object_or_404(Company, id=company_id)
    user_company = get_object_or_404(UserCompany, id=user_company_id, company=company)
    
    # Check permissions
    if not request.user.is_super_admin and not request.user.can_manage_company(company):
        messages.error(request, 'You do not have permission to remove users from this company.')
        return redirect('accounts:company_list')
    
    # Prevent managers from removing themselves or other managers
    if not request.user.is_super_admin:
        if user_company.user == request.user:
            messages.error(request, 'You cannot remove yourself from the company.')
            return redirect('accounts:company_users', company_id=company.id)
        
        if user_company.role in ['MANAGER', 'ADMIN']:
            messages.error(request, 'You do not have permission to remove this user.')
            return redirect('accounts:company_users', company_id=company.id)
    
    if request.method == 'POST':
        user_name = user_company.user.get_full_name() or user_company.user.username
        user_company.delete()
        
        messages.success(request, f'"{user_name}" has been removed from "{company.name}".')
        return redirect('accounts:company_users', company_id=company.id)
    
    context = {
        'company': company,
        'user_company': user_company,
    }
    
    return render(request, 'accounts/remove_user_from_company.html', context)


@login_required
def user_list(request):
    """List all users with their company assignments."""
    # Only super admin can view all users
    if not request.user.is_super_admin:
        messages.error(request, 'You do not have permission to view all users.')
        return redirect('dashboard:index')
    
    users = User.objects.all().prefetch_related('usercompany_set__company')
    
    context = {
        'users': users,
    }
    
    return render(request, 'accounts/user_list.html', context)
