"""
OpenAI Service for AI Insights
Provides intelligent financial analysis using GPT models
"""

from django.conf import settings
from openai import OpenAI
import json
from decimal import Decimal
from datetime import datetime


class OpenAIService:
    """Service class for OpenAI API interactions"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        if not self.api_key or self.api_key == 'your-openai-api-key-here':
            raise ValueError("OpenAI API key not configured. Please set OPENAI_API_KEY in your .env file")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
    
    def _prepare_financial_context(self, data):
        """Prepare financial data context for AI analysis"""
        context = []
        
        if 'income' in data:
            context.append(f"Total Income: GH₵{data['income']:,.2f}")
        if 'expenses' in data:
            context.append(f"Total Expenses: GH₵{data['expenses']:,.2f}")
        if 'net_cash_flow' in data:
            context.append(f"Net Cash Flow: GH₵{data['net_cash_flow']:,.2f}")
        if 'monthly_data' in data and data['monthly_data']:
            context.append(f"Historical Data: {len(data['monthly_data'])} months")
        if 'expense_categories' in data:
            context.append(f"Expense Categories: {', '.join(data['expense_categories'].keys())}")
        if 'customer_count' in data:
            context.append(f"Total Customers: {data['customer_count']}")
        
        return "\n".join(context)
    
    def analyze_cash_flow(self, monthly_data, predictions):
        """Generate AI-powered cash flow insights"""
        try:
            context = f"""
Analyze the following cash flow data and provide actionable insights:

Historical Data (Last 12 months):
{json.dumps(monthly_data, indent=2)}

Predicted Data (Next 3 months):
{json.dumps(predictions, indent=2)}

Provide:
1. Overall trend analysis
2. Specific risks or opportunities
3. 3-5 actionable recommendations
4. Priority level (critical, high, medium, low) for each insight
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analyst AI specializing in cash flow analysis. Provide clear, actionable insights in JSON format."
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            
            return self._parse_insights_response(response.choices[0].message.content)
        
        except Exception as e:
            return {
                'insights': [
                    {
                        'type': 'cash_flow',
                        'priority': 'medium',
                        'content': 'Unable to generate AI insights at this time. Please check your OpenAI API configuration.',
                        'recommendations': ['Verify OpenAI API key', 'Check API quota'],
                        'confidence': 0
                    }
                ],
                'error': str(e)
            }
    
    def analyze_expenses(self, expense_data, anomalies):
        """Generate AI-powered expense analysis"""
        try:
            context = f"""
Analyze the following expense data and identify optimization opportunities:

Expense Summary:
- Total Expenses (30 days): GH₵{expense_data.get('total_30d', 0):,.2f}
- Total Expenses (90 days): GH₵{expense_data.get('total_90d', 0):,.2f}

Category Breakdown:
{json.dumps(expense_data.get('categories', {}), indent=2)}

Detected Anomalies:
{json.dumps(anomalies, indent=2)}

Provide:
1. Expense optimization opportunities
2. Category-specific recommendations
3. Anomaly explanations and suggested actions
4. Cost-saving strategies
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a cost optimization AI expert. Analyze expenses and provide practical cost-saving recommendations in JSON format."
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            
            return self._parse_insights_response(response.choices[0].message.content)
        
        except Exception as e:
            return {
                'insights': [
                    {
                        'type': 'expense_optimization',
                        'priority': 'medium',
                        'content': 'Expense analysis temporarily unavailable.',
                        'recommendations': ['Review monthly expense reports manually'],
                        'confidence': 0
                    }
                ],
                'error': str(e)
            }
    
    def analyze_customer_risk(self, customer_data):
        """Generate AI-powered customer risk analysis"""
        try:
            context = f"""
Analyze customer payment behavior and provide risk assessment:

Customer Statistics:
- Total Customers: {customer_data.get('total_customers', 0)}
- High Risk: {customer_data.get('high_risk_count', 0)}
- Medium Risk: {customer_data.get('medium_risk_count', 0)}
- Low Risk: {customer_data.get('low_risk_count', 0)}

High Risk Customers:
{json.dumps(customer_data.get('high_risk_customers', []), indent=2)}

Provide:
1. Risk mitigation strategies
2. Collection recommendations
3. Customer relationship insights
4. Credit policy suggestions
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a credit risk management AI. Analyze customer payment patterns and provide risk mitigation strategies in JSON format."
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            
            return self._parse_insights_response(response.choices[0].message.content)
        
        except Exception as e:
            return {
                'insights': [
                    {
                        'type': 'customer_risk',
                        'priority': 'medium',
                        'content': 'Customer risk analysis temporarily unavailable.',
                        'recommendations': ['Review customer accounts manually'],
                        'confidence': 0
                    }
                ],
                'error': str(e)
            }
    
    def generate_comprehensive_insights(self, financial_summary):
        """Generate comprehensive business insights"""
        try:
            context = f"""
Analyze the overall business financial health and provide strategic insights:

Financial Summary:
{self._prepare_financial_context(financial_summary)}

Detailed Metrics:
{json.dumps(financial_summary, indent=2, default=str)}

Provide:
1. Overall business health assessment
2. Growth opportunities
3. Financial risks
4. Strategic recommendations
5. KPI improvement suggestions
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business intelligence AI. Analyze financial data and provide strategic business insights in JSON format with this structure: {'insights': [{'type': str, 'priority': str, 'content': str, 'recommendations': [str], 'confidence': int}]}"
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            return self._parse_insights_response(response.choices[0].message.content)
        
        except Exception as e:
            return {
                'insights': [
                    {
                        'type': 'general',
                        'priority': 'low',
                        'content': f'AI insights generation encountered an issue: {str(e)}',
                        'recommendations': ['Check OpenAI API configuration', 'Verify API key and quota'],
                        'confidence': 0
                    }
                ],
                'error': str(e)
            }
    
    def _parse_insights_response(self, response_content):
        """Parse AI response into structured insights"""
        try:
            # Try to parse as JSON
            data = json.loads(response_content)
            
            # Validate structure
            if 'insights' in data and isinstance(data['insights'], list):
                return data
            
            # If no insights key, wrap the response
            return {'insights': [data] if isinstance(data, dict) else data}
        
        except json.JSONDecodeError:
            # If not JSON, create a structured response from text
            return {
                'insights': [
                    {
                        'type': 'general',
                        'priority': 'medium',
                        'content': response_content[:500],  # Limit content length
                        'recommendations': [],
                        'confidence': 70
                    }
                ]
            }
    
    def test_connection(self):
        """Test OpenAI API connection"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Respond with 'Connected' if you receive this message."}
                ],
                max_tokens=10
            )
            return {
                'success': True,
                'message': response.choices[0].message.content,
                'model': self.model
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
