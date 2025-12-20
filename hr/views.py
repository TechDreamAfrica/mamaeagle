from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q
from accounts.mixins import CompanyAccessMixin
from .models import Employee
from .forms import EmployeeForm
from common.bulk_operations import bulk_delete_view, bulk_export_view

@login_required
def hr_dashboard(request):
    return render(request, 'hr/hr_dashboard.html')


class EmployeeListView(LoginRequiredMixin, CompanyAccessMixin, ListView):
    """List all employees with filtering and search"""
    model = Employee
    template_name = 'hr/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('user', 'manager__user')
        
        # Search
        search = self.request.GET.get('q', '')
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(job_title__icontains=search) |
                Q(department__icontains=search)
            )
        
        # Filters
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        department = self.request.GET.get('department', '')
        if department:
            queryset = queryset.filter(department=department)
        
        employment_type = self.request.GET.get('employment_type', '')
        if employment_type:
            queryset = queryset.filter(employment_type=employment_type)
        
        return queryset.order_by('user__last_name', 'user__first_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_employees'] = Employee.objects.count()
        context['active_employees'] = Employee.objects.filter(status='active').count()
        context['departments'] = Employee.objects.values_list('department', flat=True).distinct()
        context['status_choices'] = Employee.STATUS_CHOICES
        context['employment_types'] = Employee.EMPLOYMENT_TYPES
        return context


class EmployeeDetailView(LoginRequiredMixin, CompanyAccessMixin, DetailView):
    """Detailed view of an employee"""
    model = Employee
    template_name = 'hr/employee_detail.html'
    context_object_name = 'employee'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.object
        
        # Get related data
        context['time_entries'] = employee.timeentry_set.order_by('-date')[:10]
        context['leave_requests'] = employee.leaverequest_set.order_by('-start_date')[:10] 
        context['performance_reviews'] = employee.performancereview_set.order_by('-review_period_start')[:5]
        context['subordinates'] = Employee.objects.filter(manager=employee)
        context['recent_payrolls'] = employee.payroll_set.order_by('-payroll_period__start_date')[:5]
        
        # Calculate time statistics
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Sum
        
        now = timezone.now()
        week_start = now - timedelta(days=now.weekday())
        month_start = now.replace(day=1)
        
        # Time stats
        this_week_hours = employee.timeentry_set.filter(
            date__gte=week_start.date(),
            is_approved=True
        ).aggregate(total=Sum('total_hours'))['total'] or 0
        
        this_month_hours = employee.timeentry_set.filter(
            date__gte=month_start.date(),
            is_approved=True
        ).aggregate(total=Sum('total_hours'))['total'] or 0
        
        # PTO remaining (assuming 20 days per year)
        used_vacation_days = employee.leaverequest_set.filter(
            leave_type='vacation',
            status='approved',
            start_date__year=now.year
        ).aggregate(total=Sum('total_days'))['total'] or 0
        
        context['time_stats'] = {
            'hours_this_week': float(this_week_hours),
            'hours_this_month': float(this_month_hours), 
            'pto_remaining': float(20 - used_vacation_days)
        }
        
        return context


class EmployeeCreateView(LoginRequiredMixin, CompanyAccessMixin, CreateView):
    """Create a new employee"""
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    success_url = reverse_lazy('hr:employee_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Exclude termination_date from create form
        if 'termination_date' in form.fields:
            form.fields.pop('termination_date')
        return form

    def form_valid(self, form):
        # Ensure company is set
        if not hasattr(self.request, 'company') or not self.request.company:
            messages.error(self.request, 'No company associated with your account. Please contact administrator.')
            return self.form_invalid(form)

        form.instance.company = self.request.company
        messages.success(self.request, 'Employee created successfully!')
        return super().form_valid(form)


class EmployeeUpdateView(LoginRequiredMixin, CompanyAccessMixin, UpdateView):
    """Update an existing employee"""
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    success_url = reverse_lazy('hr:employee_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Employee updated successfully!')
        return super().form_valid(form)


class EmployeeDeleteView(LoginRequiredMixin, CompanyAccessMixin, DeleteView):
    """Delete an employee"""
    model = Employee
    template_name = 'hr/employee_confirm_delete.html'
    success_url = reverse_lazy('hr:employee_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Employee deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
def payroll_list(request):
    return render(request, 'hr/payroll_list.html')

@login_required
def time_tracking(request):
    return render(request, 'hr/time_tracking.html')


# Bulk Operations
@login_required
def bulk_delete_employees(request):
    """Bulk delete employees"""
    return bulk_delete_view(
        request=request,
        model=Employee,
        filter_kwargs={},
        success_message="employees deleted successfully"
    )


@login_required  
def bulk_export_employees(request):
    """Bulk export employees to CSV"""
    return bulk_export_view(
        request=request,
        model=Employee,
        filter_kwargs={},
        filename="employees_export"
    )
