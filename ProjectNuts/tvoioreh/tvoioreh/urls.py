"""
Главный URL-конфиг проекта.
Подключает админку, приложение shop и встроенные маршруты аутентификации.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),                # админ-панель Django
    path('', include('shop.urls')),                 # все маршруты магазина (shop/urls.py)
    # Авторизация
    path('login/', auth_views.LoginView.as_view(template_name='shop/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Смена пароля
    path('password-change/',
         auth_views.PasswordChangeView.as_view(
             template_name='shop/password_change.html',
             success_url='/profile/'                # после смены пароля – в личный кабинет
         ),
         name='password_change'),
]

# В режиме отладки добавляем раздачу медиа-файлов
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)