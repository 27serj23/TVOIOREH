"""
Настройки Django-проекта «Твой орех».
Содержит конфигурацию базы данных, шаблонизаторов, путей к статике и медиа,
а также параметры безопасности и аутентификации.
"""

import os
from pathlib import Path

# Корень проекта: папка tvoioreh (где лежит manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# Секретный ключ (в продакшене должен быть скрыт!)
SECRET_KEY = 'django-insecure-your-secret-key-here'
DEBUG = True                         # Режим отладки (выключать на боевом сервере)
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']   # Разрешённые хосты

# Приложения Django
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'shop',                          # наше приложение интернет-магазина
]

# Промежуточное ПО (middleware) – обрабатывает запросы по цепочке
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tvoioreh.urls'       # главный URL-конфиг

# Шаблонизаторы
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.jinja2.Jinja2',   # используем Jinja2
        'DIRS': [BASE_DIR / 'shop' / 'templates'],             # глобальная папка шаблонов
        'APP_DIRS': True,
        'OPTIONS': {
            'environment': 'tvoioreh.jinja2.environment',      # кастомное окружение Jinja2
            'context_processors': [                            # контекстные процессоры
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.csrf',
                'shop.context_processors.cart_count',          # добавляем счётчик корзины
            ],
        },
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',  # стандартный Django-шаблонизатор
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'shop.context_processors.cart_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'tvoioreh.wsgi.application'

# База данных SQLite (файл db.sqlite3 в корне проекта)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Валидаторы паролей
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Язык и часовой пояс
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# Статические файлы (CSS, JS, изображения)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']   # дополнительные папки со статикой
STATIC_ROOT = BASE_DIR / 'staticfiles'     # для продакшена (python manage.py collectstatic)

# Медиа-файлы (загружаемые пользователем, например, фото товаров)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Настройки аутентификации
LOGIN_URL = 'login'                      # URL для входа
LOGIN_REDIRECT_URL = 'index'             # куда перенаправлять после входа
LOGOUT_REDIRECT_URL = 'index'            # куда после выхода