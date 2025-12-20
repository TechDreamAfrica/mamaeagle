from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Main reports dashboard
    path('', views.reports_main, name='reports_main'),
    path('list/', views.report_list, name='report_list'),
    
    # Traditional reports
    path('profit-loss/', views.profit_loss_report, name='profit_loss'),
    path('balance-sheet/', views.balance_sheet_report, name='balance_sheet'),
    path('cash-flow/', views.cash_flow_report, name='cash_flow'),
    path('ar-aging/', views.ar_aging_report, name='ar_aging'),
    path('expense-category/', views.expense_category_report, name='expense_category'),
    path('sales-tax/', views.sales_tax_report, name='sales_tax'),
    path('budget-actual/', views.budget_actual_report, name='budget_actual'),
    path('trial-balance/', views.trial_balance_report, name='trial_balance'),
    path('customer-sales/', views.customer_sales_report, name='customer_sales'),
    
    # Financial Statement Generation
    path('generate/monthly/', views.generate_monthly_statement, name='generate_monthly'),
    path('generate/annual/', views.generate_annual_statement, name='generate_annual'),
    path('generate/quarterly/', views.generate_quarterly_statement, name='generate_quarterly'),
    
    # Comprehensive Financial Statements (NEW)
    path('statements/monthly/', views.monthly_financial_statements, name='monthly_statements'),
    path('statements/annual/', views.annual_financial_statements, name='annual_statements'),
    path('statements/comparative/', views.comparative_analysis, name='comparative_analysis'),
    
    # View and Export Statements
    path('statement/<int:pk>/', views.view_statement, name='view_statement'),
    path('statement/<int:pk>/export/', views.export_statement, name='export_statement'),
    
    # Chart of Accounts and Journal Entries
    path('chart-of-accounts/', views.chart_of_accounts, name='chart_of_accounts'),
    path('journal-entries/', views.journal_entries, name='journal_entries'),
]
