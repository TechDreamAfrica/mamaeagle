from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('customize/', views.customize_dashboard, name='customize'),
    path('export/', views.export_dashboard_data, name='export_data'),
    path('api/revenue-chart/', views.get_revenue_chart_data, name='revenue_chart_data'),
    path('api/expense-chart/', views.get_expense_chart_data, name='expense_chart_data'),
    path('api/recent-activity/', views.get_recent_activity, name='recent_activity'),
    path('api/product-stats/', views.get_product_stats, name='product_stats'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
]
