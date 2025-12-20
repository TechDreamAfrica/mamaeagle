from django.contrib import admin
from django.utils.html import format_html
from .models import ExpenseCategory, Vendor, Expense, ExpenseReport, ExpenseReportItem, MileageLog


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'color_display', 'is_tax_deductible', 'budget_limit', 'is_active']
    list_filter = ['is_tax_deductible', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'tax_category']
    readonly_fields = ['created_at']
    autocomplete_fields = ['user']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'description', 'color')
        }),
        ('Tax Settings', {
            'fields': ('is_tax_deductible', 'tax_category')
        }),
        ('Budget', {
            'fields': ('budget_limit',)
        }),
        ('AI Insights', {
            'fields': ('ai_spending_pattern',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 3px;"></div>',
            obj.color
        )
    color_display.short_description = 'Color'


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'country', 'reliability_score', 'is_active']
    list_filter = ['country', 'is_active', 'created_at']
    search_fields = ['name', 'email', 'tax_id']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['user']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'email', 'phone', 'website')
        }),
        ('Address', {
            'fields': ('address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Financial Information', {
            'fields': ('tax_id', 'payment_terms')
        }),
        ('AI Insights', {
            'fields': ('reliability_score', 'payment_history'),
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


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['description', 'amount', 'user', 'category', 'vendor', 'date', 'status', 'payment_method']
    list_filter = ['status', 'payment_method', 'category', 'is_billable', 'date', 'created_at']
    search_fields = ['description', 'reference_number', 'location']
    readonly_fields = ['created_at', 'updated_at', 'total_amount', 'receipt_processed', 'ai_confidence_score']
    autocomplete_fields = ['user', 'category', 'vendor', 'approved_by']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'description', 'amount', 'date', 'category', 'vendor')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'reference_number')
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_by', 'approved_at')
        }),
        ('Tax Information', {
            'fields': ('is_billable', 'tax_amount', 'total_amount')
        }),
        ('Receipt Management', {
            'fields': ('receipt', 'receipt_processed'),
            'classes': ('collapse',)
        }),
        ('AI Features', {
            'fields': ('ai_extracted_data', 'ai_confidence_score'),
            'classes': ('collapse',)
        }),
        ('Additional Details', {
            'fields': ('notes', 'location'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_expenses', 'reject_expenses']
    
    def approve_expenses(self, request, queryset):
        queryset.update(status='approved', approved_by=request.user)
        self.message_user(request, f"{queryset.count()} expenses approved.")
    approve_expenses.short_description = "Approve selected expenses"
    
    def reject_expenses(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f"{queryset.count()} expenses rejected.")
    reject_expenses.short_description = "Reject selected expenses"


class ExpenseReportItemInline(admin.TabularInline):
    model = ExpenseReportItem
    extra = 0
    autocomplete_fields = ['expense']


@admin.register(ExpenseReport)
class ExpenseReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'start_date', 'end_date', 'status', 'total_amount', 'submitted_at']
    list_filter = ['status', 'start_date', 'end_date', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at', 'total_amount', 'total_tax']
    autocomplete_fields = ['user', 'approved_by']
    date_hierarchy = 'start_date'
    inlines = [ExpenseReportItemInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'description')
        }),
        ('Date Range', {
            'fields': ('start_date', 'end_date')
        }),
        ('Status', {
            'fields': ('status', 'submitted_at', 'approved_by', 'approved_at')
        }),
        ('Totals', {
            'fields': ('total_amount', 'total_tax')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['submit_reports', 'approve_reports']
    
    def submit_reports(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='submitted', submitted_at=timezone.now())
        self.message_user(request, f"{queryset.count()} reports submitted.")
    submit_reports.short_description = "Submit selected reports"
    
    def approve_reports(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='approved', approved_by=request.user, approved_at=timezone.now())
        self.message_user(request, f"{queryset.count()} reports approved.")
    approve_reports.short_description = "Approve selected reports"


@admin.register(MileageLog)
class MileageLogAdmin(admin.ModelAdmin):
    list_display = ['date', 'user', 'start_location', 'end_location', 'miles', 'purpose', 'total_amount']
    list_filter = ['purpose', 'date', 'gps_verified']
    search_fields = ['start_location', 'end_location', 'description', 'vehicle']
    readonly_fields = ['created_at', 'updated_at', 'total_amount']
    autocomplete_fields = ['user']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Trip Information', {
            'fields': ('user', 'date', 'start_location', 'end_location', 'purpose', 'description')
        }),
        ('Mileage Details', {
            'fields': ('miles', 'rate_per_mile', 'total_amount')
        }),
        ('Vehicle Information', {
            'fields': ('vehicle',)
        }),
        ('GPS Verification', {
            'fields': ('gps_verified', 'route_data'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
