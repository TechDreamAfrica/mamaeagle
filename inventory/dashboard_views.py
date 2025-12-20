"""
Inventory dashboard views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.http import JsonResponse
from .models import Product, StockMovement, Category, Supplier
from .utils import check_and_alert_low_stock


@login_required
def inventory_dashboard(request):
    """
    Main inventory dashboard showing overview and low stock alerts
    """
    # Get current company from session
    company = request.user.current_company
    
    # Get inventory statistics
    total_products = Product.objects.filter(company=company, is_active=True).count()
    
    # Get low stock products
    low_stock_products = []
    for product in Product.objects.filter(company=company, is_active=True):
        if product.is_low_stock():
            low_stock_products.append(product)
    
    # Get recent stock movements
    recent_movements = StockMovement.objects.filter(
        company=company
    ).order_by('-movement_date')[:10]
    
    # Get categories with product counts
    categories = Category.objects.filter(company=company).annotate(
        product_count=Count('products')
    )
    
    # Calculate total inventory value
    total_inventory_value = 0
    for product in Product.objects.filter(company=company, is_active=True):
        total_inventory_value += product.current_stock * product.cost_price
    
    context = {
        'total_products': total_products,
        'low_stock_count': len(low_stock_products),
        'low_stock_products': low_stock_products[:5],  # Show top 5
        'recent_movements': recent_movements,
        'categories': categories,
        'total_inventory_value': total_inventory_value,
    }
    
    return render(request, 'inventory/dashboard.html', context)


@login_required
def product_list(request):
    """
    Display all products with current stock levels
    """
    company = request.user.current_company
    products = Product.objects.filter(company=company, is_active=True).order_by('name')
    
    # Add stock status to each product
    for product in products:
        product.stock_status = 'low' if product.is_low_stock() else 'normal'
        product.needs_reorder_status = product.needs_reorder()
    
    context = {
        'products': products,
    }
    
    return render(request, 'inventory/product_list.html', context)


@login_required
def low_stock_alert(request):
    """
    AJAX endpoint to trigger low stock alerts
    """
    if request.method == 'POST':
        try:
            alert_count = check_and_alert_low_stock()
            return JsonResponse({
                'success': True,
                'alert_count': alert_count,
                'message': f'Checked stock levels. Sent {alert_count} low stock alerts.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def stock_movements_list(request):
    """
    Display stock movement history
    """
    company = request.user.current_company
    movements = StockMovement.objects.filter(
        company=company
    ).select_related('product', 'warehouse').order_by('-movement_date')
    
    # Filter by product if specified
    product_id = request.GET.get('product')
    if product_id:
        movements = movements.filter(product_id=product_id)
    
    # Filter by movement type if specified
    movement_type = request.GET.get('type')
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    
    # Paginate results
    from django.core.paginator import Paginator
    paginator = Paginator(movements, 25)
    page_number = request.GET.get('page')
    movements = paginator.get_page(page_number)
    
    context = {
        'movements': movements,
        'products': Product.objects.filter(company=company, is_active=True),
        'movement_types': StockMovement.MOVEMENT_TYPES,
        'current_product': product_id,
        'current_type': movement_type,
    }
    
    return render(request, 'inventory/stock_movements.html', context)