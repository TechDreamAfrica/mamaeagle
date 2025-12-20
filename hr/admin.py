from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, PayrollPeriod, Payroll, TimeEntry, LeaveRequest, PerformanceReview


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['user', 'employee_id', 'department', 'job_title', 'base_salary', 'hire_date', 'status']
    list_filter = ['department', 'job_title', 'employment_type', 'status', 'hire_date']
    search_fields = ['user__first_name', 'user__last_name', 'employee_id', 'tax_id']
    readonly_fields = ['created_at', 'updated_at', 'performance_score']
    autocomplete_fields = ['user', 'manager']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'employee_id', 'department', 'job_title', 'manager')
        }),
        ('Employment Details', {
            'fields': ('employment_type', 'hire_date', 'termination_date', 'status')
        }),
        ('Compensation', {
            'fields': ('base_salary', 'hourly_rate')
        }),
        ('Tax Information', {
            'fields': ('tax_id', 'tax_exemptions')
        }),
        ('Benefits', {
            'fields': ('health_insurance', 'dental_insurance', 'vision_insurance', 'retirement_plan')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship'),
            'classes': ('collapse',)
        }),
        ('Performance', {
            'fields': ('performance_score',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ['frequency', 'start_date', 'end_date', 'pay_date', 'is_processed']
    list_filter = ['is_processed', 'start_date', 'end_date']
    search_fields = ['frequency']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Period Information', {
            'fields': ('name', 'start_date', 'end_date', 'pay_date')
        }),
        ('Status', {
            'fields': ('is_processed',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['employee', 'payroll_period', 'gross_pay', 'net_pay', 'is_processed', 'is_paid']
    list_filter = ['payroll_period', 'is_processed', 'is_paid', 'paid_date']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_id']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['employee', 'payroll_period']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('employee', 'payroll_period')
        }),
        ('Hours & Pay', {
            'fields': ('regular_hours', 'overtime_hours', 'sick_hours', 
                      'regular_pay', 'overtime_pay', 'bonus', 'commission')
        }),
        ('Pre-tax Deductions', {
            'fields': ('health_insurance_deduction', 'dental_insurance_deduction', 'retirement_contribution')
        }),
        ('Taxes', {
            'fields': ('federal_tax', 'state_tax', 'social_security_tax', 'medicare_tax')
        }),
        ('Post-tax Deductions', {
            'fields': ('garnishments',)
        }),
        ('Totals', {
            'fields': ('gross_pay', 'net_pay')
        }),
        ('Status', {
            'fields': ('is_processed', 'is_paid', 'paid_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['process_payroll', 'mark_as_paid']
    
    def process_payroll(self, request, queryset):
        queryset.update(is_processed=True)
        self.message_user(request, f"{queryset.count()} payroll records processed.")
    process_payroll.short_description = "Process selected payroll records"
    
    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_paid=True, paid_date=timezone.now())
        self.message_user(request, f"{queryset.count()} payroll records marked as paid.")
    mark_as_paid.short_description = "Mark selected payroll as paid"


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'total_hours', 'entry_type', 'project', 'is_approved']
    list_filter = ['is_approved', 'date', 'entry_type']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'project', 'task_description']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['employee', 'approved_by']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('employee', 'date', 'entry_type', 'total_hours')
        }),
        ('Time Details', {
            'fields': ('start_time', 'end_time', 'break_duration')
        }),
        ('Work Details', {
            'fields': ('project', 'task_description')
        }),
        ('GPS Tracking', {
            'fields': ('gps_location', 'is_gps_verified'),
            'classes': ('collapse',)
        }),
        ('Approval', {
            'fields': ('is_approved', 'approved_by', 'approved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'total_days', 'status']
    list_filter = ['leave_type', 'status', 'start_date', 'created_at']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'reason']
    readonly_fields = ['created_at', 'updated_at', 'total_days']
    autocomplete_fields = ['employee', 'approved_by']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Leave Information', {
            'fields': ('employee', 'leave_type', 'start_date', 'end_date', 'days_requested')
        }),
        ('Request Details', {
            'fields': ('reason', 'notes')
        }),
        ('Review', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'review_comments')
        }),
        ('Timestamps', {
            'fields': ('submitted_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='approved', reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} leave requests approved.")
    approve_requests.short_description = "Approve selected leave requests"
    
    def reject_requests(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='rejected', reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} leave requests rejected.")
    reject_requests.short_description = "Reject selected leave requests"


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ['employee', 'review_period_start', 'review_period_end', 'overall_rating', 'reviewer', 'review_type']
    list_filter = ['overall_rating', 'review_type', 'review_period_start']
    search_fields = ['employee__user__first_name', 'employee__user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['employee', 'reviewer']
    date_hierarchy = 'review_period_end'
    
    fieldsets = (
        ('Review Information', {
            'fields': ('employee', 'reviewer', 'review_type')
        }),
        ('Review Period', {
            'fields': ('review_period_start', 'review_period_end')
        }),
        ('Ratings', {
            'fields': ('overall_rating', 'technical_skills', 'communication', 'teamwork', 'leadership')
        }),
        ('Comments', {
            'fields': ('strengths', 'areas_for_improvement', 'goals')
        }),
        ('Employee Feedback', {
            'fields': ('employee_comments', 'employee_signature_date')
        }),
        ('AI Insights', {
            'fields': ('ai_performance_analysis', 'recommended_training'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
