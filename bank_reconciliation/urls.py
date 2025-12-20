"""
URLs for the Bank Reconciliation app - Bank Account Reconciliation Management
"""
from django.urls import path
from . import views

app_name = 'bank_reconciliation'

urlpatterns = [
    # Dashboard
    path('', views.reconciliation_dashboard, name='dashboard'),
    
    # Bank Account URLs
    path('accounts/', views.BankAccountListView.as_view(), name='account_list'),
    path('accounts/create/', views.BankAccountCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/', views.BankAccountDetailView.as_view(), name='account_detail'),
    path('accounts/<int:pk>/edit/', views.BankAccountUpdateView.as_view(), name='account_update'),
    path('accounts/<int:account_id>/export/', views.export_transactions, name='export_transactions'),
    
    # Bank Statement URLs
    path('statements/', views.BankStatementListView.as_view(), name='statement_list'),
    path('statements/create/', views.BankStatementCreateView.as_view(), name='statement_create'),
    path('statements/<int:pk>/', views.BankStatementDetailView.as_view(), name='statement_detail'),
    path('statements/<int:statement_id>/import/', views.import_transactions, name='import_transactions'),
    
    # Bank Transaction URLs
    path('transactions/', views.BankTransactionListView.as_view(), name='transaction_list'),
    path('transactions/<int:pk>/', views.BankTransactionDetailView.as_view(), name='transaction_detail'),
    path('transactions/<int:pk>/edit/', views.BankTransactionUpdateView.as_view(), name='transaction_update'),
    path('transactions/<int:transaction_id>/clear/', views.mark_transaction_cleared, name='mark_cleared'),
    
    # Reconciliation Session URLs
    path('sessions/', views.ReconciliationSessionListView.as_view(), name='session_list'),
    path('sessions/<int:pk>/', views.ReconciliationSessionDetailView.as_view(), name='session_detail'),
    path('sessions/start/<int:account_id>/', views.start_reconciliation, name='start_reconciliation'),
    path('sessions/<int:session_id>/reconcile/', views.reconcile_transactions, name='reconcile_transactions'),
    path('sessions/<int:session_id>/complete/', views.complete_reconciliation, name='complete_reconciliation'),
    path('sessions/<int:session_id>/auto-match/', views.auto_match_transactions, name='auto_match'),
    
    # Reconciliation Rule URLs
    path('rules/', views.ReconciliationRuleListView.as_view(), name='rule_list'),
    path('rules/create/', views.ReconciliationRuleCreateView.as_view(), name='rule_create'),
    
    # API endpoints
    path('api/unreconciled-count/', views.unreconciled_count, name='unreconciled_count'),
]
