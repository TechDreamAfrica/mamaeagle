from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Q, F
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .forms import ProductForm

from .models import (
    Category, Supplier, Product, ProductSupplier, Warehouse,
    StockMovement, StockLevel, PurchaseOrder, InventoryCount, InventoryCountItem
)


# Dashboard and Overview Views
@login_required
def inventory_dashboard(request):
    """Inventory dashboard with key metrics and alerts."""
    # Key metrics
    total_products = Product.objects.filter(is_active=True).count()
    total_suppliers = Supplier.objects.filter(is_active=True).count()
    total_warehouses = Warehouse.objects.filter(is_active=True).count()
    
    # Stock metrics
    low_stock_products = Product.objects.filter(
        is_active=True
    ).annotate(
        current_stock=Sum('stock_movements__quantity_change')
    ).filter(
        current_stock__lte=F('reorder_point')
    ).count()
    
    # Financial metrics - Calculate total inventory value
    total_inventory_value = Decimal('0.00')
    products = Product.objects.filter(is_active=True).select_related('category')
    for product in products:
        total_inventory_value += product.stock_value
    
    # Recent activity
    recent_movements = StockMovement.objects.select_related(
        'product', 'warehouse', 'created_by'
    ).order_by('-created_at')[:10]
    
    # Purchase orders
    pending_pos = PurchaseOrder.objects.filter(
        status__in=['sent', 'confirmed', 'partially_received']
    ).count()
    
    # Low stock alerts
    low_stock_alerts = Product.objects.filter(
        is_active=True
    ).annotate(
        current_stock=Sum('stock_movements__quantity_change')
    ).filter(
        current_stock__lte=F('reorder_point')
    )[:10]
    
    # Products needing count
    products_needing_count = Product.objects.filter(
        is_active=True,
        count_items__inventory_count__count_date__lt=timezone.now().date() - timedelta(days=90)
    ).distinct()[:10]
    
    context = {
        'total_products': total_products,
        'total_suppliers': total_suppliers,
        'total_warehouses': total_warehouses,
        'low_stock_products': low_stock_products,
        'total_inventory_value': total_inventory_value,
        'recent_movements': recent_movements,
        'pending_pos': pending_pos,
        'low_stock_alerts': low_stock_alerts,
        'products_needing_count': products_needing_count,
    }
    
    return render(request, 'inventory/dashboard.html', context)


# Product Views
class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('category')
        search_query = self.request.GET.get('q', '')
        category_id = self.request.GET.get('category', '')

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(sku__icontains=search_query)
            )
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True).order_by('name')
        context['total_products'] = Product.objects.count()
        return context


class ProductDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a product."""
    model = Product
    template_name = 'inventory/product_detail.html'
    context_object_name = 'product'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stock_movements'] = self.object.stock_movements.order_by('-movement_date')[:20]
        context['suppliers'] = self.object.suppliers.through.objects.filter(
            product=self.object, is_active=True
        ).select_related('supplier')
        context['stock_levels'] = self.object.stock_levels.select_related('warehouse')
        context['purchase_order_items'] = self.object.purchase_order_items.select_related(
            'purchase_order'
        ).order_by('-created_at')[:10]
        return context


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('inventory:product_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filter categories by current user's company
        if self.request.company:
            form.fields['category'].queryset = Category.objects.filter(
                company=self.request.company, is_active=True
            ).order_by('name')
        form.fields['category'].empty_label = "Select a category (optional)"
        return form

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # Set company - handle both regular users and superusers
        if self.request.company:
            form.instance.company = self.request.company
        else:
            # For superusers or users without request.company, get from UserCompany
            from accounts.models import UserCompany
            user_company = UserCompany.objects.filter(
                user=self.request.user,
                is_active=True
            ).first()
            if user_company:
                form.instance.company = user_company.company
            else:
                messages.error(self.request, 'No company associated with your account.')
                return redirect('inventory:product_list')
                
        messages.success(self.request, 'Product created successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'There were errors in the form. Please correct them and try again.')
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.company:
            context['categories'] = Category.objects.filter(
                company=self.request.company, is_active=True
            ).order_by('name')
        return context
    

class ProductUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing product."""
    model = Product
    template_name = 'inventory/product_form.html'
    fields = [
        'sku', 'barcode', 'name', 'description', 'category', 'product_type',
        'unit_type', 'cost_price', 'selling_price', 'minimum_stock_level',
        'maximum_stock_level', 'reorder_point', 'reorder_quantity',
        'weight', 'dimensions', 'is_active', 'is_serialized', 'tax_exempt'
    ]
    success_url = reverse_lazy('inventory:product_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Product updated successfully!')
        return super().form_valid(form)


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a product."""
    model = Product
    template_name = 'inventory/product_confirm_delete.html'
    success_url = reverse_lazy('inventory:product_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Product deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Stock Movement Views
class StockMovementListView(LoginRequiredMixin, ListView):
    """List all stock movements."""
    model = StockMovement
    template_name = 'inventory/stock_movement_list.html'
    context_object_name = 'movements'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = StockMovement.objects.select_related(
            'product', 'warehouse', 'created_by'
        ).order_by('-movement_date', '-created_at')
        
        # Filter by product
        product = self.request.GET.get('product')
        if product:
            queryset = queryset.filter(product_id=product)
        
        # Filter by warehouse
        warehouse = self.request.GET.get('warehouse')
        if warehouse:
            queryset = queryset.filter(warehouse_id=warehouse)
        
        # Filter by movement type
        movement_type = self.request.GET.get('movement_type')
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        
        # Filter by date range
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date:
            queryset = queryset.filter(movement_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(movement_date__lte=end_date)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(is_active=True)
        context['warehouses'] = Warehouse.objects.filter(is_active=True)
        context['movement_types'] = StockMovement.MOVEMENT_TYPES
        return context


class StockMovementCreateView(LoginRequiredMixin, CreateView):
    """Create a new stock movement."""
    model = StockMovement
    template_name = 'inventory/stock_movement_form.html'
    fields = [
        'product', 'warehouse', 'movement_type', 'quantity_change',
        'unit_cost', 'reference_number', 'notes'
    ]
    success_url = reverse_lazy('inventory:stock_movement_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # Update stock level
        stock_level, created = StockLevel.objects.get_or_create(
            product=form.instance.product,
            warehouse=form.instance.warehouse,
            defaults={'quantity_on_hand': 0}
        )
        
        stock_level.quantity_on_hand += form.instance.quantity_change
        stock_level.last_movement_date = form.instance.movement_date
        stock_level.save()
        
        messages.success(self.request, 'Stock movement recorded successfully!')
        return super().form_valid(form)


# Purchase Order Views
class PurchaseOrderListView(LoginRequiredMixin, ListView):
    """List all purchase orders."""
    model = PurchaseOrder
    template_name = 'inventory/purchase_order_list.html'
    context_object_name = 'purchase_orders'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = PurchaseOrder.objects.select_related(
            'supplier', 'warehouse', 'created_by'
        ).annotate(
            item_count=Count('items')
        ).order_by('-order_date')
        
        # Filter by supplier
        supplier = self.request.GET.get('supplier')
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by warehouse
        warehouse = self.request.GET.get('warehouse')
        if warehouse:
            queryset = queryset.filter(warehouse_id=warehouse)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['suppliers'] = Supplier.objects.filter(is_active=True)
        context['warehouses'] = Warehouse.objects.filter(is_active=True)
        context['po_statuses'] = PurchaseOrder.STATUS_CHOICES
        return context


class PurchaseOrderDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a purchase order."""
    model = PurchaseOrder
    template_name = 'inventory/purchase_order_detail.html'
    context_object_name = 'purchase_order'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.select_related('product')
        return context


class PurchaseOrderCreateView(LoginRequiredMixin, CreateView):
    """Create a new purchase order."""
    model = PurchaseOrder
    template_name = 'inventory/purchase_order_form.html'
    fields = [
        'po_number', 'supplier', 'warehouse', 'order_date',
        'expected_delivery_date', 'status', 'subtotal', 'tax_amount',
        'shipping_cost', 'total_amount', 'notes'
    ]
    success_url = reverse_lazy('inventory:purchase_order_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Purchase order created successfully!')
        return super().form_valid(form)


class PurchaseOrderUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing purchase order."""
    model = PurchaseOrder
    template_name = 'inventory/purchase_order_form.html'
    fields = [
        'po_number', 'supplier', 'warehouse', 'order_date',
        'expected_delivery_date', 'status', 'subtotal', 'tax_amount',
        'shipping_cost', 'total_amount', 'notes'
    ]
    success_url = reverse_lazy('inventory:purchase_order_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Purchase order updated successfully!')
        return super().form_valid(form)


# Supplier Views
class SupplierListView(LoginRequiredMixin, ListView):
    """List all suppliers."""
    model = Supplier
    template_name = 'inventory/supplier_list.html'
    context_object_name = 'suppliers'
    
    def get_queryset(self):
        queryset = Supplier.objects.annotate(
            product_count=Count('products'),
            po_count=Count('purchase_orders')
        ).order_by('name')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset


class SupplierDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a supplier."""
    model = Supplier
    template_name = 'inventory/supplier_detail.html'
    context_object_name = 'supplier'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = self.object.products.filter(is_active=True)
        context['purchase_orders'] = self.object.purchase_orders.order_by('-order_date')[:10]
        context['product_suppliers'] = ProductSupplier.objects.filter(
            supplier=self.object, is_active=True
        ).select_related('product')
        return context


class SupplierCreateView(LoginRequiredMixin, CreateView):
    """Create a new supplier."""
    model = Supplier
    template_name = 'inventory/supplier_form.html'
    fields = [
        'name', 'contact_person', 'email', 'phone', 'address',
        'tax_id', 'payment_terms', 'lead_time_days', 'rating',
        'notes', 'is_active'
    ]
    success_url = reverse_lazy('inventory:supplier_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Supplier created successfully!')
        return super().form_valid(form)


# Warehouse Views
class WarehouseListView(LoginRequiredMixin, ListView):
    """List all warehouses."""
    model = Warehouse
    template_name = 'inventory/warehouse_list.html'
    context_object_name = 'warehouses'
    
    def get_queryset(self):
        return Warehouse.objects.annotate(
            product_count=Count('stock_levels'),
            total_stock_value=Sum(
                F('stock_levels__quantity_on_hand') * F('stock_levels__product__cost_price')
            )
        ).order_by('name')


class WarehouseDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a warehouse."""
    model = Warehouse
    template_name = 'inventory/warehouse_detail.html'
    context_object_name = 'warehouse'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stock_levels'] = self.object.stock_levels.select_related(
            'product'
        ).filter(quantity_on_hand__gt=0)
        context['recent_movements'] = self.object.stock_movements.select_related(
            'product', 'created_by'
        ).order_by('-movement_date')[:20]
        return context


# Inventory Count Views
class InventoryCountListView(LoginRequiredMixin, ListView):
    """List all inventory counts."""
    model = InventoryCount
    template_name = 'inventory/inventory_count_list.html'
    context_object_name = 'counts'
    
    def get_queryset(self):
        return InventoryCount.objects.select_related(
            'warehouse', 'counted_by'
        ).annotate(
            item_count=Count('count_items')
        ).order_by('-count_date')


class InventoryCountDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of an inventory count."""
    model = InventoryCount
    template_name = 'inventory/inventory_count_detail.html'
    context_object_name = 'count'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['count_items'] = self.object.count_items.select_related(
            'product', 'counted_by'
        ).order_by('product__name')
        
        # Calculate variance statistics
        items = context['count_items']
        context['total_variance'] = sum(item.variance for item in items)
        context['total_variance_value'] = sum(item.variance_value for item in items)
        context['items_with_variance'] = items.exclude(variance=0).count()
        
        return context


class InventoryCountCreateView(LoginRequiredMixin, CreateView):
    """Create a new inventory count."""
    model = InventoryCount
    template_name = 'inventory/inventory_count_form.html'
    fields = [
        'count_number', 'warehouse', 'count_date', 'count_type', 'notes'
    ]
    success_url = reverse_lazy('inventory:inventory_count_list')
    
    def form_valid(self, form):
        # Auto-generate count number if not provided
        if not form.instance.count_number:
            form.instance.count_number = f"COUNT-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        
        messages.success(self.request, 'Inventory count created successfully!')
        return super().form_valid(form)


@login_required
def start_inventory_count(request, count_id):
    """Start an inventory count and add products to count."""
    count = get_object_or_404(InventoryCount, id=count_id)
    
    if request.method == 'POST':
        # Add products to count based on selection criteria
        count_type = request.POST.get('count_type', 'selected')
        
        if count_type == 'all':
            # Add all products in warehouse
            products = Product.objects.filter(
                is_active=True,
                stock_levels__warehouse=count.warehouse
            )
        elif count_type == 'low_stock':
            # Add low stock products
            products = Product.objects.filter(
                is_active=True,
                stock_levels__warehouse=count.warehouse
            ).annotate(
                current_stock=Sum('stock_movements__quantity_change')
            ).filter(current_stock__lte=F('reorder_point'))
        else:
            # Selected products
            product_ids = request.POST.getlist('product_ids')
            products = Product.objects.filter(id__in=product_ids)
        
        # Create count items
        for product in products:
            stock_level = StockLevel.objects.filter(
                product=product, warehouse=count.warehouse
            ).first()
            
            InventoryCountItem.objects.get_or_create(
                inventory_count=count,
                product=product,
                defaults={
                    'expected_quantity': stock_level.quantity_on_hand if stock_level else 0
                }
            )
        
        count.status = 'in_progress'
        count.save()
        
        messages.success(request, 'Inventory count started successfully!')
        return redirect('inventory:inventory_count_detail', pk=count.id)
    
    # Get products in warehouse
    warehouse_products = Product.objects.filter(
        is_active=True,
        stock_levels__warehouse=count.warehouse
    ).select_related('category')
    
    context = {
        'count': count,
        'warehouse_products': warehouse_products,
    }
    
    return render(request, 'inventory/start_inventory_count.html', context)


@login_required
def record_count(request, count_id, item_id):
    """Record counted quantity for an item."""
    count_item = get_object_or_404(InventoryCountItem, id=item_id, inventory_count_id=count_id)
    
    if request.method == 'POST':
        counted_quantity = int(request.POST.get('counted_quantity', 0))
        notes = request.POST.get('notes', '')
        
        count_item.counted_quantity = counted_quantity
        count_item.notes = notes
        count_item.counted_at = timezone.now()
        count_item.counted_by = request.user
        count_item.save()  # This will calculate variance automatically
        
        return JsonResponse({
            'success': True,
            'variance': count_item.variance,
            'variance_value': float(count_item.variance_value)
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


# Report Views
@login_required
def stock_report(request):
    """Generate stock level report."""
    warehouse_id = request.GET.get('warehouse')
    category_id = request.GET.get('category')
    
    stock_levels = StockLevel.objects.select_related(
        'product', 'warehouse', 'product__category'
    ).filter(quantity_on_hand__gt=0)
    
    if warehouse_id:
        stock_levels = stock_levels.filter(warehouse_id=warehouse_id)
    if category_id:
        stock_levels = stock_levels.filter(product__category_id=category_id)
    
    context = {
        'stock_levels': stock_levels,
        'warehouses': Warehouse.objects.filter(is_active=True),
        'categories': Category.objects.filter(is_active=True),
        'selected_warehouse': warehouse_id,
        'selected_category': category_id,
    }
    
    return render(request, 'inventory/reports/stock_report.html', context)


@login_required
def low_stock_report(request):
    """Generate low stock report."""
    low_stock_products = Product.objects.filter(
        is_active=True
    ).annotate(
        current_stock=Sum('stock_movements__quantity_change')
    ).filter(
        current_stock__lte=F('reorder_point')
    ).select_related('category')
    
    context = {'low_stock_products': low_stock_products}
    return render(request, 'inventory/reports/low_stock_report.html', context)


# AJAX Views
@login_required
def get_product_info(request, product_id):
    """Get product information via AJAX."""
    product = get_object_or_404(Product, id=product_id)
    
    return JsonResponse({
        'name': product.name,
        'sku': product.sku,
        'cost_price': float(product.cost_price),
        'selling_price': float(product.selling_price),
        'current_stock': product.current_stock,
        'reorder_point': product.reorder_point,
    })


@login_required
def check_sku_availability(request):
    """Check if SKU is available."""
    sku = request.GET.get('sku')
    product_id = request.GET.get('product_id')  # For updates
    
    exists = Product.objects.filter(sku=sku)
    if product_id:
        exists = exists.exclude(id=product_id)
    
    return JsonResponse({
        'available': not exists.exists()
    })


@login_required
def inventory_analytics_data(request):
    """Get inventory analytics data for charts."""
    # Stock movement trends
    today = timezone.now().date()
    months_data = []
    
    for i in range(12):
        month_start = (today.replace(day=1) - timedelta(days=32*i)).replace(day=1)
        if i == 0:
            month_end = today
        else:
            month_end = (month_start.replace(month=month_start.month % 12 + 1, day=1) - timedelta(days=1))
        
        movements = StockMovement.objects.filter(
            movement_date__gte=month_start,
            movement_date__lte=month_end
        )
        
        months_data.append({
            'month': month_start.strftime('%Y-%m'),
            'purchases': movements.filter(movement_type='purchase').aggregate(
                total=Sum('total_cost')
            )['total'] or 0,
            'sales': movements.filter(movement_type='sale').aggregate(
                total=Sum('total_cost')
            )['total'] or 0,
        })
    
    # Top products by value
    top_products = Product.objects.filter(
        is_active=True
    ).annotate(
        stock_value=Sum('stock_movements__quantity_change') * F('cost_price')
    ).order_by('-stock_value')[:10]
    
    return JsonResponse({
        'monthly_data': list(reversed(months_data)),
        'top_products': [
            {
                'name': product.name,
                'value': float(product.stock_value or 0)
            }
            for product in top_products
        ]
    })


@login_required
def category_data(request):
    """
    Returns category data for dashboard charts.
    Returns inventory value by category.
    """
    from django.db.models import Sum, F
    
    # Get inventory value by category
    category_data = Category.objects.filter(
        is_active=True,
        product__is_active=True
    ).annotate(
        category_value=Sum(
            F('product__stocklevel__current_stock') * F('product__cost_price'),
            default=0
        )
    ).values('name', 'category_value')
    
    # Convert to dictionary format expected by frontend
    result = {}
    for item in category_data:
        if item['category_value'] and item['category_value'] > 0:
            result[item['name']] = float(item['category_value'])
    
    # If no data, return some default categories
    if not result:
        result = {
            'Electronics': 0,
            'Office Supplies': 0,
            'Furniture': 0,
            'Other': 0
        }
    
    return JsonResponse(result)


@login_required
def movement_trends(request):
    """
    Returns stock movement trends data for dashboard charts.
    Returns daily inbound and outbound movements for the last 30 days.
    """
    from django.db.models import Sum, Q
    
    # Get the last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Get daily movement data
    daily_movements = []
    current_date = start_date
    
    while current_date <= end_date:
        # Get inbound movements (positive quantity changes)
        inbound = StockMovement.objects.filter(
            created_at__date=current_date,
            quantity_change__gt=0
        ).aggregate(
            total=Sum('quantity_change')
        )['total'] or 0
        
        # Get outbound movements (negative quantity changes)
        outbound = StockMovement.objects.filter(
            created_at__date=current_date,
            quantity_change__lt=0
        ).aggregate(
            total=Sum('quantity_change')
        )['total'] or 0
        
        daily_movements.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'inbound': int(inbound),
            'outbound': abs(int(outbound))  # Make positive for display
        })
        
        current_date += timedelta(days=1)
    
    return JsonResponse({
        'daily_movements': daily_movements
    })
