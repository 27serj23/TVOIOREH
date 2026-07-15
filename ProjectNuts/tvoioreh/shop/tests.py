"""
Тесты для интернет-магазина «Твой орех».
(адаптированы под сервисный слой, POST-семантику и отсутствие сигналов)
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal

from .models import Product, Profile, Order, OrderItem
from .forms import UserRegistrationForm   # оставлен только нужный импорт
from .services import (
    generate_unique_slug, fill_missing_slugs,
    search_products, get_cart_data, create_order_from_cart,
    delete_order_item, get_or_create_profile, recalculate_order_total
)


def create_user_with_profile(username, email, password):
    user = User.objects.create_user(username, email, password)
    Profile.objects.create(user=user)
    return user


# ------------------------------------------------------------
# 1. Тесты сервисного слоя
# ------------------------------------------------------------
class ServiceTests(TestCase):
    """Изолированные тесты сервисных функций."""

    def test_generate_unique_slug_cyrillic_fallback(self):
        """Кириллица даёт базовый slug 'product'."""
        slug = generate_unique_slug('Грецкий орех')
        self.assertEqual(slug, 'product')

    def test_generate_unique_slug_latin(self):
        """Латинское название превращается в slug корректно."""
        slug = generate_unique_slug('Almond')
        self.assertEqual(slug, 'almond')

    def test_fill_missing_slugs(self):
        """Заполняем slug у товара, у которого он был очищен, и проверяем уникальность."""
        # Создаём два товара с одинаковым именем, чтобы проверить уникальность slug
        p1 = Product.objects.create(name='Миндаль', price=100)
        p2 = Product.objects.create(name='Миндаль', price=120)
        # У них уже есть slug, причём разные
        self.assertNotEqual(p1.slug, p2.slug)

        # Очищаем slug у первого товара
        Product.objects.filter(pk=p1.pk).update(slug='')

        # Запускаем заполнение
        fill_missing_slugs()

        p1.refresh_from_db()
        p2.refresh_from_db()
        # Slug у первого должен появиться и не совпадать со вторым
        self.assertTrue(p1.slug)
        self.assertNotEqual(p1.slug, p2.slug)

        # Проверяем, что второй товар не изменился
        self.assertEqual(p2.slug, Product.objects.get(pk=p2.pk).slug)

    def test_search_products(self):
        Product.objects.create(name='Almond', price=100, slug='almond')
        Product.objects.create(name='Cashew', price=200, slug='cashew')
        qs = search_products('cash')
        self.assertEqual(qs.count(), 1)

    def test_recalculate_order_total(self):
        user = create_user_with_profile('u', 'u@test.com', 'pass')
        order = Order.objects.create(user=user)
        product = Product.objects.create(name='A', price=Decimal('10.00'), slug='a')
        OrderItem.objects.create(order=order, product=product, quantity=3, price=product.price)
        total = recalculate_order_total(order)
        self.assertEqual(total, Decimal('30.00'))

    def test_delete_order_item_removes_order_when_last(self):
        user = create_user_with_profile('u1', 'u1@test.com', 'pass')
        product = Product.objects.create(name='X', price=Decimal('5.00'), slug='x')
        order = Order.objects.create(user=user)
        OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)
        success, msg = delete_order_item(OrderItem.objects.first().id, user)
        self.assertTrue(success)
        self.assertFalse(Order.objects.filter(pk=order.pk).exists())

    def test_cannot_delete_others_item(self):
        u1 = create_user_with_profile('a1', 'a1@t.com', 'pass')
        u2 = create_user_with_profile('a2', 'a2@t.com', 'pass')
        product = Product.objects.create(name='P', price=Decimal('1.00'), slug='p')
        order = Order.objects.create(user=u1)
        item = OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)
        success, msg = delete_order_item(item.id, u2)
        self.assertFalse(success)

    def test_create_order_from_cart(self):
        user = create_user_with_profile('cartuser', 'cart@t.com', 'pass')
        product = Product.objects.create(name='Q', price=Decimal('7.00'), slug='q')
        cart = {str(product.id): {'quantity': 2, 'price': str(product.price), 'name': product.name}}
        product_dict = {product.id: product}
        order = create_order_from_cart(user, cart, product_dict)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.total_price, Decimal('14.00'))


# ------------------------------------------------------------
# 2. Тесты моделей (без сигналов, профиль вручную)
# ------------------------------------------------------------
class ProductModelTest(TestCase):
    def test_create_product_with_slug(self):
        product = Product.objects.create(name='Almond', price=Decimal('350.00'))
        self.assertTrue(product.slug.startswith('almond'))

    def test_product_slug_unique(self):
        p1 = Product.objects.create(name='Cashew', price=Decimal('100.00'))
        p2 = Product.objects.create(name='Cashew', price=Decimal('120.00'))
        self.assertNotEqual(p1.slug, p2.slug)

    def test_absolute_url(self):
        product = Product.objects.create(name='Pecan', price=Decimal('200.00'))
        expected = reverse('product_detail', args=[product.slug])
        self.assertEqual(product.get_absolute_url(), expected)


class OrderModelTest(TestCase):
    def setUp(self):
        self.user = create_user_with_profile('buyer', 'buyer@test.com', 'pass')
        self.product1 = Product.objects.create(name='Pistachio', price=Decimal('300.00'), slug='pistachio')
        self.product2 = Product.objects.create(name='Hazelnut', price=Decimal('450.00'), slug='hazelnut')

    def test_order_default_status(self):
        order = Order.objects.create(user=self.user)
        self.assertEqual(order.status, 'pending')


# ------------------------------------------------------------
# 3. Тесты представлений (POST-семантика)
# ------------------------------------------------------------
class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(
            name='Almond', price=Decimal('500.00'), slug='almond', description='Fresh almonds'
        )
        self.user = create_user_with_profile('test', 'test@test.com', 'test1234')

    def test_index_page(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Almond')

    def test_product_detail_page(self):
        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)

    def test_add_to_cart_post_only(self):
        # GET запрещён
        response = self.client.get(reverse('add_to_cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 405)
        # POST работает
        response = self.client.post(reverse('add_to_cart', args=[self.product.id]))
        self.assertRedirects(response, reverse('cart_view'))

    def test_remove_from_cart_post(self):
        session = self.client.session
        session['cart'] = {str(self.product.id): {'quantity': 1, 'price': str(self.product.price), 'name': self.product.name}}
        session.save()
        response = self.client.post(reverse('remove_from_cart', args=[self.product.id]))
        self.assertRedirects(response, reverse('cart_view'))

    def test_cart_view_empty(self):
        response = self.client.get(reverse('cart_view'))
        self.assertContains(response, 'Корзина пуста')

    def test_profile_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, reverse('login') + '?next=' + reverse('profile'))


# ------------------------------------------------------------
# 4. Тесты форм
# ------------------------------------------------------------
class FormTests(TestCase):
    def test_registration_form_valid(self):
        data = {
            'username': 'newuser', 'first_name': 'A', 'last_name': 'B',
            'email': 'a@b.com', 'phone': '+79991234567', 'address': 'Moscow',
            'password1': 'Complex123!', 'password2': 'Complex123!',
        }
        form = UserRegistrationForm(data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_password_mismatch(self):
        data = {
            'username': 'u', 'first_name': 'A', 'last_name': 'B',
            'email': 'a@b.com', 'phone': '+7', 'address': 'x',
            'password1': 'qwerty123', 'password2': 'qwerty124',
        }
        form = UserRegistrationForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)


# ------------------------------------------------------------
# 5. Сквозной тест оформления заказа
# ------------------------------------------------------------
class OrderWorkflowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(
            name='Cashew', price=Decimal('400.00'), slug='cashew', description='Сочный кешью'
        )
        self.user = create_user_with_profile('orderuser', 'order@test.com', 'testpass')
        self.user.profile.address = 'г. Казань, ул. Баумана'
        self.user.profile.phone = '+79990001122'
        self.user.profile.save()

    def test_checkout_creates_order(self):
        self.client.login(username='orderuser', password='testpass')
        self.client.post(reverse('add_to_cart', args=[self.product.id]))
        response = self.client.post(reverse('checkout'))
        self.assertRedirects(response, reverse('profile'))

        order = Order.objects.first()
        self.assertIsNotNone(order)
        self.assertEqual(order.total_price, Decimal('400.00'))
        self.assertEqual(order.items.count(), 1)
        cart = self.client.session.get('cart', {})
        self.assertEqual(cart, {})
