from django.urls import path
from . import views

app_name = 'hr'

urlpatterns = [
    path('', views.hr_dashboard, name='hr_dashboard'),
    path('employees/', views.EmployeeListView.as_view(), name='employee_list'),
    path('employees/create/', views.EmployeeCreateView.as_view(), name='employee_create'),
    path('employees/<int:pk>/', views.EmployeeDetailView.as_view(), name='employee_detail'),
    path('employees/<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='employee_update'),
    path('employees/<int:pk>/delete/', views.EmployeeDeleteView.as_view(), name='employee_delete'),
    
    # Bulk operations
    path('employees/bulk-delete/', views.bulk_delete_employees, name='bulk_delete_employees'),
    path('employees/bulk-export/', views.bulk_export_employees, name='bulk_export_employees'),
    
    path('payroll/', views.payroll_list, name='payroll_list'),
    path('time-tracking/', views.time_tracking, name='time_tracking'),
]
