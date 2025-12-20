from django.contrib import admin
from django.utils.html import format_html
from .models import BankAccount, BankStatement, BankTransaction, ReconciliationRule, ReconciliationSession, ReconciliationAdjustment


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'bank_name', 'masked_account_number', 'account_type', 'current_balance', 'is_active']
    list_filter = ['account_type', 'bank_name', 'is_active', 'created_at']
    search_fields = ['name', 'bank_name', 'account_number']
    readonly_fields = ['created_at', 'masked_account_number']
    
    fieldsets = (
        ('Account Information', {
            'fields': ('name', 'bank_name', 'account_number', 'account_type', 'routing_number')
        }),
        ('Balance Information', {
            'fields': ('opening_balance', 'current_balance', 'last_reconciled_balance', 'last_reconciled_date')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('System Information', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def masked_account_number(self, obj):
        return obj.masked_account_number
    masked_account_number.short_description = 'Account Number'


@admin.register(BankStatement)
class BankStatementAdmin(admin.ModelAdmin):
    list_display = ['bank_account', 'statement_date', 'beginning_balance', 'ending_balance', 'status']
    list_filter = ['status', 'statement_date', 'bank_account']
    search_fields = ['bank_account__name', 'bank_account__bank_name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'statement_date'
    
    fieldsets = (
        ('Statement Information', {
            'fields': ('bank_account', 'statement_date', 'statement_period_start', 'statement_period_end')
        }),
        ('Balance Information', {
            'fields': ('beginning_balance', 'ending_balance', 'total_deposits', 'total_withdrawals', 'total_fees')
        }),
        ('Status', {
            'fields': ('status', 'reconciliation_date', 'reconciled_by', 'notes')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_date', 'description', 'amount', 'transaction_type', 'bank_statement', 'reconciliation_status']
    list_filter = ['transaction_type', 'reconciliation_status', 'transaction_date', 'bank_statement__bank_account']
    search_fields = ['description', 'reference_number', 'bank_statement__bank_account__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'transaction_date'
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('bank_statement', 'transaction_date', 'description', 'amount', 'transaction_type')
        }),
        ('Reference', {
            'fields': ('reference_number', 'check_number', 'running_balance')
        }),
        ('Reconciliation', {
            'fields': ('reconciliation_status', 'reconciled_date', 'reconciled_by', 'notes')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_matched', 'mark_as_cleared']
    
    def mark_as_matched(self, request, queryset):
        queryset.update(reconciliation_status='matched')
        self.message_user(request, f"{queryset.count()} transactions marked as matched.")
    mark_as_matched.short_description = "Mark selected transactions as matched"
    
    def mark_as_cleared(self, request, queryset):
        queryset.update(reconciliation_status='cleared')
        self.message_user(request, f"{queryset.count()} transactions marked as cleared.")
    mark_as_cleared.short_description = "Mark selected transactions as cleared"


@admin.register(ReconciliationRule)
class ReconciliationRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'is_active', 'auto_match', 'confidence_threshold']
    list_filter = ['rule_type', 'is_active', 'auto_match', 'created_at']
    search_fields = ['name', 'description_pattern']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Rule Information', {
            'fields': ('name', 'rule_type', 'is_active', 'auto_match', 'confidence_threshold')
        }),
        ('Matching Criteria', {
            'fields': ('description_pattern', 'amount_min', 'amount_max', 'check_number_pattern', 'reference_pattern')
        }),
        ('System Information', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ReconciliationSession)
class ReconciliationSessionAdmin(admin.ModelAdmin):
    list_display = ['session_name', 'bank_account', 'start_date', 'status', 'difference', 'is_balanced']
    list_filter = ['status', 'start_date', 'bank_account']
    search_fields = ['session_name', 'bank_account__name']
    readonly_fields = ['created_at', 'updated_at', 'is_balanced']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session_name', 'bank_account', 'bank_statement', 'status')
        }),
        ('Balance Information', {
            'fields': ('starting_book_balance', 'ending_book_balance', 'statement_balance', 'difference')
        }),
        ('Progress', {
            'fields': ('transactions_matched', 'transactions_unmatched', 'adjustments_made')
        }),
        ('Session Details', {
            'fields': ('start_date', 'end_date', 'reconciled_by', 'notes')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at', 'is_balanced'),
            'classes': ('collapse',)
        }),
    )
    
    def is_balanced(self, obj):
        return obj.is_balanced
    is_balanced.boolean = True
    is_balanced.short_description = 'Balanced'


@admin.register(ReconciliationAdjustment)
class ReconciliationAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['reconciliation_session', 'adjustment_type', 'description', 'amount', 'affects_book_balance', 'affects_bank_balance']
    list_filter = ['adjustment_type', 'affects_book_balance', 'affects_bank_balance', 'created_at']
    search_fields = ['description', 'reconciliation_session__session_name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Adjustment Information', {
            'fields': ('reconciliation_session', 'adjustment_type', 'description', 'amount')
        }),
        ('Effects', {
            'fields': ('affects_book_balance', 'affects_bank_balance', 'reference_transaction')
        }),
        ('System Information', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
