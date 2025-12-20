from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import Category, Supplier, Product, ProductSupplier, Warehouse, StockMovement, StockLevel, PurchaseOrder, PurchaseOrderItem, InventoryCount, InventoryCountItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent_category', 'full_path', 'product_count', 'is_active']
    list_filter = ['is_active', 'parent_category', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'full_path']
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'description', 'parent_category')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'email', 'phone', 'rating', 'lead_time_days', 'is_active']
    list_filter = ['rating', 'is_active', 'created_at']
    search_fields = ['name', 'contact_person', 'email', 'tax_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Supplier Information', {
            'fields': ('name', 'contact_person', 'email', 'phone', 'address')
        }),
        ('Business Details', {
            'fields': ('tax_id', 'payment_terms', 'lead_time_days', 'rating')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'category', 'product_type', 'cost_price', 'selling_price', 'profit_margin_display', 'current_stock', 'needs_reorder', 'is_active']
    list_filter = ['product_type', 'category', 'is_active', 'is_serialized', 'tax_exempt', 'created_at']
    search_fields = ['sku', 'barcode', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'current_stock', 'stock_value', 'needs_reorder', 'profit_margin']
    autocomplete_fields = ['category']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('sku', 'barcode', 'name', 'description', 'category', 'product_type')
        }),
        ('Pricing', {
            'fields': ('cost_price', 'selling_price', 'profit_margin')
        }),
        ('Physical Attributes', {
            'fields': ('unit_type', 'weight', 'dimensions')
        }),
        ('Stock Management', {
            'fields': ('minimum_stock_level', 'maximum_stock_level', 'reorder_point', 'reorder_quantity')
        }),
        ('Current Stock', {
            'fields': ('current_stock', 'stock_value', 'needs_reorder'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('is_active', 'is_serialized', 'tax_exempt')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_products', 'deactivate_products']
    
    def profit_margin_display(self, obj):
        margin = obj.profit_margin
        if margin > 0:
            color = 'green'
        elif margin < 0:
            color = 'red'
        else:
            color = 'gray'
        formatted_margin = f"{margin:.1f}%"   # Format first
        return format_html('<span style="color: {};">{}</span>', color, formatted_margin)

    profit_margin_display.short_description = 'Profit Margin'
    
    def activate_products(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} products activated.")
    activate_products.short_description = "Activate selected products"
    
    def deactivate_products(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} products deactivated.")
    deactivate_products.short_description = "Deactivate selected products"


@admin.register(ProductSupplier)
class ProductSupplierAdmin(admin.ModelAdmin):
    list_display = ['product', 'supplier', 'supplier_sku', 'supplier_cost', 'minimum_order_quantity', 'lead_time_days', 'is_preferred']
    list_filter = ['is_preferred', 'is_active', 'supplier']
    search_fields = ['product__name', 'product__sku', 'supplier__name', 'supplier_sku']
    autocomplete_fields = ['product', 'supplier']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Relationship', {
            'fields': ('product', 'supplier', 'is_preferred', 'is_active')
        }),
        ('Supplier Details', {
            'fields': ('supplier_sku', 'supplier_cost', 'minimum_order_quantity', 'lead_time_days')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'manager', 'product_count', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'address']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['manager']
    
    fieldsets = (
        ('Warehouse Information', {
            'fields': ('name', 'code', 'address', 'manager')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def product_count(self, obj):
        return obj.stock_levels.count()
    product_count.short_description = 'Products'


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'movement_type', 'quantity_change', 'unit_cost', 'total_cost', 'movement_date', 'created_by']
    list_filter = ['movement_type', 'warehouse', 'movement_date', 'created_by']
    search_fields = ['product__name', 'product__sku', 'reference_number', 'notes']
    readonly_fields = ['total_cost', 'created_at']
    autocomplete_fields = ['product', 'warehouse']
    date_hierarchy = 'movement_date'
    
    fieldsets = (
        ('Movement Information', {
            'fields': ('product', 'warehouse', 'movement_type', 'movement_date')
        }),
        ('Quantity & Cost', {
            'fields': ('quantity_change', 'unit_cost', 'total_cost')
        }),
        ('Reference', {
            'fields': ('reference_number', 'notes')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'quantity_on_hand', 'quantity_reserved', 'quantity_available', 'stock_value', 'last_movement_date']
    list_filter = ['warehouse', 'last_movement_date', 'updated_at']
    search_fields = ['product__name', 'product__sku', 'warehouse__name']
    readonly_fields = ['quantity_available', 'updated_at', 'stock_value']
    autocomplete_fields = ['product', 'warehouse']
    
    fieldsets = (
        ('Stock Information', {
            'fields': ('product', 'warehouse')
        }),
        ('Quantities', {
            'fields': ('quantity_on_hand', 'quantity_reserved', 'quantity_available')
        }),
        ('Value & Dates', {
            'fields': ('stock_value', 'last_movement_date', 'updated_at')
        }),
    )
    
    def stock_value(self, obj):
        return f"${obj.quantity_on_hand * obj.product.cost_price:,.2f}"
    stock_value.short_description = 'Stock Value'


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    autocomplete_fields = ['product']
    readonly_fields = ['total_cost', 'quantity_pending', 'is_fully_received']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'supplier', 'warehouse', 'order_date', 'status', 'total_amount', 'total_items']
    list_filter = ['status', 'order_date', 'supplier', 'warehouse']
    search_fields = ['po_number', 'supplier__name', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'total_items']
    autocomplete_fields = ['supplier', 'warehouse']
    date_hierarchy = 'order_date'
    inlines = [PurchaseOrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('po_number', 'supplier', 'warehouse', 'order_date', 'expected_delivery_date')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Financial', {
            'fields': ('subtotal', 'tax_amount', 'shipping_cost', 'total_amount')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_sent', 'mark_as_confirmed']
    
    def mark_as_sent(self, request, queryset):
        queryset.update(status='sent')
        self.message_user(request, f"{queryset.count()} purchase orders marked as sent.")
    mark_as_sent.short_description = "Mark selected orders as sent"
    
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, f"{queryset.count()} purchase orders confirmed.")
    mark_as_confirmed.short_description = "Confirm selected orders"


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ['purchase_order', 'product', 'quantity_ordered', 'quantity_received', 'quantity_pending', 'unit_cost', 'total_cost']
    list_filter = ['purchase_order__status', 'purchase_order__order_date']
    search_fields = ['purchase_order__po_number', 'product__name', 'product__sku']
    readonly_fields = ['total_cost', 'quantity_pending', 'is_fully_received', 'created_at']
    autocomplete_fields = ['purchase_order', 'product']
    
    fieldsets = (
        ('Order Item Information', {
            'fields': ('purchase_order', 'product')
        }),
        ('Quantities', {
            'fields': ('quantity_ordered', 'quantity_received', 'quantity_pending', 'is_fully_received')
        }),
        ('Pricing', {
            'fields': ('unit_cost', 'total_cost')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


class InventoryCountItemInline(admin.TabularInline):
    model = InventoryCountItem
    extra = 0
    autocomplete_fields = ['product']
    readonly_fields = ['variance', 'variance_value']


@admin.register(InventoryCount)
class InventoryCountAdmin(admin.ModelAdmin):
    list_display = ['count_number', 'warehouse', 'count_date', 'count_type', 'status', 'counted_by', 'item_count']
    list_filter = ['status', 'count_type', 'count_date', 'warehouse']
    search_fields = ['count_number', 'warehouse__name', 'notes']
    readonly_fields = ['created_at', 'completed_at', 'item_count']
    autocomplete_fields = ['warehouse']
    date_hierarchy = 'count_date'
    inlines = [InventoryCountItemInline]
    
    fieldsets = (
        ('Count Information', {
            'fields': ('count_number', 'warehouse', 'count_date', 'count_type')
        }),
        ('Status & Personnel', {
            'fields': ('status', 'counted_by')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def item_count(self, obj):
        return obj.count_items.count()
    item_count.short_description = 'Items'
    
    actions = ['mark_in_progress', 'mark_completed']
    
    def mark_in_progress(self, request, queryset):
        queryset.update(status='in_progress')
        self.message_user(request, f"{queryset.count()} counts marked as in progress.")
    mark_in_progress.short_description = "Mark selected counts as in progress"
    
    def mark_completed(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} counts marked as completed.")
    mark_completed.short_description = "Mark selected counts as completed"


@admin.register(InventoryCountItem)
class InventoryCountItemAdmin(admin.ModelAdmin):
    list_display = ['inventory_count', 'product', 'expected_quantity', 'counted_quantity', 'variance', 'variance_value', 'counted_by']
    list_filter = ['inventory_count__status', 'inventory_count__count_date', 'counted_by']
    search_fields = ['inventory_count__count_number', 'product__name', 'product__sku']
    readonly_fields = ['variance', 'variance_value', 'counted_at']
    autocomplete_fields = ['inventory_count', 'product']
    
    fieldsets = (
        ('Count Item Information', {
            'fields': ('inventory_count', 'product')
        }),
        ('Quantities', {
            'fields': ('expected_quantity', 'counted_quantity', 'variance', 'variance_value')
        }),
        ('Count Details', {
            'fields': ('counted_by', 'counted_at', 'notes')
        }),
    )
