from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.contrib.humanize.templatetags.humanize import naturaltime
from datetime import timedelta, datetime
import csv
import json
from decimal import Decimal
from .models import DashboardWidget, Notification, QuickAction
from invoicing.models import Invoice, Customer
from expenses.models import Expense
from sales.models import Lead
from inventory.models import Product, StockMovement
from common.utils import calculate_percentage_change



@login_required
def dashboard_home(request):
    """
    Main dashboard view with customizable widgets
    Much more flexible than QuickBooks' static dashboard
    """
    # Get user's dashboard widgets
    widgets = DashboardWidget.objects.filter(user=request.user, is_visible=True)
    
    # Get recent notifications
    notifications = Notification.objects.filter(
        user=request.user, 
        is_read=False
    ).order_by('-created_at')[:5]
    
    # Get quick actions
    quick_actions = QuickAction.objects.filter(
        user=request.user, 
        is_active=True
    ).order_by('order')[:8]
    
    # Calculate key metrics with company context
    today = timezone.now().date()
    month_start = today.replace(day=1)
    company = getattr(request, 'company', None)
    
    # Base querysets with company filter
    if company:
        invoice_qs = Invoice.objects.filter(company=company)
        expense_qs = Expense.objects.filter(company=company)
        customer_qs = Customer.objects.filter(company=company)
        product_qs = Product.objects.filter(company=company)
    else:
        # Fallback to user filtering where available
        invoice_qs = Invoice.objects.filter(user=request.user)
        expense_qs = Expense.objects.filter(user=request.user) if hasattr(Expense._meta.get_field('user'), 'related_model') else Expense.objects.none()
        customer_qs = Customer.objects.filter(user=request.user)
        # Product model only has company field, so filter by user's companies
        user_companies = request.user.companies.all() if hasattr(request.user, 'companies') else []
        product_qs = Product.objects.filter(company__in=user_companies)
    
    # Revenue metrics
    monthly_revenue = invoice_qs.filter(
        date_created__gte=month_start,
        status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    # Previous month for comparison
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
    prev_monthly_revenue = invoice_qs.filter(
        date_created__gte=prev_month_start,
        date_created__lt=month_start,
        status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    # Expense metrics
    monthly_expenses = expense_qs.filter(
        date__gte=month_start
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    prev_monthly_expenses = expense_qs.filter(
        date__gte=prev_month_start,
        date__lt=month_start
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Recent activity - last 10 activities
    recent_activities = []
    
    # Recent invoices
    recent_invoices = invoice_qs.order_by('-date_created')[:5]
    for invoice in recent_invoices:
        recent_activities.append({
            'type': 'invoice',
            'icon': 'fas fa-file-invoice',
            'color': 'green' if invoice.status == 'paid' else 'blue',
            'title': f'Invoice #{invoice.invoice_number}',
            'description': f'Created for {invoice.customer.name}' if invoice.customer else 'Created',
            'amount': invoice.total_amount,
            'date': invoice.date_created,
            'url': f'/invoicing/invoices/{invoice.id}/'
        })
    
    # Recent expenses
    recent_expenses = expense_qs.order_by('-date')[:5]
    for expense in recent_expenses:
        recent_activities.append({
            'type': 'expense',
            'icon': 'fas fa-receipt',
            'color': 'red',
            'title': expense.description[:50],
            'description': f'Expense recorded',
            'amount': expense.amount,
            'date': expense.date,
            'url': f'/expenses/{expense.id}/'
        })
    
    # Sort activities by date
    recent_activities.sort(key=lambda x: x['date'], reverse=True)
    recent_activities = recent_activities[:10]
    
    # Calculate percentage changes
    revenue_change = calculate_percentage_change(prev_monthly_revenue, monthly_revenue)
    expense_change = calculate_percentage_change(prev_monthly_expenses, monthly_expenses)
    
    # Outstanding invoices
    outstanding_invoices = Invoice.objects.filter(
        user=request.user,
        status__in=['sent', 'overdue']
    ).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Additional metrics
    total_customers = customer_qs.count()
    total_products = product_qs.filter(is_active=True).count()
    
    # Product Statistics
    product_stats = {}
    if company:
        from inventory.models import StockMovement
        
        # Calculate total inventory value
        total_inventory_value = Decimal('0.00')
        low_stock_count = 0
        out_of_stock_count = 0
        
        active_products = product_qs.filter(is_active=True)
        for product in active_products:
            current_stock = product.current_stock
            stock_value = current_stock * product.cost_price
            total_inventory_value += stock_value
            
            if current_stock <= 0:
                out_of_stock_count += 1
            elif current_stock <= product.reorder_point:
                low_stock_count += 1
        
        # Stock movement statistics for current month
        stock_movements_this_month = StockMovement.objects.filter(
            company=company,
            movement_date__gte=month_start
        )
        
        monthly_stock_in = stock_movements_this_month.filter(
            quantity_change__gt=0
        ).aggregate(total=Sum('quantity_change'))['total'] or 0
        
        monthly_stock_out = stock_movements_this_month.filter(
            quantity_change__lt=0
        ).aggregate(total=Sum('quantity_change'))['total'] or 0
        
        # Top selling products this month
        top_selling_products = product_qs.filter(
            stock_movements__movement_date__gte=month_start,
            stock_movements__movement_type='sale'
        ).annotate(
            units_sold=Sum('stock_movements__quantity_change')
        ).order_by('units_sold')[:5]  # Negative values, so ascending order
        
        product_stats = {
            'total_inventory_value': float(total_inventory_value),
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'monthly_stock_in': monthly_stock_in,
            'monthly_stock_out': abs(monthly_stock_out),
            'top_selling_products': list(top_selling_products.values(
                'name', 'sku', 'units_sold'
            )),
        }
    
    context = {
        'widgets': widgets,
        'notifications': notifications,
        'quick_actions': quick_actions,
        'recent_activities': recent_activities,
        'metrics': {
            'monthly_revenue': float(monthly_revenue),
            'monthly_expenses': float(monthly_expenses),
            'net_income': float(monthly_revenue - monthly_expenses),
            'outstanding_amount': outstanding_invoices['total'] or 0,
            'outstanding_count': outstanding_invoices['count'] or 0,
            'total_customers': total_customers,
            'total_products': total_products,
            'revenue_change': revenue_change,
            'expense_change': expense_change,
        },
        'product_stats': product_stats,
        'today': today,
    }
    
    return render(request, 'dashboard/home.html', context)


@login_required
def export_dashboard_data(request):
    """Export dashboard data to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="dashboard_data.csv"'
    
    writer = csv.writer(response)
    company = getattr(request, 'company', None)
    
    # Write headers
    writer.writerow(['Export Date', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
    writer.writerow(['Company', company.name if company else 'Personal'])
    writer.writerow([])  # Empty row
    
    # Base querysets
    if company:
        invoice_qs = Invoice.objects.filter(company=company)
        expense_qs = Expense.objects.filter(company=company)
    else:
        invoice_qs = Invoice.objects.filter(user=request.user)
        expense_qs = Expense.objects.filter(user=request.user)
    
    # Summary metrics
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    monthly_revenue = invoice_qs.filter(
        date_created__gte=month_start,
        status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    monthly_expenses = expense_qs.filter(
        date__gte=month_start
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    writer.writerow(['Monthly Summary'])
    writer.writerow(['Revenue', f'${monthly_revenue}'])
    writer.writerow(['Expenses', f'${monthly_expenses}'])
    writer.writerow(['Net Income', f'${monthly_revenue - monthly_expenses}'])
    writer.writerow([])
    
    # Recent Invoices
    writer.writerow(['Recent Invoices'])
    writer.writerow(['Invoice Number', 'Customer', 'Amount', 'Status', 'Date'])
    
    recent_invoices = invoice_qs.order_by('-date_created')[:20]
    for invoice in recent_invoices:
        writer.writerow([
            invoice.invoice_number,
            invoice.customer.name if invoice.customer else 'N/A',
            f'${invoice.total_amount}',
            invoice.get_status_display(),
            invoice.date_created.strftime('%Y-%m-%d')
        ])
    
    writer.writerow([])
    
    # Recent Expenses
    writer.writerow(['Recent Expenses'])
    writer.writerow(['Description', 'Category', 'Amount', 'Date'])
    
    recent_expenses = expense_qs.order_by('-date')[:20]
    for expense in recent_expenses:
        writer.writerow([
            expense.description,
            expense.category.name if expense.category else 'Uncategorized',
            f'${expense.amount}',
            expense.date.strftime('%Y-%m-%d')
        ])
    
    return response


@login_required
def get_recent_activity(request):
    """AJAX endpoint for recent activity"""
    company = getattr(request, 'company', None)
    
    if company:
        invoice_qs = Invoice.objects.filter(company=company)
        expense_qs = Expense.objects.filter(company=company)
    else:
        invoice_qs = Invoice.objects.filter(user=request.user)
        expense_qs = Expense.objects.filter(user=request.user)
    
    activities = []
    
    # Recent invoices
    recent_invoices = invoice_qs.order_by('-date_created')[:10]
    for invoice in recent_invoices:
        # Convert date to datetime for naturaltime compatibility
        invoice_datetime = timezone.make_aware(datetime.combine(invoice.date_created, datetime.min.time()))
        activities.append({
            'type': 'invoice',
            'icon': 'fas fa-file-invoice',
            'color': 'green' if invoice.status == 'paid' else 'blue',
            'title': f'Invoice #{invoice.invoice_number}',
            'description': f'Created for {invoice.customer.name}' if invoice.customer else 'Created',
            'amount': str(invoice.total_amount),
            'date': invoice.date_created.isoformat(),
            'url': f'/invoicing/invoices/{invoice.id}/',
            'time_ago': naturaltime(invoice_datetime)
        })
    
    # Recent expenses
    recent_expenses = expense_qs.order_by('-date')[:10]
    for expense in recent_expenses:
        activities.append({
            'type': 'expense',
            'icon': 'fas fa-receipt',
            'color': 'red',
            'title': expense.description[:50],
            'description': 'Expense recorded',
            'amount': str(expense.amount),
            'date': expense.date.isoformat(),
            'url': f'/expenses/{expense.id}/',
            'time_ago': naturaltime(timezone.make_aware(datetime.combine(expense.date, datetime.min.time())))
        })
    
    # Sort by date
    activities.sort(key=lambda x: x['date'], reverse=True)
    
    return JsonResponse({'activities': activities[:15]})


@login_required
def get_revenue_chart_data(request):
    """
    API endpoint for revenue chart data
    Real-time data vs QuickBooks' delayed updates
    """
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get daily revenue data
    daily_revenue = []
    current_date = start_date
    
    while current_date <= end_date:
        revenue = Invoice.objects.filter(
            user=request.user,
            date_created=current_date,
            status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        daily_revenue.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'revenue': float(revenue)
        })
        current_date += timedelta(days=1)
    
    return JsonResponse({'data': daily_revenue})


@login_required
def get_product_stats(request):
    """
    API endpoint for product statistics
    """
    company = getattr(request, 'company', None)
    if not company:
        return JsonResponse({'error': 'No active company'}, status=400)
    
    from inventory.models import Product, StockMovement
    
    # Calculate product statistics
    active_products = Product.objects.filter(company=company, is_active=True)
    total_products = active_products.count()
    
    # Calculate inventory value and stock levels
    total_inventory_value = Decimal('0.00')
    low_stock_count = 0
    out_of_stock_count = 0
    overstocked_count = 0
    
    for product in active_products:
        current_stock = product.current_stock
        stock_value = current_stock * product.cost_price
        total_inventory_value += stock_value
        
        if current_stock <= 0:
            out_of_stock_count += 1
        elif current_stock <= product.reorder_point:
            low_stock_count += 1
        elif current_stock > product.maximum_stock_level:
            overstocked_count += 1
    
    # Recent stock movements
    today = timezone.now().date()
    week_start = today - timedelta(days=7)
    month_start = today.replace(day=1)
    
    weekly_movements = StockMovement.objects.filter(
        company=company,
        movement_date__gte=week_start
    )
    
    monthly_movements = StockMovement.objects.filter(
        company=company,
        movement_date__gte=month_start
    )
    
    # Stock in/out statistics
    weekly_stock_in = weekly_movements.filter(
        quantity_change__gt=0
    ).aggregate(total=Sum('quantity_change'))['total'] or 0
    
    weekly_stock_out = weekly_movements.filter(
        quantity_change__lt=0
    ).aggregate(total=Sum('quantity_change'))['total'] or 0
    
    monthly_stock_in = monthly_movements.filter(
        quantity_change__gt=0
    ).aggregate(total=Sum('quantity_change'))['total'] or 0
    
    monthly_stock_out = monthly_movements.filter(
        quantity_change__lt=0
    ).aggregate(total=Sum('quantity_change'))['total'] or 0
    
    # Top products by value and movement
    top_value_products = active_products.annotate(
        stock_value=F('cost_price') * Sum('stock_movements__quantity_change')
    ).order_by('-stock_value')[:5]
    
    # Most active products (by movement frequency)
    most_active_products = active_products.filter(
        stock_movements__movement_date__gte=month_start
    ).annotate(
        movement_count=Count('stock_movements')
    ).order_by('-movement_count')[:5]
    
    # Low stock alerts
    low_stock_products = active_products.filter(
        stock_movements__isnull=False
    ).annotate(
        current_stock=Sum('stock_movements__quantity_change')
    ).filter(
        current_stock__lte=F('reorder_point')
    )[:10]
    
    data = {
        'overview': {
            'total_products': total_products,
            'total_inventory_value': float(total_inventory_value),
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'overstocked_count': overstocked_count,
        },
        'movements': {
            'weekly_stock_in': weekly_stock_in,
            'weekly_stock_out': abs(weekly_stock_out),
            'monthly_stock_in': monthly_stock_in,
            'monthly_stock_out': abs(monthly_stock_out),
        },
        'top_products': {
            'by_value': list(top_value_products.values(
                'name', 'sku', 'stock_value'
            )),
            'most_active': list(most_active_products.values(
                'name', 'sku', 'movement_count'
            )),
        },
        'alerts': {
            'low_stock_products': list(low_stock_products.values(
                'name', 'sku', 'current_stock', 'reorder_point'
            )),
        }
    }
    
    return JsonResponse(data)


@login_required
def get_expense_chart_data(request):
    """
    API endpoint for expense chart data
    """
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get daily expense data
    daily_expenses = []
    current_date = start_date
    
    while current_date <= end_date:
        expenses = Expense.objects.filter(
            user=request.user,
            date=current_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        daily_expenses.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'expenses': float(expenses)
        })
        current_date += timedelta(days=1)
    
    return JsonResponse({'data': daily_expenses})


@login_required
def mark_notification_read(request, notification_id):
    """
    Mark a notification as read
    """
    try:
        notification = Notification.objects.get(
            id=notification_id, 
            user=request.user
        )
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'})


@login_required
def customize_dashboard(request):
    """
    Dashboard customization interface
    Advanced customization vs QuickBooks' limited options
    """
    widgets = DashboardWidget.objects.filter(user=request.user)
    
    if request.method == 'POST':
        # Handle widget updates
        widget_data = request.POST.get('widgets')
        # Process widget position updates
        # This would handle the drag-and-drop widget positioning
        pass
    
    context = {
        'widgets': widgets,
        'available_widgets': DashboardWidget.WIDGET_TYPES,
    }
    
    return render(request, 'dashboard/customize.html', context)
