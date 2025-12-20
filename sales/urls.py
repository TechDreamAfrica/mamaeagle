"""
URLs for the Sales app - Sales Management and CRM System
"""
from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Dashboard
    path('', views.sales_dashboard, name='dashboard'),
    
    # Lead URLs
    path('leads/', views.LeadListView.as_view(), name='lead_list'),
    path('leads/create/', views.LeadCreateView.as_view(), name='lead_create'),
    path('leads/<int:pk>/', views.LeadDetailView.as_view(), name='lead_detail'),
    path('leads/<int:pk>/edit/', views.LeadUpdateView.as_view(), name='lead_update'),
    path('leads/<int:lead_id>/convert/', views.convert_lead_to_opportunity, name='convert_lead'),
    
    # Lead bulk operations
    path('leads/bulk-delete/', views.bulk_delete_leads, name='bulk_delete_leads'),
    path('leads/bulk-export/', views.bulk_export_leads, name='bulk_export_leads'),
    
    # Opportunity URLs
    path('opportunities/', views.OpportunityListView.as_view(), name='opportunity_list'),
    path('opportunities/create/', views.OpportunityCreateView.as_view(), name='opportunity_create'),
    path('opportunities/<int:pk>/', views.OpportunityDetailView.as_view(), name='opportunity_detail'),
    path('opportunities/<int:pk>/edit/', views.OpportunityUpdateView.as_view(), name='opportunity_update'),
    
    # Opportunity bulk operations
    path('opportunities/bulk-delete/', views.bulk_delete_opportunities, name='bulk_delete_opportunities'),
    path('opportunities/bulk-export/', views.bulk_export_opportunities, name='bulk_export_opportunities'),
    
    # Sales Activity URLs
    path('activities/', views.SalesActivityListView.as_view(), name='activity_list'),
    path('activities/create/', views.SalesActivityCreateView.as_view(), name='activity_create'),
    
    # Sales Rep URLs
    path('sales-reps/', views.SalesRepListView.as_view(), name='sales_rep_list'),
    path('sales-reps/<int:pk>/', views.SalesRepDetailView.as_view(), name='sales_rep_detail'),
    
    # Commission URLs
    path('commissions/', views.CommissionListView.as_view(), name='commission_list'),
    
    # Territory URLs
    path('territories/', views.TerritoryListView.as_view(), name='territory_list'),
    path('territories/<int:pk>/', views.TerritoryDetailView.as_view(), name='territory_detail'),
    
    # AJAX/API URLs
    path('api/pipeline-data/', views.sales_pipeline_data, name='pipeline_data'),
    path('api/performance-data/', views.sales_performance_data, name='performance_data'),
]
