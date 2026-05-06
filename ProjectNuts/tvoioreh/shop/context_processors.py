"""
Контекстный процессор, добавляющий в шаблоны количество товаров в корзине.
"""

def cart_count(request):
    cart = request.session.get('cart', {})
    count = sum(item['quantity'] for item in cart.values())
    return {'cart_count': count}