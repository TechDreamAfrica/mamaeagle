"""
Email Notification Utilities for DreamBiz
Centralized email sending functionality
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def send_email(subject, template_name, context, recipient_list, from_email=None):
    """
    Send HTML email using template
    
    Args:
        subject (str): Email subject
        template_name (str): Template path (e.g., 'emails/welcome.html')
        context (dict): Template context variables
        recipient_list (list): List of recipient email addresses
        from_email (str): Sender email (optional, uses default if not provided)
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else settings.EMAIL_HOST_USER
    
    try:
        # Add common context variables
        context['current_year'] = datetime.now().year
        
        # Render HTML content
        html_content = render_to_string(template_name, context)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body='Please view this email in an HTML-capable email client.',
            from_email=from_email,
            to=recipient_list
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send(fail_silently=False)
        logger.info(f"Email sent successfully: {subject} to {recipient_list}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {subject} to {recipient_list}. Error: {str(e)}")
        return False


def send_welcome_email(user, request=None):
    """Send welcome email to newly registered user"""
    dashboard_url = request.build_absolute_uri('/dashboard/') if request else 'http://localhost:8000/dashboard/'
    docs_url = request.build_absolute_uri('/documentation/') if request else 'http://localhost:8000/documentation/'
    
    context = {
        'user': user,
        'dashboard_url': dashboard_url,
        'docs_url': docs_url,
    }
    
    return send_email(
        subject='Welcome to DreamBiz! 🎉',
        template_name='emails/welcome.html',
        context=context,
        recipient_list=[user.email]
    )


def send_invoice_reminder(invoice, request=None):
    """Send payment reminder for overdue invoice"""
    from datetime import date
    
    days_overdue = (date.today() - invoice.due_date).days
    invoice_url = request.build_absolute_uri(f'/invoicing/invoice/{invoice.id}/') if request else f'http://localhost:8000/invoicing/invoice/{invoice.id}/'
    
    # Get company details
    company = invoice.company
    
    context = {
        'invoice': invoice,
        'days_overdue': days_overdue,
        'invoice_url': invoice_url,
        'company_name': company.name if company else 'DreamBiz',
        'company_email': company.email if company else 'support@techdreamafrica.com',
        'company_phone': company.phone if company else '',
    }
    
    return send_email(
        subject=f'Payment Reminder: Invoice {invoice.invoice_number} is Overdue',
        template_name='emails/invoice_reminder.html',
        context=context,
        recipient_list=[invoice.customer.email]
    )


def send_expense_notification(expense, action, recipient, request=None):
    """
    Send expense notification email
    
    Args:
        expense: Expense object
        action: 'submitted', 'approved', or 'rejected'
        recipient: User object who should receive notification
        request: HTTP request object (optional)
    """
    expense_url = request.build_absolute_uri(f'/expenses/expense/{expense.id}/') if request else f'http://localhost:8000/expenses/expense/{expense.id}/'
    
    # Determine recipient name
    recipient_name = recipient.get_full_name() if hasattr(recipient, 'get_full_name') else recipient.username
    
    context = {
        'expense': expense,
        'action': action,
        'recipient_name': recipient_name,
        'expense_url': expense_url,
        'rejection_reason': expense.notes if action == 'rejected' else '',
    }
    
    # Set subject based on action
    subjects = {
        'submitted': f'New Expense Submitted: GH₵{expense.amount} - {expense.category.name}',
        'approved': f'Expense Approved: GH₵{expense.amount} - {expense.category.name}',
        'rejected': f'Expense Rejected: GH₵{expense.amount} - {expense.category.name}',
    }
    
    return send_email(
        subject=subjects.get(action, 'Expense Notification'),
        template_name='emails/expense_notification.html',
        context=context,
        recipient_list=[recipient.email]
    )


def send_report_share_email(report_data, recipients, sender, message='', request=None):
    """
    Share report via email
    
    Args:
        report_data (dict): Report information (name, type, period, etc.)
        recipients (list): List of email addresses
        sender: User object sending the report
        message (str): Optional message to include
        request: HTTP request object (optional)
    """
    report_url = report_data.get('url', '')
    if request and not report_url.startswith('http'):
        report_url = request.build_absolute_uri(report_url)
    
    for recipient_email in recipients:
        # Extract name from email (before @)
        recipient_name = recipient_email.split('@')[0].replace('.', ' ').title()
        
        context = {
            'recipient_name': recipient_name,
            'recipient_email': recipient_email,
            'sender_name': sender.get_full_name() if hasattr(sender, 'get_full_name') else sender.username,
            'report_name': report_data.get('name', 'Financial Report'),
            'report_type': report_data.get('type', 'General Report'),
            'report_period': report_data.get('period', 'Current Period'),
            'generated_date': timezone.now(),
            'report_url': report_url,
            'message': message,
            'attachment': report_data.get('has_attachment', False),
        }
        
        send_email(
            subject=f'{report_data.get("name", "Report")} - Shared by {sender.get_full_name()}',
            template_name='emails/report_share.html',
            context=context,
            recipient_list=[recipient_email]
        )
    
    return True


def send_bulk_invoice_reminders():
    """
    Send reminders for all overdue invoices
    Called by scheduled task (e.g., daily cron job)
    """
    from invoicing.models import Invoice
    from datetime import date
    
    # Get all overdue unpaid invoices
    overdue_invoices = Invoice.objects.filter(
        due_date__lt=date.today(),
        status__in=['sent', 'partial']
    ).select_related('customer', 'company')
    
    sent_count = 0
    failed_count = 0
    
    for invoice in overdue_invoices:
        if invoice.customer.email:
            if send_invoice_reminder(invoice):
                sent_count += 1
            else:
                failed_count += 1
    
    logger.info(f"Bulk invoice reminders: {sent_count} sent, {failed_count} failed")
    return {'sent': sent_count, 'failed': failed_count}
