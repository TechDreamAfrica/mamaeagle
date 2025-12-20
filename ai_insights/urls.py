from django.urls import path
from . import views

app_name = 'ai_insights'

urlpatterns = [
    # Main pages
    path('', views.insights_dashboard, name='insights'),
    path('cash-flow-prediction/', views.cash_flow_prediction, name='cash_flow_prediction'),
    path('expense-analysis/', views.expense_analysis, name='expense_analysis'),
    path('customer-insights/', views.customer_insights, name='customer_insights'),
    
    # API endpoints
    path('api/generate-insights/', views.generate_insights_api, name='generate_insights_api'),
    path('api/acknowledge-insight/<int:insight_id>/', views.acknowledge_insight, name='acknowledge_insight'),
]
