from django.db import models
from django.contrib.auth import get_user_model
import json

User = get_user_model()


class AIInsight(models.Model):
    """
    AI-generated insights for accounting data
    Revolutionary feature not available in QuickBooks
    """
    INSIGHT_TYPES = [
        ('cash_flow_prediction', 'Cash Flow Prediction'),
        ('expense_anomaly', 'Expense Anomaly Detection'),
        ('revenue_forecast', 'Revenue Forecast'),
        ('customer_risk', 'Customer Risk Assessment'),
        ('cost_optimization', 'Cost Optimization'),
        ('tax_optimization', 'Tax Optimization'),
        ('trend_analysis', 'Trend Analysis'),
        ('budget_variance', 'Budget Variance Analysis'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    insight_type = models.CharField(max_length=50, choices=INSIGHT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # AI analysis data
    data_points = models.JSONField(default=dict)
    confidence_score = models.FloatField(default=0)  # 0-1
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='medium')
    
    # Recommendations
    recommendations = models.JSONField(default=list)
    potential_impact = models.TextField(blank=True)
    
    # User interaction
    is_viewed = models.BooleanField(default=False)
    is_acknowledged = models.BooleanField(default=False)
    user_feedback = models.TextField(blank=True)
    
    # Validity
    valid_from = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    class Meta:
        ordering = ['-created_at']


class AIModel(models.Model):
    """
    AI model configuration and performance tracking
    """
    MODEL_TYPES = [
        ('expense_categorizer', 'Expense Categorizer'),
        ('fraud_detector', 'Fraud Detector'),
        ('payment_predictor', 'Payment Predictor'),
        ('cash_flow_forecaster', 'Cash Flow Forecaster'),
        ('receipt_processor', 'Receipt Processor'),
        ('anomaly_detector', 'Anomaly Detector'),
    ]
    
    name = models.CharField(max_length=100)
    model_type = models.CharField(max_length=50, choices=MODEL_TYPES)
    version = models.CharField(max_length=20, default='1.0')
    
    # Configuration
    config = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    
    # Performance metrics
    accuracy = models.FloatField(default=0)
    precision = models.FloatField(default=0)
    recall = models.FloatField(default=0)
    f1_score = models.FloatField(default=0)
    
    # Usage statistics
    prediction_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} v{self.version}"

    @property
    def success_rate(self):
        if self.prediction_count == 0:
            return 0
        return (self.success_count / self.prediction_count) * 100


class AutomatedTask(models.Model):
    """
    AI-powered automated accounting tasks
    Advanced automation vs QuickBooks' basic rules
    """
    TASK_TYPES = [
        ('expense_categorization', 'Expense Categorization'),
        ('invoice_follow_up', 'Invoice Follow-up'),
        ('receipt_processing', 'Receipt Processing'),
        ('bank_reconciliation', 'Bank Reconciliation'),
        ('fraud_detection', 'Fraud Detection'),
        ('tax_preparation', 'Tax Preparation'),
        ('report_generation', 'Report Generation'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50, choices=TASK_TYPES)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Task configuration
    config = models.JSONField(default=dict)
    schedule = models.CharField(max_length=100, blank=True)  # Cron expression
    
    # Execution tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    
    # Results
    success_count = models.IntegerField(default=0)
    failure_count = models.IntegerField(default=0)
    last_result = models.JSONField(default=dict)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    class Meta:
        ordering = ['-created_at']


class PredictiveAnalytics(models.Model):
    """
    Store predictive analytics results
    Advanced forecasting not available in QuickBooks
    """
    PREDICTION_TYPES = [
        ('cash_flow', 'Cash Flow'),
        ('revenue', 'Revenue'),
        ('expenses', 'Expenses'),
        ('customer_churn', 'Customer Churn'),
        ('payment_delay', 'Payment Delay'),
        ('seasonal_trends', 'Seasonal Trends'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prediction_type = models.CharField(max_length=50, choices=PREDICTION_TYPES)
    
    # Prediction data
    predicted_values = models.JSONField(default=dict)
    confidence_intervals = models.JSONField(default=dict)
    
    # Time period
    prediction_date = models.DateField()
    valid_until = models.DateField()
    
    # Model information
    model_used = models.CharField(max_length=100)
    accuracy_score = models.FloatField(default=0)
    
    # Actual vs predicted (for model improvement)
    actual_values = models.JSONField(default=dict)
    variance = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.prediction_type} prediction for {self.user.username}"

    class Meta:
        ordering = ['-prediction_date']


class AITrainingData(models.Model):
    """
    Store training data for continuous AI improvement
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    data_type = models.CharField(max_length=50)
    
    # Training data
    input_data = models.JSONField()
    expected_output = models.JSONField()
    actual_output = models.JSONField(default=dict)
    
    # Feedback
    is_correct = models.BooleanField(null=True, blank=True)
    user_correction = models.JSONField(default=dict)
    
    # Model information
    model_version = models.CharField(max_length=20)
    confidence_score = models.FloatField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.data_type} training data - {self.user.username}"

    class Meta:
        ordering = ['-created_at']
