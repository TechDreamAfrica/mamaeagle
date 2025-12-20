"""
Generic bulk operations utilities for Django views
Provides standardized bulk delete and export functionality across modules
"""

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.apps import apps
import json
import csv


class BulkOperationsError(Exception):
    """Custom exception for bulk operations"""
    pass


def get_model_class(app_label, model_name):
    """Get Django model class from app and model name"""
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        raise BulkOperationsError(f"Model {app_label}.{model_name} not found")


def can_delete_item(item, entity_type):
    """
    Determine if an item can be deleted based on business rules
    Override this function for custom deletion rules
    """
    if entity_type == 'invoice':
        return getattr(item, 'status', None) != 'paid'
    elif entity_type == 'expense':
        return getattr(item, 'status', None) != 'reimbursed'
    elif entity_type == 'employee':
        # Don't allow deletion of active employees with recent activity
        return getattr(item, 'is_active', True) == False
    else:
        return True


def bulk_delete_view(request, app_label, model_name, entity_type):
    """
    Generic bulk delete view that can be used across different models
    
    Args:
        request: Django request object
        app_label: Django app label (e.g., 'invoicing', 'hr')
        model_name: Model name (e.g., 'Invoice', 'Employee')
        entity_type: Human-readable entity type (e.g., 'invoice', 'employee')
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        # Get the model class
        Model = get_model_class(app_label, model_name)
        
        # Parse item IDs from request
        item_ids_param = request.POST.get('item_ids') or request.POST.get('invoice_ids')  # Backward compatibility
        item_ids = json.loads(item_ids_param or '[]')
        
        if not item_ids:
            return JsonResponse({'error': f'No {entity_type}s selected'}, status=400)
        
        # Get items that belong to the current user
        queryset = Model.objects.filter(pk__in=item_ids)
        
        # Filter by user if the model has a user field
        if hasattr(Model, 'user'):
            queryset = queryset.filter(user=request.user)
        elif hasattr(Model, 'created_by'):
            queryset = queryset.filter(created_by=request.user)
        
        deleted_count = 0
        skipped_count = 0
        
        for item in queryset:
            try:
                if can_delete_item(item, entity_type):
                    item_identifier = getattr(item, 'name', None) or getattr(item, 'invoice_number', None) or str(item.pk)
                    item.delete()
                    deleted_count += 1
                    messages.success(request, f'{entity_type.title()} {item_identifier} deleted successfully.')
                else:
                    skipped_count += 1
            except Exception as e:
                skipped_count += 1
                messages.warning(request, f'Could not delete {entity_type}: {str(e)}')
        
        # Account for items that were not found or don't belong to user
        total_requested = len(item_ids)
        not_found_count = total_requested - (deleted_count + skipped_count)
        skipped_count += not_found_count
        
        if skipped_count > 0:
            messages.warning(request, f'{skipped_count} {entity_type}(s) were skipped or could not be deleted.')
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'skipped_count': skipped_count,
            'total_requested': total_requested
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': f'Invalid {entity_type} IDs format'}, status=400)
    except BulkOperationsError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


def bulk_export_view(request, app_label, model_name, entity_type, fields_config):
    """
    Generic bulk export view that can be used across different models
    
    Args:
        request: Django request object
        app_label: Django app label
        model_name: Model name
        entity_type: Human-readable entity type
        fields_config: List of tuples (field_name, header_name, accessor_function)
    """
    if not request.user.is_authenticated:
        messages.error(request, 'Authentication required.')
        return redirect('dashboard:home')
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('dashboard:home')
    
    try:
        # Get the model class
        Model = get_model_class(app_label, model_name)
        
        # Parse item IDs from request
        item_ids_param = request.POST.get('item_ids') or request.POST.get('invoice_ids')  # Backward compatibility
        item_ids = json.loads(item_ids_param or '[]')
        
        if not item_ids:
            messages.error(request, f'No {entity_type}s selected for export.')
            return redirect('dashboard:home')
        
        # Get items that belong to the current user
        queryset = Model.objects.filter(pk__in=item_ids)
        
        # Filter by user if the model has a user field
        if hasattr(Model, 'user'):
            queryset = queryset.filter(user=request.user)
        elif hasattr(Model, 'created_by'):
            queryset = queryset.filter(created_by=request.user)
        
        # Add select_related/prefetch_related for common relationships
        if hasattr(Model, 'customer'):
            queryset = queryset.select_related('customer')
        if hasattr(Model, 'category'):
            queryset = queryset.select_related('category')
        
        queryset = queryset.order_by('-pk')  # Most recent first
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{entity_type}s_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        header = [config[1] for config in fields_config]
        writer.writerow(header)
        
        # Write data
        for item in queryset:
            row = []
            for field_name, header_name, accessor_func in fields_config:
                try:
                    if accessor_func:
                        value = accessor_func(item)
                    else:
                        value = getattr(item, field_name, '')
                    
                    # Convert to string and handle None values
                    if value is None:
                        value = ''
                    elif hasattr(value, 'strftime'):
                        value = value.strftime('%Y-%m-%d')
                    else:
                        value = str(value)
                    
                    row.append(value)
                except Exception:
                    row.append('')  # If there's an error accessing the field, use empty string
            
            writer.writerow(row)
        
        messages.success(request, f'{len(queryset)} {entity_type}(s) exported successfully.')
        return response
        
    except json.JSONDecodeError:
        messages.error(request, 'Invalid export data format.')
        return redirect('dashboard:home')
    except BulkOperationsError as e:
        messages.error(request, str(e))
        return redirect('dashboard:home')
    except Exception as e:
        messages.error(request, f'Export failed: {str(e)}')
        return redirect('dashboard:home')


# Pre-configured field mappings for common models
INVOICE_FIELDS_CONFIG = [
    ('invoice_number', 'Invoice Number', None),
    ('customer', 'Customer Name', lambda obj: getattr(obj.customer, 'name', '')),
    ('customer', 'Customer Company', lambda obj: getattr(obj.customer, 'company', '')),
    ('customer', 'Customer Email', lambda obj: getattr(obj.customer, 'email', '')),
    ('date_created', 'Date Created', None),
    ('date_due', 'Date Due', None),
    ('status', 'Status', lambda obj: obj.get_status_display() if hasattr(obj, 'get_status_display') else obj.status),
    ('subtotal', 'Subtotal', None),
    ('tax_amount', 'Tax Amount', None),
    ('total_amount', 'Total Amount', None),
    ('amount_paid', 'Amount Paid', None),
    ('notes', 'Notes', None),
    ('terms', 'Terms', None),
]

CUSTOMER_FIELDS_CONFIG = [
    ('name', 'Customer Name', None),
    ('company', 'Company', None),
    ('email', 'Email', None),
    ('phone', 'Phone', None),
    ('billing_address_line_1', 'Address', None),
    ('billing_city', 'City', None),
    ('billing_state', 'State', None),
    ('payment_terms', 'Payment Terms', None),
    ('is_active', 'Active', None),
    ('date_created', 'Date Created', None),
]

EMPLOYEE_FIELDS_CONFIG = [
    ('first_name', 'First Name', None),
    ('last_name', 'Last Name', None),
    ('email', 'Email', None),
    ('employee_id', 'Employee ID', None),
    ('department', 'Department', None),
    ('position', 'Position', None),
    ('hire_date', 'Hire Date', None),
    ('salary', 'Salary', None),
    ('is_active', 'Active', None),
    ('phone', 'Phone', None),
]

EXPENSE_FIELDS_CONFIG = [
    ('description', 'Description', None),
    ('amount', 'Amount', None),
    ('category', 'Category', lambda obj: getattr(obj.category, 'name', '') if obj.category else ''),
    ('date', 'Date', None),
    ('vendor', 'Vendor', None),
    ('status', 'Status', lambda obj: obj.get_status_display() if hasattr(obj, 'get_status_display') else obj.status),
    ('payment_method', 'Payment Method', None),
    ('notes', 'Notes', None),
    ('receipt_url', 'Receipt', None),
]
