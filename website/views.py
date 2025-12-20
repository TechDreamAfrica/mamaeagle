from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from accounts.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, F, Sum
from django.db import transaction
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.http import require_POST
from django.urls import reverse
from functools import wraps
from .models import Product, ProductCategory, Cart, CartItem, Order, OrderItem, Newsletter, ContactMessage
from .forms import ContactForm, NewsletterForm, CheckoutForm, CustomerRegistrationForm, CustomerLoginForm, CustomerProfileForm
from invoicing.models import Product as InvoiceProduct
import json


def customer_login_required(view_func):
    """Custom decorator that redirects to customer login page"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = reverse('website:customer_login')
            return redirect(f"{login_url}?next={request.get_full_path()}")
        return view_func(request, *args, **kwargs)
    return wrapper


class ProductListView(ListView):
    """Display all products with filtering and search"""
    model = Product
    template_name = 'website/products/list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(short_description__icontains=search_query)
            )
        
        # Category filtering
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Price filtering
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Sorting
        sort_by = self.request.GET.get('sort', 'name')
        if sort_by == 'price_low':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('name')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ProductCategory.objects.filter(is_active=True, parent=None)
        context['current_category'] = self.request.GET.get('category')
        context['search_query'] = self.request.GET.get('search', '')
        return context


class ProductDetailView(DetailView):
    """Display product details"""
    model = Product
    template_name = 'website/products/detail.html'
    context_object_name = 'product'
    
    def get_queryset(self):
        return Product.objects.filter(is_active=True).prefetch_related('images')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_products'] = Product.objects.filter(
            category=self.object.category,
            is_active=True
        ).exclude(id=self.object.id)[:4]
        return context


def home(request):
    """Homepage with featured products"""
    from django.db.models import Count, Avg
    
    # Get featured products (using latest or highest priced as featured)
    featured_products = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
    categories = ProductCategory.objects.filter(is_active=True)[:8]  # Show all categories
    latest_products = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
    
    # Real database statistics
    total_products = Product.objects.filter(is_active=True).count()
    total_orders = Order.objects.count()
    total_customers = User.objects.filter(order__isnull=False).distinct().count()
    
    # Calculate average rating (placeholder since we don't have reviews yet)
    # For now, use a calculated average based on order count and customer satisfaction
    if total_orders > 0:
        avg_rating = min(4.8, 3.5 + (total_orders / 100))  # Simulated rating based on orders
    else:
        avg_rating = 4.0
    
    stats = {
        'total_products': f"{total_products:,}",
        'total_orders': f"{total_orders:,}",
        'total_customers': f"{total_customers:,}",
        'avg_rating': round(avg_rating, 1),
    }
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'latest_products': latest_products,
        'stats': stats,
    }
    return render(request, 'website/home.html', context)


def about(request):
    """About us page with real statistics"""
    from django.db.models import Count, Avg
    from accounts.models import User
    
    # Get real statistics from database
    total_products = Product.objects.count()
    total_users = User.objects.count()  # Happy customers
    total_orders = Order.objects.count()  # Total orders
    delivered_orders = Order.objects.filter(status='delivered').count()
    
    # Calculate average rating (placeholder - you can implement real rating system later)
    avg_rating = 4.7
    
    context = {
        'stats': {
            'products': total_products,
            'customers': total_users,
            'orders': delivered_orders,  # Show delivered orders as success metric
            'rating': avg_rating,
            'total_orders': total_orders,
        }
    }
    
    return render(request, 'website/about.html', context)


def contact(request):
    """Contact page with form"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_message = form.save()
            
            # Send email notification (optional)
            try:
                send_mail(
                    f'New Contact Message: {contact_message.subject}',
                    f'From: {contact_message.name} ({contact_message.email})\n\n{contact_message.message}',
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.ADMIN_EMAIL] if hasattr(settings, 'ADMIN_EMAIL') else ['admin@mamaeagle.com'],
                    fail_silently=True
                )
            except:
                pass
            
            messages.success(request, 'Thank you for your message! We will get back to you soon.')
            return redirect('website:contact')
    else:
        form = ContactForm()
    
    return render(request, 'website/contact.html', {'form': form})


def newsletter_subscribe(request):
    """Newsletter subscription"""
    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            newsletter, created = Newsletter.objects.get_or_create(
                email=email,
                defaults={'is_active': True}
            )
            
            if created:
                messages.success(request, 'Successfully subscribed to our newsletter!')
            else:
                messages.info(request, 'You are already subscribed to our newsletter.')
            
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    
    return JsonResponse({'success': False})


@customer_login_required
@customer_login_required
def add_to_cart(request, product_id):
    """Add product to cart"""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # Validate stock availability
        if not product.in_stock:
            return JsonResponse({
                'success': False,
                'message': 'Product is out of stock'
            })
        
        # Handle both JSON and form data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            quantity = int(data.get('quantity', 1))
        else:
            quantity = int(request.POST.get('quantity', 1))
        
        # Validate quantity
        if quantity < 1:
            return JsonResponse({
                'success': False,
                'message': 'Invalid quantity'
            })
            
        if product.track_inventory and quantity > product.stock_quantity:
            return JsonResponse({
                'success': False,
                'message': f'Only {product.stock_quantity} items available in stock'
            })
        
        # Get or create cart for authenticated user
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            # Check total quantity doesn't exceed stock
            new_quantity = cart_item.quantity + quantity
            if product.track_inventory and new_quantity > product.stock_quantity:
                return JsonResponse({
                    'success': False,
                    'message': f'Cannot add {quantity} more. Only {product.stock_quantity - cart_item.quantity} available.'
                })
            cart_item.quantity = new_quantity
            cart_item.save()
        
        # Update cart item count in session for header display
        cart_count = cart.items.aggregate(total=Sum('quantity'))['total'] or 0
        request.session['cart_count'] = cart_count
        
        messages.success(request, f'{product.name} added to cart!')
        return JsonResponse({
            'success': True, 
            'cart_items': cart_count,
            'cart_total': float(cart.total_amount),
            'message': f'{product.name} added to cart!'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@customer_login_required
def view_cart(request):
    """View shopping cart with related products"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.all().select_related('product', 'product__category')
        # Update session cart count
        request.session['cart_count'] = cart_items.count()
        
        # Get related products based on cart items
        if cart_items.exists():
            # Get categories from cart items
            cart_categories = [item.product.category for item in cart_items if item.product.category]
            
            # Get related products from same categories, excluding items already in cart
            cart_product_ids = [item.product.id for item in cart_items]
            related_products = Product.objects.filter(
                category__in=cart_categories,
                is_active=True
            ).exclude(
                id__in=cart_product_ids
            ).order_by('?')[:8]  # Random order, limit 8
            
            # If not enough related products, add popular products
            if related_products.count() < 6:
                additional_products = Product.objects.filter(
                    is_active=True,
                    is_featured=True
                ).exclude(
                    id__in=cart_product_ids
                ).exclude(
                    id__in=[p.id for p in related_products]
                )[:6]
                related_products = list(related_products) + list(additional_products)
        else:
            # For empty cart, show featured/popular products
            related_products = Product.objects.filter(
                is_active=True,
                is_featured=True
            ).order_by('?')[:8]
            
    except Cart.DoesNotExist:
        cart = None
        cart_items = []
        request.session['cart_count'] = 0
        # Show popular products for users with no cart
        related_products = Product.objects.filter(
            is_active=True,
            is_featured=True
        ).order_by('?')[:8]
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'recommended_products': related_products,
    }
    return render(request, 'website/orders/cart.html', context)


@customer_login_required
def update_cart_item(request, item_id):
    """Update cart item quantity with complete cart data"""
    if request.method == 'POST':
        try:
            cart_item = CartItem.objects.get(
                id=item_id,
                cart__user=request.user
            )
            quantity = int(request.POST.get('quantity', 1))
            
            if quantity > 0:
                cart_item.quantity = quantity
                cart_item.save()
                
                # Get cart with updated totals
                cart = cart_item.cart
                cart_items = cart.items.all()
                cart_count = cart_items.count()
                
                # Calculate totals
                subtotal = sum(item.get_total_price() for item in cart_items)
                shipping = 0 if subtotal >= 500 else 25
                total = subtotal + shipping
                
                # Update session
                request.session['cart_count'] = cart_count
                
                return JsonResponse({
                    'success': True,
                    'item_total': float(cart_item.get_total_price()),
                    'cart_subtotal': float(subtotal),
                    'cart_total': float(total),
                    'cart_items': cart_count,
                    'shipping_cost': float(shipping)
                })
            else:
                cart_item.delete()
                cart = Cart.objects.get(user=request.user)
                cart_items = cart.items.all()
                cart_count = cart_items.count()
                
                # Calculate totals after removal
                subtotal = sum(item.get_total_price() for item in cart_items)
                shipping = 0 if subtotal >= 500 else 25
                total = subtotal + shipping
                
                request.session['cart_count'] = cart_count
                
                return JsonResponse({
                    'success': True,
                    'cart_subtotal': float(subtotal),
                    'cart_total': float(total),
                    'cart_items': cart_count,
                    'shipping_cost': float(shipping)
                })
                
        except (CartItem.DoesNotExist, ValueError):
            return JsonResponse({'success': False, 'message': 'Item not found or invalid quantity'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@customer_login_required
def remove_from_cart(request, item_id):
    """Remove item from cart with JSON response for AJAX"""
    if request.method == 'POST':
        try:
            cart_item = CartItem.objects.get(
                id=item_id,
                cart__user=request.user
            )
            cart_item.delete()
            
            # Get updated cart data
            try:
                cart = Cart.objects.get(user=request.user)
                cart_items = cart.items.all()
                cart_count = cart_items.count()
                
                # Calculate totals after removal
                subtotal = sum(item.get_total_price() for item in cart_items)
                shipping = 0 if subtotal >= 500 else 25
                total = subtotal + shipping
                
                request.session['cart_count'] = cart_count
                
                return JsonResponse({
                    'success': True,
                    'cart_subtotal': float(subtotal),
                    'cart_total': float(total),
                    'cart_items': cart_count,
                    'shipping_cost': float(shipping),
                    'message': 'Item removed from cart.'
                })
                
            except Cart.DoesNotExist:
                request.session['cart_count'] = 0
                return JsonResponse({
                    'success': True,
                    'cart_subtotal': 0.0,
                    'cart_total': 0.0,
                    'cart_items': 0,
                    'shipping_cost': 0.0,
                    'message': 'Cart is now empty.'
                })
                
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Item not found.'})
    
    # Fallback for non-AJAX requests
    try:
        cart_item = CartItem.objects.get(
            id=item_id,
            cart__user=request.user
        )
        cart_item.delete()
        messages.success(request, 'Item removed from cart.')
    except CartItem.DoesNotExist:
        messages.error(request, 'Item not found.')
    
    return redirect('website:cart_view')


@customer_login_required
def checkout(request):
    """Checkout process with payment mode selection"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.all().select_related('product')
        
        if not cart_items:
            messages.error(request, 'Your cart is empty.')
            return redirect('website:cart_view')
        
        # Calculate totals
        subtotal = cart.total_amount
        shipping_cost = 0 if subtotal >= 500 else 25
        total_amount = subtotal + shipping_cost
        
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty.')
        return redirect('website:cart_view')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                payment_method = form.cleaned_data['payment_method']
                
                # Generate order number
                import uuid
                order_number = f"ME{str(uuid.uuid4()).replace('-', '').upper()[:10]}"
                
                # Create order with updated fields
                order = Order.objects.create(
                    order_number=order_number,
                    user=request.user,
                    customer_email=form.cleaned_data['email'],
                    customer_name=f"{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}",
                    customer_phone=form.cleaned_data['phone'],
                    billing_address=form.cleaned_data['billing_address'],
                    billing_city=form.cleaned_data['billing_city'],
                    billing_state=form.cleaned_data['billing_state'],
                    billing_postal_code=form.cleaned_data['billing_postal_code'],
                    billing_country=form.cleaned_data['billing_country'],
                    shipping_address=form.cleaned_data.get('shipping_address') or f"{form.cleaned_data['address_line_1']}, {form.cleaned_data.get('address_line_2', '')}".strip(', '),
                    shipping_city=form.cleaned_data.get('shipping_city') or form.cleaned_data['city'],
                    shipping_state=form.cleaned_data.get('shipping_state') or form.cleaned_data['region'],
                    shipping_postal_code=form.cleaned_data.get('shipping_postal_code') or form.cleaned_data.get('postal_code', ''),
                    shipping_country=form.cleaned_data.get('shipping_country') or 'Ghana',
                    subtotal=subtotal,
                    shipping_cost=shipping_cost,
                    total_amount=total_amount,
                    payment_method=payment_method,
                    status='pending',
                    notes=form.cleaned_data.get('notes', '')
                )
                
                # Create order items
                for cart_item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        unit_price=cart_item.product.price
                    )
                
                # Handle payment based on method
                if payment_method == 'cash':
                    # Cash on delivery - complete the order
                    order.status = 'processing'
                    order.save()
                    
                    # Update product stock
                    for cart_item in cart_items:
                        if cart_item.product.track_inventory:
                            if cart_item.product.stock_quantity >= cart_item.quantity:
                                cart_item.product.stock_quantity -= cart_item.quantity
                                cart_item.product.save()
                    
                    # Clear cart
                    cart.delete()
                    request.session.pop('cart_count', None)
                    
                    messages.success(request, f'Order {order.order_number} placed successfully! We will contact you for delivery arrangements.')
                    return redirect('website:order_success', order_number=order.order_number)
                    
                elif payment_method == 'paystack':
                    # Online payment - redirect to Paystack
                    # Store order reference for verification
                    order.payment_reference = order.order_number
                    order.save()
                    return redirect('website:paystack_payment', order_number=order.order_number)
                    
            except Exception as e:
                messages.error(request, f'Error creating order: {str(e)}')
                return render(request, 'website/orders/checkout.html', {
                    'form': form,
                    'cart': cart,
                    'cart_items': cart_items,
                    'subtotal': subtotal,
                    'shipping_cost': shipping_cost,
                    'total_amount': total_amount,
                    'free_shipping_threshold': 500,
                })
        else:
            # Form validation errors
            messages.error(request, 'Please correct the errors below.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            
    else:
        # Pre-fill form with user information if available
        initial_data = {}
        if request.user.first_name:
            initial_data['first_name'] = request.user.first_name
        if request.user.last_name:
            initial_data['last_name'] = request.user.last_name
        if request.user.email:
            initial_data['email'] = request.user.email
        
        form = CheckoutForm(initial=initial_data)
    
    context = {
        'form': form,
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total_amount': total_amount,
        'free_shipping_threshold': 500,
    }
    return render(request, 'website/orders/checkout.html', context)


@customer_login_required
def order_success(request, order_number):
    """Order success page"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'website/orders/order_success.html', {'order': order})


@customer_login_required
def paystack_payment(request, order_number):
    """Initialize Paystack payment"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    if order.status != 'pending':
        messages.error(request, 'This order has already been processed.')
        return redirect('website:order_detail', order_number=order.order_number)
    
    # Paystack configuration (these should be in settings)
    PAYSTACK_PUBLIC_KEY = getattr(settings, 'PAYSTACK_PUBLIC_KEY', 'pk_test_your_key_here')
    PAYSTACK_SECRET_KEY = getattr(settings, 'PAYSTACK_SECRET_KEY', 'sk_test_your_key_here')
    
    # Convert amount to kobo (multiply by 100)
    amount_in_kobo = int(order.total_amount * 100)
    
    context = {
        'order': order,
        'paystack_public_key': PAYSTACK_PUBLIC_KEY,
        'amount_in_kobo': amount_in_kobo,
        'callback_url': request.build_absolute_uri(reverse('website:paystack_callback')),
    }
    return render(request, 'website/payment/paystack.html', context)


@customer_login_required
def paystack_callback(request):
    """Handle Paystack payment callback"""
    reference = request.GET.get('reference')
    
    if not reference:
        messages.error(request, 'Payment reference not found.')
        return redirect('website:cart_view')
    
    # Verify payment with Paystack API
    import requests
    
    PAYSTACK_SECRET_KEY = getattr(settings, 'PAYSTACK_SECRET_KEY', 'sk_test_your_key_here')
    
    headers = {
        'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }
    
    try:
        response = requests.get(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data['status'] and data['data']['status'] == 'success':
                # Find order by reference (stored in payment_reference)
                try:
                    order = Order.objects.get(payment_reference=reference)
                    
                    if order.status == 'pending':
                        # Payment successful - complete the order
                        order.status = 'processing'
                        order.save()
                        
                        # Update product stock
                        for order_item in order.items.all():
                            if order_item.product.track_inventory:
                                if order_item.product.stock_quantity >= order_item.quantity:
                                    order_item.product.stock_quantity -= order_item.quantity
                                    order_item.product.save()
                        
                        # Clear cart if it exists
                        try:
                            cart = Cart.objects.get(user=request.user)
                            cart.delete()
                            request.session.pop('cart_count', None)
                        except Cart.DoesNotExist:
                            pass
                        
                        messages.success(request, f'Payment successful! Order {order.order_number} confirmed.')
                        return redirect('website:order_success', order_number=order.order_number)
                    else:
                        messages.info(request, 'This order has already been processed.')
                        return redirect('website:order_detail', order_number=order.order_number)
                        
                except Order.DoesNotExist:
                    messages.error(request, 'Order not found.')
                    return redirect('website:cart_view')
            else:
                messages.error(request, 'Payment verification failed. Please contact support.')
                return redirect('website:cart_view')
        else:
            messages.error(request, 'Unable to verify payment. Please contact support.')
            return redirect('website:cart_view')
            
    except requests.RequestException:
        messages.error(request, 'Payment verification failed due to network error. Please contact support.')
        return redirect('website:cart_view')


@customer_login_required
def order_history(request):
    """User order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'website/orders/history.html', {'orders': orders})


@customer_login_required
def order_detail(request, order_number):
    """Order details"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'website/orders/detail.html', {'order': order})


def download_invoice(request, order_number):
    """Download order invoice as PDF"""
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    
    # Get order without user restriction for testing
    order = get_object_or_404(Order, order_number=order_number)
    
    # Create invoice HTML
    invoice_html = render_to_string('website/orders/invoice.html', {
        'order': order,
        'company_name': 'Mama Eagle Enterprise',
        'company_address': 'Ghana - Professional Plumbing Solutions',
        'company_phone': '+233 XXX XXX XXX',
        'company_email': 'info@mamaeagle.com'
    })
    
    response = HttpResponse(content_type='text/html')
    response['Content-Disposition'] = f'inline; filename="invoice-{order.order_number}.html"'
    response.write(invoice_html)
    return response


def sync_product_to_invoice_app(website_product):
    """
    Sync website product to invoice app for real-time inventory tracking
    This creates or updates the corresponding product in the invoicing app
    """
    try:
        # Get the first available company for sync (since website doesn't require branch assignment)
        from accounts.models import Company
        company = Company.objects.filter(is_active=True).first()
        
        if not company:
            return None
            
        # Check if invoice product already exists
        invoice_product, created = InvoiceProduct.objects.get_or_create(
            company=company,
            sku=website_product.sku or f"WEB-{website_product.id}",
            defaults={
                'user': company.users.first(),
                'name': website_product.name,
                'description': website_product.description or website_product.short_description,
                'unit_price': website_product.price,
                'cost_price': getattr(website_product, 'cost_price', 0),
                'track_inventory': True,
                'current_stock': website_product.stock_quantity,
                'minimum_stock': 10,  # Default minimum stock
                'category': website_product.category.name if website_product.category else '',
                'product_type': 'product',
                'is_active': website_product.is_active,
            }
        )
        
        # If product already exists, update the stock quantity
        if not created:
            invoice_product.current_stock = website_product.stock_quantity
            invoice_product.unit_price = website_product.price
            invoice_product.is_active = website_product.is_active
            invoice_product.save()
        
        return invoice_product
        
    except Exception as e:
        # Log the error but don't break the flow
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error syncing product {website_product.id} to invoice app: {e}")
        return None


def deduct_inventory_for_invoice(invoice_item):
    """
    Deduct inventory from website product when invoice item is added
    This ensures real-time inventory tracking between invoice and website
    """
    try:
        if not invoice_item.product:
            return False
            
        # Find corresponding website product by SKU
        sku = invoice_item.product.sku
        if sku and sku.startswith('WEB-'):
            # Extract website product ID from SKU
            website_product_id = sku.replace('WEB-', '')
            try:
                website_product = Product.objects.get(id=website_product_id)
            except Product.DoesNotExist:
                return False
        else:
            # Try to find by SKU or name
            website_product = Product.objects.filter(
                Q(sku=sku) | Q(name=invoice_item.product.name)
            ).first()
            
        if not website_product:
            return False
            
        # Check if we have enough stock
        if website_product.stock_quantity < invoice_item.quantity:
            return False
            
        # Deduct the quantity using atomic transaction
        with transaction.atomic():
            website_product.stock_quantity = F('stock_quantity') - invoice_item.quantity
            website_product.save()
            
            # Update the invoice product stock as well
            invoice_item.product.current_stock = F('current_stock') - invoice_item.quantity
            invoice_item.product.save()
            
        return True
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error deducting inventory for invoice item {invoice_item.id}: {e}")
        return False


@require_POST
def sync_products_to_invoice(request):
    """
    API endpoint to sync all website products to invoice app
    This can be called manually or scheduled
    """
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
        
    try:
        products = Product.objects.filter(is_active=True)
        synced_count = 0
        
        for product in products:
            if sync_product_to_invoice_app(product):
                synced_count += 1
                
        return JsonResponse({
            'success': True,
            'message': f'Successfully synced {synced_count} products to invoice app'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error syncing products: {str(e)}'
        })


@require_POST  
def check_invoice_inventory(request):
    """
    API endpoint for invoice app to check website inventory before adding items
    This ensures real-time inventory validation
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        
        if not product_id:
            return JsonResponse({'success': False, 'message': 'Product ID required'})
            
        # Find website product
        try:
            invoice_product = InvoiceProduct.objects.get(id=product_id)
            
            # Find corresponding website product
            if invoice_product.sku and invoice_product.sku.startswith('WEB-'):
                website_product_id = invoice_product.sku.replace('WEB-', '')
                website_product = Product.objects.get(id=website_product_id)
            else:
                website_product = Product.objects.filter(
                    Q(sku=invoice_product.sku) | Q(name=invoice_product.name)
                ).first()
                
            if not website_product:
                return JsonResponse({
                    'success': False,
                    'available_quantity': 0,
                    'message': 'Product not found in website inventory'
                })
                
            # Check availability
            available = website_product.stock_quantity >= quantity
            
            return JsonResponse({
                'success': True,
                'available': available,
                'available_quantity': website_product.stock_quantity,
                'requested_quantity': quantity,
                'message': 'OK' if available else 'Insufficient stock'
            })
            
        except (InvoiceProduct.DoesNotExist, Product.DoesNotExist):
            return JsonResponse({
                'success': False,
                'message': 'Product not found'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error checking inventory: {str(e)}'
        })


def get_products_for_invoice_autocomplete(request):
    """
    API endpoint for invoice app to get product suggestions with real-time stock info
    This provides filtered product list for invoice item creation
    """
    query = request.GET.get('q', '')
    
    # Search website products
    products = Product.objects.filter(
        is_active=True,
        stock_quantity__gt=0
    )
    
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    products = products.select_related('category')[:20]  # Limit results
    
    results = []
    for product in products:
        # Get corresponding invoice product if it exists
        invoice_product = None
        try:
            if product.sku:
                invoice_product = InvoiceProduct.objects.get(sku=product.sku)
            else:
                # Find by auto-generated SKU
                sku = f"WEB-{product.id}"
                invoice_product = InvoiceProduct.objects.get(sku=sku)
        except InvoiceProduct.DoesNotExist:
            # Create invoice product if it doesn't exist
            invoice_product = sync_product_to_invoice_app(product)
        
        if invoice_product:
            results.append({
                'id': invoice_product.id,
                'name': product.name,
                'sku': product.sku or f"WEB-{product.id}",
                'price': float(product.price),
                'stock_quantity': product.stock_quantity,
                'category': product.category.name if product.category else '',
                'description': product.short_description or product.description[:100],
            })
    
    return JsonResponse({'results': results})


# Customer Authentication Views
def customer_register(request):
    """Customer registration for e-commerce"""
    if request.user.is_authenticated:
        return redirect('website:home')
        
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('website:customer_login')
    else:
        form = CustomerRegistrationForm()
    
    return render(request, 'website/auth/register.html', {'form': form})


def customer_login(request):
    """Customer login for e-commerce"""
    if request.user.is_authenticated:
        next_url = request.GET.get('next', 'website:home')
        return redirect(next_url)
        
    if request.method == 'POST':
        form = CustomerLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                next_url = request.GET.get('next', 'website:home')
                return redirect(next_url)
    else:
        form = CustomerLoginForm()
    
    return render(request, 'website/auth/login.html', {'form': form})


def customer_logout(request):
    """Customer logout for e-commerce"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('website:home')


@customer_login_required
def customer_profile(request):
    """Customer profile management"""
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('website:customer_profile')
    else:
        form = CustomerProfileForm(instance=request.user)
    
    # Get customer orders
    orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    context = {
        'form': form,
        'orders': orders,
    }
    return render(request, 'website/auth/profile.html', context)


def cart_count_api(request):
    """API endpoint to get cart item count"""
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})
    
    try:
        cart = Cart.objects.get(user=request.user)
        count = cart.items.aggregate(total=Sum('quantity'))['total'] or 0
        return JsonResponse({'count': count})
    except Cart.DoesNotExist:
        return JsonResponse({'count': 0})