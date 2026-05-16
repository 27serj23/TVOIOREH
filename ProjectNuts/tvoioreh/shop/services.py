"""
Сервисный слой интернет-магазина «Твой орех».
Содержит всю бизнес-логику: работа с товарами, корзиной, заказами, профилями.
"""
from django.db import transaction
from django.db.models import Sum, F
from django.utils.text import slugify
from decimal import Decimal

from .models import Product, Order, OrderItem, Profile


# ------------------------------------------------------------
# Товары
# ------------------------------------------------------------
def generate_unique_slug(name, exclude_pk=None):
    """
    Генерирует уникальный slug на основе названия товара.
    Использует один запрос к БД для поиска существующих slug'ов.
    """
    base_slug = slugify(name)
    if not base_slug:          # если название целиком на кириллице / спецсимволах
        base_slug = 'product'

    # Находим все slug, начинающиеся с base_slug
    queryset = Product.objects.filter(slug__startswith=base_slug)
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)

    existing_slugs = set(queryset.values_list('slug', flat=True))

    if base_slug not in existing_slugs:
        return base_slug

    counter = 1
    while f"{base_slug}-{counter}" in existing_slugs:
        counter += 1
    return f"{base_slug}-{counter}"


def fill_missing_slugs():
    """Заполняет slug у товаров, где он пуст."""
    products = Product.objects.filter(slug='')
    for product in products:
        product.slug = generate_unique_slug(product.name, exclude_pk=product.pk)
        # Сохраняем без вызова save(), чтобы не триггерить логику модели повторно
        Product.objects.filter(pk=product.pk).update(slug=product.slug)


def search_products(query):
    """Поиск товаров по названию (без учёта регистра)."""
    if query:
        return Product.objects.filter(name__icontains=query)
    return Product.objects.all()


# ------------------------------------------------------------
# Профиль
# ------------------------------------------------------------
def get_or_create_profile(user):
    """Получает или создаёт профиль пользователя."""
    profile, created = Profile.objects.get_or_create(user=user)
    return profile


# ------------------------------------------------------------
# Корзина
# ------------------------------------------------------------
def build_cart_items(cart, product_dict):
    """
    Строит список позиций корзины и общую сумму.
    Используется и в cart_view, и в checkout.
    """
    items = []
    total = Decimal('0.00')
    for product_id_str, data in cart.items():
        product_id = int(product_id_str)
        product = product_dict.get(product_id)
        if product:
            quantity = data['quantity']
            subtotal = product.price * quantity
            total += subtotal
            items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal,
            })
    return items, total


def get_cart_data(cart):
    """
    Получает данные корзины из сессии.
    Возвращает словарь продуктов и общую информацию о корзине.
    """
    if not cart:
        return {}, [], Decimal('0.00')

    product_ids = [int(pid) for pid in cart.keys()]
    products = Product.objects.filter(id__in=product_ids)
    product_dict = {p.id: p for p in products}
    items, total = build_cart_items(cart, product_dict)
    return product_dict, items, total


# ------------------------------------------------------------
# Заказы
# ------------------------------------------------------------
@transaction.atomic
def create_order_from_cart(user, cart, product_dict):
    """
    Создаёт заказ из корзины.
    Использует транзакцию и bulk_create для эффективности.
    """
    if not cart:
        raise ValueError('Корзина пуста')

    profile = get_or_create_profile(user)

    # Создаём заказ
    order = Order.objects.create(
        user=user,
        delivery_address=profile.address
    )

    # Готовим позиции заказа
    order_items = []
    for product_id_str, data in cart.items():
        product_id = int(product_id_str)
        product = product_dict.get(product_id)
        if product:
            order_items.append(OrderItem(
                order=order,
                product=product,
                quantity=data['quantity'],
                price=product.price
            ))

    # Массовое создание (один INSERT вместо N)
    OrderItem.objects.bulk_create(order_items)

    # Пересчитываем итог заказа
    recalculate_order_total(order)

    return order


def recalculate_order_total(order):
    """
    Пересчитывает итоговую сумму заказа на стороне БД.
    Использует агрегацию с F-выражениями.
    """
    total = OrderItem.objects.filter(order=order).aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or Decimal('0.00')

    order.total_price = total
    order.save(update_fields=['total_price'])
    return total


def delete_order_item(item_id, user):
    """
    Удаляет позицию заказа с проверками прав.
    Возвращает (success, message).
    """
    from django.shortcuts import get_object_or_404

    order_item = get_object_or_404(OrderItem, id=item_id)
    order = order_item.order

    if order.user != user:
        return False, 'Вы не можете удалять чужие заказы.'

    if order.status != 'pending':
        return False, 'Можно удалять товары только из необработанных заказов.'

    product_name = order_item.product.name
    order_item.delete()

    if order.items.count() == 0:
        order.delete()
        return True, f'Товар "{product_name}" удалён. Заказ полностью отменён.'
    else:
        recalculate_order_total(order)
        return True, f'Товар "{product_name}" удалён из заказа.'


def get_user_orders(user):
    """Получает заказы пользователя с предзагрузкой позиций и товаров."""
    orders = Order.objects.filter(user=user).prefetch_related(
        'items__product'
    ).order_by('-created_at')

    orders_with_items = []
    for order in orders:
        items_list = [
            {
                'id': item.id,
                'product': item.product,
                'quantity': item.quantity,
                'price': item.price,
                'total': item.item_total,
            }
            for item in order.items.all()
        ]
        orders_with_items.append({
            'order': order,
            'order_items': items_list,
        })
    return orders_with_items
