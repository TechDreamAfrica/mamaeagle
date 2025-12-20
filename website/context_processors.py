"""
Context processors for website
"""
from django.db.models import Sum
from .models import Cart


def cart_context(request):
    """Add cart context to all templates"""
    cart_count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_count = cart.items.aggregate(total=Sum('quantity'))['total'] or 0
        except Cart.DoesNotExist:
            cart_count = 0
    else:
        cart_count = request.session.get('cart_count', 0)
    
    return {
        'cart_count': cart_count
    }