"""
Тесты для интернет-магазина «Твой орех»
(адаптированы под ручное создание Profile)
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal

from .models import Product, Profile, Order, OrderItem
from .forms import UserRegistrationForm, UserEditForm, ProfileEditForm


# Вспомогательная функция для создания пользователя с профилем
def create_user_with_profile(username, email, password):
    user = User.objects.create_user(username, email, password)
    Profile.objects.create(user=user)          # явно создаём профиль
    return user


# ------------------------------------------------------------
# 1. Тесты моделей
# ------------------------------------------------------------
class ProductModelTest(TestCase):
    """Тесты модели Product."""

    def test_create_product(self):
        """Проверяет создание товара и автоматическую генерацию slug."""
        product = Product.objects.create(
            name='Almond',
            description='Свежий миндаль',
            price=Decimal('350.00')
        )
        self.assertEqual(product.slug, 'almond')
        self.assertEqual(str(product), 'Almond')
        self.assertIsNotNone(product.slug)

    def test_product_slug_unique(self):
        """Проверяет, что slug остаётся уникальным при совпадении названий."""
        p1 = Product.objects.create(name='Cashew', price=Decimal('100.00'))
        p2 = Product.objects.create(name='Cashew', price=Decimal('120.00'))
        self.assertNotEqual(p1.slug, p2.slug)
        self.assertTrue(p2.slug.startswith('cashew'))

    def test_get_absolute_url(self):
        """Проверяет метод get_absolute_url."""
        product = Product.objects.create(name='Pecan', price=Decimal('200.00'))
        expected = reverse('product_detail', args=[product.slug])
        self.assertEqual(product.get_absolute_url(), expected)


class ProfileModelTest(TestCase):
    """Тесты модели Profile (создаётся вручную)."""

    def test_profile_manual_creation(self):
        """Профиль создаётся вручную и доступен через user.profile."""
        user = create_user_with_profile('testuser', 'test@example.com', 'pass123')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, Profile)
        self.assertEqual(str(user.profile), 'Профиль testuser')

    def test_profile_fields(self):
        """Проверяет сохранение телефона и адреса."""
        user = create_user_with_profile('john', 'john@example.com', 'pass123')
        profile = user.profile
        profile.phone = '+79991234567'
        profile.address = 'ул. Пушкина, д. 10'
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.phone, '+79991234567')
        self.assertEqual(profile.address, 'ул. Пушкина, д. 10')


class OrderModelTest(TestCase):
    """Тесты модели Order и OrderItem."""

    def setUp(self):
        self.user = create_user_with_profile('buyer', 'buyer@example.com', 'buyerpass')
        self.product1 = Product.objects.create(name='Pistachio', price=Decimal('300.00'), slug='pistachio')
        self.product2 = Product.objects.create(name='Hazelnut', price=Decimal('450.00'), slug='hazelnut')

    def test_order_creation_and_total(self):
        """Проверяет создание заказа и автоматический пересчёт суммы."""
        order = Order.objects.create(user=self.user, delivery_address='г. Москва')
        OrderItem.objects.create(order=order, product=self.product1, quantity=2, price=self.product1.price)
        OrderItem.objects.create(order=order, product=self.product2, quantity=1, price=self.product2.price)
        order.refresh_from_db()
        self.assertEqual(order.total_price, Decimal('1050.00'))
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(str(order), f'Заказ #{order.id} от buyer')

    def test_order_item_delete_updates_total(self):
        """При удалении позиции сумма заказа пересчитывается."""
        order = Order.objects.create(user=self.user)
        item = OrderItem.objects.create(
            order=order, product=self.product1, quantity=3, price=self.product1.price
        )
        order.refresh_from_db()
        self.assertEqual(order.total_price, Decimal('900.00'))
        item.delete()
        order.refresh_from_db()
        self.assertEqual(order.total_price, Decimal('0.00'))

    def test_order_status_default(self):
        """Статус по умолчанию — 'pending'."""
        order = Order.objects.create(user=self.user)
        self.assertEqual(order.status, 'pending')


# ------------------------------------------------------------
# 2. Тесты представлений
# ------------------------------------------------------------
class ViewTests(TestCase):
    """Интеграционные тесты доступности страниц и работы корзины."""

    def setUp(self):
        self.client = Client()
        self.product1 = Product.objects.create(
            name='Almond', price=Decimal('500.00'), slug='almond', description='Fresh almonds'
        )
        self.product2 = Product.objects.create(
            name='Cashew', price=Decimal('700.00'), slug='cashew', description='Roasted cashew'
        )
        self.product3 = Product.objects.create(
            name='Walnut', price=Decimal('600.00'), slug='walnut', description='English walnut'
        )
        self.user = create_user_with_profile('test', 'test@test.com', 'test1234')

    # ----- Главная и товар -----
    def test_index_page(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Almond')

    def test_product_detail_page(self):
        response = self.client.get(reverse('product_detail', args=[self.product1.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Almond')

    # ----- Поиск -----
    def test_search_filters_products(self):
        response = self.client.get(reverse('index'), {'q': 'cash'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cashew')
        self.assertNotContains(response, 'Almond')
        self.assertNotContains(response, 'Walnut')

    def test_search_case_insensitive(self):
        response = self.client.get(reverse('index'), {'q': 'ALMOND'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Almond')

    def test_search_no_results(self):
        response = self.client.get(reverse('index'), {'q': 'peanut'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ничего не найдено')

    # ----- Корзина -----
    def test_add_to_cart_redirect(self):
        response = self.client.get(reverse('add_to_cart', args=[self.product1.id]))
        self.assertRedirects(response, reverse('cart_view'))
        cart = self.client.session.get('cart', {})
        self.assertIn(str(self.product1.id), cart)
        self.assertEqual(cart[str(self.product1.id)]['quantity'], 1)

    def test_cart_view_empty(self):
        response = self.client.get(reverse('cart_view'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Корзина пуста')

    def test_cart_view_with_items(self):
        session = self.client.session
        session['cart'] = {
            str(self.product1.id): {
                'quantity': 2,
                'price': str(self.product1.price),
                'name': self.product1.name
            }
        }
        session.save()
        response = self.client.get(reverse('cart_view'))
        self.assertContains(response, 'Almond')
        self.assertContains(response, '1000')

    # ----- Авторизация и профиль -----
    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, reverse('login') + '?next=' + reverse('profile'))

    def test_profile_authenticated(self):
        self.client.login(username='test', password='test1234')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test@test.com')

    def test_register_view(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_checkout_requires_login(self):
        response = self.client.get(reverse('checkout'))
        self.assertRedirects(response, reverse('login') + '?next=' + reverse('checkout'))


# ------------------------------------------------------------
# 3. Тесты форм
# ------------------------------------------------------------
class FormTests(TestCase):
    """Тесты валидации форм."""

    def test_registration_form_valid(self):
        data = {
            'username': 'newuser',
            'first_name': 'Иван',
            'last_name': 'Петров',
            'email': 'ivan@example.com',
            'phone': '+79991234567',
            'address': 'г. Москва, ул. Лесная',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }
        form = UserRegistrationForm(data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_registration_form_password_mismatch(self):
        data = {
            'username': 'user',
            'first_name': 'A', 'last_name': 'B', 'email': 'a@b.com',
            'phone': '+79991112233', 'address': 'г. Москва',
            'password1': 'qwerty123', 'password2': 'qwerty124',
        }
        form = UserRegistrationForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_user_edit_form(self):
        user = create_user_with_profile('editme', 'edit@me.com', 'pass')
        data = {'first_name': 'Сергей', 'last_name': 'Сергеев', 'email': 'new@me.com'}
        form = UserEditForm(data, instance=user)
        self.assertTrue(form.is_valid())
        form.save()
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Сергей')

    def test_profile_edit_form(self):
        user = create_user_with_profile('puser', 'p@user.com', 'pass')
        profile = user.profile
        data = {'phone': '+78887776655', 'address': 'пр. Мира, 5'}
        form = ProfileEditForm(data, instance=profile)
        self.assertTrue(form.is_valid())
        form.save()
        profile.refresh_from_db()
        self.assertEqual(profile.phone, '+78887776655')


# ------------------------------------------------------------
# 4. Тест контекстного процессора
# ------------------------------------------------------------
class ContextProcessorTest(TestCase):
    def test_cart_count_empty(self):
        from .context_processors import cart_count
        request = self.client.get('/').wsgi_request
        self.assertEqual(cart_count(request), {'cart_count': 0})

    def test_cart_count_with_items(self):
        from .context_processors import cart_count
        request = self.client.get('/').wsgi_request
        request.session['cart'] = {
            '1': {'quantity': 2, 'price': '100'},
            '2': {'quantity': 3, 'price': '200'},
        }
        request.session.save()
        self.assertEqual(cart_count(request), {'cart_count': 5})


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
        self.client.get(reverse('add_to_cart', args=[self.product.id]))
        response = self.client.post(reverse('checkout'))
        self.assertRedirects(response, reverse('profile'))

        order = Order.objects.first()
        self.assertIsNotNone(order)
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.total_price, Decimal('400.00'))
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.status, 'pending')

        cart = self.client.session.get('cart', {})
        self.assertEqual(cart, {})

        profile_response = self.client.get(reverse('profile'))
        self.assertContains(profile_response, 'Cashew')


# ------------------------------------------------------------
# 6. Тесты удаления позиций заказа
# ------------------------------------------------------------
class OrderItemDeleteViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = create_user_with_profile('alice', 'alice@shop.com', 'alicepass')
        self.user2 = create_user_with_profile('bob', 'bob@shop.com', 'bobpass')
        self.product1 = Product.objects.create(
            name='Pistachio', price=Decimal('300.00'), slug='pistachio'
        )
        self.product2 = Product.objects.create(
            name='Hazelnut', price=Decimal('450.00'), slug='hazelnut'
        )
        self.order_user1 = Order.objects.create(user=self.user1, status='pending')
        self.item1 = OrderItem.objects.create(
            order=self.order_user1, product=self.product1, quantity=2, price=self.product1.price
        )
        self.item2 = OrderItem.objects.create(
            order=self.order_user1, product=self.product2, quantity=1, price=self.product2.price
        )
        self.order_user1.refresh_from_db()
        self.order_user2 = Order.objects.create(user=self.user2, status='pending')
        self.item3 = OrderItem.objects.create(
            order=self.order_user2, product=self.product1, quantity=1, price=self.product1.price
        )

    def test_delete_own_pending_item(self):
        self.client.login(username='alice', password='alicepass')
        url = reverse('delete_order_item', args=[self.item1.id])
        response = self.client.post(url)
        self.assertRedirects(response, reverse('profile'))
        self.assertFalse(OrderItem.objects.filter(id=self.item1.id).exists())
        self.assertTrue(Order.objects.filter(id=self.order_user1.id).exists())
        self.order_user1.refresh_from_db()
        self.assertEqual(self.order_user1.items.count(), 1)

    def test_delete_last_item_removes_order(self):
        self.client.login(username='alice', password='alicepass')
        self.client.post(reverse('delete_order_item', args=[self.item2.id]))
        url = reverse('delete_order_item', args=[self.item1.id])
        response = self.client.post(url)
        self.assertRedirects(response, reverse('profile'))
        self.assertFalse(Order.objects.filter(id=self.order_user1.id).exists())

    def test_cannot_delete_others_item(self):
        self.client.login(username='alice', password='alicepass')
        url = reverse('delete_order_item', args=[self.item3.id])
        response = self.client.post(url)
        self.assertRedirects(response, reverse('profile'))
        self.assertTrue(OrderItem.objects.filter(id=self.item3.id).exists())

    def test_cannot_delete_if_status_not_pending(self):
        self.order_user1.status = 'paid'
        self.order_user1.save()
        self.client.login(username='alice', password='alicepass')
        url = reverse('delete_order_item', args=[self.item1.id])
        response = self.client.post(url)
        self.assertRedirects(response, reverse('profile'))
        self.assertTrue(OrderItem.objects.filter(id=self.item1.id).exists())
