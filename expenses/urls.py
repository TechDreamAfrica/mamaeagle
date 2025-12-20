from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('', views.expense_list, name='expense_list'),
    path('create/', views.expense_create, name='expense_create'),
    path('<int:pk>/', views.expense_detail, name='expense_detail'),
    path('<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('<int:pk>/duplicate/', views.expense_duplicate, name='expense_duplicate'),
    path('<int:pk>/approve/', views.expense_approve, name='expense_approve'),
    path('<int:pk>/reject/', views.expense_reject, name='expense_reject'),
    path('<int:pk>/export-pdf/', views.expense_export_pdf, name='expense_export_pdf'),
    path('<int:pk>/add-to-report/', views.expense_add_to_report, name='expense_add_to_report'),
    
    # Bulk operations
    path('bulk-delete/', views.bulk_delete_expenses, name='bulk_delete_expenses'),
    path('bulk-export/', views.bulk_export_expenses, name='bulk_export_expenses'),
    
    # AJAX endpoints
    path('ajax/add-category/', views.add_category_ajax, name='add_category_ajax'),
    path('ajax/add-vendor/', views.add_vendor_ajax, name='add_vendor_ajax'),
    path('ajax/process-receipt/', views.process_receipt_ajax, name='process_receipt_ajax'),
    path('ajax/vendor/<int:vendor_id>/', views.get_vendor_details, name='get_vendor_details'),

    # Vendor Management
    path('vendors/', views.VendorListView.as_view(), name='vendor_list'),
    path('vendors/create/', views.VendorCreateView.as_view(), name='vendor_create'),
    path('vendors/<int:pk>/edit/', views.VendorUpdateView.as_view(), name='vendor_update'),
    path('vendors/<int:pk>/delete/', views.VendorDeleteView.as_view(), name='vendor_delete'),
]
