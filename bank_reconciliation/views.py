from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Q
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import csv

from .models import (
    BankAccount, BankStatement, BankTransaction,
    ReconciliationRule, ReconciliationSession
)


# Dashboard and Overview Views
@login_required
def reconciliation_dashboard(request):
    """Bank reconciliation dashboard with key metrics."""
    # Get date ranges
    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    
    # Key metrics
    total_accounts = BankAccount.objects.filter(is_active=True).count()
    unreconciled_statements = BankStatement.objects.filter(
        status__in=['imported', 'processing', 'partially_reconciled']
    ).count()
    
    # Financial metrics
    total_bank_balance = BankAccount.objects.filter(
        is_active=True
    ).aggregate(total=Sum('current_balance'))['total'] or 0
    
    unreconciled_transactions = BankTransaction.objects.filter(
        reconciliation_status='unreconciled'
    ).count()
    
    # Recent activity
    recent_sessions = ReconciliationSession.objects.order_by('-start_date')[:5]
    recent_transactions = BankTransaction.objects.select_related(
        'bank_statement__bank_account'
    ).order_by('-transaction_date')[:10]
    
    # Accounts needing attention
    accounts_needing_reconciliation = BankAccount.objects.filter(
        is_active=True,
        last_reconciled_date__lt=today - timedelta(days=30)
    ).order_by('last_reconciled_date')
    
    # All bank accounts for overview
    bank_accounts = BankAccount.objects.filter(is_active=True).order_by('bank_name', 'name')
    
    context = {
        'total_accounts': total_accounts,
        'unreconciled_statements': unreconciled_statements,
        'total_bank_balance': total_bank_balance,
        'unreconciled_transactions': unreconciled_transactions,
        'recent_sessions': recent_sessions,
        'recent_transactions': recent_transactions,
        'accounts_needing_reconciliation': accounts_needing_reconciliation,
        'bank_accounts': bank_accounts,
        'total_balance': total_bank_balance,  # Add this for the dashboard card
    }
    
    return render(request, 'bank_reconciliation/dashboard.html', context)


# Bank Account Views
class BankAccountListView(LoginRequiredMixin, ListView):
    """List all bank accounts."""
    model = BankAccount
    template_name = 'bank_reconciliation/account_list.html'
    context_object_name = 'accounts'
    
    def get_queryset(self):
        queryset = BankAccount.objects.annotate(
            statement_count=Count('statements'),
            unreconciled_count=Count(
                'statements__transactions',
                filter=Q(statements__transactions__reconciliation_status='unreconciled')
            )
        ).order_by('bank_name', 'name')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Filter by bank
        bank = self.request.GET.get('bank')
        if bank:
            queryset = queryset.filter(bank_name__icontains=bank)
        
        return queryset


class BankAccountDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a bank account."""
    model = BankAccount
    template_name = 'bank_reconciliation/account_detail.html'
    context_object_name = 'account'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_statements'] = self.object.statements.order_by('-statement_date')[:10]
        context['recent_transactions'] = BankTransaction.objects.filter(
            bank_statement__bank_account=self.object
        ).order_by('-transaction_date')[:20]
        context['unreconciled_count'] = BankTransaction.objects.filter(
            bank_statement__bank_account=self.object,
            reconciliation_status='unreconciled'
        ).count()
        return context


class BankAccountCreateView(LoginRequiredMixin, CreateView):
    """Create a new bank account."""
    model = BankAccount
    template_name = 'bank_reconciliation/account_form.html'
    fields = [
        'name', 'account_number', 'account_type', 'bank_name',
        'routing_number', 'opening_balance', 'current_balance', 'is_active'
    ]
    success_url = reverse_lazy('bank_reconciliation:account_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Bank account created successfully!')
        return super().form_valid(form)


class BankAccountUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing bank account."""
    model = BankAccount
    template_name = 'bank_reconciliation/account_form.html'
    fields = [
        'name', 'account_number', 'account_type', 'bank_name',
        'routing_number', 'current_balance', 'is_active'
    ]
    success_url = reverse_lazy('bank_reconciliation:account_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Bank account updated successfully!')
        return super().form_valid(form)


# Bank Statement Views
class BankStatementListView(LoginRequiredMixin, ListView):
    """List all bank statements."""
    model = BankStatement
    template_name = 'bank_reconciliation/statement_list.html'
    context_object_name = 'statements'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = BankStatement.objects.select_related(
            'bank_account', 'reconciled_by'
        ).annotate(
            transaction_count=Count('transactions')
        ).order_by('-statement_date')
        
        # Filter by account
        account = self.request.GET.get('account')
        if account:
            queryset = queryset.filter(bank_account_id=account)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by date range
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date:
            queryset = queryset.filter(statement_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(statement_date__lte=end_date)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accounts'] = BankAccount.objects.filter(is_active=True)
        context['statement_statuses'] = BankStatement.STATUS_CHOICES
        return context


class BankStatementDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a bank statement."""
    model = BankStatement
    template_name = 'bank_reconciliation/statement_detail.html'
    context_object_name = 'statement'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transactions'] = self.object.transactions.order_by('-transaction_date')
        context['reconciliation_sessions'] = self.object.reconciliation_sessions.order_by('-start_date')
        return context


class BankStatementCreateView(LoginRequiredMixin, CreateView):
    """Create/import a new bank statement."""
    model = BankStatement
    template_name = 'bank_reconciliation/statement_form.html'
    fields = [
        'bank_account', 'statement_date', 'beginning_balance', 'ending_balance',
        'statement_period_start', 'statement_period_end', 'total_deposits',
        'total_withdrawals', 'total_fees', 'notes'
    ]
    success_url = reverse_lazy('bank_reconciliation:statement_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Bank statement created successfully!')
        return super().form_valid(form)


# Bank Transaction Views
class BankTransactionListView(LoginRequiredMixin, ListView):
    """List all bank transactions."""
    model = BankTransaction
    template_name = 'bank_reconciliation/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = BankTransaction.objects.select_related(
            'bank_statement__bank_account', 'reconciled_by'
        ).order_by('-transaction_date', '-created_at')
        
        # Filter by account
        account = self.request.GET.get('account')
        if account:
            queryset = queryset.filter(bank_statement__bank_account_id=account)
        
        # Filter by reconciliation status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(reconciliation_status=status)
        
        # Filter by transaction type
        transaction_type = self.request.GET.get('transaction_type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        # Search by description
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(description__icontains=search)
        
        # Filter by amount range
        min_amount = self.request.GET.get('min_amount')
        max_amount = self.request.GET.get('max_amount')
        if min_amount:
            queryset = queryset.filter(amount__gte=min_amount)
        if max_amount:
            queryset = queryset.filter(amount__lte=max_amount)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accounts'] = BankAccount.objects.filter(is_active=True)
        context['reconciliation_statuses'] = BankTransaction.RECONCILIATION_STATUS
        context['transaction_types'] = BankTransaction.TRANSACTION_TYPES
        return context


class BankTransactionDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a bank transaction."""
    model = BankTransaction
    template_name = 'bank_reconciliation/transaction_detail.html'
    context_object_name = 'transaction'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['adjustments'] = self.object.adjustments.all()
        return context


class BankTransactionUpdateView(LoginRequiredMixin, UpdateView):
    """Update a bank transaction."""
    model = BankTransaction
    template_name = 'bank_reconciliation/transaction_form.html'
    fields = [
        'description', 'transaction_type', 'amount', 'check_number',
        'reference_number', 'reconciliation_status', 'notes'
    ]
    success_url = reverse_lazy('bank_reconciliation:transaction_list')
    
    def form_valid(self, form):
        if form.instance.reconciliation_status in ['matched', 'cleared']:
            form.instance.reconciled_date = timezone.now()
            form.instance.reconciled_by = self.request.user
        
        messages.success(self.request, 'Transaction updated successfully!')
        return super().form_valid(form)


# Reconciliation Session Views
class ReconciliationSessionListView(LoginRequiredMixin, ListView):
    """List all reconciliation sessions."""
    model = ReconciliationSession
    template_name = 'bank_reconciliation/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ReconciliationSession.objects.select_related(
            'bank_account', 'bank_statement', 'reconciled_by'
        ).order_by('-start_date')
        
        # Filter by account
        account = self.request.GET.get('account')
        if account:
            queryset = queryset.filter(bank_account_id=account)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accounts'] = BankAccount.objects.filter(is_active=True)
        context['session_statuses'] = ReconciliationSession.STATUS_CHOICES
        return context


class ReconciliationSessionDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a reconciliation session."""
    model = ReconciliationSession
    template_name = 'bank_reconciliation/session_detail.html'
    context_object_name = 'session'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['adjustments'] = self.object.adjustments.order_by('-created_at')
        return context


@login_required
def start_reconciliation(request, account_id):
    """Start a new reconciliation session."""
    account = get_object_or_404(BankAccount, id=account_id)
    
    if request.method == 'POST':
        statement_id = request.POST.get('statement_id')
        statement = get_object_or_404(BankStatement, id=statement_id)
        
        # Create new reconciliation session
        session = ReconciliationSession.objects.create(
            bank_account=account,
            bank_statement=statement,
            session_name=f"Reconciliation - {account.name} - {statement.statement_date}",
            starting_book_balance=account.current_balance,
            statement_balance=statement.ending_balance,
            reconciled_by=request.user
        )
        
        messages.success(request, 'Reconciliation session started!')
        return redirect('bank_reconciliation:reconcile_transactions', session_id=session.id)
    
    # Get unreconciled statements for this account
    statements = account.statements.filter(
        status__in=['imported', 'processing']
    ).order_by('-statement_date')
    
    context = {
        'account': account,
        'statements': statements,
    }
    
    return render(request, 'bank_reconciliation/start_reconciliation.html', context)


@login_required
def reconcile_transactions(request, session_id):
    """Reconcile transactions in a session."""
    session = get_object_or_404(ReconciliationSession, id=session_id)
    
    # Get unreconciled transactions for this statement
    transactions = session.bank_statement.transactions.filter(
        reconciliation_status='unreconciled'
    ).order_by('-transaction_date')
    
    if request.method == 'POST':
        # Process reconciliation actions
        action = request.POST.get('action')
        transaction_ids = request.POST.getlist('transaction_ids')
        
        if action == 'mark_cleared':
            BankTransaction.objects.filter(
                id__in=transaction_ids
            ).update(
                reconciliation_status='cleared',
                reconciled_date=timezone.now(),
                reconciled_by=request.user
            )
            
            session.transactions_matched += len(transaction_ids)
            session.save()
            
            messages.success(request, f'{len(transaction_ids)} transactions marked as cleared!')
        
        elif action == 'mark_disputed':
            BankTransaction.objects.filter(
                id__in=transaction_ids
            ).update(
                reconciliation_status='disputed',
                reconciled_date=timezone.now(),
                reconciled_by=request.user
            )
            
            messages.warning(request, f'{len(transaction_ids)} transactions marked as disputed!')
        
        return redirect('bank_reconciliation:reconcile_transactions', session_id=session.id)
    
    # Calculate current reconciliation status
    cleared_transactions = session.bank_statement.transactions.filter(
        reconciliation_status='cleared'
    )
    cleared_amount = cleared_transactions.aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    session.ending_book_balance = session.starting_book_balance + cleared_amount
    session.difference = session.statement_balance - session.ending_book_balance
    session.save()
    
    context = {
        'session': session,
        'transactions': transactions,
        'cleared_amount': cleared_amount,
    }
    
    return render(request, 'bank_reconciliation/reconcile_transactions.html', context)


@login_required
def complete_reconciliation(request, session_id):
    """Complete a reconciliation session."""
    session = get_object_or_404(ReconciliationSession, id=session_id)
    
    if request.method == 'POST':
        # Mark session as completed
        session.status = 'completed'
        session.end_date = timezone.now()
        
        # Update statement status
        if session.difference == 0:
            session.bank_statement.status = 'reconciled'
        else:
            session.bank_statement.status = 'discrepancy'
        
        session.bank_statement.reconciliation_date = timezone.now()
        session.bank_statement.reconciled_by = request.user
        session.bank_statement.save()
        
        # Update account reconciliation date
        session.bank_account.last_reconciled_date = session.bank_statement.statement_date
        session.bank_account.last_reconciled_balance = session.statement_balance
        session.bank_account.save()
        
        session.save()
        
        if session.difference == 0:
            messages.success(request, 'Reconciliation completed successfully!')
        else:
            messages.warning(request, f'Reconciliation completed with difference of GH₵{session.difference}')
        
        return redirect('bank_reconciliation:session_detail', pk=session.id)
    
    context = {'session': session}
    return render(request, 'bank_reconciliation/complete_reconciliation.html', context)


# Reconciliation Rule Views
class ReconciliationRuleListView(LoginRequiredMixin, ListView):
    """List all reconciliation rules."""
    model = ReconciliationRule
    template_name = 'bank_reconciliation/rule_list.html'
    context_object_name = 'rules'
    
    def get_queryset(self):
        return ReconciliationRule.objects.order_by('-created_at')


class ReconciliationRuleCreateView(LoginRequiredMixin, CreateView):
    """Create a new reconciliation rule."""
    model = ReconciliationRule
    template_name = 'bank_reconciliation/rule_form.html'
    fields = [
        'name', 'rule_type', 'description_pattern', 'amount_min', 'amount_max',
        'check_number_pattern', 'reference_pattern', 'auto_match',
        'confidence_threshold', 'is_active'
    ]
    success_url = reverse_lazy('bank_reconciliation:rule_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Reconciliation rule created successfully!')
        return super().form_valid(form)


# Import/Export Views
@login_required
def import_transactions(request, statement_id):
    """Import transactions from CSV file."""
    statement = get_object_or_404(BankStatement, id=statement_id)
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        try:
            # Read CSV file
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            transactions_created = 0
            for row in reader:
                # Create transaction from CSV row
                BankTransaction.objects.create(
                    bank_statement=statement,
                    transaction_date=datetime.strptime(row['date'], '%Y-%m-%d').date(),
                    description=row['description'],
                    transaction_type=row.get('type', 'other'),
                    amount=Decimal(row['amount']),
                    check_number=row.get('check_number', ''),
                    reference_number=row.get('reference', ''),
                )
                transactions_created += 1
            
            messages.success(request, f'Successfully imported {transactions_created} transactions!')
            return redirect('bank_reconciliation:statement_detail', pk=statement.id)
            
        except Exception as e:
            messages.error(request, f'Error importing transactions: {str(e)}')
    
    context = {'statement': statement}
    return render(request, 'bank_reconciliation/import_transactions.html', context)


@login_required
def export_transactions(request, account_id):
    """Export transactions to CSV."""
    account = get_object_or_404(BankAccount, id=account_id)
    
    # Get date range from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    transactions = BankTransaction.objects.filter(
        bank_statement__bank_account=account
    ).order_by('-transaction_date')
    
    if start_date:
        transactions = transactions.filter(transaction_date__gte=start_date)
    if end_date:
        transactions = transactions.filter(transaction_date__lte=end_date)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="transactions_{account.name}_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Date', 'Description', 'Type', 'Amount', 'Check Number',
        'Reference', 'Status', 'Running Balance'
    ])
    
    for transaction in transactions:
        writer.writerow([
            transaction.transaction_date,
            transaction.description,
            transaction.get_transaction_type_display(),
            transaction.amount,
            transaction.check_number,
            transaction.reference_number,
            transaction.get_reconciliation_status_display(),
            transaction.running_balance or ''
        ])
    
    return response


# AJAX Views
@login_required
def mark_transaction_cleared(request, transaction_id):
    """Mark a transaction as cleared via AJAX."""
    if request.method == 'POST':
        transaction = get_object_or_404(BankTransaction, id=transaction_id)
        
        transaction.reconciliation_status = 'cleared'
        transaction.reconciled_date = timezone.now()
        transaction.reconciled_by = request.user
        transaction.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Transaction marked as cleared!'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
def auto_match_transactions(request, session_id):
    """Automatically match transactions using rules."""
    session = get_object_or_404(ReconciliationSession, id=session_id)
    
    # Get active reconciliation rules
    rules = ReconciliationRule.objects.filter(is_active=True)
    unreconciled_transactions = session.bank_statement.transactions.filter(
        reconciliation_status='unreconciled'
    )
    
    matched_count = 0
    
    for transaction in unreconciled_transactions:
        for rule in rules:
            match_confidence = 0
            
            # Apply rule logic based on rule type
            if rule.rule_type == 'description_contains':
                if rule.description_pattern.lower() in transaction.description.lower():
                    match_confidence = 90
            elif rule.rule_type == 'amount_exact':
                if rule.amount_min <= transaction.amount <= rule.amount_max:
                    match_confidence = 95
            # Add more rule types as needed
            
            if match_confidence >= rule.confidence_threshold:
                if rule.auto_match:
                    transaction.reconciliation_status = 'matched'
                    transaction.reconciled_date = timezone.now()
                    transaction.reconciled_by = request.user
                    transaction.save()
                    matched_count += 1
                break
    
    return JsonResponse({
        'success': True,
        'message': f'Automatically matched {matched_count} transactions!',
        'matched_count': matched_count
    })


@login_required
def unreconciled_count(request):
    """API endpoint to get the count of unreconciled transactions."""
    count = BankTransaction.objects.filter(
        reconciliation_status='unreconciled'
    ).count()
    
    return JsonResponse({'count': count})
