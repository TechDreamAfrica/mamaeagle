from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Main admin dashboard
    path('', views.AdminDashboardView.as_view(), name='dashboard'),
    
    # Users Management
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    
    # Companies Management
    path('companies/', views.CompanyListView.as_view(), name='company_list'),
    path('companies/create/', views.CompanyCreateView.as_view(), name='company_create'),
    path('companies/<int:pk>/', views.CompanyDetailView.as_view(), name='company_detail'),
    path('companies/<int:pk>/edit/', views.CompanyUpdateView.as_view(), name='company_update'),
    path('companies/<int:pk>/delete/', views.CompanyDeleteView.as_view(), name='company_delete'),
    
    # Website Products Management
    path('website/products/', views.WebsiteProductListView.as_view(), name='website_product_list'),
    path('website/products/create/', views.WebsiteProductCreateView.as_view(), name='website_product_create'),
    path('website/products/<int:pk>/', views.WebsiteProductDetailView.as_view(), name='website_product_detail'),
    path('website/products/<int:pk>/edit/', views.WebsiteProductUpdateView.as_view(), name='website_product_update'),
    path('website/products/<int:pk>/delete/', views.WebsiteProductDeleteView.as_view(), name='website_product_delete'),
    
    # Website Categories Management
    path('website/categories/', views.WebsiteCategoryListView.as_view(), name='website_category_list'),
    path('website/categories/create/', views.WebsiteCategoryCreateView.as_view(), name='website_category_create'),
    path('website/categories/<int:pk>/edit/', views.WebsiteCategoryUpdateView.as_view(), name='website_category_update'),
    path('website/categories/<int:pk>/delete/', views.WebsiteCategoryDeleteView.as_view(), name='website_category_delete'),
    
    # Orders Management
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/bulk-action/', views.order_bulk_action, name='order_bulk_action'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/edit/', views.OrderUpdateView.as_view(), name='order_update'),
    path('orders/<int:pk>/delete/', views.OrderDeleteView.as_view(), name='order_delete'),
    
    # Inventory Products Management
    path('inventory/products/', views.InventoryProductListView.as_view(), name='inventory_product_list'),
    path('inventory/products/create/', views.InventoryProductCreateView.as_view(), name='inventory_product_create'),
    path('inventory/products/<int:pk>/', views.InventoryProductDetailView.as_view(), name='inventory_product_detail'),
    path('inventory/products/<int:pk>/edit/', views.InventoryProductUpdateView.as_view(), name='inventory_product_update'),
    path('inventory/products/<int:pk>/delete/', views.InventoryProductDeleteView.as_view(), name='inventory_product_delete'),
    
    # Inventory Categories Management
    path('inventory/categories/', views.InventoryCategoryListView.as_view(), name='inventory_category_list'),
    path('inventory/categories/create/', views.InventoryCategoryCreateView.as_view(), name='inventory_category_create'),
    path('inventory/categories/<int:pk>/edit/', views.InventoryCategoryUpdateView.as_view(), name='inventory_category_update'),
    path('inventory/categories/<int:pk>/delete/', views.InventoryCategoryDeleteView.as_view(), name='inventory_category_delete'),
    
    # Suppliers Management
    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/create/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('suppliers/<int:pk>/', views.SupplierDetailView.as_view(), name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.SupplierDeleteView.as_view(), name='supplier_delete'),
    
    # Customers Management
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_update'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
]