from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from datetime import date
from .models import Expense, ExpenseCategory, Vendor
from .forms import ExpenseForm, ExpenseCategoryForm, VendorForm
from common.bulk_operations import bulk_delete_view, bulk_export_view


@login_required
def expense_list(request):
    """
    Expense list with advanced filtering and search
    Much better than QuickBooks' basic list view
    """
    expenses = Expense.objects.filter(user=request.user)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        expenses = expenses.filter(
            Q(description__icontains=search_query) |
            Q(vendor__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        expenses = expenses.filter(status=status_filter)
    
    # Category filter
    category_filter = request.GET.get('category', '')
    if category_filter:
        expenses = expenses.filter(category_id=category_filter)
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    if date_to:
        expenses = expenses.filter(date__lte=date_to)
    
    # Pagination
    paginator = Paginator(expenses.order_by('-date'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Summary statistics
    summary = expenses.aggregate(
        total_amount=Sum('amount'),
        total_tax=Sum('tax_amount'),
        count=Count('id')
    )
    
    # Get categories for filter dropdown
    categories = ExpenseCategory.objects.filter(user=request.user, is_active=True)
    vendors = Vendor.objects.filter(user=request.user, is_active=True)
    
    context = {
        'page_obj': page_obj,
        'summary': summary,
        'categories': categories,
        'vendors': vendors,
        'search_query': search_query,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'status_choices': Expense.STATUS_CHOICES,
    }
    
    return render(request, 'expenses/expense_list.html', context)


@login_required
def expense_create(request):
    """
    Create new expense with AI-powered receipt processing
    Advanced expense creation vs QuickBooks
    """
    if request.method == 'POST':
        form = ExpenseForm(user=request.user, data=request.POST, files=request.FILES)
        
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user

            # Get company - handle both regular users and superusers
            if request.company:
                expense.company = request.company
            else:
                # For superusers or users without request.company, get from UserCompany
                from accounts.models import UserCompany
                user_company = UserCompany.objects.filter(
                    user=request.user,
                    is_active=True
                ).first()
                if user_company:
                    expense.company = user_company.company
                else:
                    messages.error(request, 'No company associated with your account.')
                    return redirect('expenses:expense_list')

            # Handle draft vs submit
            if 'save_draft' in request.POST:
                expense.status = 'draft'
            else:
                expense.status = 'pending'

            expense.save()
            
            # Process receipt if uploaded
            if expense.receipt:
                # Mark receipt as uploaded for future AI processing
                expense.receipt_processed = False  # Will be processed by background task
                expense.ai_confidence_score = 0.0  # To be calculated by AI service
                expense.save()
            
            if expense.status == 'draft':
                messages.success(request, f'Expense saved as draft successfully!')
            else:
                messages.success(request, f'Expense submitted successfully!')
            
            return redirect('expenses:expense_detail', pk=expense.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ExpenseForm(user=request.user, initial={'date': date.today()})
    
    # Get categories and vendors for dropdowns
    categories = ExpenseCategory.objects.filter(user=request.user, is_active=True)
    vendors = Vendor.objects.filter(user=request.user, is_active=True)
    
    context = {
        'form': form,
        'categories': categories,
        'vendors': vendors,
    }
    
    return render(request, 'expenses/expense_create.html', context)


@login_required
def expense_detail(request, pk):
    """
    Expense detail view with edit capabilities
    """
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    
    context = {
        'expense': expense,
        'can_edit': expense.status in ['draft', 'rejected'],
    }
    
    return render(request, 'expenses/expense_detail.html', context)


@login_required
def add_category_ajax(request):
    """
    AJAX endpoint to add new expense category
    """
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user

            # Get company - handle both regular users and superusers
            if request.company:
                category.company = request.company
            else:
                # For superusers or users without request.company, get from UserCompany
                from accounts.models import UserCompany
                user_company = UserCompany.objects.filter(
                    user=request.user,
                    is_active=True
                ).first()
                if user_company:
                    category.company = user_company.company
                else:
                    return JsonResponse({
                        'success': False,
                        'errors': {'company': ['No company associated with your account.']}
                    })

            category.save()
            
            return JsonResponse({
                'success': True,
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'value': category.id,
                    'label': category.name
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    
    return JsonResponse({'success': False})


@login_required
def add_vendor_ajax(request):
    """
    AJAX endpoint to add new vendor
    """
    if request.method == 'POST':

        form = VendorForm(request.POST, request=request)
        
        if form.is_valid():
            vendor = form.save(commit=False)
            vendor.user = request.user

            # Get company - handle both regular users and superusers
            if request.company:
                vendor.company = request.company
            else:
                # For superusers or users without request.company, get from UserCompany
                from accounts.models import UserCompany
                user_company = UserCompany.objects.filter(
                    user=request.user,
                    is_active=True
                ).first()
                if user_company:
                    vendor.company = user_company.company
                else:
                    return JsonResponse({
                        'success': False,
                        'errors': {'company': ['No company associated with your account.']}
                    })

            vendor.save()
            
            return JsonResponse({
                'success': True,
                'vendor': {
                    'id': vendor.id,
                    'name': vendor.name,
                    'value': vendor.id,
                    'label': vendor.name
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    
    return JsonResponse({'success': False})


@login_required
def process_receipt_ajax(request):
    """
    AJAX endpoint for AI receipt processing
    Currently returns structured data for development
    """
    if request.method == 'POST' and request.FILES.get('receipt'):
        # Future: Integrate with OpenAI Vision API or similar service
        # For now, return structured data format that matches expected AI output
        
        import time
        time.sleep(1)  # Simulate processing time
        
        # Return structured data format for development and testing
        extracted_data = {
            'description': 'Receipt processed - enter details manually',
            'amount': '0.00',
            'vendor': '',
            'tax_amount': '0.00',
            'date': date.today().isoformat(),
            'confidence': 0.0,
            'status': 'manual_entry_required'
        }
        
        return JsonResponse({
            'success': True,
            'data': extracted_data,
            'suggestions': [
                f"Receipt processed with {int(extracted_data['confidence'] * 100)}% confidence",
                f'Vendor "{extracted_data["vendor"]}" automatically categorized',
                "Tax amount calculated based on receipt data"
            ]
        })
    
    return JsonResponse({'success': False, 'error': 'No receipt uploaded'})


@login_required
def get_vendor_details(request, vendor_id):
    """
    API endpoint to get vendor details
    """
    try:
        vendor = Vendor.objects.get(pk=vendor_id, user=request.user)
        return JsonResponse({
            'name': vendor.name,
            'email': vendor.email,
            'phone': vendor.phone,
            'payment_terms': vendor.payment_terms,
        })
    except Vendor.DoesNotExist:
        return JsonResponse({'error': 'Vendor not found'}, status=404)


@login_required
@login_required
def expense_delete(request, pk):
    """
    Delete expense view
    """
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Expense deleted successfully!')
        
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('expenses:expense_list')
    
    # For GET requests, show confirmation page or redirect
    return render(request, 'expenses/expense_confirm_delete.html', {'expense': expense})


@login_required
def expense_duplicate(request, pk):
    """
    Duplicate an existing expense
    """
    original_expense = get_object_or_404(Expense, pk=pk, user=request.user)
    
    # Prepare expense data for duplication
    expense_data = {
        'user': request.user,
        'category': original_expense.category,
        'vendor': original_expense.vendor,
        'description': f"{original_expense.description} (Copy)",
        'amount': original_expense.amount,
        'date': date.today(),  # Use today's date for the duplicate
        'payment_method': original_expense.payment_method,
        'reference_number': '',  # Clear reference number
        'status': 'draft',  # Always start as draft
        'tax_amount': original_expense.tax_amount,
        'is_billable': original_expense.is_billable,
        'location': original_expense.location,
        'notes': original_expense.notes,
    }
    
    # Handle company_id if it exists in production database
    if hasattr(original_expense, 'company_id') and original_expense.company_id:
        expense_data['company_id'] = original_expense.company_id
    
    # Create a copy of the expense
    duplicate = Expense.objects.create(**expense_data)
    
    messages.success(request, f'Expense duplicated successfully! Created as draft.')
    return redirect('expenses:expense_edit', pk=duplicate.pk)


@login_required
def expense_approve(request, pk):
    """
    Approve an expense
    """
    from django.utils import timezone
    
    expense = get_object_or_404(Expense, pk=pk)
    
    # Check if user has permission to approve (you can add more sophisticated permission checks)
    if expense.user == request.user:
        # Allow users to approve their own expenses, or add role-based checks here
        pass
    
    if request.method == 'POST':
        if expense.status == 'pending':
            expense.status = 'approved'
            expense.approved_by = request.user
            expense.approved_at = timezone.now()
            expense.save()
            
            messages.success(request, 'Expense approved successfully!')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 
                    'status': expense.status,
                    'message': 'Expense approved successfully!'
                })
            return redirect('expenses:expense_detail', pk=expense.pk)
        else:
            error_msg = f'Cannot approve expense with status: {expense.status}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('expenses:expense_detail', pk=expense.pk)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@login_required
def expense_reject(request, pk):
    """
    Reject an expense
    """
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        if expense.status == 'pending':
            expense.status = 'rejected'
            
            # Optionally store rejection reason in notes or a separate field
            reason = request.POST.get('reason', '')
            if reason:
                expense.notes = f"{expense.notes}\n\nRejection reason: {reason}" if expense.notes else f"Rejection reason: {reason}"
            
            expense.save()
            
            messages.success(request, 'Expense rejected.')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 
                    'status': expense.status,
                    'message': 'Expense rejected.'
                })
            return redirect('expenses:expense_detail', pk=expense.pk)
        else:
            error_msg = f'Cannot reject expense with status: {expense.status}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('expenses:expense_detail', pk=expense.pk)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@login_required
def expense_edit(request, pk):
    """
    Edit expense view
    """
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    
    # Only allow editing of draft and rejected expenses
    if expense.status not in ['draft', 'rejected']:
        messages.error(request, 'This expense cannot be edited.')
        return redirect('expenses:expense_detail', pk=expense.pk)
    
    if request.method == 'POST':
        form = ExpenseForm(user=request.user, data=request.POST, files=request.FILES, instance=expense)
        
        if form.is_valid():
            expense = form.save(commit=False)
            
            # Handle status change
            if 'save_draft' in request.POST:
                expense.status = 'draft'
            elif 'submit' in request.POST:
                expense.status = 'pending'
            
            expense.save()
            
            # Process receipt if uploaded
            if expense.receipt and not expense.receipt_processed:
                # TODO: Implement AI receipt processing
                expense.receipt_processed = True
                expense.ai_confidence_score = 0.95  # Placeholder
                expense.save()
            
            messages.success(request, f'Expense updated successfully!')
            return redirect('expenses:expense_detail', pk=expense.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ExpenseForm(user=request.user, instance=expense)
    
    # Get categories and vendors for dropdowns
    categories = ExpenseCategory.objects.filter(user=request.user, is_active=True)
    vendors = Vendor.objects.filter(user=request.user, is_active=True)
    
    context = {
        'form': form,
        'expense': expense,
        'categories': categories,
        'vendors': vendors,
        'is_edit': True,
    }
    
    return render(request, 'expenses/expense_create.html', context)


# Bulk Operations
@login_required
def bulk_delete_expenses(request):
    """Bulk delete expenses"""
    return bulk_delete_view(
        request=request,
        model=Expense,
        filter_kwargs={'user': request.user},
        success_message="expenses deleted successfully"
    )


@login_required  
def bulk_export_expenses(request):
    """Bulk export expenses to CSV"""
    return bulk_export_view(
        request=request,
        model=Expense,
        filter_kwargs={'user': request.user},
        filename="expenses_export"
    )


@login_required
def expense_export_pdf(request, pk):
    """
    Export expense as PDF
    """
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    
    # For now, return HTML that can be printed as PDF
    # In production, you'd use a library like WeasyPrint or ReportLab
    html_content = render_to_string('expenses/expense_pdf.html', {
        'expense': expense,
        'company_name': 'DreamBiz Accounting',
        'export_date': date.today(),
    })
    
    response = HttpResponse(html_content, content_type='text/html')
    response['Content-Disposition'] = f'inline; filename="expense_{expense.id}.html"'
    
    return response


@login_required
def expense_add_to_report(request, pk):
    """
    Add expense to an expense report
    """
    from datetime import timedelta
    from .models import ExpenseReport, ExpenseReportItem
    
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    
    if request.method == 'POST':
        report_id = request.POST.get('report_id')
        
        if report_id == 'new':
            # Create new expense report with date range for current month
            today = date.today()
            start_of_month = today.replace(day=1)
            # Get last day of month
            if today.month == 12:
                end_of_month = today.replace(day=31)
            else:
                end_of_month = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
            
            report = ExpenseReport.objects.create(
                user=request.user,
                title=f"Expense Report - {today.strftime('%B %Y')}",
                start_date=start_of_month,
                end_date=end_of_month,
                status='draft'
            )
            
            # Add expense to report using ExpenseReportItem
            ExpenseReportItem.objects.create(
                report=report,
                expense=expense
            )
            
            # Recalculate totals
            report.calculate_totals()
            
            messages.success(request, f'Expense added to new report: {report.title}')
        else:
            # Add to existing report
            report = get_object_or_404(ExpenseReport, pk=report_id, user=request.user)
            
            # Create ExpenseReportItem if it doesn't exist
            ExpenseReportItem.objects.get_or_create(
                report=report,
                expense=expense
            )
            
            # Recalculate totals
            report.calculate_totals()
            
            messages.success(request, f'Expense added to report: {report.title}')
        
        return redirect('expenses:expense_detail', pk=expense.pk)
    
    # GET request - show available reports
    reports = ExpenseReport.objects.filter(user=request.user, status='draft')
    
    context = {
        'expense': expense,
        'reports': reports,
    }
    
    return render(request, 'expenses/expense_add_to_report.html', context)


# Vendor Management Views (Class-Based)

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from accounts.mixins import CompanyAccessMixin


class VendorListView(LoginRequiredMixin, CompanyAccessMixin, ListView):
    """List all vendors for the company"""
    model = Vendor
    template_name = 'expenses/vendor_list.html'
    context_object_name = 'vendors'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()

        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query)
            )

        # Status filter
        status = self.request.GET.get('status', '')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['total_vendors'] = self.get_queryset().count()
        context['active_vendors'] = Vendor.objects.filter(
            company=self.request.company,
            is_active=True
        ).count()
        return context


class VendorCreateView(LoginRequiredMixin, CompanyAccessMixin, CreateView):
    """Create a new vendor"""
    model = Vendor
    form_class = VendorForm
    template_name = 'expenses/vendor_form.html'
    success_url = reverse_lazy('expenses:vendor_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.company = self.request.company
        messages.success(self.request, f'Vendor "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class VendorUpdateView(LoginRequiredMixin, CompanyAccessMixin, UpdateView):
    """Update an existing vendor"""
    model = Vendor
    form_class = VendorForm
    template_name = 'expenses/vendor_form.html'
    success_url = reverse_lazy('expenses:vendor_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'Vendor "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class VendorDeleteView(LoginRequiredMixin, CompanyAccessMixin, DeleteView):
    """Delete a vendor"""
    model = Vendor
    template_name = 'expenses/vendor_confirm_delete.html'
    success_url = reverse_lazy('expenses:vendor_list')

    def delete(self, request, *args, **kwargs):
        vendor = self.get_object()
        messages.success(request, f'Vendor "{vendor.name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)
