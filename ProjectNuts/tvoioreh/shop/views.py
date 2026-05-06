"""
Представления (views) интернет-магазина.
Каждая функция обрабатывает запрос, взаимодействует с моделями и возвращает шаблон.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.db import transaction
from .models import Product, Order, OrderItem, Profile
from .forms import UserRegistrationForm, UserEditForm, ProfileEditForm


def index(request):
    """Главная страница со списком товаров и поиском."""
    # Автоматически заполняем slug у товаров, где оно пустое
    products_without_slug = Product.objects.filter(slug='')
    for product in products_without_slug:
        product.save()   # вызовет save() модели, который генерирует slug

    # Поиск по названию товара
    query = request.GET.get('q', '').strip()
    if query:
        products = Product.objects.filter(name__icontains=query)
    else:
        products = Product.objects.all()

    return render(request, 'shop/index.html', {
        'products': products,
        'query': query
    })


def product_detail(request, slug):
    """Страница отдельного товара (по slug)."""
    product = get_object_or_404(Product, slug=slug)
    return render(request, 'shop/product_detail.html', {'product': product})


def product_detail_by_id(request, pk):
    """Запасной вариант для товаров без slug (по ID)."""
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'shop/product_detail.html', {'product': product})


def add_to_cart(request, product_id):
    """Добавление товара в корзину (хранится в сессии)."""
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    if product_id_str in cart:
        cart[product_id_str]['quantity'] += 1   # увеличиваем количество
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
    if not cart:
        return render(request, 'shop/cart.html', {'items': [], 'total': 0})

    product_ids = [int(pid) for pid in cart.keys()]
    products = Product.objects.filter(id__in=product_ids)
    product_dict = {p.id: p for p in products}

    items = []
    total = 0
    for product_id_str, data in cart.items():
        product_id = int(product_id_str)
        product = product_dict.get(product_id)
        if product:
            subtotal = data['quantity'] * product.price
            total += subtotal
            items.append({
                'product': product,
                'quantity': data['quantity'],
                'subtotal': subtotal,
            })
    return render(request, 'shop/cart.html', {'items': items, 'total': total})


def remove_from_cart(request, product_id):
    """Удаление товара из корзины."""
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    if product_id_str in cart:
        del cart[product_id_str]
        request.session['cart'] = cart
        request.session.modified = True
        messages.success(request, 'Товар удалён из корзины')
    return redirect('cart_view')


def update_cart(request, product_id):
    """Обновление количества товара в корзине."""
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        cart = request.session.get('cart', {})
        product_id_str = str(product_id)
        if quantity <= 0:
            if product_id_str in cart:
                del cart[product_id_str]          # удаляем, если 0
        else:
            if product_id_str in cart:
                cart[product_id_str]['quantity'] = quantity
        request.session['cart'] = cart
        request.session.modified = True
        messages.success(request, 'Корзина обновлена')
    return redirect('cart_view')


@login_required
def checkout(request):
    """Оформление заказа: создание Order и привязанных OrderItem."""
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, 'Корзина пуста')
        return redirect('index')

    profile, created = Profile.objects.get_or_create(user=request.user)

    product_ids = [int(pid) for pid in cart.keys()]
    products = Product.objects.filter(id__in=product_ids)
    product_dict = {p.id: p for p in products}

    items = []
    total = 0
    for product_id_str, data in cart.items():
        product_id = int(product_id_str)
        product = product_dict.get(product_id)
        if product:
            subtotal = data['quantity'] * product.price
            total += subtotal
            items.append({
                'product': product,
                'quantity': data['quantity'],
                'subtotal': subtotal,
            })

    if request.method == 'POST':
        with transaction.atomic():          # все операции в одной транзакции
            order = Order.objects.create(
                user=request.user,
                total_price=0,
                delivery_address=profile.address
            )
            total_price = 0
            for product_id_str, data in cart.items():
                product_id = int(product_id_str)
                product = product_dict.get(product_id)
                if product:
                    quantity = data['quantity']
                    price = product.price
                    subtotal = price * quantity
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price=price
                    )
                    total_price += subtotal
            order.total_price = total_price
            order.save(update_fields=['total_price'])
            request.session['cart'] = {}          # очищаем корзину
            request.session.modified = True
            messages.success(request, f'Заказ #{order.id} оформлен! Доставка по адресу: {order.delivery_address}')
            return redirect('profile')

    return render(request, 'shop/checkout.html', {'items': items, 'total': total, 'profile': profile})


@login_required
def profile(request):
    """Личный кабинет пользователя: данные профиля и история заказов."""
    profile, created = Profile.objects.get_or_create(user=request.user)
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product').order_by('-created_at')
    orders_with_items = []
    for order in orders:
        items_list = []
        for item in order.items.all():
            items_list.append({
                'id': item.id,
                'product': item.product,
                'quantity': item.quantity,
                'price': item.price,
                'total': item.item_total,
            })
        orders_with_items.append({
            'order': order,
            'order_items': items_list,   # ключ 'order_items' чтобы не конфликтовать со встроенным .items
        })
    return render(request, 'shop/profile.html', {
        'orders_with_items': orders_with_items,
        'profile': profile,
    })


@login_required
def edit_profile(request):
    """Редактирование профиля."""
    profile, created = Profile.objects.get_or_create(user=request.user)

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
def delete_order_item(request, item_id):
    """Удаление отдельной позиции из заказа (только в статусе 'pending')."""
    order_item = get_object_or_404(OrderItem, id=item_id)
    order = order_item.order

    # Проверяем, что заказ принадлежит текущему пользователю
    if order.user != request.user:
        messages.error(request, 'Вы не можете удалять чужие заказы.')
        return redirect('profile')

    # Удалять можно только необработанные заказы
    if order.status != 'pending':
        messages.error(request, 'Можно удалять товары только из необработанных заказов.')
        return redirect('profile')

    product_name = order_item.product.name
    order_item.delete()

    # Если товаров не осталось, удаляем весь заказ
    if order.items.count() == 0:
        order.delete()
        messages.success(request, f'Товар "{product_name}" удалён. Заказ #{order.id} полностью отменён.')
    else:
        messages.success(request, f'Товар "{product_name}" удалён из заказа #{order.id}.')

    return redirect('profile')


def register(request):
    """Регистрация нового пользователя."""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)   # сразу авторизуем после регистрации
            messages.success(request, 'Регистрация успешна!')
            return redirect('index')
    else:
        form = UserRegistrationForm()
    return render(request, 'shop/register.html', {'form': form})