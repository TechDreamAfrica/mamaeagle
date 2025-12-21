from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from datetime import datetime, date, timedelta
import json
import csv
from decimal import Decimal

from .models import (
    FinancialStatement, FinancialPeriod, Account, AccountType,
    JournalEntry
)
from .financial_statements import (
    get_monthly_statements, get_annual_statements, get_quarterly_statements
)
from .statement_generator import ComprehensiveStatementGenerator
from common.utils import calculate_percentage_change


@login_required
def reports_main(request):
    """Main reports dashboard"""
    recent_statements = FinancialStatement.objects.filter(user=request.user)[:10]
    periods = FinancialPeriod.objects.filter(user=request.user, is_closed=False)[:5]
    
    context = {
        'recent_statements': recent_statements,
        'periods': periods,
    }
    return render(request, 'reports/reports_main.html', context)


@login_required
def report_list(request):
    """List all generated financial statements"""
    statements = FinancialStatement.objects.filter(user=request.user)
    
    # Filter by type if specified
    statement_type = request.GET.get('type')
    if statement_type:
        statements = statements.filter(statement_type=statement_type)
    
    context = {
        'statements': statements,
        'statement_types': FinancialStatement.STATEMENT_TYPES,
    }
    return render(request, 'reports/report_list.html', context)


@login_required
def profit_loss_report(request):
    """Generate and display Profit & Loss (Income Statement)"""
    from django.db.models import Sum, Q
    from calendar import monthrange
    
    # Get date range from request or default to current month
    period = request.GET.get('period', 'current-month')
    custom_start = request.GET.get('start_date')
    custom_end = request.GET.get('end_date')
    
    today = date.today()
    
    # Calculate date range based on period
    if period == 'current-month':
        start_date = date(today.year, today.month, 1)
        last_day = monthrange(today.year, today.month)[1]
        end_date = date(today.year, today.month, last_day)
        period_name = today.strftime("%B %Y")
    elif period == 'last-month':
        first = today.replace(day=1)
        last_month = first - timedelta(days=1)
        start_date = date(last_month.year, last_month.month, 1)
        last_day = monthrange(last_month.year, last_month.month)[1]
        end_date = date(last_month.year, last_month.month, last_day)
        period_name = last_month.strftime("%B %Y")
    elif period == 'current-quarter':
        quarter = (today.month - 1) // 3 + 1
        start_date = date(today.year, 3 * quarter - 2, 1)
        end_month = 3 * quarter
        last_day = monthrange(today.year, end_month)[1]
        end_date = date(today.year, end_month, last_day)
        period_name = f"Q{quarter} {today.year}"
    elif period == 'current-year':
        start_date = date(today.year, 1, 1)
        end_date = date(today.year, 12, 31)
        period_name = str(today.year)
    elif period == 'custom' and custom_start and custom_end:
        start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
        end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
        period_name = f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"
    else:
        # Default to current month
        start_date = date(today.year, today.month, 1)
        last_day = monthrange(today.year, today.month)[1]
        end_date = date(today.year, today.month, last_day)
        period_name = today.strftime("%B %Y")
    
    # Get all revenue and expense accounts with their balances
    from .models import Account, AccountType, JournalEntryLine
    
    # Revenue accounts
    revenue_accounts = Account.objects.filter(
        user=request.user,
        account_type__category='revenue',
        is_active=True
    ).select_related('account_type')
    
    # Expense accounts
    expense_accounts = Account.objects.filter(
        user=request.user,
        account_type__category='expense',
        is_active=True
    ).select_related('account_type')
    
    # Calculate revenue balances from journal entries
    revenue_data = []
    total_revenue = Decimal('0')
    
    for account in revenue_accounts:
        # Credits increase revenue, debits decrease
        balance = JournalEntryLine.objects.filter(
            account=account,
            journal_entry__user=request.user,
            journal_entry__entry_date__range=[start_date, end_date],
            journal_entry__status='posted'
        ).aggregate(
            total=Sum('credit') - Sum('debit')
        )['total'] or Decimal('0')
        
        if balance != 0:
            revenue_data.append({
                'account': account,
                'balance': balance
            })
            total_revenue += balance
    
    # Calculate expense balances from journal entries
    expense_data = []
    total_expenses = Decimal('0')
    expense_by_category = {}
    
    for account in expense_accounts:
        # Debits increase expenses, credits decrease
        balance = JournalEntryLine.objects.filter(
            account=account,
            journal_entry__user=request.user,
            journal_entry__entry_date__range=[start_date, end_date],
            journal_entry__status='posted'
        ).aggregate(
            total=Sum('debit') - Sum('credit')
        )['total'] or Decimal('0')
        
        if balance != 0:
            expense_data.append({
                'account': account,
                'balance': balance
            })
            total_expenses += balance
            
            # Group by subtype or name
            category = account.account_type.subtype or account.account_type.name
            if category not in expense_by_category:
                expense_by_category[category] = Decimal('0')
            expense_by_category[category] += balance
    
    # Calculate net income
    net_income = total_revenue - total_expenses
    net_margin = (net_income / total_revenue * 100) if total_revenue > 0 else Decimal('0')
    
    # Get comparison data (previous period)
    if period == 'current-month':
        prev_start = (start_date.replace(day=1) - timedelta(days=1)).replace(day=1)
        prev_last_day = monthrange(prev_start.year, prev_start.month)[1]
        prev_end = date(prev_start.year, prev_start.month, prev_last_day)
    elif period == 'current-year':
        prev_start = date(start_date.year - 1, 1, 1)
        prev_end = date(start_date.year - 1, 12, 31)
    else:
        days_diff = (end_date - start_date).days + 1
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=days_diff - 1)
    
    # Previous period revenue
    prev_revenue = JournalEntryLine.objects.filter(
        account__user=request.user,
        account__account_type__category='revenue',
        journal_entry__user=request.user,
        journal_entry__entry_date__range=[prev_start, prev_end],
        journal_entry__status='posted'
    ).aggregate(
        total=Sum('credit') - Sum('debit')
    )['total'] or Decimal('0')
    
    # Previous period expenses
    prev_expenses = JournalEntryLine.objects.filter(
        account__user=request.user,
        account__account_type__category='expense',
        journal_entry__user=request.user,
        journal_entry__entry_date__range=[prev_start, prev_end],
        journal_entry__status='posted'
    ).aggregate(
        total=Sum('debit') - Sum('credit')
    )['total'] or Decimal('0')
    
    prev_net_income = prev_revenue - prev_expenses
    
    # Calculate changes
    revenue_change = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else Decimal('0')
    expense_change = ((total_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else Decimal('0')
    income_change = ((net_income - prev_net_income) / abs(prev_net_income) * 100) if prev_net_income != 0 else Decimal('0')
    
    context = {
        'period_name': period_name,
        'start_date': start_date,
        'end_date': end_date,
        'current_period': period,
        'revenue_data': revenue_data,
        'expense_data': expense_data,
        'expense_by_category': expense_by_category,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_income': net_income,
        'net_margin': net_margin,
        'prev_revenue': prev_revenue,
        'prev_expenses': prev_expenses,
        'prev_net_income': prev_net_income,
        'revenue_change': revenue_change,
        'expense_change': expense_change,
        'income_change': income_change,
    }
    return render(request, 'reports/profit_loss.html', context)


@login_required
def balance_sheet_report(request):
    """Generate and display Balance Sheet"""
    from django.db.models import Sum
    
    # Get date parameter or default to today
    as_of_date_str = request.GET.get('as_of_date')
    if as_of_date_str:
        try:
            as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
        except ValueError:
            as_of_date = date.today()
    else:
        as_of_date = date.today()
    
    from .models import AccountType, JournalEntryLine
    
    # Get all asset accounts
    asset_accounts = Account.objects.filter(
        user=request.user,
        account_type__category='asset',
        is_active=True
    ).select_related('account_type').order_by('account_type__subtype', 'account_number')
    
    # Get all liability accounts
    liability_accounts = Account.objects.filter(
        user=request.user,
        account_type__category='liability',
        is_active=True
    ).select_related('account_type').order_by('account_type__subtype', 'account_number')
    
    # Get all equity accounts
    equity_accounts = Account.objects.filter(
        user=request.user,
        account_type__category='equity',
        is_active=True
    ).select_related('account_type').order_by('account_number')
    
    # Calculate asset balances
    assets_data = {
        'current_assets': [],
        'fixed_assets': [],
        'other_assets': []
    }
    total_current_assets = Decimal('0')
    total_fixed_assets = Decimal('0')
    total_other_assets = Decimal('0')
    
    for account in asset_accounts:
        # Debits increase assets, credits decrease
        balance = account.opening_balance + (JournalEntryLine.objects.filter(
            account=account,
            journal_entry__user=request.user,
            journal_entry__entry_date__lte=as_of_date,
            journal_entry__status='posted'
        ).aggregate(
            total=Sum('debit') - Sum('credit')
        )['total'] or Decimal('0'))
        
        if balance != 0:
            account_data = {
                'account': account,
                'balance': balance
            }
            
            subtype = account.account_type.subtype
            if subtype == 'current_asset':
                assets_data['current_assets'].append(account_data)
                total_current_assets += balance
            elif subtype == 'fixed_asset':
                assets_data['fixed_assets'].append(account_data)
                total_fixed_assets += balance
            else:
                assets_data['other_assets'].append(account_data)
                total_other_assets += balance
    
    total_assets = total_current_assets + total_fixed_assets + total_other_assets
    
    # Calculate liability balances
    liabilities_data = {
        'current_liabilities': [],
        'long_term_liabilities': [],
        'other_liabilities': []
    }
    total_current_liabilities = Decimal('0')
    total_long_term_liabilities = Decimal('0')
    total_other_liabilities = Decimal('0')
    
    for account in liability_accounts:
        # Credits increase liabilities, debits decrease
        balance = account.opening_balance + (JournalEntryLine.objects.filter(
            account=account,
            journal_entry__user=request.user,
            journal_entry__entry_date__lte=as_of_date,
            journal_entry__status='posted'
        ).aggregate(
            total=Sum('credit') - Sum('debit')
        )['total'] or Decimal('0'))
        
        if balance != 0:
            account_data = {
                'account': account,
                'balance': balance
            }
            
            subtype = account.account_type.subtype
            if subtype == 'current_liability':
                liabilities_data['current_liabilities'].append(account_data)
                total_current_liabilities += balance
            elif subtype == 'long_term_liability':
                liabilities_data['long_term_liabilities'].append(account_data)
                total_long_term_liabilities += balance
            else:
                liabilities_data['other_liabilities'].append(account_data)
                total_other_liabilities += balance
    
    total_liabilities = total_current_liabilities + total_long_term_liabilities + total_other_liabilities
    
    # Calculate equity balances
    equity_data = []
    total_equity = Decimal('0')
    
    for account in equity_accounts:
        # Credits increase equity, debits decrease
        balance = account.opening_balance + (JournalEntryLine.objects.filter(
            account=account,
            journal_entry__user=request.user,
            journal_entry__entry_date__lte=as_of_date,
            journal_entry__status='posted'
        ).aggregate(
            total=Sum('credit') - Sum('debit')
        )['total'] or Decimal('0'))
        
        if balance != 0:
            equity_data.append({
                'account': account,
                'balance': balance
            })
            total_equity += balance
    
    # Calculate retained earnings (net income year-to-date)
    year_start = date(as_of_date.year, 1, 1)
    
    ytd_revenue = JournalEntryLine.objects.filter(
        account__user=request.user,
        account__account_type__category='revenue',
        journal_entry__user=request.user,
        journal_entry__entry_date__range=[year_start, as_of_date],
        journal_entry__status='posted'
    ).aggregate(
        total=Sum('credit') - Sum('debit')
    )['total'] or Decimal('0')
    
    ytd_expenses = JournalEntryLine.objects.filter(
        account__user=request.user,
        account__account_type__category='expense',
        journal_entry__user=request.user,
        journal_entry__entry_date__range=[year_start, as_of_date],
        journal_entry__status='posted'
    ).aggregate(
        total=Sum('debit') - Sum('credit')
    )['total'] or Decimal('0')
    
    retained_earnings = ytd_revenue - ytd_expenses
    total_equity += retained_earnings
    
    # Total liabilities and equity
    total_liabilities_equity = total_liabilities + total_equity
    
    # Calculate financial ratios
    current_ratio = (total_current_assets / total_current_liabilities) if total_current_liabilities > 0 else Decimal('0')
    debt_to_equity = (total_liabilities / total_equity) if total_equity > 0 else Decimal('0')
    equity_ratio = (total_equity / total_assets) if total_assets > 0 else Decimal('0')
    
    context = {
        'as_of_date': as_of_date,
        'assets_data': assets_data,
        'liabilities_data': liabilities_data,
        'equity_data': equity_data,
        'total_current_assets': total_current_assets,
        'total_fixed_assets': total_fixed_assets,
        'total_other_assets': total_other_assets,
        'total_assets': total_assets,
        'total_current_liabilities': total_current_liabilities,
        'total_long_term_liabilities': total_long_term_liabilities,
        'total_other_liabilities': total_other_liabilities,
        'total_liabilities': total_liabilities,
        'retained_earnings': retained_earnings,
        'total_equity': total_equity,
        'total_liabilities_equity': total_liabilities_equity,
        'current_ratio': current_ratio,
        'debt_to_equity': debt_to_equity,
        'equity_ratio': equity_ratio,
        'is_balanced': abs(total_assets - total_liabilities_equity) < Decimal('0.01'),
    }
    return render(request, 'reports/balance_sheet.html', context)


@login_required
def cash_flow_report(request):
    """Generate and display Cash Flow Statement"""
    from django.db.models import Sum, Q
    from calendar import monthrange
    
    # Get date range from request or default to current month
    period = request.GET.get('period', 'current-month')
    today = date.today()
    
    # Calculate date range
    if period == 'current-month':
        start_date = date(today.year, today.month, 1)
        last_day = monthrange(today.year, today.month)[1]
        end_date = date(today.year, today.month, last_day)
        period_name = today.strftime("%B %Y")
    elif period == 'current-quarter':
        quarter = (today.month - 1) // 3 + 1
        start_date = date(today.year, 3 * quarter - 2, 1)
        end_month = 3 * quarter
        last_day = monthrange(today.year, end_month)[1]
        end_date = date(today.year, end_month, last_day)
        period_name = f"Q{quarter} {today.year}"
    elif period == 'current-year':
        start_date = date(today.year, 1, 1)
        end_date = date(today.year, 12, 31)
        period_name = str(today.year)
    else:
        start_date = date(today.year, today.month, 1)
        last_day = monthrange(today.year, today.month)[1]
        end_date = date(today.year, today.month, last_day)
        period_name = today.strftime("%B %Y")
    
    from .models import JournalEntryLine
    from invoicing.models import Invoice, Payment
    from expenses.models import Expense
    
    # Operating Activities
    # Cash received from customers (invoice payments)
    cash_from_customers = Payment.objects.filter(
        invoice__user=request.user,
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Cash paid for expenses
    cash_paid_expenses = Expense.objects.filter(
        user=request.user,
        date__range=[start_date, end_date],
        status='approved'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Net cash from operating activities
    net_operating = cash_from_customers - cash_paid_expenses
    
    # Investing Activities (Fixed asset purchases/sales)
    investing_outflows = JournalEntryLine.objects.filter(
        account__account_type__category='asset',
        account__account_type__subtype='fixed_asset',
        journal_entry__user=request.user,
        journal_entry__entry_date__range=[start_date, end_date],
        journal_entry__status='posted',
        debit__gt=0
    ).aggregate(total=Sum('debit'))['total'] or Decimal('0')
    
    investing_inflows = JournalEntryLine.objects.filter(
        account__account_type__category='asset',
        account__account_type__subtype='fixed_asset',
        journal_entry__user=request.user,
        journal_entry__entry_date__range=[start_date, end_date],
        journal_entry__status='posted',
        credit__gt=0
    ).aggregate(total=Sum('credit'))['total'] or Decimal('0')
    
    net_investing = investing_inflows - investing_outflows
    
    # Financing Activities (Loans, equity)
    financing_inflows = JournalEntryLine.objects.filter(
        account__account_type__category__in=['liability', 'equity'],
        journal_entry__user=request.user,
        journal_entry__entry_date__range=[start_date, end_date],
        journal_entry__status='posted',
        credit__gt=0
    ).aggregate(total=Sum('credit'))['total'] or Decimal('0')
    
    financing_outflows = JournalEntryLine.objects.filter(
        account__account_type__category__in=['liability', 'equity'],
        journal_entry__user=request.user,
        journal_entry__entry_date__range=[start_date, end_date],
        journal_entry__status='posted',
        debit__gt=0
    ).aggregate(total=Sum('debit'))['total'] or Decimal('0')
    
    net_financing = financing_inflows - financing_outflows
    
    # Net change in cash
    net_change_in_cash = net_operating + net_investing + net_financing
    
    # Beginning and ending cash balance
    from .models import Account
    cash_accounts = Account.objects.filter(
        user=request.user,
        account_type__category='asset',
        account_name__icontains='cash'
    )
    
    beginning_cash = sum([
        acc.opening_balance + (JournalEntryLine.objects.filter(
            account=acc,
            journal_entry__entry_date__lt=start_date,
            journal_entry__status='posted'
        ).aggregate(total=Sum('debit') - Sum('credit'))['total'] or Decimal('0'))
        for acc in cash_accounts
    ])
    
    ending_cash = beginning_cash + net_change_in_cash
    
    context = {
        'period_name': period_name,
        'start_date': start_date,
        'end_date': end_date,
        'current_period': period,
        'cash_from_customers': cash_from_customers,
        'cash_paid_expenses': cash_paid_expenses,
        'net_operating': net_operating,
        'investing_outflows': investing_outflows,
        'investing_inflows': investing_inflows,
        'net_investing': net_investing,
        'financing_inflows': financing_inflows,
        'financing_outflows': financing_outflows,
        'net_financing': net_financing,
        'net_change_in_cash': net_change_in_cash,
        'beginning_cash': beginning_cash,
        'ending_cash': ending_cash,
    }
    return render(request, 'reports/cash_flow.html', context)


@login_required
def ar_aging_report(request):
    """Accounts Receivable Aging Report"""
    from invoicing.models import Invoice
    
    today = date.today()
    
    # Get all unpaid or partially paid invoices
    invoices = Invoice.objects.filter(
        user=request.user,
        status__in=['sent', 'overdue', 'partial']
    ).select_related('customer')
    
    # Categorize by age
    current = []  # 0-30 days
    days_31_60 = []
    days_61_90 = []
    over_90 = []
    
    total_current = Decimal('0')
    total_31_60 = Decimal('0')
    total_61_90 = Decimal('0')
    total_over_90 = Decimal('0')
    
    for invoice in invoices:
        balance = invoice.balance_due
        if balance <= 0:
            continue
            
        days_overdue = (today - invoice.due_date).days
        
        invoice_data = {
            'invoice': invoice,
            'balance': balance,
            'days_overdue': days_overdue
        }
        
        if days_overdue <= 30:
            current.append(invoice_data)
            total_current += balance
        elif days_overdue <= 60:
            days_31_60.append(invoice_data)
            total_31_60 += balance
        elif days_overdue <= 90:
            days_61_90.append(invoice_data)
            total_61_90 += balance
        else:
            over_90.append(invoice_data)
            total_over_90 += balance
    
    total_ar = total_current + total_31_60 + total_61_90 + total_over_90
    
    context = {
        'as_of_date': today,
        'current': current,
        'days_31_60': days_31_60,
        'days_61_90': days_61_90,
        'over_90': over_90,
        'total_current': total_current,
        'total_31_60': total_31_60,
        'total_61_90': total_61_90,
        'total_over_90': total_over_90,
        'total_ar': total_ar,
    }
    return render(request, 'reports/ar_aging.html', context)


@login_required
def expense_category_report(request):
    """Expense Report by Category"""
    from django.db.models import Sum
    from expenses.models import Expense
    from calendar import monthrange
    
    period = request.GET.get('period', 'current-month')
    today = date.today()
    
    if period == 'current-month':
        start_date = date(today.year, today.month, 1)
        last_day = monthrange(today.year, today.month)[1]
        end_date = date(today.year, today.month, last_day)
        period_name = today.strftime("%B %Y")
    elif period == 'current-year':
        start_date = date(today.year, 1, 1)
        end_date = date(today.year, 12, 31)
        period_name = str(today.year)
    else:
        start_date = date(today.year, today.month, 1)
        last_day = monthrange(today.year, today.month)[1]
        end_date = date(today.year, today.month, last_day)
        period_name = today.strftime("%B %Y")
    
    # Get expenses by category
    expenses = Expense.objects.filter(
        user=request.user,
        date__range=[start_date, end_date]
    ).values('category').annotate(
        total=Sum('amount'),
        count=Sum('id')
    ).order_by('-total')
    
    # Get individual expenses for detail
    all_expenses = Expense.objects.filter(
        user=request.user,
        date__range=[start_date, end_date]
    ).select_related('vendor').order_by('-date')
    
    total_expenses = sum([e['total'] for e in expenses])
    
    # Add percentage to each category
    for expense in expenses:
        expense['percentage'] = (expense['total'] / total_expenses * 100) if total_expenses > 0 else 0
    
    context = {
        'period_name': period_name,
        'start_date': start_date,
        'end_date': end_date,
        'current_period': period,
        'expenses_by_category': expenses,
        'all_expenses': all_expenses,
        'total_expenses': total_expenses,
    }
    return render(request, 'reports/expense_category.html', context)


@login_required
def sales_tax_report(request):
    """Sales Tax Report"""
    from django.db.models import Sum
    from invoicing.models import Invoice
    from calendar import monthrange
    
    period = request.GET.get('period', 'current-month')
    today = date.today()
    
    if period == 'current-month':
        start_date = date(today.year, today.month, 1)
        last_day = monthrange(today.year, today.month)[1]
        end_date = date(today.year, today.month, last_day)
        period_name = today.strftime("%B %Y")
    elif period == 'current-quarter':
        quarter = (today.month - 1) // 3 + 1
        start_date = date(today.year, 3 * quarter - 2, 1)
        end_month = 3 * quarter
        last_day = monthrange(today.year, end_month)[1]
        end_date = date(today.year, end_month, last_day)
        period_name = f"Q{quarter} {today.year}"
    elif period == 'current-year':
        start_date = date(today.year, 1, 1)
        end_date = date(today.year, 12, 31)
        period_name = str(today.year)
    else:
        start_date = date(today.year, today.month, 1)
        last_day = monthrange(today.year, today.month)[1]
        end_date = date(today.year, today.month, last_day)
        period_name = today.strftime("%B %Y")
    
    # Get all invoices with tax
    invoices = Invoice.objects.filter(
        user=request.user,
        date_created__range=[start_date, end_date]
    ).select_related('customer')
    
    total_sales = Decimal('0')
    total_tax = Decimal('0')
    taxable_sales = []
    
    for invoice in invoices:
        if invoice.tax_amount and invoice.tax_amount > 0:
            total_sales += invoice.subtotal
            total_tax += invoice.tax_amount
            taxable_sales.append(invoice)
    
    context = {
        'period_name': period_name,
        'start_date': start_date,
        'end_date': end_date,
        'current_period': period,
        'taxable_sales': taxable_sales,
        'total_sales': total_sales,
        'total_tax': total_tax,
        'total_with_tax': total_sales + total_tax,
    }
    return render(request, 'reports/sales_tax.html', context)


@login_required
def budget_actual_report(request):
    """Budget vs Actual Report"""
    from django.db.models import Sum
    from .models import JournalEntryLine
    from calendar import monthrange
    
    year = int(request.GET.get('year', date.today().year))
    
    # Get revenue and expenses for each month
    months_data = []
    
    for month in range(1, 13):
        start_date = date(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = date(year, month, last_day)
        
        # Actual revenue
        actual_revenue = JournalEntryLine.objects.filter(
            account__user=request.user,
            account__account_type__category='revenue',
            journal_entry__entry_date__range=[start_date, end_date],
            journal_entry__status='posted'
        ).aggregate(total=Sum('credit') - Sum('debit'))['total'] or Decimal('0')
        
        # Actual expenses
        actual_expenses = JournalEntryLine.objects.filter(
            account__user=request.user,
            account__account_type__category='expense',
            journal_entry__entry_date__range=[start_date, end_date],
            journal_entry__status='posted'
        ).aggregate(total=Sum('debit') - Sum('credit'))['total'] or Decimal('0')
        
        # Simple budget calculation (could be enhanced with a Budget model)
        # For now, use average of previous year or YTD average
        budget_revenue = actual_revenue * Decimal('1.1')  # Assume 10% growth target
        budget_expenses = actual_expenses * Decimal('0.95')  # Assume 5% reduction target
        
        months_data.append({
            'month': start_date.strftime('%B'),
            'actual_revenue': actual_revenue,
            'budget_revenue': budget_revenue,
            'revenue_variance': actual_revenue - budget_revenue,
            'actual_expenses': actual_expenses,
            'budget_expenses': budget_expenses,
            'expense_variance': budget_expenses - actual_expenses,
            'actual_net': actual_revenue - actual_expenses,
            'budget_net': budget_revenue - budget_expenses,
        })
    
    # Calculate totals
    total_actual_revenue = sum([m['actual_revenue'] for m in months_data])
    total_budget_revenue = sum([m['budget_revenue'] for m in months_data])
    total_actual_expenses = sum([m['actual_expenses'] for m in months_data])
    total_budget_expenses = sum([m['budget_expenses'] for m in months_data])
    
    context = {
        'year': year,
        'months_data': months_data,
        'total_actual_revenue': total_actual_revenue,
        'total_budget_revenue': total_budget_revenue,
        'total_actual_expenses': total_actual_expenses,
        'total_budget_expenses': total_budget_expenses,
        'total_revenue_variance': total_actual_revenue - total_budget_revenue,
        'total_expense_variance': total_budget_expenses - total_actual_expenses,
    }
    return render(request, 'reports/budget_actual.html', context)


@login_required
def trial_balance_report(request):
    """Trial Balance Report"""
    from django.db.models import Sum
    from .models import Account, JournalEntryLine
    
    as_of_date_str = request.GET.get('as_of_date')
    if as_of_date_str:
        try:
            as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
        except ValueError:
            as_of_date = date.today()
    else:
        as_of_date = date.today()
    
    # Get all accounts with their balances
    accounts = Account.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('account_type').order_by('account_number')
    
    trial_balance_data = []
    total_debits = Decimal('0')
    total_credits = Decimal('0')
    
    for account in accounts:
        # Calculate balance from journal entries
        entries = JournalEntryLine.objects.filter(
            account=account,
            journal_entry__entry_date__lte=as_of_date,
            journal_entry__status='posted'
        ).aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )
        
        debit_sum = entries['total_debit'] or Decimal('0')
        credit_sum = entries['total_credit'] or Decimal('0')
        
        # Add opening balance
        debit_sum += account.opening_balance if account.opening_balance > 0 else Decimal('0')
        credit_sum += abs(account.opening_balance) if account.opening_balance < 0 else Decimal('0')
        
        # Determine final debit or credit balance
        if account.account_type.category in ['asset', 'expense']:
            # Normal debit balance accounts
            balance = debit_sum - credit_sum
            if balance > 0:
                debit_balance = balance
                credit_balance = Decimal('0')
            else:
                debit_balance = Decimal('0')
                credit_balance = abs(balance)
        else:
            # Normal credit balance accounts (liability, equity, revenue)
            balance = credit_sum - debit_sum
            if balance > 0:
                credit_balance = balance
                debit_balance = Decimal('0')
            else:
                credit_balance = Decimal('0')
                debit_balance = abs(balance)
        
        if debit_balance != 0 or credit_balance != 0:
            trial_balance_data.append({
                'account': account,
                'debit': debit_balance,
                'credit': credit_balance,
            })
            total_debits += debit_balance
            total_credits += credit_balance
    
    is_balanced = abs(total_debits - total_credits) < Decimal('0.01')
    
    context = {
        'as_of_date': as_of_date,
        'trial_balance_data': trial_balance_data,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'is_balanced': is_balanced,
        'difference': total_debits - total_credits,
    }
    return render(request, 'reports/trial_balance.html', context)


@login_required
def customer_sales_report(request):
    """Customer Sales Report"""
    from django.db.models import Sum, Count
    from invoicing.models import Invoice
    from calendar import monthrange
    
    period = request.GET.get('period', 'current-month')
    today = date.today()
    
    if period == 'current-month':
        start_date = date(today.year, today.month, 1)
        last_day = monthrange(today.year, today.month)[1]
        end_date = date(today.year, today.month, last_day)
        period_name = today.strftime("%B %Y")
    elif period == 'current-year':
        start_date = date(today.year, 1, 1)
        end_date = date(today.year, 12, 31)
        period_name = str(today.year)
    else:
        start_date = date(today.year, today.month, 1)
        last_day = monthrange(today.year, today.month)[1]
        end_date = date(today.year, today.month, last_day)
        period_name = today.strftime("%B %Y")
    
    # Get sales by customer
    from accounts.models import Company
    customer_sales = Invoice.objects.filter(
        user=request.user,
        date_created__range=[start_date, end_date]
    ).values('customer__name', 'customer_id').annotate(
        total_sales=Sum('total_amount'),
        total_paid=Sum('amount_paid'),
        invoice_count=Count('id')
    ).order_by('-total_sales')
    
    # Calculate outstanding balance for each customer
    for customer in customer_sales:
        customer['outstanding'] = customer['total_sales'] - customer['total_paid']
    
    total_sales = sum([c['total_sales'] for c in customer_sales])
    total_paid = sum([c['total_paid'] for c in customer_sales])
    total_outstanding = total_sales - total_paid
    
    # Add percentage to each customer
    for customer in customer_sales:
        customer['percentage'] = (customer['total_sales'] / total_sales * 100) if total_sales > 0 else 0
    
    context = {
        'period_name': period_name,
        'start_date': start_date,
        'end_date': end_date,
        'current_period': period,
        'customer_sales': customer_sales,
        'total_sales': total_sales,
        'total_paid': total_paid,
        'total_outstanding': total_outstanding,
    }
    return render(request, 'reports/customer_sales.html', context)


@login_required
def generate_monthly_statement(request):
    """
    Generate detailed monthly financial statement
    """
    if request.method == 'POST':
        year = int(request.POST.get('year', datetime.now().year))
        month = int(request.POST.get('month', datetime.now().month))
        accounting_standard = request.POST.get('accounting_standard', 'GAAP')
        statement_type = request.POST.get('statement_type', 'comprehensive')
        
        try:
            # Generate the statements
            statements = get_monthly_statements(request.user, year, month, accounting_standard)
            
            # Create or get the period
            from calendar import monthrange
            start_date = date(year, month, 1)
            last_day = monthrange(year, month)[1]
            end_date = date(year, month, last_day)
            
            period, created = FinancialPeriod.objects.get_or_create(
                user=request.user,
                period_type='monthly',
                start_date=start_date,
                end_date=end_date,
                defaults={'name': f'{start_date.strftime("%B %Y")}'}
            )
            
            # Save the statement
            statement = FinancialStatement.objects.create(
                user=request.user,
                statement_type=statement_type,
                period=period,
                generated_by=request.user,
                statement_data=statements,
                accounting_standard=accounting_standard
            )
            
            messages.success(request, f'Monthly financial statement for {start_date.strftime("%B %Y")} generated successfully.')
            return redirect('reports:view_statement', pk=statement.pk)
        
        except Exception as e:
            messages.error(request, f'Error generating statement: {str(e)}')
            return redirect('reports:monthly_statement_form')
    
    # GET request - show form
    context = {
        'years': range(2020, datetime.now().year + 2),
        'months': range(1, 13),
        'current_year': datetime.now().year,
        'current_month': datetime.now().month,
        'accounting_standards': ['GAAP', 'IFRS'],
        'statement_types': FinancialStatement.STATEMENT_TYPES,
    }
    return render(request, 'reports/generate_monthly_statement.html', context)


@login_required
def generate_annual_statement(request):
    """
    Generate detailed annual financial statement
    """
    if request.method == 'POST':
        year = int(request.POST.get('year', datetime.now().year))
        accounting_standard = request.POST.get('accounting_standard', 'GAAP')
        statement_type = request.POST.get('statement_type', 'comprehensive')
        
        try:
            # Generate the statements
            statements = get_annual_statements(request.user, year, accounting_standard)
            
            # Create or get the period
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            
            period, created = FinancialPeriod.objects.get_or_create(
                user=request.user,
                period_type='annual',
                start_date=start_date,
                end_date=end_date,
                defaults={'name': f'Fiscal Year {year}'}
            )
            
            # Save the statement
            statement = FinancialStatement.objects.create(
                user=request.user,
                statement_type=statement_type,
                period=period,
                generated_by=request.user,
                statement_data=statements,
                accounting_standard=accounting_standard
            )
            
            messages.success(request, f'Annual financial statement for {year} generated successfully.')
            return redirect('reports:view_statement', pk=statement.pk)
        
        except Exception as e:
            messages.error(request, f'Error generating statement: {str(e)}')
            return redirect('reports:annual_statement_form')
    
    # GET request - show form
    context = {
        'years': range(2020, datetime.now().year + 2),
        'current_year': datetime.now().year,
        'accounting_standards': ['GAAP', 'IFRS'],
        'statement_types': FinancialStatement.STATEMENT_TYPES,
    }
    return render(request, 'reports/generate_annual_statement.html', context)


@login_required
def generate_quarterly_statement(request):
    """
    Generate detailed quarterly financial statement
    """
    if request.method == 'POST':
        year = int(request.POST.get('year', datetime.now().year))
        quarter = int(request.POST.get('quarter', 1))
        accounting_standard = request.POST.get('accounting_standard', 'GAAP')
        statement_type = request.POST.get('statement_type', 'comprehensive')
        
        try:
            # Generate the statements
            statements = get_quarterly_statements(request.user, year, quarter, accounting_standard)
            
            # Create or get the period
            quarter_months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
            start_month, end_month = quarter_months[quarter]
            start_date = date(year, start_month, 1)
            
            from calendar import monthrange
            last_day = monthrange(year, end_month)[1]
            end_date = date(year, end_month, last_day)
            
            period, created = FinancialPeriod.objects.get_or_create(
                user=request.user,
                period_type='quarterly',
                start_date=start_date,
                end_date=end_date,
                defaults={'name': f'Q{quarter} {year}'}
            )
            
            # Save the statement
            statement = FinancialStatement.objects.create(
                user=request.user,
                statement_type=statement_type,
                period=period,
                generated_by=request.user,
                statement_data=statements,
                accounting_standard=accounting_standard
            )
            
            messages.success(request, f'Quarterly financial statement for Q{quarter} {year} generated successfully.')
            return redirect('reports:view_statement', pk=statement.pk)
        
        except Exception as e:
            messages.error(request, f'Error generating statement: {str(e)}')
            return redirect('reports:quarterly_statement_form')
    
    # GET request - show form
    context = {
        'years': range(2020, datetime.now().year + 2),
        'quarters': range(1, 5),
        'current_year': datetime.now().year,
        'accounting_standards': ['GAAP', 'IFRS'],
        'statement_types': FinancialStatement.STATEMENT_TYPES,
    }
    return render(request, 'reports/generate_quarterly_statement.html', context)


@login_required
def view_statement(request, pk):
    """
    View a generated financial statement
    """
    statement = FinancialStatement.objects.get(pk=pk, user=request.user)
    
    context = {
        'statement': statement,
        'statement_data': statement.statement_data,
    }
    return render(request, 'reports/view_statement.html', context)


@login_required
def export_statement(request, pk):
    """
    Export financial statement to CSV or JSON
    """
    statement = FinancialStatement.objects.get(pk=pk, user=request.user)
    export_format = request.GET.get('format', 'json')
    
    if export_format == 'json':
        response = HttpResponse(
            json.dumps(statement.statement_data, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="statement_{statement.pk}.json"'
        return response
    
    elif export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="statement_{statement.pk}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Financial Statement Export'])
        writer.writerow(['Type:', statement.get_statement_type_display()])
        writer.writerow(['Period:', statement.period.name])
        writer.writerow(['Standard:', statement.accounting_standard])
        writer.writerow(['Generated:', statement.generated_date.strftime('%Y-%m-%d %H:%M')])
        writer.writerow([])
        
        # Write statement data (simplified)
        data = statement.statement_data
        
        if statement.statement_type == 'comprehensive':
            # Balance Sheet
            if 'balance_sheet' in data:
                writer.writerow(['BALANCE SHEET'])
                bs = data['balance_sheet']
                writer.writerow(['Assets'])
                if 'assets' in bs and 'current_assets' in bs['assets']:
                    for item in bs['assets']['current_assets']:
                        writer.writerow([item['account_name'], item['balance']])
                writer.writerow([])
        
        return response
    
    messages.error(request, 'Invalid export format')
    return redirect('reports:view_statement', pk=pk)


@login_required
def chart_of_accounts(request):
    """
    View and manage Chart of Accounts
    """
    accounts = Account.objects.filter(user=request.user, is_active=True).select_related('account_type')
    account_types = AccountType.objects.filter(is_active=True)
    
    context = {
        'accounts': accounts,
        'account_types': account_types,
    }
    return render(request, 'reports/chart_of_accounts.html', context)


@login_required
def journal_entries(request):
    """
    View journal entries
    """
    entries = JournalEntry.objects.filter(user=request.user).prefetch_related('lines')[:50]
    
    context = {
        'entries': entries,
    }
    return render(request, 'reports/journal_entries.html', context)


@login_required
def monthly_financial_statements(request):
    """
    Generate detailed monthly financial statements
    """
    # Get month and year from request
    year = int(request.GET.get('year', datetime.now().year))
    month = int(request.GET.get('month', datetime.now().month))
    accounting_standard = request.GET.get('standard', 'GAAP')
    
    # Calculate date range
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year, 12, 31)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # Generate statements
    generator = ComprehensiveStatementGenerator(
        user=request.user,
        start_date=start_date,
        end_date=end_date,
        accounting_standard=accounting_standard
    )
    
    statements = generator.generate_comprehensive_package()
    
    # Get previous month for comparison
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
    
    prev_month_start = date(prev_year, prev_month, 1)
    if prev_month == 12:
        prev_month_end = date(prev_year, 12, 31)
    else:
        prev_month_end = date(prev_year, prev_month + 1, 1) - timedelta(days=1)
    
    prev_generator = ComprehensiveStatementGenerator(
        user=request.user,
        start_date=prev_month_start,
        end_date=prev_month_end,
        accounting_standard=accounting_standard
    )
    
    prev_statements = prev_generator.generate_income_statement()
    
    # Calculate month-over-month changes
    current_income = statements['income_statement']
    mom_changes = {
        'revenue_change': calculate_percentage_change(
            prev_statements.get('revenue', {}).get('gross_revenue', 0),
            current_income['revenue']['gross_revenue']
        ),
        'gross_profit_change': calculate_percentage_change(
            prev_statements.get('gross_profit', 0),
            current_income['gross_profit']
        ),
        'operating_income_change': calculate_percentage_change(
            prev_statements.get('operating_income', 0),
            current_income['operating_income']
        ),
        'net_income_change': calculate_percentage_change(
            prev_statements.get('net_income', 0),
            current_income['net_income']
        ),
    }
    
    context = {
        'statements': statements,
        'year': year,
        'month': month,
        'month_name': date(year, month, 1).strftime('%B'),
        'accounting_standard': accounting_standard,
        'mom_changes': mom_changes,
        'previous_period': {
            'start': prev_month_start,
            'end': prev_month_end,
        },
    }
    
    # Handle export requests
    export_format = request.GET.get('export')
    if export_format == 'pdf':
        return _export_to_pdf(statements, f'Monthly_Statements_{year}_{month:02d}')
    elif export_format == 'excel':
        return _export_to_excel(statements, f'Monthly_Statements_{year}_{month:02d}')
    elif export_format == 'csv':
        return _export_to_csv(statements, f'Monthly_Statements_{year}_{month:02d}')
    
    return render(request, 'reports/monthly_statements.html', context)


@login_required
def annual_financial_statements(request):
    """
    Generate detailed annual financial statements
    """
    # Get year from request
    year = int(request.GET.get('year', datetime.now().year))
    accounting_standard = request.GET.get('standard', 'GAAP')
    
    # Calculate date range
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    # Generate statements
    generator = ComprehensiveStatementGenerator(
        user=request.user,
        start_date=start_date,
        end_date=end_date,
        accounting_standard=accounting_standard
    )
    
    statements = generator.generate_comprehensive_package()
    
    # Get previous year for comparison
    prev_year_start = date(year - 1, 1, 1)
    prev_year_end = date(year - 1, 12, 31)
    
    prev_generator = ComprehensiveStatementGenerator(
        user=request.user,
        start_date=prev_year_start,
        end_date=prev_year_end,
        accounting_standard=accounting_standard
    )
    
    prev_statements = prev_generator.generate_comprehensive_package()
    
    # Calculate year-over-year changes
    current_income = statements['income_statement']
    prev_income = prev_statements['income_statement']
    
    yoy_changes = {
        'revenue_change': calculate_percentage_change(
            prev_income['revenue']['gross_revenue'],
            current_income['revenue']['gross_revenue']
        ),
        'gross_profit_change': calculate_percentage_change(
            prev_income['gross_profit'],
            current_income['gross_profit']
        ),
        'operating_income_change': calculate_percentage_change(
            prev_income['operating_income'],
            current_income['operating_income']
        ),
        'net_income_change': calculate_percentage_change(
            prev_income['net_income'],
            current_income['net_income']
        ),
    }
    
    # Calculate financial ratios
    balance_sheet = statements['balance_sheet']
    financial_ratios = _calculate_financial_ratios(statements)
    
    # Generate quarterly breakdown
    quarterly_data = []
    for quarter in range(1, 5):
        q_start_month = (quarter - 1) * 3 + 1
        q_start = date(year, q_start_month, 1)
        q_end_month = quarter * 3
        if q_end_month == 12:
            q_end = date(year, 12, 31)
        else:
            q_end = date(year, q_end_month + 1, 1) - timedelta(days=1)
        
        q_generator = ComprehensiveStatementGenerator(
            user=request.user,
            start_date=q_start,
            end_date=q_end,
            accounting_standard=accounting_standard
        )
        
        q_income = q_generator.generate_income_statement()
        quarterly_data.append({
            'quarter': quarter,
            'revenue': q_income['revenue']['gross_revenue'],
            'gross_profit': q_income['gross_profit'],
            'net_income': q_income['net_income'],
        })
    
    context = {
        'statements': statements,
        'prev_statements': prev_statements,
        'year': year,
        'accounting_standard': accounting_standard,
        'yoy_changes': yoy_changes,
        'financial_ratios': financial_ratios,
        'quarterly_data': quarterly_data,
    }
    
    # Handle export requests
    export_format = request.GET.get('export')
    if export_format == 'pdf':
        return _export_to_pdf(statements, f'Annual_Statements_{year}')
    elif export_format == 'excel':
        return _export_to_excel(statements, f'Annual_Statements_{year}')
    elif export_format == 'csv':
        return _export_to_csv(statements, f'Annual_Statements_{year}')
    
    return render(request, 'reports/annual_statements.html', context)


@login_required
def comparative_analysis(request):
    """
    Generate comparative financial analysis across multiple periods
    """
    # Get parameters
    start_year = int(request.GET.get('start_year', datetime.now().year - 2))
    end_year = int(request.GET.get('end_year', datetime.now().year))
    accounting_standard = request.GET.get('standard', 'GAAP')
    
    # Generate statements for each year
    yearly_data = []
    for year in range(start_year, end_year + 1):
        generator = ComprehensiveStatementGenerator(
            user=request.user,
            start_date=date(year, 1, 1),
            end_date=date(year, 12, 31),
            accounting_standard=accounting_standard
        )
        
        statements = generator.generate_comprehensive_package()
        income = statements['income_statement']
        balance = statements['balance_sheet']
        cash_flow = statements['cash_flow_statement']
        
        yearly_data.append({
            'year': year,
            'revenue': income['revenue']['gross_revenue'],
            'gross_profit': income['gross_profit'],
            'operating_income': income['operating_income'],
            'net_income': income['net_income'],
            'total_assets': balance['assets']['total_assets'],
            'total_liabilities': balance['liabilities']['total_liabilities'],
            'total_equity': balance['equity']['total_equity'],
            'operating_cash_flow': cash_flow['operating_activities']['net_cash_from_operating'],
        })
    
    # Calculate trends
    trends = _calculate_trends(yearly_data)
    
    context = {
        'yearly_data': yearly_data,
        'start_year': start_year,
        'end_year': end_year,
        'trends': trends,
        'accounting_standard': accounting_standard,
    }
    
    return render(request, 'reports/comparative_analysis.html', context)


# Helper functions
def _calculate_financial_ratios(statements):
    """Calculate comprehensive financial ratios"""
    income = statements['income_statement']
    balance = statements['balance_sheet']
    cash_flow = statements['cash_flow_statement']
    
    # Profitability Ratios
    revenue = income['revenue']['gross_revenue']
    gross_profit = income['gross_profit']
    operating_income = income['operating_income']
    net_income = income['net_income']
    
    total_assets = balance['assets']['total_assets']
    total_equity = balance['equity']['total_equity']
    
    profitability_ratios = {
        'gross_profit_margin': (gross_profit / revenue * 100) if revenue > 0 else 0,
        'operating_profit_margin': (operating_income / revenue * 100) if revenue > 0 else 0,
        'net_profit_margin': (net_income / revenue * 100) if revenue > 0 else 0,
        'return_on_assets': (net_income / total_assets * 100) if total_assets > 0 else 0,
        'return_on_equity': (net_income / total_equity * 100) if total_equity > 0 else 0,
    }
    
    # Liquidity Ratios
    current_assets = balance['assets']['current_assets']['total']
    current_liabilities = balance['liabilities']['current_liabilities']['total']
    
    liquidity_ratios = {
        'current_ratio': (current_assets / current_liabilities) if current_liabilities > 0 else 0,
        'working_capital': current_assets - current_liabilities,
    }
    
    # Leverage Ratios
    total_liabilities = balance['liabilities']['total_liabilities']
    
    leverage_ratios = {
        'debt_to_equity': (total_liabilities / total_equity) if total_equity > 0 else 0,
        'debt_to_assets': (total_liabilities / total_assets) if total_assets > 0 else 0,
        'equity_ratio': (total_equity / total_assets) if total_assets > 0 else 0,
    }
    
    # Efficiency Ratios
    operating_cash_flow = cash_flow['operating_activities']['net_cash_from_operating']
    
    efficiency_ratios = {
        'asset_turnover': (revenue / total_assets) if total_assets > 0 else 0,
        'operating_cash_flow_ratio': (operating_cash_flow / current_liabilities) if current_liabilities > 0 else 0,
    }
    
    return {
        'profitability': profitability_ratios,
        'liquidity': liquidity_ratios,
        'leverage': leverage_ratios,
        'efficiency': efficiency_ratios,
    }


def _calculate_trends(yearly_data):
    """Calculate trends from yearly data"""
    if len(yearly_data) < 2:
        return {}
    
    trends = {
        'revenue_growth': [],
        'profit_growth': [],
        'asset_growth': [],
    }
    
    for i in range(1, len(yearly_data)):
        prev_year = yearly_data[i-1]
        curr_year = yearly_data[i]
        
        trends['revenue_growth'].append({
            'year': curr_year['year'],
            'growth': calculate_percentage_change(prev_year['revenue'], curr_year['revenue'])
        })
        
        trends['profit_growth'].append({
            'year': curr_year['year'],
            'growth': calculate_percentage_change(prev_year['net_income'], curr_year['net_income'])
        })
        
        trends['asset_growth'].append({
            'year': curr_year['year'],
            'growth': calculate_percentage_change(prev_year['total_assets'], curr_year['total_assets'])
        })
    
    return trends


def _export_to_pdf(statements, filename):
    """Export statements to PDF - Feature Coming Soon"""
    # Professional PDF export functionality will be implemented with reportlab
    response = HttpResponse(
        'PDF Export Feature Coming Soon! Please use the web view for now.',
        content_type='text/plain'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}.txt"'
    return response


def _export_to_excel(statements, filename):
    """Export statements to Excel - Feature Coming Soon"""
    # Professional Excel export functionality will be implemented with openpyxl
    response = HttpResponse(
        'Excel Export Feature Coming Soon! Please use CSV export for now.',
        content_type='text/plain'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}.txt"'
    return response


def _export_to_csv(statements, filename):
    """Export statements to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    
    writer = csv.writer(response)
    
    # Write Income Statement
    writer.writerow(['INCOME STATEMENT'])
    writer.writerow([])
    writer.writerow(['Revenue'])
    
    income = statements['income_statement']
    for item in income['revenue']['items']:
        writer.writerow([item['account_name'], f"GH₵{item['amount']:.2f}"])
    
    writer.writerow(['Total Revenue', f"GH₵{income['revenue']['gross_revenue']:.2f}"])
    writer.writerow([])
    writer.writerow(['Net Income', f"GH₵{income['net_income']:.2f}"])
    
    return response


@login_required
def journal_entries(request):
    """
    View journal entries
    """
    entries = JournalEntry.objects.filter(user=request.user).prefetch_related('lines')[:50]
    
    context = {
        'entries': entries,
    }
    return render(request, 'reports/journal_entries.html', context)
