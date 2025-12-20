from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import SalesTerritory, SalesRep, Lead, Opportunity, SalesActivity, Commission


@admin.register(SalesTerritory)
class SalesTerritoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'region', 'country', 'monthly_target', 'is_active', 'created_at']
    list_filter = ['region', 'country', 'is_active', 'created_at']
    search_fields = ['name', 'region', 'country', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'region', 'country', 'is_active')
        }),
        ('Performance Targets', {
            'fields': ('monthly_target', 'quarterly_target', 'annual_target')
        }),
        ('Territory Data', {
            'fields': ('boundaries',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SalesRep)
class SalesRepAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'employee_id', 'territory', 'commission_type', 'monthly_quota', 'is_active']
    list_filter = ['commission_type', 'territory', 'is_active', 'hire_date']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'employee_id']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['user', 'territory', 'manager']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'employee_id', 'territory', 'manager', 'hire_date', 'is_active')
        }),
        ('Commission Structure', {
            'fields': ('commission_type', 'commission_rate', 'commission_tiers')
        }),
        ('Performance Targets', {
            'fields': ('monthly_quota', 'quarterly_quota', 'annual_quota')
        }),
        ('Contact Information', {
            'fields': ('phone', 'mobile'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Full Name'


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'company', 'email', 'status', 'priority', 'assigned_to', 'estimated_value', 'lead_score']
    list_filter = ['status', 'priority', 'source', 'assigned_to', 'territory', 'created_at']
    search_fields = ['first_name', 'last_name', 'company', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at', 'conversion_probability']
    autocomplete_fields = ['assigned_to', 'territory']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('first_name', 'last_name', 'company', 'title', 'email', 'phone', 'website')
        }),
        ('Address', {
            'fields': ('address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country'),
            'classes': ('collapse',)
        }),
        ('Lead Management', {
            'fields': ('source', 'status', 'priority', 'assigned_to', 'territory')
        }),
        ('Opportunity Details', {
            'fields': ('estimated_value', 'probability', 'expected_close_date')
        }),
        ('Scoring & AI', {
            'fields': ('lead_score', 'scoring_factors', 'conversion_probability', 'ai_recommendations'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('description', 'notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_qualified', 'mark_as_contacted']
    
    def mark_as_qualified(self, request, queryset):
        queryset.update(status='qualified')
        self.message_user(request, f"{queryset.count()} leads marked as qualified.")
    mark_as_qualified.short_description = "Mark selected leads as qualified"
    
    def mark_as_contacted(self, request, queryset):
        queryset.update(status='contacted')
        self.message_user(request, f"{queryset.count()} leads marked as contacted.")
    mark_as_contacted.short_description = "Mark selected leads as contacted"


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ['name', 'customer_display', 'stage', 'amount', 'weighted_amount_display', 'probability', 'sales_rep', 'expected_close_date']
    list_filter = ['stage', 'sales_rep', 'territory', 'expected_close_date', 'created_at']
    search_fields = ['name', 'customer_name', 'customer_company', 'lead__first_name', 'lead__last_name']
    readonly_fields = ['created_at', 'updated_at', 'weighted_amount']
    autocomplete_fields = ['lead', 'sales_rep', 'territory']
    date_hierarchy = 'expected_close_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'lead')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email', 'customer_phone', 'customer_company'),
            'description': 'Fill this section if the opportunity is not linked to a lead'
        }),
        ('Opportunity Details', {
            'fields': ('stage', 'amount', 'probability', 'expected_close_date', 'actual_close_date')
        }),
        ('Assignment', {
            'fields': ('sales_rep', 'territory')
        }),
        ('Strategic Information', {
            'fields': ('competitors', 'decision_factors', 'decision_makers'),
            'classes': ('collapse',)
        }),
        ('Financial Details', {
            'fields': ('cost_of_sale', 'margin'),
            'classes': ('collapse',)
        }),
        ('Next Steps', {
            'fields': ('next_step', 'next_step_date')
        }),
        ('AI Insights', {
            'fields': ('ai_forecast', 'churn_risk'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['move_to_proposal', 'move_to_negotiation']
    
    def customer_display(self, obj):
        if obj.lead:
            return f"{obj.lead.full_name} ({obj.lead.company})"
        return f"{obj.customer_name} ({obj.customer_company})"
    customer_display.short_description = 'Customer'
    
    def weighted_amount_display(self, obj):
        return f"${obj.weighted_amount:,.2f}"
    weighted_amount_display.short_description = 'Weighted Amount'
    
    def move_to_proposal(self, request, queryset):
        queryset.update(stage='proposal')
        self.message_user(request, f"{queryset.count()} opportunities moved to proposal stage.")
    move_to_proposal.short_description = "Move selected opportunities to proposal stage"
    
    def move_to_negotiation(self, request, queryset):
        queryset.update(stage='negotiation')
        self.message_user(request, f"{queryset.count()} opportunities moved to negotiation stage.")
    move_to_negotiation.short_description = "Move selected opportunities to negotiation stage"


@admin.register(SalesActivity)
class SalesActivityAdmin(admin.ModelAdmin):
    list_display = ['subject', 'activity_type', 'sales_rep', 'related_object', 'activity_date', 'requires_follow_up']
    list_filter = ['activity_type', 'sales_rep', 'requires_follow_up', 'follow_up_completed', 'activity_date']
    search_fields = ['subject', 'description', 'outcome']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['lead', 'opportunity', 'sales_rep']
    date_hierarchy = 'activity_date'
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('activity_type', 'subject', 'description', 'activity_date', 'duration')
        }),
        ('Related Objects', {
            'fields': ('lead', 'opportunity', 'sales_rep')
        }),
        ('Outcome', {
            'fields': ('outcome',)
        }),
        ('Follow-up', {
            'fields': ('requires_follow_up', 'follow_up_date', 'follow_up_completed')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def related_object(self, obj):
        if obj.lead:
            return format_html('<a href="{}">{}</a>', 
                             reverse('admin:sales_lead_change', args=[obj.lead.pk]), 
                             str(obj.lead))
        elif obj.opportunity:
            return format_html('<a href="{}">{}</a>', 
                             reverse('admin:sales_opportunity_change', args=[obj.opportunity.pk]), 
                             str(obj.opportunity))
        return '-'
    related_object.short_description = 'Related To'


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ['sales_rep', 'commission_amount', 'commission_rate', 'opportunity', 'earned_date', 'is_paid']
    list_filter = ['is_paid', 'sales_rep', 'earned_date', 'payment_date']
    search_fields = ['sales_rep__user__first_name', 'sales_rep__user__last_name', 'payment_reference']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['sales_rep', 'opportunity']
    date_hierarchy = 'earned_date'
    
    fieldsets = (
        ('Commission Details', {
            'fields': ('sales_rep', 'opportunity', 'commission_amount', 'commission_rate', 'base_amount')
        }),
        ('Timing', {
            'fields': ('earned_date', 'payment_date')
        }),
        ('Payment Status', {
            'fields': ('is_paid', 'payment_reference')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_paid']
    
    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_paid=True, payment_date=timezone.now().date())
        self.message_user(request, f"{queryset.count()} commissions marked as paid.")
    mark_as_paid.short_description = "Mark selected commissions as paid"


# Customize admin site header and title
admin.site.site_header = "AccuFlow Sales Administration"
admin.site.site_title = "AccuFlow Sales Admin"
admin.site.index_title = "Sales Management"
