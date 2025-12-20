from django.contrib import admin
from django.utils.html import format_html
from .models import AIInsight, AIModel, AutomatedTask, PredictiveAnalytics, AITrainingData


@admin.register(AIInsight)
class AIInsightAdmin(admin.ModelAdmin):
    list_display = ['title', 'insight_type', 'user', 'priority', 'confidence_score', 'is_viewed', 'is_active']
    list_filter = ['insight_type', 'priority', 'is_viewed', 'is_acknowledged', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'valid_from']
    autocomplete_fields = ['user']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'insight_type', 'title', 'description', 'priority')
        }),
        ('AI Analysis', {
            'fields': ('data_points', 'confidence_score')
        }),
        ('Recommendations', {
            'fields': ('recommendations', 'potential_impact')
        }),
        ('User Interaction', {
            'fields': ('is_viewed', 'is_acknowledged', 'user_feedback')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_until', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_viewed', 'deactivate_insights']
    
    def mark_as_viewed(self, request, queryset):
        queryset.update(is_viewed=True)
        self.message_user(request, f"{queryset.count()} insights marked as viewed.")
    mark_as_viewed.short_description = "Mark selected insights as viewed"
    
    def deactivate_insights(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} insights deactivated.")
    deactivate_insights.short_description = "Deactivate selected insights"


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'model_type', 'version', 'accuracy', 'is_active', 'success_rate']
    list_filter = ['model_type', 'is_active', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at', 'accuracy', 'precision', 'recall', 'f1_score', 'success_rate']
    
    fieldsets = (
        ('Model Information', {
            'fields': ('name', 'model_type', 'version')
        }),
        ('Configuration', {
            'fields': ('config', 'is_active')
        }),
        ('Performance Metrics', {
            'fields': ('accuracy', 'precision', 'recall', 'f1_score', 'prediction_count', 'success_count', 'success_rate')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def success_rate(self, obj):
        return f"{obj.success_rate:.2f}%"
    success_rate.short_description = 'Success Rate'


@admin.register(AutomatedTask)
class AutomatedTaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'task_type', 'user', 'status', 'last_run', 'next_run', 'success_count', 'is_active']
    list_filter = ['task_type', 'status', 'is_active', 'last_run']
    search_fields = ['name', 'description', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'success_count', 'failure_count']
    autocomplete_fields = ['user']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'task_type', 'name', 'description')
        }),
        ('Configuration', {
            'fields': ('config', 'schedule', 'is_active')
        }),
        ('Status & Execution', {
            'fields': ('status', 'last_run', 'next_run')
        }),
        ('Performance', {
            'fields': ('success_count', 'failure_count', 'last_result')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_tasks', 'deactivate_tasks']
    
    def activate_tasks(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} tasks activated.")
    activate_tasks.short_description = "Activate selected tasks"
    
    def deactivate_tasks(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} tasks deactivated.")
    deactivate_tasks.short_description = "Deactivate selected tasks"


@admin.register(PredictiveAnalytics)
class PredictiveAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['prediction_type', 'user', 'prediction_date', 'accuracy_score', 'created_at']
    list_filter = ['prediction_type', 'created_at', 'prediction_date']
    search_fields = ['prediction_type', 'user__username']
    readonly_fields = ['created_at']
    autocomplete_fields = ['user']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Prediction Information', {
            'fields': ('user', 'prediction_type', 'prediction_date', 'valid_until')
        }),
        ('Prediction Data', {
            'fields': ('predicted_values', 'confidence_intervals', 'model_used', 'accuracy_score')
        }),
        ('Actual Results', {
            'fields': ('actual_values', 'variance'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(AITrainingData)
class AITrainingDataAdmin(admin.ModelAdmin):
    list_display = ['data_type', 'user', 'confidence_score', 'is_correct', 'created_at']
    list_filter = ['data_type', 'is_correct', 'created_at']
    search_fields = ['data_type', 'user__username']
    readonly_fields = ['created_at']
    autocomplete_fields = ['user']
    
    fieldsets = (
        ('Data Information', {
            'fields': ('user', 'data_type', 'model_version')
        }),
        ('Training Data', {
            'fields': ('input_data', 'expected_output', 'actual_output', 'confidence_score')
        }),
        ('Feedback', {
            'fields': ('is_correct', 'user_correction')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
