"""
Представления интернет-магазина «Твой орех».
View только принимает запрос, вызывает сервисный слой и возвращает ответ.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import Product
from .forms import UserRegistrationForm, UserEditForm, ProfileEditForm
from .services import (
    fill_missing_slugs, search_products,
    get_cart_data, create_order_from_cart,
    delete_order_item, get_or_create_profile,
    get_user_orders, recalculate_order_total
)


def index(request):
    """Главная страница со списком товаров и поиском."""
    # Заполняем slug только если их нет (административная операция)
    fill_missing_slugs()

    query = request.GET.get('q', '').strip()
    products = search_products(query)

    return render(request, 'shop/index.html', {
        'products': products,
        'query': query
    })


def product_detail(request, slug):
    """Страница отдельного товара."""
    product = get_object_or_404(Product, slug=slug)
    return render(request, 'shop/product_detail.html', {'product': product})


@require_POST
def add_to_cart(request, product_id):
    """Добавление товара в корзину (только POST)."""
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)

    if product_id_str in cart:
        cart[product_id_str]['quantity'] += 1
    else:
        cart[product_id_str] = {
            'quantity': 1,
            'price': str(product.price),
            'name': product.name
        }

    request.session['cart'] = cart
    request.session.modified = True
    messages.success(request, f'Товар "{product.name}" добавлен в корзину')
    return redirect('cart_view')


def cart_view(request):
    """Просмотр корзины."""
    cart = request.session.get('cart', {})
    product_dict, items, total = get_cart_data(cart)
    return render(request, 'shop/cart.html', {'items': items, 'total': total})


@require_POST
def remove_from_cart(request, product_id):
    """Удаление товара из корзины (только POST)."""
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)

    if product_id_str in cart:
        del cart[product_id_str]
        request.session['cart'] = cart
        request.session.modified = True
        messages.success(request, 'Товар удалён из корзины')

    return redirect('cart_view')


@require_POST
def update_cart(request, product_id):
    """Обновление количества товара в корзине (только POST)."""
    try:
        quantity = int(request.POST.get('quantity', 0))
    except (ValueError, TypeError):
        quantity = 0

    cart = request.session.get('cart', {})
    product_id_str = str(product_id)

    if quantity <= 0:
        cart.pop(product_id_str, None)
    elif product_id_str in cart:
        cart[product_id_str]['quantity'] = quantity

    request.session['cart'] = cart
    request.session.modified = True
    messages.success(request, 'Корзина обновлена')
    return redirect('cart_view')


@login_required
def checkout(request):
    """Оформление заказа."""
    cart = request.session.get('cart', {})
    product_dict, items, total = get_cart_data(cart)

    if not cart:
        messages.error(request, 'Корзина пуста')
        return redirect('index')

    profile = get_or_create_profile(request.user)

    if request.method == 'POST':
        try:
            order = create_order_from_cart(request.user, cart, product_dict)
            request.session['cart'] = {}
            request.session.modified = True
            messages.success(request, f'Заказ #{order.id} оформлен! Доставка по адресу: {order.delivery_address}')
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('profile')

    return render(request, 'shop/checkout.html', {
        'items': items,
        'total': total,
        'profile': profile
    })


@login_required
def profile(request):
    """Личный кабинет пользователя."""
    profile = get_or_create_profile(request.user)
    orders_with_items = get_user_orders(request.user)

    return render(request, 'shop/profile.html', {
        'orders_with_items': orders_with_items,
        'profile': profile,
    })


@login_required
def edit_profile(request):
    """Редактирование профиля."""
    profile = get_or_create_profile(request.user)

    if request.method == 'POST':
        user_form = UserEditForm(request.POST, instance=request.user)
        profile_form = ProfileEditForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Ваши данные успешно обновлены!')
            return redirect('profile')
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=profile)

    return render(request, 'shop/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })


@login_required
@require_POST
def delete_order_item_view(request, item_id):
    """Удаление позиции из заказа (только POST)."""
    success, message_text = delete_order_item(item_id, request.user)
    if success:
        messages.success(request, message_text)
    else:
        messages.error(request, message_text)
    return redirect('profile')


def register(request):
    """Регистрация нового пользователя."""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна!')
            return redirect('index')
    else:
        form = UserRegistrationForm()
    return render(request, 'shop/register.html', {'form': form})
