"""
URLs for the Inventory app - Inventory Management System
"""
from django.urls import path
from . import views
from . import ajax_extra

app_name = 'inventory'

urlpatterns = [
    # Dashboard
    path('', views.inventory_dashboard, name='dashboard'),
    
    # Product URLs
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/bulk-upload/', views.product_bulk_upload, name='product_bulk_upload'),
    path('products/template-download/', views.product_template_download, name='product_template_download'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    
    # Stock Movement URLs
    path('movements/', views.StockMovementListView.as_view(), name='stock_movement_list'),
    path('movements/create/', views.StockMovementCreateView.as_view(), name='stock_movement_create'),
    
    # Purchase Order URLs
    path('purchase-orders/', views.PurchaseOrderListView.as_view(), name='purchase_order_list'),
    path('purchase-orders/create/', views.PurchaseOrderCreateView.as_view(), name='purchase_order_create'),
    path('purchase-orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='purchase_order_detail'),
    path('purchase-orders/<int:pk>/edit/', views.PurchaseOrderUpdateView.as_view(), name='purchase_order_update'),
    
    # Supplier URLs
    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/create/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('suppliers/<int:pk>/', views.SupplierDetailView.as_view(), name='supplier_detail'),
    
    # Warehouse URLs
    path('warehouses/', views.WarehouseListView.as_view(), name='warehouse_list'),
    path('warehouses/<int:pk>/', views.WarehouseDetailView.as_view(), name='warehouse_detail'),
    
    # Inventory Count URLs
    path('counts/', views.InventoryCountListView.as_view(), name='inventory_count_list'),
    path('counts/create/', views.InventoryCountCreateView.as_view(), name='inventory_count_create'),
    path('counts/<int:pk>/', views.InventoryCountDetailView.as_view(), name='inventory_count_detail'),
    path('counts/<int:count_id>/start/', views.start_inventory_count, name='start_inventory_count'),
    path('counts/<int:count_id>/items/<int:item_id>/record/', views.record_count, name='record_count'),
    
    # Report URLs
    path('reports/stock/', views.stock_report, name='stock_report'),
    path('reports/low-stock/', views.low_stock_report, name='low_stock_report'),
    
    # Dashboard and Stock Management URLs
    path('stock-movements/', views.stock_movements_list, name='stock_movements'),
    path('low-stock-alert/', views.low_stock_alert, name='low_stock_alert'),
    
    # AJAX/API URLs
    path('api/product-info/<int:product_id>/', views.get_product_info, name='get_product_info'),
    path('api/check-sku/', views.check_sku_availability, name='check_sku_availability'),
    path('api/analytics-data/', views.inventory_analytics_data, name='analytics_data'),
    path('api/category-data/', views.category_data, name='category_data'),
    path('api/movement-trends/', views.movement_trends, name='movement_trends'),
    path('ajax/add-category/', ajax_extra.add_category_ajax, name='add_category_ajax'),
    path('ajax/barcode-lookup/', ajax_extra.barcode_lookup, name='barcode_lookup'),
]
