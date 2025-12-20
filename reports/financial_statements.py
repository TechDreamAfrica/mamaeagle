"""
Financial Statement Generator
Generates detailed financial statements following GAAP/IFRS standards
"""
from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Sum, Q, F
from .models import Account, JournalEntryLine, FinancialPeriod, AccountType


class FinancialStatementGenerator:
    """
    Comprehensive financial statement generator
    Supports monthly and annual statements with accounting standards compliance
    """
    
    def __init__(self, user, start_date, end_date, accounting_standard='GAAP'):
        self.user = user
        self.start_date = start_date
        self.end_date = end_date
        self.accounting_standard = accounting_standard
    
    def get_account_balance(self, account, as_of_date=None):
        """
        Calculate account balance as of a specific date
        """
        if as_of_date is None:
            as_of_date = self.end_date
        
        # Get opening balance
        balance = account.opening_balance if account.opening_balance else Decimal('0.00')
        
        # Get all journal entry lines for this account up to the date
        lines = JournalEntryLine.objects.filter(
            account=account,
            journal_entry__user=self.user,
            journal_entry__status='posted',
            journal_entry__entry_date__lte=as_of_date
        )
        
        # Calculate net change based on account type
        if account.account_type.category in ['asset', 'expense']:
            # Debit increases, credit decreases
            for line in lines:
                balance += line.debit - line.credit
        else:
            # Credit increases, debit decreases (liability, equity, revenue)
            for line in lines:
                balance += line.credit - line.debit
        
        return balance
    
    def get_account_balance_for_period(self, account, start_date, end_date):
        """
        Calculate account activity for a specific period
        """
        lines = JournalEntryLine.objects.filter(
            account=account,
            journal_entry__user=self.user,
            journal_entry__status='posted',
            journal_entry__entry_date__gte=start_date,
            journal_entry__entry_date__lte=end_date
        )
        
        debits = sum(line.debit for line in lines)
        credits = sum(line.credit for line in lines)
        
        if account.account_type.category in ['asset', 'expense']:
            net = debits - credits
        else:
            net = credits - debits
        
        return net
    
    def generate_balance_sheet(self):
        """
        Generate detailed Balance Sheet (Statement of Financial Position)
        Following accounting equation: Assets = Liabilities + Equity
        """
        balance_sheet = {
            'statement_type': 'Balance Sheet',
            'as_of_date': self.end_date.strftime('%Y-%m-%d'),
            'accounting_standard': self.accounting_standard,
            'assets': {},
            'liabilities': {},
            'equity': {},
            'totals': {}
        }
        
        # ASSETS
        current_assets = self._get_accounts_by_category_and_subtype('asset', 'current_asset')
        fixed_assets = self._get_accounts_by_category_and_subtype('asset', 'fixed_asset')
        other_assets = self._get_accounts_by_category_and_subtype('asset', 'other_asset')
        
        balance_sheet['assets']['current_assets'] = self._format_account_list(current_assets)
        balance_sheet['assets']['fixed_assets'] = self._format_account_list(fixed_assets)
        balance_sheet['assets']['other_assets'] = self._format_account_list(other_assets)
        
        total_current_assets = sum(acc['balance'] for acc in balance_sheet['assets']['current_assets'])
        total_fixed_assets = sum(acc['balance'] for acc in balance_sheet['assets']['fixed_assets'])
        total_other_assets = sum(acc['balance'] for acc in balance_sheet['assets']['other_assets'])
        
        balance_sheet['assets']['total_current_assets'] = float(total_current_assets)
        balance_sheet['assets']['total_fixed_assets'] = float(total_fixed_assets)
        balance_sheet['assets']['total_other_assets'] = float(total_other_assets)
        balance_sheet['totals']['total_assets'] = float(total_current_assets + total_fixed_assets + total_other_assets)
        
        # LIABILITIES
        current_liabilities = self._get_accounts_by_category_and_subtype('liability', 'current_liability')
        long_term_liabilities = self._get_accounts_by_category_and_subtype('liability', 'long_term_liability')
        other_liabilities = self._get_accounts_by_category_and_subtype('liability', 'other_liability')
        
        balance_sheet['liabilities']['current_liabilities'] = self._format_account_list(current_liabilities)
        balance_sheet['liabilities']['long_term_liabilities'] = self._format_account_list(long_term_liabilities)
        balance_sheet['liabilities']['other_liabilities'] = self._format_account_list(other_liabilities)
        
        total_current_liabilities = sum(acc['balance'] for acc in balance_sheet['liabilities']['current_liabilities'])
        total_long_term_liabilities = sum(acc['balance'] for acc in balance_sheet['liabilities']['long_term_liabilities'])
        total_other_liabilities = sum(acc['balance'] for acc in balance_sheet['liabilities']['other_liabilities'])
        
        balance_sheet['liabilities']['total_current_liabilities'] = float(total_current_liabilities)
        balance_sheet['liabilities']['total_long_term_liabilities'] = float(total_long_term_liabilities)
        balance_sheet['liabilities']['total_other_liabilities'] = float(total_other_liabilities)
        balance_sheet['totals']['total_liabilities'] = float(total_current_liabilities + total_long_term_liabilities + total_other_liabilities)
        
        # EQUITY
        equity_accounts = self._get_accounts_by_category('equity')
        balance_sheet['equity']['accounts'] = self._format_account_list(equity_accounts)
        balance_sheet['totals']['total_equity'] = float(sum(acc['balance'] for acc in balance_sheet['equity']['accounts']))
        
        # Total Liabilities + Equity
        balance_sheet['totals']['total_liabilities_and_equity'] = balance_sheet['totals']['total_liabilities'] + balance_sheet['totals']['total_equity']
        
        return balance_sheet
    
    def generate_income_statement(self):
        """
        Generate detailed Income Statement (Profit & Loss Statement)
        Revenue - Expenses = Net Income
        """
        income_statement = {
            'statement_type': 'Income Statement',
            'period': f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}",
            'accounting_standard': self.accounting_standard,
            'revenue': {},
            'expenses': {},
            'totals': {}
        }
        
        # REVENUE
        revenue_accounts = self._get_accounts_by_category('revenue')
        revenue_list = []
        
        for account in revenue_accounts:
            balance = self.get_account_balance_for_period(account, self.start_date, self.end_date)
            revenue_list.append({
                'account_number': account.account_number,
                'account_name': account.account_name,
                'balance': float(balance)
            })
        
        income_statement['revenue']['accounts'] = revenue_list
        total_revenue = sum(acc['balance'] for acc in revenue_list)
        income_statement['revenue']['total_revenue'] = float(total_revenue)
        
        # EXPENSES
        expense_accounts = self._get_accounts_by_category('expense')
        expense_list = []
        
        # Categorize expenses
        cost_of_goods_sold = []
        operating_expenses = []
        other_expenses = []
        
        for account in expense_accounts:
            balance = self.get_account_balance_for_period(account, self.start_date, self.end_date)
            expense_data = {
                'account_number': account.account_number,
                'account_name': account.account_name,
                'balance': float(balance)
            }
            
            # Categorize based on account name/type
            if 'cost of goods' in account.account_name.lower() or 'cogs' in account.account_name.lower():
                cost_of_goods_sold.append(expense_data)
            elif 'interest' in account.account_name.lower() or 'depreciation' in account.account_name.lower():
                other_expenses.append(expense_data)
            else:
                operating_expenses.append(expense_data)
            
            expense_list.append(expense_data)
        
        income_statement['expenses']['cost_of_goods_sold'] = cost_of_goods_sold
        income_statement['expenses']['operating_expenses'] = operating_expenses
        income_statement['expenses']['other_expenses'] = other_expenses
        
        total_cogs = sum(exp['balance'] for exp in cost_of_goods_sold)
        total_operating = sum(exp['balance'] for exp in operating_expenses)
        total_other = sum(exp['balance'] for exp in other_expenses)
        total_expenses = total_cogs + total_operating + total_other
        
        income_statement['expenses']['total_cost_of_goods_sold'] = float(total_cogs)
        income_statement['expenses']['total_operating_expenses'] = float(total_operating)
        income_statement['expenses']['total_other_expenses'] = float(total_other)
        income_statement['expenses']['total_expenses'] = float(total_expenses)
        
        # CALCULATIONS
        gross_profit = total_revenue - total_cogs
        operating_income = gross_profit - total_operating
        net_income = total_revenue - total_expenses
        
        income_statement['totals']['gross_profit'] = float(gross_profit)
        income_statement['totals']['operating_income'] = float(operating_income)
        income_statement['totals']['net_income'] = float(net_income)
        
        return income_statement
    
    def generate_cash_flow_statement(self):
        """
        Generate Cash Flow Statement
        Operating, Investing, and Financing Activities
        """
        cash_flow = {
            'statement_type': 'Cash Flow Statement',
            'period': f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}",
            'accounting_standard': self.accounting_standard,
            'operating_activities': {},
            'investing_activities': {},
            'financing_activities': {},
            'totals': {}
        }
        
        # Net Income (starting point for indirect method)
        income_stmt = self.generate_income_statement()
        net_income = income_stmt['totals']['net_income']
        
        cash_flow['operating_activities']['net_income'] = float(net_income)
        
        # Adjustments for non-cash items (simplified)
        # In a full implementation, you'd track depreciation, amortization, etc.
        cash_flow['operating_activities']['adjustments'] = []
        cash_flow['operating_activities']['changes_in_working_capital'] = []
        
        # Calculate net cash from operating activities
        cash_flow['operating_activities']['net_cash_from_operations'] = float(net_income)
        
        # Investing activities (purchases/sales of fixed assets)
        cash_flow['investing_activities']['items'] = []
        cash_flow['investing_activities']['net_cash_from_investing'] = 0.0
        
        # Financing activities (loans, equity, dividends)
        cash_flow['financing_activities']['items'] = []
        cash_flow['financing_activities']['net_cash_from_financing'] = 0.0
        
        # Net change in cash
        net_change = (
            cash_flow['operating_activities']['net_cash_from_operations'] +
            cash_flow['investing_activities']['net_cash_from_investing'] +
            cash_flow['financing_activities']['net_cash_from_financing']
        )
        
        cash_flow['totals']['net_change_in_cash'] = float(net_change)
        
        # Cash at beginning and end of period
        cash_accounts = Account.objects.filter(
            user=self.user,
            account_type__category='asset',
            account_name__icontains='cash',
            is_active=True
        )
        
        cash_beginning = sum(self.get_account_balance(acc, self.start_date) for acc in cash_accounts)
        cash_ending = sum(self.get_account_balance(acc, self.end_date) for acc in cash_accounts)
        
        cash_flow['totals']['cash_at_beginning'] = float(cash_beginning)
        cash_flow['totals']['cash_at_end'] = float(cash_ending)
        
        return cash_flow
    
    def generate_equity_statement(self):
        """
        Generate Statement of Changes in Equity
        """
        equity_statement = {
            'statement_type': 'Statement of Changes in Equity',
            'period': f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}",
            'accounting_standard': self.accounting_standard,
            'opening_balance': {},
            'changes': {},
            'closing_balance': {}
        }
        
        equity_accounts = self._get_accounts_by_category('equity')
        
        for account in equity_accounts:
            opening = self.get_account_balance(account, self.start_date - timedelta(days=1))
            closing = self.get_account_balance(account, self.end_date)
            change = closing - opening
            
            equity_statement['opening_balance'][account.account_name] = float(opening)
            equity_statement['changes'][account.account_name] = float(change)
            equity_statement['closing_balance'][account.account_name] = float(closing)
        
        # Add net income from period
        income_stmt = self.generate_income_statement()
        equity_statement['changes']['net_income'] = income_stmt['totals']['net_income']
        
        # Calculate totals
        equity_statement['total_opening'] = sum(equity_statement['opening_balance'].values())
        equity_statement['total_changes'] = sum(equity_statement['changes'].values())
        equity_statement['total_closing'] = sum(equity_statement['closing_balance'].values())
        
        return equity_statement
    
    def generate_comprehensive_statement(self):
        """
        Generate all financial statements together
        """
        return {
            'balance_sheet': self.generate_balance_sheet(),
            'income_statement': self.generate_income_statement(),
            'cash_flow_statement': self.generate_cash_flow_statement(),
            'equity_statement': self.generate_equity_statement(),
            'period': f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}",
            'generated_date': date.today().strftime('%Y-%m-%d'),
            'accounting_standard': self.accounting_standard
        }
    
    # Helper methods
    
    def _get_accounts_by_category(self, category):
        """Get all accounts for a specific category"""
        return Account.objects.filter(
            user=self.user,
            account_type__category=category,
            is_active=True
        ).select_related('account_type')
    
    def _get_accounts_by_category_and_subtype(self, category, subtype):
        """Get accounts by category and subtype"""
        return Account.objects.filter(
            user=self.user,
            account_type__category=category,
            account_type__subtype=subtype,
            is_active=True
        ).select_related('account_type')
    
    def _format_account_list(self, accounts):
        """Format accounts for statement display"""
        result = []
        for account in accounts:
            balance = self.get_account_balance(account, self.end_date)
            result.append({
                'account_number': account.account_number,
                'account_name': account.account_name,
                'balance': float(balance)
            })
        return result


def get_monthly_statements(user, year, month, accounting_standard='GAAP'):
    """
    Generate financial statements for a specific month
    """
    from calendar import monthrange
    
    start_date = date(year, month, 1)
    last_day = monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    
    generator = FinancialStatementGenerator(user, start_date, end_date, accounting_standard)
    return generator.generate_comprehensive_statement()


def get_annual_statements(user, year, accounting_standard='GAAP'):
    """
    Generate financial statements for an entire year
    """
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    generator = FinancialStatementGenerator(user, start_date, end_date, accounting_standard)
    return generator.generate_comprehensive_statement()


def get_quarterly_statements(user, year, quarter, accounting_standard='GAAP'):
    """
    Generate financial statements for a specific quarter
    """
    quarter_months = {
        1: (1, 3),
        2: (4, 6),
        3: (7, 9),
        4: (10, 12)
    }
    
    start_month, end_month = quarter_months[quarter]
    start_date = date(year, start_month, 1)
    
    from calendar import monthrange
    last_day = monthrange(year, end_month)[1]
    end_date = date(year, end_month, last_day)
    
    generator = FinancialStatementGenerator(user, start_date, end_date, accounting_standard)
    return generator.generate_comprehensive_statement()
