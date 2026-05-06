from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify


class Product(models.Model):
    """Товар интернет-магазина."""
    name = models.CharField(max_length=200, verbose_name='Название')
    slug = models.SlugField(max_length=200, unique=True, blank=True, verbose_name='URL')
    description = models.TextField(verbose_name='Описание')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='Изображение')

    def save(self, *args, **kwargs):
        """При сохранении автоматически генерируем slug из названия."""
        new_slug = slugify(self.name)
        if not self.slug or self.slug != new_slug:
            self.slug = new_slug

        # Обеспечиваем уникальность slug
        original_slug = self.slug
        counter = 1
        while Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', args=[self.slug])

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'


class Profile(models.Model):
    """Дополнительные данные пользователя."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    address = models.TextField(blank=True, verbose_name='Адрес доставки')

    def __str__(self):
        return f'Профиль {self.user.username}'

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'


class Order(models.Model):
    """Заказ пользователя."""
    STATUS_CHOICES = [
        ('pending', 'В обработке'),
        ('paid', 'Оплачен'),
        ('shipped', 'Отправлен'),
        ('completed', 'Завершён'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name='Пользователь')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Итоговая сумма')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    delivery_address = models.TextField(blank=True, verbose_name='Адрес доставки')

    def __str__(self):
        return f'Заказ #{self.id} от {self.user.username}'

    def update_total(self):
        """Пересчёт итоговой суммы на основе позиций заказа."""
        total = sum(item.price * item.quantity for item in self.items.all())
        self.total_price = total
        self.save(update_fields=['total_price'])

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'


class OrderItem(models.Model):
    """Отдельная позиция в заказе."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Заказ')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена на момент покупки')

    def save(self, *args, **kwargs):
        """После сохранения позиции обновляем итог заказа."""
        super().save(*args, **kwargs)
        self.order.update_total()

    def delete(self, *args, **kwargs):
        """После удаления позиции также пересчитываем итог."""
        order = self.order
        super().delete(*args, **kwargs)
        order.update_total()

    @property
    def item_total(self):
        """Сумма для данной позиции."""
        return self.price * self.quantity

    def __str__(self):
        return f'{self.product.name} x{self.quantity}'

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказов'