"""
Multi-Tenancy and Branch Access Middleware for Mama Eagle Enterprise
Enforces company-based data isolation and branch access control across all requests
"""
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from threading import local

# Thread-local storage for current company and branch context
_thread_locals = local()


def get_current_company():
    """Get the current company from thread-local storage"""
    return getattr(_thread_locals, 'company', None)


def set_current_company(company):
    """Set the current company in thread-local storage"""
    _thread_locals.company = company


def get_current_branch():
    """Get the current branch from thread-local storage"""
    return getattr(_thread_locals, 'branch', None)


def set_current_branch(branch):
    """Set the current branch in thread-local storage"""
    _thread_locals.branch = branch


def is_website_path(path):
    """Check if the path belongs to the e-commerce website (not the accounting app)"""
    # Website paths (e-commerce) - these don't need company/branch
    website_patterns = [
        '/',  # Homepage
        '/about/',
        '/contact/', 
        '/newsletter/',
        '/products/',
        '/product/',
        '/cart/',
        '/checkout/',
        '/payment/',
        '/order/',
        '/orders/',
        '/customer/',
        '/api/cart/',
        '/api/sync-products-to-invoice/',
        '/api/check-invoice-inventory/',
        '/api/products-autocomplete/',
    ]
    
    # Check if path matches any website pattern
    for pattern in website_patterns:
        if path.startswith(pattern):
            return True
    
    # Special case for exact homepage match
    if path == '/':
        return True
        
    return False


class CompanyIsolationMiddleware(MiddlewareMixin):
    """
    Middleware to ensure data isolation between companies.
    Sets the current company context for the request.
    """
    
    def process_request(self, request):
        # Initialize company as None by default
        company = None

        # Skip for anonymous users
        if not request.user.is_authenticated:
            set_current_company(None)
            request.company = None
            return None

        # Skip for superusers (they can see all data)
        if request.user.is_superuser:
            set_current_company(None)
            request.company = None
            return None

        # Check if user has explicitly switched to a specific company via session
        requested_company_id = request.session.get('active_company_id')

        if requested_company_id:
            # Use the company from session (set by CompanyAccessControlMiddleware)
            from accounts.models import UserCompany
            try:
                user_company = UserCompany.objects.get(
                    user=request.user,
                    company_id=requested_company_id,
                    is_active=True
                )
                company = user_company.company
            except UserCompany.DoesNotExist:
                # Invalid session, clear it and fall back to default
                del request.session['active_company_id']
                company = getattr(request.user, 'company', None)
        else:
            # No session company, use user's default company
            company = getattr(request.user, 'company', None)

        # If user has no company, redirect to company setup ONLY for app users (not website)
        if not company and not is_website_path(request.path):
            # Allow access to company setup, logout, and profile pages
            allowed_paths = [
                reverse('accounts:logout'),
                reverse('accounts:profile'),
                '/accounts/setup-company/',  # Add this URL if it exists
            ]

            if request.path not in allowed_paths:
                messages.warning(request, 'Please set up your company profile to continue.')
                # You can redirect to company setup page here
                # return redirect('accounts:setup_company')

        # Set company in thread-local storage for model managers to use
        set_current_company(company)

        # Always store company in request (even if None) to avoid AttributeError
        request.company = company

        return None
    
    def process_response(self, request, response):
        # Clean up thread-local storage
        set_current_company(None)
        return response


class BranchAccessControlMiddleware(MiddlewareMixin):
    """
    Middleware to handle branch access control for Mama Eagle Enterprise.
    Only administrators can switch branches, and users are restricted to assigned branches.
    """
    
    def process_request(self, request):
        # Initialize branch as None by default
        branch = None

        # Skip for anonymous users or website users (no branch requirement)
        if not request.user.is_authenticated or is_website_path(request.path):
            set_current_branch(None)
            request.current_branch = None
            request.accessible_branches = []
            return None
            return None
            return None

        # Handle branch switching (admin only)
        if 'switch_branch' in request.POST and request.user.role == 'admin':
            branch_id = request.POST.get('branch_id')
            if branch_id:
                from accounts.models import Branch
                try:
                    branch = Branch.objects.get(id=branch_id, is_active=True)
                    request.session['active_branch_id'] = branch.id
                    messages.success(request, f'Switched to {branch.name}')
                except Branch.DoesNotExist:
                    messages.error(request, 'Invalid branch selected.')

        # Check if user has explicitly switched to a specific branch via session
        requested_branch_id = request.session.get('active_branch_id')

        # Get user's accessible branches
        accessible_branches = request.user.get_accessible_branches()

        if requested_branch_id:
            # Use the branch from session
            from accounts.models import Branch
            try:
                branch = Branch.objects.get(id=requested_branch_id, is_active=True)
                # Check if user has access to this branch
                if not (request.user.role == 'admin' or branch in accessible_branches):
                    # User lost access, clear session and use default
                    del request.session['active_branch_id']
                    branch = request.user.current_branch
                    if branch and branch not in accessible_branches:
                        branch = accessible_branches.first() if accessible_branches.exists() else None
            except Branch.DoesNotExist:
                # Invalid session, clear it and fall back to default
                del request.session['active_branch_id']
                branch = request.user.current_branch
        else:
            # No session branch, use user's current branch
            branch = request.user.current_branch
            # Ensure user has access to their current branch
            if branch and not (request.user.role == 'admin' or branch in accessible_branches):
                branch = accessible_branches.first() if accessible_branches.exists() else None

        # If user has no accessible branch and is not admin (excluding website users)
        if not branch and request.user.role != 'admin' and not is_website_path(request.path):
            # Allow access to certain pages
            allowed_paths = [
                reverse('accounts:logout'),
                reverse('accounts:profile'),
                '/accounts/branch-assignment/',  # Add this URL if it exists
            ]

            if request.path not in allowed_paths:
                messages.warning(request, 'You are not assigned to any branch. Please contact administrator.')

        # Set branch in thread-local storage
        set_current_branch(branch)

        # Store branch and accessible branches in request
        request.current_branch = branch
        request.accessible_branches = accessible_branches

        return None
    
    def process_response(self, request, response):
        # Clean up thread-local storage
        set_current_branch(None)
        return response
