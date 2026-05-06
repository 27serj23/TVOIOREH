"""
Регистрация моделей в админ-панели Django.
"""

from django.contrib import admin
from .models import Product, Profile, Order, OrderItem


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'slug')
    prepopulated_fields = {'slug': ('name',)}   # автоматическое заполнение slug
    search_fields = ('name',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'address')
    search_fields = ('user__username', 'phone')


class OrderItemInline(admin.TabularInline):
    """Встроенные позиции заказа внутри Order."""
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price', 'item_total')
    fields = ('product', 'quantity', 'price', 'item_total')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'total_price', 'status')
    list_filter = ('status', 'created_at', 'user')
    search_fields = ('user__username', 'delivery_address')
    inlines = [OrderItemInline]
    readonly_fields = ('total_price',)