"""
Маршруты приложения shop.
Обрабатывают главную страницу, товары, корзину, заказы, профиль.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),                                          # главная
    path('product/id/<int:pk>/', views.product_detail_by_id, name='product_detail_by_id'),  # товар по ID (запасной)
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),    # товар по slug
    path('cart/', views.cart_view, name='cart_view'),                             # корзина
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),    # добавить в корзину
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),  # удалить из корзины
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'), # обновить количество
    path('checkout/', views.checkout, name='checkout'),                           # оформление заказа
    path('profile/', views.profile, name='profile'),                              # личный кабинет
    path('profile/edit/', views.edit_profile, name='edit_profile'),               # редактирование профиля
    path('register/', views.register, name='register'),                           # регистрация
    path('order-item/<int:item_id>/delete/', views.delete_order_item, name='delete_order_item'),  # удаление позиции заказа
]