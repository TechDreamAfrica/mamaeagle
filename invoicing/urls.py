from django.urls import path
from . import views

app_name = 'invoicing'

urlpatterns = [
    # Invoice URLs
    path('', views.invoice_list, name='invoice_list'),
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('invoices/<int:pk>/send/', views.invoice_send, name='invoice_send'),
    path('invoices/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    
    # Bulk operations
    path('bulk-delete/', views.bulk_delete_invoices, name='bulk_delete_invoices'),
    path('bulk-export/', views.bulk_export_invoices, name='bulk_export_invoices'),
    
    # Customer URLs
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    
    # Product URLs
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    
    # Payment URLs
    path('invoices/<int:invoice_id>/payments/record/', views.record_payment, name='record_payment'),
    
    # API URLs
    path('api/products/<int:product_id>/', views.get_product_details, name='product_details'),
    path('api/customers/create/', views.api_customer_create, name='api_customer_create'),
    
    # Admin/Testing URLs
    path('create-sample-data/', views.create_sample_data, name='create_sample_data'),
]
