from django.urls import path
from . import views

app_name = 'website'

urlpatterns = [
    # Main website pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    
    # Newsletter
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    
    # Products
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    
    # Shopping cart
    path('cart/', views.view_cart, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_cart_item'),
    
    # Checkout and orders
    path('checkout/', views.checkout, name='checkout'),
    path('payment/paystack/<str:order_number>/', views.paystack_payment, name='paystack_payment'),
    path('payment/callback/', views.paystack_callback, name='paystack_callback'),
    path('order/success/<str:order_number>/', views.order_success, name='order_success'),
    path('orders/', views.order_history, name='order_history'),
    path('order/<str:order_number>/', views.order_detail, name='order_detail'),
    path('order/<str:order_number>/invoice/', views.download_invoice, name='download_invoice'),
    
    # Customer Authentication (separate from management auth)
    path('customer/register/', views.customer_register, name='customer_register'),
    path('customer/login/', views.customer_login, name='customer_login'),
    path('customer/logout/', views.customer_logout, name='customer_logout'),
    path('customer/profile/', views.customer_profile, name='customer_profile'),
    
    # Invoice Integration API endpoints
    path('api/sync-products-to-invoice/', views.sync_products_to_invoice, name='sync_products_to_invoice'),
    path('api/check-invoice-inventory/', views.check_invoice_inventory, name='check_invoice_inventory'),
    path('api/products-autocomplete/', views.get_products_for_invoice_autocomplete, name='products_autocomplete'),
    path('api/cart/count/', views.cart_count_api, name='cart_count_api'),
]