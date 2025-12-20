from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Customer, Product, Invoice, InvoiceItem, Payment


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'company', 'payment_terms', 'credit_limit', 'risk_score', 'is_active']
    list_filter = ['payment_terms', 'currency', 'is_active', 'created_at']
    search_fields = ['name', 'email', 'company', 'tax_id']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['user']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'email', 'phone', 'company')
        }),
        ('Billing Address', {
            'fields': ('billing_address_line_1', 'billing_address_line_2', 'billing_city', 
                      'billing_state', 'billing_postal_code', 'billing_country')
        }),
        ('Financial Information', {
            'fields': ('credit_limit', 'payment_terms', 'tax_id', 'preferred_payment_method', 'currency')
        }),
        ('Preferences', {
            'fields': ('language',),
            'classes': ('collapse',)
        }),
        ('AI Insights', {
            'fields': ('ai_insights', 'risk_score'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'product_type', 'unit_price', 'cost_price', 'track_inventory', 'is_active']
    list_filter = ['product_type', 'track_inventory', 'is_active', 'created_at']
    search_fields = ['name', 'sku', 'description']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['user']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'description', 'sku', 'product_type')
        }),
        ('Pricing', {
            'fields': ('unit_price', 'cost_price')
        }),
        ('Inventory', {
            'fields': ('track_inventory',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ['product', 'description', 'quantity', 'unit_price', 'tax_rate', 'get_total']
    readonly_fields = ['get_total']
    
    def get_total(self, obj):
        if obj.pk:  # Only calculate for saved objects
            return f"${obj.total:.2f}"
        return "-"
    get_total.short_description = "Total"


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'date_created', 'date_due', 'status', 'total_amount', 'balance_due', 'is_overdue']
    list_filter = ['status', 'date_created', 'date_due']
    search_fields = ['invoice_number', 'customer__name', 'customer__company']
    readonly_fields = ['date_created', 'created_at', 'updated_at', 'balance_due', 'is_overdue', 'days_overdue']
    autocomplete_fields = ['customer', 'user']
    date_hierarchy = 'date_created'
    inlines = [InvoiceItemInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'customer', 'invoice_number', 'status')
        }),
        ('Dates', {
            'fields': ('date_created', 'date_due', 'terms')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'amount_paid', 'balance_due')
        }),
        ('Additional Information', {
            'fields': ('notes', 'payment_instructions'),
            'classes': ('collapse',)
        }),
        ('AI Features', {
            'fields': ('ai_payment_prediction', 'risk_assessment'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('view_count', 'last_viewed'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_sent', 'mark_as_paid']
    
    def mark_as_sent(self, request, queryset):
        queryset.update(status='sent')
        self.message_user(request, f"{queryset.count()} invoices marked as sent.")
    mark_as_sent.short_description = "Mark selected invoices as sent"
    
    def mark_as_paid(self, request, queryset):
        queryset.update(status='paid')
        self.message_user(request, f"{queryset.count()} invoices marked as paid.")
    mark_as_paid.short_description = "Mark selected invoices as paid"


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'product', 'description', 'quantity', 'unit_price', 'total']
    list_filter = ['invoice__status', 'product__product_type']
    search_fields = ['invoice__invoice_number', 'product__name', 'description']
    autocomplete_fields = ['invoice', 'product']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'amount', 'payment_method', 'payment_date', 'reference_number']
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['invoice__invoice_number', 'reference_number']
    autocomplete_fields = ['invoice']
    date_hierarchy = 'payment_date'
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('invoice', 'amount', 'payment_method', 'payment_date')
        }),
        ('Reference', {
            'fields': ('reference_number', 'bank_account')
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
