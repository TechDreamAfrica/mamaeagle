from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count, F
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.forms import modelformset_factory
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import decimal
from .models import Invoice, Customer, Product, InvoiceItem, Payment
from .forms import InvoiceForm, CustomerForm, ProductForm, InvoiceItemForm, PaymentForm
import json


@login_required
def invoice_list(request):
    """
    Invoice list with advanced filtering and search
    Much better than QuickBooks' basic list view
    """
    invoices = Invoice.objects.filter(user=request.user)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(customer__name__icontains=search_query) |
            Q(customer__company__icontains=search_query)
        )
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        invoices = invoices.filter(date_created__gte=date_from)
    if date_to:
        invoices = invoices.filter(date_created__lte=date_to)
    
    # Pagination
    paginator = Paginator(invoices.order_by('-date_created'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Summary statistics
    summary = invoices.aggregate(
        total_amount=Sum('total_amount'),
        total_paid=Sum('amount_paid'),
        count=Count('id')
    )
    
    # Get customers for the modal
    customers = Customer.objects.filter(user=request.user, is_active=True).values('id', 'name', 'company', 'email')
    
    # Prepare invoice data for JavaScript (for bulk operations)
    invoices_data = [
        {
            'id': invoice.pk,
            'status': invoice.status,
            'invoice_number': invoice.invoice_number,
            'customer_name': invoice.customer.name,
            'total_amount': str(invoice.total_amount)
        }
        for invoice in page_obj
    ]
    
    context = {
        'page_obj': page_obj,
        'summary': summary,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': Invoice.STATUS_CHOICES,
        'customers': list(customers),
        'invoices_data': json.dumps(invoices_data),
        'overdue_count': invoices.filter(status='overdue').count(),
    }
    
    return render(request, 'invoicing/invoice_list.html', context)


@login_required
def invoice_detail(request, pk):
    """
    Invoice detail view with payment tracking
    """
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    payments = Payment.objects.filter(invoice=invoice).order_by('-payment_date')
    
    context = {
        'invoice': invoice,
        'payments': payments,
        'can_edit': invoice.status == 'draft',
    }
    
    return render(request, 'invoicing/invoice_detail.html', context)


@login_required
def invoice_create(request):
    """
    Create new invoice with dynamic line items
    Advanced invoice creation vs QuickBooks
    """
    # Create formsets for line items
    InvoiceItemFormSet = modelformset_factory(
        InvoiceItem, 
        form=InvoiceItemForm, 
        extra=5, 
        can_delete=True
    )
    
    if request.method == 'POST':
        # Check if this is a traditional form submission or modal submission
        if request.POST.get('line_items'):
            # Handle modal submission with JSON line items
            customer_id = request.POST.get('customer')
            
            # Validate customer ID
            if not customer_id:
                messages.error(request, 'Please select a customer for this invoice.')
                # Return to form with error
                context = {
                    'customers': Customer.objects.filter(user=request.user, is_active=True),
                    'products': Product.objects.filter(user=request.user, is_active=True),
                }
                return render(request, 'invoicing/invoice_create.html', context)
            
            customer = get_object_or_404(Customer, pk=customer_id, user=request.user)
            
            # Generate unique invoice number with proper database locking
            from django.db import IntegrityError, transaction
            import re
            import time
            import random
            
            invoice = None
            max_attempts = 5
            
            # Parse line items before the transaction
            line_items = json.loads(request.POST.get('line_items', '[]'))
            
            for attempt in range(max_attempts):
                try:
                    with transaction.atomic():
                        # Use select_for_update to lock rows and prevent race conditions
                        # Get the last invoice with a lock
                        last_invoice = (
                            Invoice.objects.filter(user=request.user)
                            .select_for_update()
                            .order_by('-id')
                            .first()
                        )
                        
                        # Find the highest numeric invoice number
                        max_number = 0
                        if last_invoice:
                            # Get all invoice numbers for this user
                            all_invoices = Invoice.objects.filter(user=request.user).values_list('invoice_number', flat=True)
                            pattern = re.compile(r'^INV-(\d+)(?:-\d+)?$')
                            
                            for inv_num in all_invoices:
                                match = pattern.match(inv_num)
                                if match:
                                    num = int(match.group(1))
                                    if num > max_number:
                                        max_number = num
                        
                        # Generate new invoice number with random suffix to avoid collisions
                        next_number = max_number + 1
                        random_suffix = random.randint(100, 999)
                        invoice_number = f"INV-{next_number:05d}-{random_suffix}"
                        
                        # Create invoice
                        invoice = Invoice.objects.create(
                            company=request.company,  # Set the active company
                            user=request.user,
                            customer=customer,
                            invoice_number=invoice_number,
                            date_due=request.POST.get('date_due'),
                            notes=request.POST.get('notes', ''),
                            terms=request.POST.get('terms', ''),
                            status='draft' if request.POST.get('action') == 'save_draft' else 'sent',
                            total_amount=0  # Will be calculated from line items
                        )
                        
                        # Process line items inside the transaction
                        subtotal = Decimal('0')
                        tax_total = Decimal('0')
                        
                        for item_data in line_items:
                            # Support both 'rate' and 'unit_price' for flexibility
                            unit_price = item_data.get('unit_price') or item_data.get('rate')
                            quantity = item_data.get('quantity')
                            tax_rate = item_data.get('tax_rate', 0)
                            
                            # Validate and clean values before conversion
                            if not item_data.get('description'):
                                continue
                            
                            # Clean and validate numeric values
                            try:
                                # Convert to string and strip whitespace, handle empty strings
                                quantity_str = str(quantity).strip() if quantity else '0'
                                unit_price_str = str(unit_price).strip() if unit_price else '0'
                                tax_rate_str = str(tax_rate).strip() if tax_rate else '0'
                                
                                # Skip if any critical value is empty or zero
                                if not quantity_str or not unit_price_str or quantity_str == '0' or unit_price_str == '0':
                                    continue
                                
                                # Convert to Decimal
                                quantity_decimal = Decimal(quantity_str)
                                unit_price_decimal = Decimal(unit_price_str)
                                tax_rate_decimal = Decimal(tax_rate_str)
                                
                                # Create invoice item
                                item = InvoiceItem.objects.create(
                                    invoice=invoice,
                                    description=item_data['description'],
                                    quantity=quantity_decimal,
                                    unit_price=unit_price_decimal,
                                    tax_rate=tax_rate_decimal
                                )
                                
                                # Calculate totals using proper Decimal arithmetic
                                line_total = item.total
                                line_tax = line_total * (item.tax_rate / Decimal('100'))
                                subtotal += line_total
                                tax_total += line_tax
                                
                            except (ValueError, decimal.InvalidOperation, decimal.ConversionSyntax) as e:
                                # Log the error and skip this item
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.warning(f"Invalid decimal value in line item: {e}. Item data: {item_data}")
                                continue
                        
                        # Update invoice totals
                        invoice.subtotal = subtotal
                        invoice.tax_amount = tax_total
                        invoice.total_amount = subtotal + tax_total
                        invoice.save()
                        
                        break  # Success, exit retry loop
                        
                except IntegrityError as e:
                    if attempt == max_attempts - 1:
                        # Last attempt failed
                        messages.error(request, f'Unable to create invoice after {max_attempts} attempts. Please try again.')
                        context = {
                            'customers': Customer.objects.filter(user=request.user, is_active=True),
                            'products': Product.objects.filter(user=request.user, is_active=True),
                        }
                        return render(request, 'invoicing/invoice_create.html', context)
                    # Retry with small delay
                    time.sleep(0.1 * (attempt + 1))
                    continue
                    
            if not invoice:
                messages.error(request, 'Failed to create invoice. Please try again.')
                context = {
                    'customers': Customer.objects.filter(user=request.user, is_active=True),
                    'products': Product.objects.filter(user=request.user, is_active=True),
                }
                return render(request, 'invoicing/invoice_create.html', context)
            
            if request.POST.get('action') == 'save_draft':
                messages.success(request, f'Invoice {invoice.invoice_number} saved as draft!')
            else:
                messages.success(request, f'Invoice {invoice.invoice_number} created and sent successfully!')
            
            return redirect('invoicing:invoice_detail', pk=invoice.pk)
        
        else:
            # Handle traditional formset submission
            form = InvoiceForm(user=request.user, data=request.POST)
            formset = InvoiceItemFormSet(request.POST, queryset=InvoiceItem.objects.none())
            
            if form.is_valid() and formset.is_valid():
                from django.db import IntegrityError, transaction
                import re
                import random
                import time
                
                invoice = None
                # Retry logic for handling race conditions
                for attempt in range(5):
                    try:
                        with transaction.atomic():
                            # Lock the last invoice to prevent race conditions
                            last_invoice = (
                                Invoice.objects.filter(user=request.user)
                                .select_for_update()
                                .order_by('-id')
                                .first()
                            )
                            
                            # Create invoice
                            invoice = form.save(commit=False)
                            invoice.user = request.user
                            invoice.company = request.company  # Set the active company
                            
                            # Get all existing invoice numbers
                            existing_numbers = set(
                                Invoice.objects.filter(user=request.user)
                                .values_list('invoice_number', flat=True)
                            )
                            
                            # Find the highest numeric invoice number
                            max_number = 0
                            pattern = re.compile(r'^INV-(\d+)(?:-\d+)?$')
                            
                            for inv_num in existing_numbers:
                                match = pattern.match(inv_num)
                                if match:
                                    num = int(match.group(1))
                                    if num > max_number:
                                        max_number = num
                            
                            # Generate new invoice number with random suffix for uniqueness
                            next_number = max_number + 1
                            random_suffix = random.randint(100, 999)
                            invoice.invoice_number = f"INV-{next_number:05d}-{random_suffix}"
                            
                            # Set default due date if not provided
                            if not invoice.date_due:
                                invoice.date_due = date.today() + timedelta(days=30)
                            
                            invoice.total_amount = 0  # Will be calculated from line items
                            invoice.save()
                            
                            # Create line items inside the transaction
                            subtotal = 0
                            tax_total = 0
                            
                            for item_form in formset:
                                if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                                    item = item_form.save(commit=False)
                                    item.invoice = invoice
                                    
                                    # Auto-populate from product if selected
                                    if item.product:
                                        item.description = item.description or item.product.name
                                        item.unit_price = item.unit_price or item.product.unit_price
                                        item.tax_rate = item.tax_rate or item.product.tax_rate
                                    
                                    item.save()
                                    
                                    # Calculate totals
                                    line_total = item.total
                                    line_tax = line_total * (item.tax_rate / 100)
                                    subtotal += line_total
                                    tax_total += line_tax
                            
                            # Update invoice totals
                            invoice.subtotal = subtotal
                            invoice.tax_amount = tax_total
                            invoice.total_amount = subtotal + tax_total
                            invoice.save()
                            
                            break  # Success, exit retry loop
                            
                    except IntegrityError as e:
                        if attempt < 4:  # Still have retries left
                            time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                            continue
                        else:  # Final attempt failed
                            messages.error(request, f'Failed to create invoice due to duplicate number. Please try again.')
                            form = InvoiceForm(user=request.user)
                            formset = InvoiceItemFormSet(queryset=InvoiceItem.objects.none())
                            context = {
                                'form': form,
                                'formset': formset,
                                'customers': Customer.objects.filter(user=request.user, is_active=True),
                                'products': Product.objects.filter(user=request.user, is_active=True),
                            }
                            return render(request, 'invoicing/invoice_create.html', context)
                    except Exception as e:
                        messages.error(request, f'An error occurred: {str(e)}')
                        form = InvoiceForm(user=request.user)
                        formset = InvoiceItemFormSet(queryset=InvoiceItem.objects.none())
                        context = {
                            'form': form,
                            'formset': formset,
                            'customers': Customer.objects.filter(user=request.user, is_active=True),
                            'products': Product.objects.filter(user=request.user, is_active=True),
                        }
                        return render(request, 'invoicing/invoice_create.html', context)
                
                if not invoice:
                    messages.error(request, 'Failed to create invoice. Please try again.')
                    form = InvoiceForm(user=request.user)
                    formset = InvoiceItemFormSet(queryset=InvoiceItem.objects.none())
                    context = {
                        'form': form,
                        'formset': formset,
                        'customers': Customer.objects.filter(user=request.user, is_active=True),
                        'products': Product.objects.filter(user=request.user, is_active=True),
                    }
                    return render(request, 'invoicing/invoice_create.html', context)
                
                messages.success(request, f'Invoice {invoice.invoice_number} created successfully!')
                return redirect('invoicing:invoice_detail', pk=invoice.pk)
            else:
                messages.error(request, 'Please correct the errors below.')
    else:
        form = InvoiceForm(user=request.user)
        formset = InvoiceItemFormSet(queryset=InvoiceItem.objects.none())
    
    context = {
        'form': form,
        'formset': formset,
        'customers': Customer.objects.filter(user=request.user, is_active=True),
        'products': Product.objects.filter(user=request.user, is_active=True),
    }
    
    return render(request, 'invoicing/invoice_create.html', context)


@login_required
def invoice_edit(request, pk):
    """
    Edit an existing invoice (only draft invoices can be edited)
    """
    import json
    from django.db import transaction
    
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    
    # Only allow editing draft invoices
    if invoice.status != 'draft':
        messages.error(request, 'Only draft invoices can be edited.')
        return redirect('invoicing:invoice_detail', pk=invoice.pk)
    
    if request.method == 'POST':
        # Check if this is a JSON submission
        if request.POST.get('line_items'):
            customer_id = request.POST.get('customer')
            
            if not customer_id:
                messages.error(request, 'Please select a customer for this invoice.')
                context = {
                    'invoice': invoice,
                    'customers': Customer.objects.filter(user=request.user, is_active=True),
                    'products': Product.objects.filter(user=request.user, is_active=True),
                }
                return render(request, 'invoicing/invoice_edit.html', context)
            
            customer = get_object_or_404(Customer, pk=customer_id, user=request.user)
            
            try:
                with transaction.atomic():
                    # Update invoice
                    invoice.customer = customer
                    invoice.date_due = request.POST.get('date_due')
                    invoice.notes = request.POST.get('notes', '')
                    invoice.terms = request.POST.get('terms', '')
                    invoice.status = 'draft' if request.POST.get('action') == 'save_draft' else 'sent'
                    
                    # Delete existing line items
                    invoice.invoiceitem_set.all().delete()
                    
                    # Process new line items
                    line_items = json.loads(request.POST.get('line_items', '[]'))
                    subtotal = Decimal('0')
                    tax_total = Decimal('0')
                    
                    for item_data in line_items:
                        unit_price = item_data.get('unit_price') or item_data.get('rate')
                        
                        if item_data.get('description') and item_data.get('quantity') and unit_price:
                            item = InvoiceItem.objects.create(
                                invoice=invoice,
                                description=item_data['description'],
                                quantity=Decimal(str(item_data['quantity'])),
                                unit_price=Decimal(str(unit_price)),
                                tax_rate=Decimal(str(item_data.get('tax_rate', 0)))
                            )
                            
                            line_total = item.total
                            line_tax = line_total * (item.tax_rate / Decimal('100'))
                            subtotal += line_total
                            tax_total += line_tax
                    
                    # Update invoice totals
                    invoice.subtotal = subtotal
                    invoice.tax_amount = tax_total
                    invoice.total_amount = subtotal + tax_total
                    invoice.save()
                    
                    if request.POST.get('action') == 'save_draft':
                        messages.success(request, f'Invoice {invoice.invoice_number} updated and saved as draft!')
                    else:
                        messages.success(request, f'Invoice {invoice.invoice_number} updated and sent!')
                    
                    return redirect('invoicing:invoice_detail', pk=invoice.pk)
                    
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
    
    # GET request - show the edit form
    # Prepare existing line items for the template
    line_items = [
        {
            'description': item.description,
            'quantity': float(item.quantity),
            'rate': float(item.unit_price),
            'tax_rate': float(item.tax_rate),
            'total': float(item.total)
        }
        for item in invoice.invoiceitem_set.all()
    ]
    
    context = {
        'invoice': invoice,
        'line_items_json': json.dumps(line_items),
        'customers': Customer.objects.filter(user=request.user, is_active=True),
        'products': Product.objects.filter(user=request.user, is_active=True),
    }
    
    return render(request, 'invoicing/invoice_edit.html', context)


@login_required
def customer_list(request):
    """
    Customer management with AI insights
    """
    customers = Customer.objects.filter(user=request.user)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(customers.order_by('name'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'invoicing/customer_list.html', context)


@login_required
def customer_create(request):
    """
    Create new customer with comprehensive form
    """
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.user = request.user
            customer.company = request.company  # Set the active company
            customer.save()
            
            messages.success(request, f'Customer {customer.name} created successfully!')
            
            # If this is an AJAX request (from invoice creation modal)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'customer': {
                        'id': customer.id,
                        'name': customer.name,
                        'company': customer.company,
                        'email': customer.email
                    }
                })
            
            return redirect('invoicing:customer_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomerForm()
    
    context = {'form': form}
    return render(request, 'invoicing/customer_create.html', context)


@login_required
def product_list(request):
    """
    Product/Service management
    """
    # Use company filtering for products as Product model has company field, not user
    company = getattr(request, 'company', None)
    if company:
        products = Product.objects.filter(company=company)
    else:
        # Fallback: get products from all user's companies
        user_companies = request.user.companies.all() if hasattr(request.user, 'companies') else []
        products = Product.objects.filter(company__in=user_companies)
    
    # Search and filter
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
    
    # Category filter
    category_filter = request.GET.get('category', '')
    if category_filter:
        products = products.filter(category=category_filter)
    
    # Low stock alert
    low_stock_products = products.filter(
        track_inventory=True,
        current_stock__lte=F('minimum_stock')
    )
    
    context = {
        'products': products.order_by('name'),
        'low_stock_products': low_stock_products,
        'search_query': search_query,
    }
    
    return render(request, 'invoicing/product_list.html', context)


@login_required
def invoice_pdf(request, pk):
    """
    Generate PDF invoice
    Professional PDF generation vs QuickBooks' basic PDFs
    """
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    
    # Update view count for tracking
    invoice.view_count += 1
    invoice.last_viewed = timezone.now()
    invoice.save(update_fields=['view_count', 'last_viewed'])
    
    context = {
        'invoice': invoice,
        'company_info': {
            'name': 'DreamBiz Accounting',
            'tagline': 'AI-Powered Accounting Platform',
            'email': 'support@dreambizaccounting.com',
            'website': 'www.dreambizaccounting.com'
        }
    }
    
    # Check if user wants actual PDF (future enhancement)
    if request.GET.get('format') == 'pdf':
        # This would use a library like weasyprint or reportlab
        # For now, we'll return HTML with print-friendly styling
        html_content = render_to_string('invoicing/invoice_pdf.html', context, request=request)
        response = HttpResponse(html_content, content_type='text/html')
        response['Content-Disposition'] = f'inline; filename="invoice_{invoice.invoice_number}.html"'
        return response
    
    # Default: return HTML version for browser viewing/printing
    html_content = render_to_string('invoicing/invoice_pdf.html', context, request=request)
    response = HttpResponse(html_content, content_type='text/html')
    response['Content-Disposition'] = f'inline; filename="invoice_{invoice.invoice_number}.html"'
    
    return response


@login_required
def get_product_details(request, product_id):
    """
    API endpoint to get product details for invoice creation
    """
    try:
        product = Product.objects.get(pk=product_id, user=request.user)
        return JsonResponse({
            'name': product.name,
            'description': product.description,
            'unit_price': str(product.unit_price),
            'tax_rate': str(product.tax_rate),
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)


@login_required
def product_create(request):
    """
    Create new product/service
    """
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.user = request.user
            product.company = request.company  # Set the active company
            product.save()
            
            messages.success(request, f'Product {product.name} created successfully!')
            
            # If this is an AJAX request (from invoice creation modal)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'product': {
                        'id': product.id,
                        'name': product.name,
                        'description': product.description,
                        'unit_price': str(product.unit_price),
                        'tax_rate': str(product.tax_rate)
                    }
                })
            
            return redirect('invoicing:product_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm()
    
    context = {'form': form}
    return render(request, 'invoicing/product_create.html', context)


@login_required
def record_payment(request, invoice_id):
    """
    Record a payment for an invoice
    """
    invoice = get_object_or_404(Invoice, pk=invoice_id, user=request.user)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.save()
            
            # Update invoice amount paid
            invoice.amount_paid += payment.amount
            if invoice.amount_paid >= invoice.total_amount:
                invoice.status = 'paid'
            invoice.save()
            
            messages.success(request, f'Payment of GH₵{payment.amount} recorded successfully!')
            return redirect('invoicing:invoice_detail', pk=invoice.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PaymentForm(initial={
            'amount': invoice.balance_due,
            'payment_date': date.today()
        })
    
    context = {
        'form': form,
        'invoice': invoice
    }
    return render(request, 'invoicing/record_payment.html', context)


@login_required
def invoice_send(request, pk):
    """
    Send invoice to customer (mark as sent)
    """
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    
    if invoice.status == 'draft':
        invoice.status = 'sent'
        from django.utils import timezone
        invoice.date_sent = timezone.now()
        invoice.save()
        
        messages.success(request, f'Invoice {invoice.invoice_number} has been sent!')
        
        # TODO: Implement actual email sending
        # send_invoice_email(invoice)
    else:
        messages.warning(request, 'Invoice has already been sent.')
    
    return redirect('invoicing:invoice_detail', pk=invoice.pk)


@login_required
def invoice_delete(request, pk):
    """
    Delete invoice with confirmation
    Only allow deletion of draft invoices or unpaid invoices
    Administrators and Accountants can delete paid invoices
    """
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    
    # Check if user has permission to delete paid invoices
    is_admin_or_accountant = request.user.role in ['admin', 'accountant']
    
    # Business logic: Only allow deletion of paid invoices by admin/accountant
    if invoice.status == 'paid' and not is_admin_or_accountant:
        messages.error(request, 'Cannot delete paid invoices. This would affect your accounting records. Contact an administrator.')
        return redirect('invoicing:invoice_detail', pk=invoice.pk)
    
    if request.method == 'POST':
        invoice_number = invoice.invoice_number
        
        # If deleting a paid invoice, also delete associated journal entries
        if invoice.status == 'paid' and is_admin_or_accountant:
            from reports.models import JournalEntry
            # Delete journal entries created by payments for this invoice
            JournalEntry.objects.filter(invoice=invoice).delete()
            # Also delete payment-specific journal entries
            for payment in invoice.payment_set.all():
                JournalEntry.objects.filter(
                    user=request.user,
                    reference_type='payment',
                    reference_id=payment.id
                ).delete()
            messages.warning(request, 'Associated journal entries have been deleted. This affects your accounting records.')
        
        # Check if there are any payments associated with this invoice (non-admin users)
        if invoice.payment_set.exists() and not is_admin_or_accountant:
            messages.error(request, 'Cannot delete invoice with recorded payments. Please remove payments first or contact an administrator.')
            return redirect('invoicing:invoice_detail', pk=invoice.pk)
        
        # Delete the invoice (cascade will handle related objects including payments)
        invoice.delete()
        
        messages.success(request, f'Invoice {invoice_number} has been deleted successfully.')
        return redirect('invoicing:invoice_list')
    
    # For GET requests, return confirmation page or JSON for AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        can_delete = (invoice.status != 'paid' and not invoice.payment_set.exists()) or is_admin_or_accountant
        return JsonResponse({
            'invoice_number': invoice.invoice_number,
            'customer_name': invoice.customer.name,
            'total_amount': str(invoice.total_amount),
            'can_delete': can_delete,
            'is_paid': invoice.status == 'paid',
            'has_payments': invoice.payment_set.exists()
        })
    
    context = {
        'invoice': invoice,
        'can_delete': (invoice.status != 'paid' and not invoice.payment_set.exists()) or is_admin_or_accountant,
        'is_admin_or_accountant': is_admin_or_accountant
    }
    return render(request, 'invoicing/invoice_delete.html', context)


@login_required
def bulk_delete_invoices(request):
    """
    Bulk delete multiple invoices
    Only allows deletion of non-paid invoices without payments (unless user is admin/accountant)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        invoice_ids = json.loads(request.POST.get('invoice_ids', '[]'))
        
        if not invoice_ids:
            return JsonResponse({'error': 'No invoices selected'}, status=400)
        
        # Check if user has permission to delete paid invoices
        is_admin_or_accountant = request.user.role in ['admin', 'accountant']
        
        # Get invoices that can be deleted
        if is_admin_or_accountant:
            # Admins and accountants can delete any invoice
            deletable_invoices = Invoice.objects.filter(
                pk__in=invoice_ids,
                user=request.user
            )
        else:
            # Regular users can only delete draft/sent/overdue invoices without payments
            deletable_invoices = Invoice.objects.filter(
                pk__in=invoice_ids,
                user=request.user,
                status__in=['draft', 'sent', 'overdue']  # Cannot delete paid invoices
            ).exclude(
                payment__isnull=False  # Cannot delete invoices with payments
            )
        
        deleted_count = 0
        skipped_count = 0
        
        for invoice in deletable_invoices:
            try:
                invoice_number = invoice.invoice_number
                
                # If deleting a paid invoice, also delete associated journal entries
                if invoice.status == 'paid' and is_admin_or_accountant:
                    from reports.models import JournalEntry
                    # Delete journal entries created by payments for this invoice
                    JournalEntry.objects.filter(invoice=invoice).delete()
                    # Also delete payment-specific journal entries
                    for payment in invoice.payment_set.all():
                        JournalEntry.objects.filter(
                            user=request.user,
                            reference_type='payment',
                            reference_id=payment.id
                        ).delete()
                
                invoice.delete()
                deleted_count += 1
                messages.success(request, f'Invoice {invoice_number} deleted successfully.')
            except Exception as e:
                skipped_count += 1
                messages.warning(request, f'Could not delete invoice {invoice.invoice_number}: {str(e)}')
        
        # Check for invoices that were skipped due to business rules
        total_requested = len(invoice_ids)
        skipped_count += total_requested - deleted_count
        
        if skipped_count > 0:
            if is_admin_or_accountant:
                messages.warning(request, f'{skipped_count} invoice(s) could not be deleted due to an error.')
            else:
                messages.warning(request, f'{skipped_count} invoice(s) were skipped (paid invoices or invoices with payments cannot be deleted by regular users).')
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'skipped_count': skipped_count,
            'total_requested': total_requested
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid invoice IDs format'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def bulk_export_invoices(request):
    """
    Bulk export multiple invoices as CSV
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('invoicing:invoice_list')
    
    try:
        invoice_ids = json.loads(request.POST.get('invoice_ids', '[]'))
        
        if not invoice_ids:
            messages.error(request, 'No invoices selected for export.')
            return redirect('invoicing:invoice_list')
        
        # Get the selected invoices
        invoices = Invoice.objects.filter(
            pk__in=invoice_ids,
            user=request.user
        ).select_related('customer').order_by('-date_created')
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="invoices_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        import csv
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Invoice Number',
            'Customer Name',
            'Customer Company',
            'Customer Email',
            'Date Created',
            'Date Due',
            'Status',
            'Subtotal',
            'Tax Amount',
            'Total Amount',
            'Amount Paid',
            'Balance Due',
            'Notes',
            'Terms'
        ])
        
        # Write invoice data
        for invoice in invoices:
            writer.writerow([
                invoice.invoice_number,
                invoice.customer.name,
                invoice.customer.company or '',
                invoice.customer.email,
                invoice.date_created.strftime('%Y-%m-%d'),
                invoice.date_due.strftime('%Y-%m-%d') if invoice.date_due else '',
                invoice.get_status_display(),
                str(invoice.subtotal or 0),
                str(invoice.tax_amount or 0),
                str(invoice.total_amount),
                str(invoice.amount_paid or 0),
                str(invoice.balance_due),
                invoice.notes or '',
                invoice.terms or ''
            ])
        
        messages.success(request, f'{len(invoices)} invoice(s) exported successfully.')
        return response
        
    except json.JSONDecodeError:
        messages.error(request, 'Invalid export data format.')
        return redirect('invoicing:invoice_list')
    except Exception as e:
        messages.error(request, f'Export failed: {str(e)}')
        return redirect('invoicing:invoice_list')


@login_required
def create_sample_data(request):
    """
    Create sample invoicing data for testing
    """
    if not request.user.is_superuser:
        messages.error(request, 'Only administrators can create sample data.')
        return redirect('invoicing:invoice_list')
    
    # Create sample customers
    customers_data = [
        {
            'name': 'John Smith',
            'email': 'john@example.com',
            'company': 'Smith Consulting',
            'phone': '+1 (555) 123-4567',
            'billing_city': 'New York',
            'billing_state': 'NY',
            'payment_terms': 'Net 30'
        },
        {
            'name': 'Sarah Johnson',
            'email': 'sarah@techcorp.com',
            'company': 'TechCorp Inc.',
            'phone': '+1 (555) 987-6543',
            'billing_city': 'San Francisco',
            'billing_state': 'CA',
            'payment_terms': 'Net 15'
        }
    ]
    
    for customer_data in customers_data:
        customer, created = Customer.objects.get_or_create(
            user=request.user,
            email=customer_data['email'],
            defaults=customer_data
        )
        if created:
            messages.success(request, f'Created customer: {customer.name}')
    
    # Create sample products
    products_data = [
        {
            'name': 'Website Design',
            'description': 'Custom website design and development',
            'unit_price': 2500.00,
            'product_type': 'service',
            'tax_rate': 8.25
        },
        {
            'name': 'SEO Optimization',
            'description': 'Search engine optimization services',
            'unit_price': 500.00,
            'product_type': 'service',
            'tax_rate': 8.25
        },
        {
            'name': 'Hosting Setup',
            'description': 'Web hosting setup and configuration',
            'unit_price': 150.00,
            'product_type': 'service',
            'tax_rate': 8.25
        }
    ]
    
    for product_data in products_data:
        product, created = Product.objects.get_or_create(
            user=request.user,
            name=product_data['name'],
            defaults=product_data
        )
        if created:
            messages.success(request, f'Created product: {product.name}')
    
    messages.success(request, 'Sample data created successfully!')
    return redirect('invoicing:invoice_list')


@login_required
def api_customer_create(request):
    """
    API endpoint for creating customers via AJAX
    """
    if request.method == 'POST':
        try:
            # Parse JSON data
            data = json.loads(request.body)
            
            # Validate required fields
            if not data.get('name') or not data.get('email'):
                return JsonResponse({
                    'success': False,
                    'message': 'Name and email are required fields'
                }, status=400)
            
            # Check if customer with this email already exists
            existing_customer = Customer.objects.filter(
                user=request.user,
                email=data.get('email')
            ).first()
            
            if existing_customer:
                return JsonResponse({
                    'success': False,
                    'message': 'A customer with this email already exists'
                }, status=400)
            
            # Create new customer
            customer = Customer.objects.create(
                company=request.company,  # Set the active company (ForeignKey)
                user=request.user,
                name=data.get('name'),
                email=data.get('email'),
                phone=data.get('phone', ''),
                company_name=data.get('company', ''),  # Customer's company name (CharField)
                billing_address_line_1=data.get('address', ''),
                billing_city=data.get('city', ''),
                billing_state=data.get('state', ''),
                billing_postal_code=data.get('zip_code', ''),
                billing_country=data.get('country', 'US'),
                tax_id=data.get('tax_id', ''),
            )
            
            # Return success response with customer data
            return JsonResponse({
                'success': True,
                'message': 'Customer created successfully',
                'id': customer.id,
                'name': customer.name,
                'email': customer.email,
                'company': customer.company_name,  # Return the company name, not the ForeignKey
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Only POST requests are allowed'
    }, status=405)
