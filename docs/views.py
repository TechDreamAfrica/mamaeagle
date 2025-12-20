"""
Documentation Views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def get_base_context(section=None):
    """Get base context for documentation pages"""
    return {
        'section': section,
        'section_title': section.replace('_', ' ').title() if section else 'Documentation',
    }


@login_required
def documentation_home(request):
    """Main documentation homepage"""
    context = {
        'page_title': 'Documentation',
        'sections': [
            {
                'title': 'Getting Started',
                'icon': 'fa-rocket',
                'description': 'Learn the basics of AccuFlow and set up your account',
                'url': 'docs:getting_started',
            },
            {
                'title': 'Dashboard',
                'icon': 'fa-tachometer-alt',
                'description': 'Overview of your business metrics and KPIs',
                'url': 'docs:dashboard',
            },
            {
                'title': 'Invoicing',
                'icon': 'fa-file-invoice',
                'description': 'Create, manage, and track invoices',
                'url': 'docs:invoicing',
            },
            {
                'title': 'Expenses',
                'icon': 'fa-receipt',
                'description': 'Track and categorize business expenses',
                'url': 'docs:expenses',
            },
            {
                'title': 'Inventory',
                'icon': 'fa-boxes',
                'description': 'Manage products, stock levels, and warehouses',
                'url': 'docs:inventory',
            },
            {
                'title': 'HR Management',
                'icon': 'fa-users',
                'description': 'Employee management and payroll',
                'url': 'docs:hr',
            },
            {

                'title': 'AI Insights',
                'icon': 'fa-brain',
                'description': 'AI-powered financial analysis and predictions',
                'url': 'docs:ai_insights',
            },
            {
                'title': 'Bank Reconciliation',
                'icon': 'fa-university',
                'description': 'Match transactions with bank statements',
                'url': 'docs:bank_reconciliation',
            },
            {
                'title': 'Reports',
                'icon': 'fa-chart-bar',
                'description': 'Generate financial and operational reports',
                'url': 'docs:reports',
            },
            {
                'title': 'Sales',
                'icon': 'fa-shopping-cart',
                'description': 'Sales tracking and customer management',
                'url': 'docs:sales',
            },
            {
                'title': 'Account Management',
                'icon': 'fa-user-cog',
                'description': 'User profiles, companies, and settings',
                'url': 'docs:accounts',
            },
            {
                'title': 'API Reference',
                'icon': 'fa-code',
                'description': 'REST API documentation for developers',
                'url': 'docs:api',
            },
            {
                'title': 'Troubleshooting',
                'icon': 'fa-tools',
                'description': 'Common issues and solutions',
                'url': 'docs:troubleshooting',
            },
        ]
    }
    return render(request, 'docs/home.html', context)


@login_required
def getting_started(request):
    """Getting started guide"""
    return render(request, 'docs/getting_started.html', get_base_context('getting_started'))


@login_required
def dashboard_docs(request):
    """Dashboard documentation"""
    return render(request, 'docs/dashboard.html', get_base_context('dashboard'))


@login_required
def invoicing_docs(request):
    """Invoicing documentation"""
    return render(request, 'docs/invoicing.html', get_base_context('invoicing'))


@login_required
def expenses_docs(request):
    """Expenses documentation"""
    return render(request, 'docs/expenses.html', get_base_context('expenses'))


@login_required
def inventory_docs(request):
    """Inventory documentation"""
    return render(request, 'docs/inventory.html', get_base_context('inventory'))


@login_required
def hr_docs(request):
    """HR management documentation"""
    return render(request, 'docs/hr.html', get_base_context('hr'))


@login_required
def ai_insights_docs(request):
    """AI Insights documentation"""
    return render(request, 'docs/ai_insights.html', get_base_context('ai_insights'))


@login_required
def bank_reconciliation_docs(request):
    """Bank reconciliation documentation"""
    return render(request, 'docs/bank_reconciliation.html', get_base_context('bank_reconciliation'))


@login_required
def reports_docs(request):
    """Reports documentation"""
    return render(request, 'docs/reports.html', get_base_context('reports'))


@login_required
def sales_docs(request):
    """Sales documentation"""
    return render(request, 'docs/sales.html', get_base_context('sales'))


@login_required
def accounts_docs(request):
    """Account management documentation"""
    return render(request, 'docs/accounts.html', get_base_context('accounts'))


@login_required
def api_docs(request):
    """API documentation"""
    return render(request, 'docs/api.html', get_base_context('api'))


@login_required
def troubleshooting(request):
    """Troubleshooting guide"""
    return render(request, 'docs/troubleshooting.html', get_base_context('troubleshooting'))
