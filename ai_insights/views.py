from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from .models import AIInsight, AIModel, AutomatedTask
from .openai_service import OpenAIService
from reports.models import JournalEntry
from invoicing.models import Invoice
from expenses.models import Expense


@login_required
def insights_dashboard(request):
    """Main AI Insights dashboard with overview of all AI-powered features."""
    user = request.user
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # Get active insights
    active_insights = AIInsight.objects.filter(
        user=user,
        is_active=True,
        valid_until__gte=timezone.now()
    ).order_by('-priority', '-created_at')[:10]
    
    # Count insights by priority
    critical_count = AIInsight.objects.filter(user=user, priority='critical', is_active=True).count()
    high_count = AIInsight.objects.filter(user=user, priority='high', is_active=True).count()
    medium_count = AIInsight.objects.filter(user=user, priority='medium', is_active=True).count()
    low_count = AIInsight.objects.filter(user=user, priority='low', is_active=True).count()
    
    # Get automated tasks
    automated_tasks = AutomatedTask.objects.filter(
        user=user,
        is_active=True
    ).order_by('-created_at')[:5]
    
    # AI Model Performance
    ai_models = AIModel.objects.filter(is_active=True)
    
    context = {
        'insights': active_insights,
        'critical_count': critical_count,
        'high_count': high_count,
        'medium_count': medium_count,
        'low_count': low_count,
        'automated_tasks': automated_tasks,
        'ai_models': ai_models,
    }
    
    return render(request, 'ai_insights/insights_dashboard.html', context)


@login_required
def cash_flow_prediction(request):
    """Cash flow prediction and forecasting using AI."""
    user = request.user
    today = timezone.now().date()
    
    # Get historical cash flow data (last 12 months)
    twelve_months_ago = today - timedelta(days=365)
    
    # Calculate monthly cash flows from journal entries
    monthly_data = []
    for i in range(12):
        month_start = twelve_months_ago + timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        
        # Income (credit entries in revenue accounts)
        income = JournalEntry.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lt=month_end,
            status='posted'
        ).aggregate(
            total=Sum('journalentryline__credit')
        )['total'] or 0
        
        # Expenses (debit entries in expense accounts)
        expenses = JournalEntry.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lt=month_end,
            status='posted'
        ).aggregate(
            total=Sum('journalentryline__debit')
        )['total'] or 0
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'income': float(income),
            'expenses': float(expenses),
            'net_cash_flow': float(income - expenses)
        })
    
    # Simple prediction for next 3 months (average-based)
    avg_income = sum(m['income'] for m in monthly_data[-3:]) / 3
    avg_expenses = sum(m['expenses'] for m in monthly_data[-3:]) / 3
    
    predictions = []
    for i in range(1, 4):
        pred_month = today + timedelta(days=30*i)
        predictions.append({
            'month': pred_month.strftime('%b %Y'),
            'predicted_income': round(avg_income * (1 + (i * 0.02)), 2),  # 2% growth
            'predicted_expenses': round(avg_expenses * (1 + (i * 0.01)), 2),  # 1% growth
            'confidence': round(85 - (i * 5), 1)  # Decreasing confidence
        })
    
    # Calculate trend
    recent_avg = sum(m['net_cash_flow'] for m in monthly_data[-3:]) / 3
    older_avg = sum(m['net_cash_flow'] for m in monthly_data[-6:-3]) / 3
    trend = 'improving' if recent_avg > older_avg else 'declining'
    
    # Generate AI insights
    insights = []
    if trend == 'declining':
        insights.append({
            'type': 'warning',
            'title': 'Declining Cash Flow Trend',
            'description': 'Your cash flow has been declining over the past 3 months.',
            'recommendation': 'Consider reducing expenses or increasing revenue streams.'
        })
    
    # Check for negative predictions
    for pred in predictions:
        net = pred['predicted_income'] - pred['predicted_expenses']
        if net < 0:
            insights.append({
                'type': 'critical',
                'title': f'Negative Cash Flow Predicted for {pred["month"]}',
                'description': f'Projected shortfall of GH₵{abs(net):,.2f}',
                'recommendation': 'Prepare a cash reserve or arrange for short-term financing.'
            })
    
    context = {
        'monthly_data': monthly_data,
        'predictions': predictions,
        'trend': trend,
        'insights': insights,
        'current_cash_position': monthly_data[-1]['net_cash_flow'] if monthly_data else 0,
    }
    
    return render(request, 'ai_insights/cash_flow_prediction.html', context)


@login_required
def expense_analysis(request):
    """AI-powered expense analysis and anomaly detection."""
    user = request.user
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    ninety_days_ago = today - timedelta(days=90)
    
    # Get expenses for analysis
    recent_expenses = Expense.objects.filter(
        date__gte=thirty_days_ago
    ).values('category').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Historical average for comparison
    historical_expenses = Expense.objects.filter(
        date__gte=ninety_days_ago,
        date__lt=thirty_days_ago
    ).values('category').annotate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    # Create historical lookup
    historical_lookup = {e['category']: e['total'] for e in historical_expenses}
    
    # Analyze for anomalies
    anomalies = []
    expense_breakdown = []
    
    total_recent = sum(e['total'] for e in recent_expenses)
    
    for expense in recent_expenses:
        category = expense['category']
        current_total = expense['total']
        historical_total = historical_lookup.get(category, 0)
        
        percentage = (current_total / total_recent * 100) if total_recent > 0 else 0
        
        expense_breakdown.append({
            'category': category or 'Uncategorized',
            'amount': float(current_total),
            'count': expense['count'],
            'percentage': round(percentage, 1)
        })
        
        # Detect anomalies (50% increase)
        if historical_total > 0:
            increase_pct = ((current_total - historical_total) / historical_total) * 100
            if increase_pct > 50:
                anomalies.append({
                    'category': category or 'Uncategorized',
                    'current': float(current_total),
                    'historical': float(historical_total),
                    'increase_pct': round(increase_pct, 1),
                    'severity': 'high' if increase_pct > 100 else 'medium'
                })
    
    # Top expenses
    top_expenses = Expense.objects.filter(
        date__gte=thirty_days_ago
    ).order_by('-amount')[:10]
    
    # Recommendations
    recommendations = []
    if anomalies:
        recommendations.append({
            'title': 'Unusual Spending Patterns Detected',
            'description': f'{len(anomalies)} expense categories show significant increases.',
            'action': 'Review these expenses for potential cost savings.'
        })
    
    if total_recent > 0:
        avg_expense = total_recent / 30
        recommendations.append({
            'title': 'Daily Average Spend',
            'description': f'You are spending an average of GH₵{avg_expense:,.2f} per day.',
            'action': 'Consider setting daily spending limits for better control.'
        })
    
    context = {
        'expense_breakdown': expense_breakdown,
        'anomalies': anomalies,
        'top_expenses': top_expenses,
        'total_recent': total_recent,
        'recommendations': recommendations,
    }
    
    return render(request, 'ai_insights/expense_analysis.html', context)


@login_required
def customer_insights(request):
    """AI-powered customer behavior analysis and risk assessment."""
    user = request.user
    today = timezone.now().date()
    
    # Get customer data from invoices
    customer_stats = Invoice.objects.values('customer').annotate(
        total_invoices=Count('id'),
        total_revenue=Sum('total_amount'),
        paid_invoices=Count('id', filter=Q(status='paid')),
        overdue_invoices=Count('id', filter=Q(status='overdue'))
    ).order_by('-total_revenue')[:20]
    
    # Calculate payment behavior
    customer_analysis = []
    for stat in customer_stats:
        if stat['customer']:
            payment_rate = (stat['paid_invoices'] / stat['total_invoices'] * 100) if stat['total_invoices'] > 0 else 0
            risk_level = 'low'
            
            if stat['overdue_invoices'] > 2 or payment_rate < 50:
                risk_level = 'high'
            elif stat['overdue_invoices'] > 0 or payment_rate < 80:
                risk_level = 'medium'
            
            customer_analysis.append({
                'customer_id': stat['customer'],
                'total_revenue': float(stat['total_revenue'] or 0),
                'total_invoices': stat['total_invoices'],
                'payment_rate': round(payment_rate, 1),
                'overdue_count': stat['overdue_invoices'],
                'risk_level': risk_level
            })
    
    # Risk distribution
    risk_distribution = {
        'low': len([c for c in customer_analysis if c['risk_level'] == 'low']),
        'medium': len([c for c in customer_analysis if c['risk_level'] == 'medium']),
        'high': len([c for c in customer_analysis if c['risk_level'] == 'high']),
    }
    
    # Top customers
    top_customers = sorted(customer_analysis, key=lambda x: x['total_revenue'], reverse=True)[:5]
    
    # At-risk customers
    at_risk_customers = [c for c in customer_analysis if c['risk_level'] == 'high'][:5]
    
    # Recommendations
    recommendations = []
    if at_risk_customers:
        total_at_risk_revenue = sum(c['total_revenue'] for c in at_risk_customers)
        recommendations.append({
            'title': 'High-Risk Customers Detected',
            'description': f'{len(at_risk_customers)} customers at risk, representing GH₵{total_at_risk_revenue:,.2f} in revenue.',
            'action': 'Follow up on overdue invoices and consider payment plans.'
        })
    
    context = {
        'customer_analysis': customer_analysis,
        'risk_distribution': risk_distribution,
        'top_customers': top_customers,
        'at_risk_customers': at_risk_customers,
        'recommendations': recommendations,
    }
    
    return render(request, 'ai_insights/customer_insights.html', context)


@login_required
def generate_insights_api(request):
    """API endpoint to generate new AI insights using OpenAI."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)
    
    user = request.user
    today = timezone.now()
    
    try:
        # Initialize OpenAI service
        ai_service = OpenAIService()
        
        # Gather comprehensive financial data
        financial_summary = {}
        
        # Cash flow data
        thirty_days_ago = today - timedelta(days=30)
        ninety_days_ago = today - timedelta(days=90)
        
        income = JournalEntry.objects.filter(
            created_at__gte=thirty_days_ago,
            status='posted',
            entry_type='debit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        expenses = JournalEntry.objects.filter(
            created_at__gte=thirty_days_ago,
            status='posted',
            entry_type='credit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        financial_summary['income'] = float(income)
        financial_summary['expenses'] = float(expenses)
        financial_summary['net_cash_flow'] = float(income - expenses)
        
        # Customer data
        total_customers = Invoice.objects.values('customer').distinct().count()
        high_risk_customers = Invoice.objects.filter(
            payment_status='unpaid',
            due_date__lt=today.date()
        ).values('customer').distinct().count()
        
        financial_summary['customer_count'] = total_customers
        financial_summary['high_risk_customer_count'] = high_risk_customers
        
        # Expense categories
        expense_categories = Expense.objects.filter(
            expense_date__gte=thirty_days_ago
        ).values('category').annotate(
            total=Sum('amount')
        )
        
        financial_summary['expense_categories'] = {
            item['category']: float(item['total'])
            for item in expense_categories
        }
        
        # Generate AI insights
        ai_response = ai_service.generate_comprehensive_insights(financial_summary)
        
        # Save insights to database
        insights_created = 0
        if 'insights' in ai_response:
            for insight_data in ai_response['insights']:
                # Determine priority
                priority = insight_data.get('priority', 'medium').lower()
                if priority not in ['critical', 'high', 'medium', 'low']:
                    priority = 'medium'
                
                # Create insight
                AIInsight.objects.create(
                    user=user,
                    insight_type=insight_data.get('type', 'general'),
                    title=f"AI Insight: {insight_data.get('type', 'General').replace('_', ' ').title()}",
                    content=insight_data.get('content', ''),
                    confidence_score=insight_data.get('confidence', 75),
                    priority=priority,
                    recommendations=json.dumps(insight_data.get('recommendations', [])),
                    valid_until=today + timedelta(days=7)
                )
                insights_created += 1
        
        return JsonResponse({
            'success': True,
            'message': f'{insights_created} new AI insights generated successfully',
            'insights_count': insights_created
        })
    
    except ValueError as e:
        # API key not configured
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Please configure your OpenAI API key in the .env file'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate insights'
        }, status=500)


@login_required
def acknowledge_insight(request, insight_id):
    """Mark an insight as acknowledged."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)
    
    try:
        data = json.loads(request.body)
        insight_id = data.get('insight_id')
        
        if not insight_id:
            return JsonResponse({'success': False, 'error': 'insight_id required'}, status=400)
        
        insight = get_object_or_404(AIInsight, id=insight_id, user=request.user)
        insight.is_acknowledged = True
        insight.save()
        
        return JsonResponse({'success': True})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


