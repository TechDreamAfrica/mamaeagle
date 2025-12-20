from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class DashboardWidget(models.Model):
    """
    Customizable dashboard widgets
    Superior to QuickBooks' fixed dashboard layout
    """
    WIDGET_TYPES = [
        ('revenue_chart', 'Revenue Chart'),
        ('expense_chart', 'Expense Chart'),
        ('invoice_status', 'Invoice Status'),
        ('cash_flow', 'Cash Flow'),
        ('top_customers', 'Top Customers'),
        ('recent_transactions', 'Recent Transactions'),
        ('ai_insights', 'AI Insights'),
        ('kpi_metrics', 'KPI Metrics'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    widget_type = models.CharField(max_length=50, choices=WIDGET_TYPES)
    title = models.CharField(max_length=200)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=6)  # Grid columns (out of 12)
    height = models.IntegerField(default=4)  # Grid rows
    is_visible = models.BooleanField(default=True)
    settings = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    class Meta:
        ordering = ['position_y', 'position_x']


class Notification(models.Model):
    """
    System notifications for users
    Enhanced notification system vs QuickBooks
    """
    NOTIFICATION_TYPES = [
        ('invoice_overdue', 'Invoice Overdue'),
        ('payment_received', 'Payment Received'),
        ('expense_approval', 'Expense Approval Required'),
        ('ai_insight', 'AI Insight'),
        ('system_update', 'System Update'),
        ('security_alert', 'Security Alert'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='medium')
    is_read = models.BooleanField(default=False)
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    class Meta:
        ordering = ['-created_at']


class QuickAction(models.Model):
    """
    Quick action shortcuts for dashboard
    Customizable vs QuickBooks' limited shortcuts
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-plus')
    url = models.URLField()
    color = models.CharField(max_length=20, default='blue')
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    class Meta:
        ordering = ['order', 'name']
