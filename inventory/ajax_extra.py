from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Category, Product


@login_required
def add_category_ajax(request):
    """AJAX endpoint to add new category"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name:
            return JsonResponse({
                'success': False,
                'errors': {'name': ['Category name is required.']}
            })
        
        # Get company
        company = None
        if hasattr(request, 'company') and request.company:
            company = request.company
        else:
            from accounts.models import UserCompany
            user_company = UserCompany.objects.filter(
                user=request.user,
                is_active=True
            ).first()
            if user_company:
                company = user_company.company
            else:
                return JsonResponse({
                    'success': False,
                    'errors': {'general': ['No company associated with your account.']}
                })
        
        # Check if category already exists for this company
        if Category.objects.filter(company=company, name=name).exists():
            return JsonResponse({
                'success': False,
                'errors': {'name': ['A category with this name already exists.']}
            })
        
        try:
            category = Category.objects.create(
                company=company,
                name=name,
                description=description
            )
            
            return JsonResponse({
                'success': True,
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'value': category.id,
                    'label': category.name
                }
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'errors': {'general': [str(e)]}
            })
    
    return JsonResponse({'success': False})


@login_required
def barcode_lookup(request):
    """AJAX endpoint to lookup product by barcode"""
    barcode = request.GET.get('barcode', '').strip()
    
    if not barcode:
        return JsonResponse({
            'success': False,
            'error': 'Barcode is required'
        })
    
    try:
        # Get company
        company = None
        if hasattr(request, 'company') and request.company:
            company = request.company
        else:
            from accounts.models import UserCompany
            user_company = UserCompany.objects.filter(
                user=request.user,
                is_active=True
            ).first()
            if user_company:
                company = user_company.company
        
        if company:
            # Check if product with this barcode already exists in the company
            existing_product = Product.objects.filter(
                company=company,
                barcode=barcode
            ).first()
            
            if existing_product:
                return JsonResponse({
                    'success': True,
                    'exists': True,
                    'product': {
                        'name': existing_product.name,
                        'sku': existing_product.sku,
                        'cost_price': str(existing_product.cost_price),
                        'selling_price': str(existing_product.selling_price)
                    }
                })
        
        # If not exists, return success with suggestion to create new
        return JsonResponse({
            'success': True,
            'exists': False,
            'suggestion': {
                'name': f'Product with barcode {barcode}',
                'sku': f'PROD-{barcode[:8]}' if len(barcode) >= 8 else f'PROD-{barcode}'
            }
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })