"""
Mama Eagle Enterprise URL Configuration

Modern AI-Powered Accounting Platform with E-commerce
Multi-branch business management system
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Admin Panel - Comprehensive system administration
    path('admin-panel/', include('admin_panel.urls', namespace='admin_panel')),

    # Main e-commerce website
    path('', include('website.urls', namespace='website')),
    
    # Authentication
    path('accounts/', include('accounts.urls', namespace='accounts')),

    # Convenience redirects for authentication
    path('login/', RedirectView.as_view(url='/accounts/login/', permanent=False)),
    path('register/', RedirectView.as_view(url='/accounts/register/', permanent=False)),

    # Main application URLs (Business Management Dashboard)
    path('app/', RedirectView.as_view(url='/app/dashboard/', permanent=False)),
    path('app/dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('app/invoicing/', include('invoicing.urls', namespace='invoicing')),
    path('app/expenses/', include('expenses.urls', namespace='expenses')),
    path('app/reports/', include('reports.urls', namespace='reports')),
    path('app/hr/', include('hr.urls', namespace='hr')),
    path('app/ai-insights/', include('ai_insights.urls', namespace='ai_insights')),
    
    # Legacy reports URL redirect (for backward compatibility)
    path('reports/', include('reports.urls')),
    
    # New feature apps
    path('app/sales/', include('sales.urls', namespace='sales')),
    path('app/bank-reconciliation/', include('bank_reconciliation.urls', namespace='bank_reconciliation')),
    path('app/inventory/', include('inventory.urls', namespace='inventory')),
    
    # API endpoints
    path('api/v1/', include('api.urls', namespace='api')),
    
    # Documentation
    path('documentation/', include('docs.urls', namespace='docs')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
