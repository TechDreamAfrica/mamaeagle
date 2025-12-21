"""
Common utility functions for DreamBiz Accounting
Shared functions used across multiple modules
"""

from decimal import Decimal


def calculate_percentage_change(old_value, new_value):
    """
    Calculate percentage change between two values
    
    Args:
        old_value: Previous value
        new_value: Current value
    
    Returns:
        float: Percentage change rounded to 2 decimal places
    """
    # Convert to Decimal for precise calculations
    old_value = Decimal(str(old_value)) if old_value else Decimal('0')
    new_value = Decimal(str(new_value)) if new_value else Decimal('0')
    
    if old_value == 0:
        return 100 if new_value > 0 else 0
    
    change = ((new_value - old_value) / old_value) * 100
    return float(round(change, 2))


def format_currency(amount, currency_symbol='GH'):
    """
    Format decimal amount as currency string
    
    Args:
        amount: Decimal or float amount
        currency_symbol: Currency symbol prefix
    
    Returns:
        str: Formatted currency string
    """
    if amount is None:
        amount = 0
    
    amount = Decimal(str(amount))
    return f"{currency_symbol}₵{amount:,.2f}"


def safe_divide(numerator, denominator, default=0):
    """
    Safely divide two numbers, returning default if denominator is zero
    
    Args:
        numerator: Number to divide
        denominator: Number to divide by
        default: Value to return if denominator is zero
    
    Returns:
        Decimal: Result of division or default value
    """
    numerator = Decimal(str(numerator)) if numerator else Decimal('0')
    denominator = Decimal(str(denominator)) if denominator else Decimal('0')
    
    if denominator == 0:
        return Decimal(str(default))
    
    return numerator / denominator