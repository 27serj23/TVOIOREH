"""
Маршруты приложения shop.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('register/', views.register, name='register'),
    path('order-item/<int:item_id>/delete/', views.delete_order_item_view, name='delete_order_item'),
]
