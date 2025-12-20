"""
Documentation URLs
"""
from django.urls import path
from . import views

app_name = 'docs'

urlpatterns = [
    path('', views.documentation_home, name='home'),
    path('getting-started/', views.getting_started, name='getting_started'),
    path('dashboard/', views.dashboard_docs, name='dashboard'),
    path('invoicing/', views.invoicing_docs, name='invoicing'),
    path('expenses/', views.expenses_docs, name='expenses'),
    path('inventory/', views.inventory_docs, name='inventory'),
    path('hr/', views.hr_docs, name='hr'),
    path('ai-insights/', views.ai_insights_docs, name='ai_insights'),
    path('bank-reconciliation/', views.bank_reconciliation_docs, name='bank_reconciliation'),
    path('reports/', views.reports_docs, name='reports'),
    path('sales/', views.sales_docs, name='sales'),
    path('accounts/', views.accounts_docs, name='accounts'),
    path('api/', views.api_docs, name='api'),
    path('troubleshooting/', views.troubleshooting, name='troubleshooting'),
]
