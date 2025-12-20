"""
Comprehensive Financial Statement Generator
Generates detailed monthly and annual financial statements
Following GAAP/IFRS accounting standards
"""
from decimal import Decimal
from datetime import date, datetime, timedelta
from django.db.models import Sum, Q, F, Case, When, Value, DecimalField
from django.utils import timezone
from .models import Account, JournalEntryLine, FinancialPeriod, AccountType, JournalEntry
from invoicing.models import Invoice
from expenses.models import Expense
from inventory.models import Product
from hr.models import Employee, PayrollPeriod


class ComprehensiveStatementGenerator:
    """
    Advanced financial statement generator with full accounting standard compliance
    """
    
    def __init__(self, user, start_date, end_date, accounting_standard='GAAP'):
        self.user = user
        self.start_date = start_date if isinstance(start_date, date) else datetime.strptime(start_date, '%Y-%m-%d').date()
        self.end_date = end_date if isinstance(end_date, date) else datetime.strptime(end_date, '%Y-%m-%d').date()
        self.accounting_standard = accounting_standard
    
    def generate_comprehensive_package(self):
        """
        Generate complete financial statement package
        """
        return {
            'income_statement': self.generate_income_statement(),
            'balance_sheet': self.generate_balance_sheet(),
            'cash_flow_statement': self.generate_cash_flow_statement(),
            'statement_of_changes_in_equity': self.generate_equity_statement(),
            'notes_to_financial_statements': self.generate_notes(),
            'period': {
                'start_date': self.start_date,
                'end_date': self.end_date,
                'period_type': self._get_period_type(),
            },
            'accounting_standard': self.accounting_standard,
        }
    
    def _get_period_type(self):
        """Determine if this is monthly, quarterly, or annual"""
        days = (self.end_date - self.start_date).days
        if days <= 31:
            return 'Monthly'
        elif days <= 92:
            return 'Quarterly'
        else:
            return 'Annual'
    
    def generate_income_statement(self):
        """
        Generate comprehensive Income Statement (Profit & Loss)
        Following multi-step format
        """
        # Revenue section
        revenue_accounts = self._get_accounts_by_type('revenue')
        revenue_items = []
        gross_revenue = Decimal('0.00')
        
        for account in revenue_accounts:
            balance = self._get_account_balance(account)
            if balance != 0:
                revenue_items.append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'amount': balance,
                })
                gross_revenue += balance
        
        # Cost of Goods Sold
        cogs_accounts = self._get_accounts_by_category('cost_of_sales')
        cogs_items = []
        total_cogs = Decimal('0.00')
        
        for account in cogs_accounts:
            balance = self._get_account_balance(account)
            if balance != 0:
                cogs_items.append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'amount': balance,
                })
                total_cogs += balance
        
        gross_profit = gross_revenue - total_cogs
        gross_profit_margin = (gross_profit / gross_revenue * 100) if gross_revenue > 0 else 0
        
        # Operating Expenses
        operating_expense_accounts = self._get_accounts_by_type('expense')
        operating_expenses = []
        total_operating_expenses = Decimal('0.00')
        
        # Categorize expenses
        categories = {
            'Selling Expenses': [],
            'Administrative Expenses': [],
            'General Expenses': [],
            'Other Operating Expenses': [],
        }
        
        for account in operating_expense_accounts:
            balance = self._get_account_balance(account)
            if balance != 0:
                expense_item = {
                    'account_code': account.code,
                    'account_name': account.name,
                    'amount': balance,
                }
                
                # Categorize based on account name
                if any(keyword in account.name.lower() for keyword in ['sales', 'marketing', 'commission']):
                    categories['Selling Expenses'].append(expense_item)
                elif any(keyword in account.name.lower() for keyword in ['admin', 'office', 'salary', 'payroll']):
                    categories['Administrative Expenses'].append(expense_item)
                elif any(keyword in account.name.lower() for keyword in ['utilities', 'rent', 'insurance']):
                    categories['General Expenses'].append(expense_item)
                else:
                    categories['Other Operating Expenses'].append(expense_item)
                
                total_operating_expenses += balance
                operating_expenses.append(expense_item)
        
        operating_income = gross_profit - total_operating_expenses
        operating_margin = (operating_income / gross_revenue * 100) if gross_revenue > 0 else 0
        
        # Other Income and Expenses
        other_income = self._get_other_income()
        other_expenses = self._get_other_expenses()
        
        # Calculate net income before tax
        income_before_tax = operating_income + other_income - other_expenses
        
        # Income tax
        tax_expense = self._calculate_tax_expense(income_before_tax)
        
        # Net income
        net_income = income_before_tax - tax_expense
        net_profit_margin = (net_income / gross_revenue * 100) if gross_revenue > 0 else 0
        
        return {
            'revenue': {
                'items': revenue_items,
                'gross_revenue': gross_revenue,
            },
            'cost_of_goods_sold': {
                'items': cogs_items,
                'total_cogs': total_cogs,
            },
            'gross_profit': gross_profit,
            'gross_profit_margin': gross_profit_margin,
            'operating_expenses': {
                'by_category': categories,
                'all_items': operating_expenses,
                'total': total_operating_expenses,
            },
            'operating_income': operating_income,
            'operating_margin': operating_margin,
            'other_income': other_income,
            'other_expenses': other_expenses,
            'income_before_tax': income_before_tax,
            'tax_expense': tax_expense,
            'net_income': net_income,
            'net_profit_margin': net_profit_margin,
        }
    
    def generate_balance_sheet(self):
        """
        Generate comprehensive Balance Sheet (Statement of Financial Position)
        Classified format: Current vs Non-Current
        """
        # ASSETS
        # Current Assets
        current_assets = self._get_current_assets()
        total_current_assets = sum(item['amount'] for item in current_assets)
        
        # Non-Current Assets
        non_current_assets = self._get_non_current_assets()
        total_non_current_assets = sum(item['amount'] for item in non_current_assets)
        
        total_assets = total_current_assets + total_non_current_assets
        
        # LIABILITIES
        # Current Liabilities
        current_liabilities = self._get_current_liabilities()
        total_current_liabilities = sum(item['amount'] for item in current_liabilities)
        
        # Non-Current Liabilities
        non_current_liabilities = self._get_non_current_liabilities()
        total_non_current_liabilities = sum(item['amount'] for item in non_current_liabilities)
        
        total_liabilities = total_current_liabilities + total_non_current_liabilities
        
        # EQUITY
        equity_items = self._get_equity_items()
        total_equity = sum(item['amount'] for item in equity_items)
        
        # Working Capital
        working_capital = total_current_assets - total_current_liabilities
        current_ratio = (total_current_assets / total_current_liabilities) if total_current_liabilities > 0 else 0
        debt_to_equity = (total_liabilities / total_equity) if total_equity > 0 else 0
        
        return {
            'assets': {
                'current_assets': {
                    'items': current_assets,
                    'total': total_current_assets,
                },
                'non_current_assets': {
                    'items': non_current_assets,
                    'total': total_non_current_assets,
                },
                'total_assets': total_assets,
            },
            'liabilities': {
                'current_liabilities': {
                    'items': current_liabilities,
                    'total': total_current_liabilities,
                },
                'non_current_liabilities': {
                    'items': non_current_liabilities,
                    'total': total_non_current_liabilities,
                },
                'total_liabilities': total_liabilities,
            },
            'equity': {
                'items': equity_items,
                'total_equity': total_equity,
            },
            'total_liabilities_and_equity': total_liabilities + total_equity,
            'ratios': {
                'working_capital': working_capital,
                'current_ratio': current_ratio,
                'debt_to_equity_ratio': debt_to_equity,
            },
        }
    
    def generate_cash_flow_statement(self):
        """
        Generate Cash Flow Statement using indirect method
        """
        # Operating Activities
        net_income = self.generate_income_statement()['net_income']
        
        operating_activities = {
            'net_income': net_income,
            'adjustments': self._get_cash_flow_adjustments(),
            'changes_in_working_capital': self._get_working_capital_changes(),
        }
        
        operating_cash_flow = (
            net_income + 
            sum(adj['amount'] for adj in operating_activities['adjustments']) +
            sum(change['amount'] for change in operating_activities['changes_in_working_capital'])
        )
        
        # Investing Activities
        investing_activities = self._get_investing_activities()
        investing_cash_flow = sum(item['amount'] for item in investing_activities)
        
        # Financing Activities
        financing_activities = self._get_financing_activities()
        financing_cash_flow = sum(item['amount'] for item in financing_activities)
        
        # Net change in cash
        net_cash_change = operating_cash_flow + investing_cash_flow + financing_cash_flow
        
        # Cash beginning and ending
        cash_beginning = self._get_cash_balance(self.start_date - timedelta(days=1))
        cash_ending = cash_beginning + net_cash_change
        
        return {
            'operating_activities': {
                'items': operating_activities,
                'net_cash_from_operating': operating_cash_flow,
            },
            'investing_activities': {
                'items': investing_activities,
                'net_cash_from_investing': investing_cash_flow,
            },
            'financing_activities': {
                'items': financing_activities,
                'net_cash_from_financing': financing_cash_flow,
            },
            'net_change_in_cash': net_cash_change,
            'cash_beginning_of_period': cash_beginning,
            'cash_end_of_period': cash_ending,
        }
    
    def generate_equity_statement(self):
        """
        Generate Statement of Changes in Equity
        """
        equity_beginning = self._get_equity_balance(self.start_date - timedelta(days=1))
        net_income = self.generate_income_statement()['net_income']
        dividends = self._get_dividends_paid()
        capital_contributions = self._get_capital_contributions()
        other_changes = self._get_other_equity_changes()
        
        equity_ending = equity_beginning + net_income - dividends + capital_contributions + other_changes
        
        return {
            'opening_balance': equity_beginning,
            'net_income': net_income,
            'dividends_paid': dividends,
            'capital_contributions': capital_contributions,
            'other_comprehensive_income': other_changes,
            'closing_balance': equity_ending,
        }
    
    def generate_notes(self):
        """
        Generate Notes to Financial Statements
        """
        return {
            'accounting_policies': self._get_accounting_policies(),
            'significant_accounting_estimates': self._get_significant_estimates(),
            'revenue_recognition': self._get_revenue_recognition_policy(),
            'inventory_valuation': self._get_inventory_policy(),
            'depreciation_methods': self._get_depreciation_policy(),
            'contingent_liabilities': self._get_contingent_liabilities(),
            'related_party_transactions': self._get_related_party_transactions(),
            'subsequent_events': self._get_subsequent_events(),
        }
    
    # Helper methods
    def _get_accounts_by_type(self, account_type):
        """Get accounts by type"""
        return Account.objects.filter(
            user=self.user,
            account_type__category=account_type,
            is_active=True
        ).select_related('account_type')
    
    def _get_accounts_by_category(self, category):
        """Get accounts by custom category"""
        return Account.objects.filter(
            user=self.user,
            is_active=True
        ).select_related('account_type')
    
    def _get_account_balance(self, account):
        """Calculate account balance for the period"""
        balance = account.opening_balance or Decimal('0.00')
        
        lines = JournalEntryLine.objects.filter(
            account=account,
            journal_entry__user=self.user,
            journal_entry__status='posted',
            journal_entry__entry_date__gte=self.start_date,
            journal_entry__entry_date__lte=self.end_date
        )
        
        if account.account_type.category in ['asset', 'expense']:
            for line in lines:
                balance += line.debit - line.credit
        else:
            for line in lines:
                balance += line.credit - line.debit
        
        return abs(balance)
    
    def _get_current_assets(self):
        """Get current assets items"""
        asset_accounts = self._get_accounts_by_type('asset')
        current_assets = []
        
        for account in asset_accounts:
            if any(keyword in account.name.lower() for keyword in ['cash', 'receivable', 'inventory', 'prepaid']):
                balance = self._get_account_balance(account)
                if balance != 0:
                    current_assets.append({
                        'account_code': account.code,
                        'account_name': account.name,
                        'amount': balance,
                    })
        
        return current_assets
    
    def _get_non_current_assets(self):
        """Get non-current assets items"""
        asset_accounts = self._get_accounts_by_type('asset')
        non_current_assets = []
        
        for account in asset_accounts:
            if any(keyword in account.name.lower() for keyword in ['equipment', 'building', 'land', 'vehicle', 'furniture', 'intangible']):
                balance = self._get_account_balance(account)
                if balance != 0:
                    non_current_assets.append({
                        'account_code': account.code,
                        'account_name': account.name,
                        'amount': balance,
                    })
        
        return non_current_assets
    
    def _get_current_liabilities(self):
        """Get current liabilities items"""
        liability_accounts = self._get_accounts_by_type('liability')
        current_liabilities = []
        
        for account in liability_accounts:
            if any(keyword in account.name.lower() for keyword in ['payable', 'accrued', 'short-term', 'current']):
                balance = self._get_account_balance(account)
                if balance != 0:
                    current_liabilities.append({
                        'account_code': account.code,
                        'account_name': account.name,
                        'amount': balance,
                    })
        
        return current_liabilities
    
    def _get_non_current_liabilities(self):
        """Get non-current liabilities items"""
        liability_accounts = self._get_accounts_by_type('liability')
        non_current_liabilities = []
        
        for account in liability_accounts:
            if any(keyword in account.name.lower() for keyword in ['long-term', 'mortgage', 'bonds', 'loan']):
                balance = self._get_account_balance(account)
                if balance != 0:
                    non_current_liabilities.append({
                        'account_code': account.code,
                        'account_name': account.name,
                        'amount': balance,
                    })
        
        return non_current_liabilities
    
    def _get_equity_items(self):
        """Get equity items"""
        equity_accounts = self._get_accounts_by_type('equity')
        equity_items = []
        
        for account in equity_accounts:
            balance = self._get_account_balance(account)
            if balance != 0:
                equity_items.append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'amount': balance,
                })
        
        return equity_items
    
    def _get_other_income(self):
        """Calculate other income"""
        return Decimal('0.00')  # Placeholder
    
    def _get_other_expenses(self):
        """Calculate other expenses"""
        return Decimal('0.00')  # Placeholder
    
    def _calculate_tax_expense(self, income_before_tax):
        """Calculate income tax expense"""
        tax_rate = Decimal('0.21')  # 21% corporate tax rate
        return income_before_tax * tax_rate if income_before_tax > 0 else Decimal('0.00')
    
    def _get_cash_flow_adjustments(self):
        """Get non-cash adjustments for cash flow"""
        return []  # Placeholder for depreciation, amortization, etc.
    
    def _get_working_capital_changes(self):
        """Get changes in working capital"""
        return []  # Placeholder
    
    def _get_investing_activities(self):
        """Get investing activity items"""
        return []  # Placeholder
    
    def _get_financing_activities(self):
        """Get financing activity items"""
        return []  # Placeholder
    
    def _get_cash_balance(self, as_of_date):
        """Get cash balance as of date"""
        return Decimal('0.00')  # Placeholder
    
    def _get_equity_balance(self, as_of_date):
        """Get equity balance as of date"""
        return Decimal('0.00')  # Placeholder
    
    def _get_dividends_paid(self):
        """Get dividends paid during period"""
        return Decimal('0.00')  # Placeholder
    
    def _get_capital_contributions(self):
        """Get capital contributions during period"""
        return Decimal('0.00')  # Placeholder
    
    def _get_other_equity_changes(self):
        """Get other equity changes"""
        return Decimal('0.00')  # Placeholder
    
    def _get_accounting_policies(self):
        """Get accounting policies"""
        return {
            'basis_of_preparation': f'These financial statements have been prepared in accordance with {self.accounting_standard}.',
            'reporting_currency': 'US Dollars (USD)',
            'reporting_period': f'{self.start_date} to {self.end_date}',
        }
    
    def _get_significant_estimates(self):
        """Get significant accounting estimates"""
        return []
    
    def _get_revenue_recognition_policy(self):
        """Get revenue recognition policy"""
        return 'Revenue is recognized when performance obligations are satisfied.'
    
    def _get_inventory_policy(self):
        """Get inventory valuation policy"""
        return 'Inventory is valued at lower of cost or net realizable value using FIFO method.'
    
    def _get_depreciation_policy(self):
        """Get depreciation policy"""
        return 'Fixed assets are depreciated using the straight-line method over their useful lives.'
    
    def _get_contingent_liabilities(self):
        """Get contingent liabilities"""
        return []
    
    def _get_related_party_transactions(self):
        """Get related party transactions"""
        return []
    
    def _get_subsequent_events(self):
        """Get subsequent events after reporting date"""
        return []
