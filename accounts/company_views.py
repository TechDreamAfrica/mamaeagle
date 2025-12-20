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
from .forms import CompanyCreationForm


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
    Switch active company context (Admin only)
    """
    # Check if user has admin/company management permissions
    from .context_processors import team_permissions as get_permissions
    perms = get_permissions(request)
    
    if not perms.get('can_manage_roles', False):
        messages.error(request, 'Only administrators can switch companies.')
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
    Create a new company - unlimited companies for Mama Eagle Enterprise
    """
    if request.method == 'POST':
        form = CompanyCreationForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.created_by = request.user
            company.save()
            
            # Add user as owner
            UserCompany.objects.create(
                user=request.user,
                company=company,
                role='owner'
            )
            
            messages.success(request, f'Company "{company.name}" created successfully!')
            
            # Switch to new company via session
            request.session['active_company_id'] = company.id
            
            return redirect('dashboard:home')
    else:
        form = CompanyCreationForm()
    
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
