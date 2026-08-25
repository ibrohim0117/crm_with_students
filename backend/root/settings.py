"""
Django settings for root project.

Barcha muhitga bog'liq qiymatlar `.env` faylidan o'qiladi (django-environ).
Namuna uchun: `.env.example` ga qara.

Hujjatlar: https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from datetime import timedelta
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------
# .env ni o'qish
# ------------------------------------------------------------------
env = environ.Env()

# `.env` BASE_DIR (backend/) ichida turadi. Fayl bo'lmasa — xato bermaydi,
# faqat quyidagi default qiymatlar ishlaydi.
environ.Env.read_env(BASE_DIR / '.env')


# ------------------------------------------------------------------
# Core
# ------------------------------------------------------------------
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str('DJANGO_SECRET_KEY', default='django-insecure-CHANGE-ME-IN-ENV')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DJANGO_DEBUG', default=False)

ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

CSRF_TRUSTED_ORIGINS = env.list('DJANGO_CSRF_TRUSTED_ORIGINS', default=[])


# ------------------------------------------------------------------
# Application definition
# ------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # my apps
    'analytics',
    'auth',
    'product',
    'order',

    # install apps
    'rest_framework',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'root.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'root.wsgi.application'
ASGI_APPLICATION = 'root.asgi.application'


# ------------------------------------------------------------------
# Database
# ------------------------------------------------------------------
# DATABASE_URL formati: postgres://user:parol@host:port/db_nomi
# PostgreSQL uchun `psycopg[binary]` o'rnatilgan bo'lishi kerak.
DATABASES = {
    'default': env.db_url(
        'DATABASE_URL',
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
    ),
}


# ------------------------------------------------------------------
# Cache (Redis)
# ------------------------------------------------------------------
REDIS_URL = env.str('REDIS_URL', default='redis://localhost:6379/0')
CACHE_TTL = env.int('CACHE_TTL', default=300)

if env.bool('USE_REDIS_CACHE', default=False):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': env.str('CACHE_URL', default=REDIS_URL),
        },
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'crm-locmem',
        },
    }


# ------------------------------------------------------------------
# Celery
# ------------------------------------------------------------------
CELERY_BROKER_URL = env.str('CELERY_BROKER_URL', default=REDIS_URL)
CELERY_RESULT_BACKEND = env.str('CELERY_RESULT_BACKEND', default=REDIS_URL)
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=False)
CELERY_TIMEZONE = env.str('DJANGO_TIME_ZONE', default='Asia/Tashkent')


# ------------------------------------------------------------------
# JWT (djangorestframework-simplejwt o'rnatilgach ishlaydi)
# ------------------------------------------------------------------
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=30)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=env.int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7)
    ),
    'ROTATE_REFRESH_TOKENS': env.bool('JWT_ROTATE_REFRESH_TOKENS', default=True),
}


# ------------------------------------------------------------------
# Telegram bot (aiogram)
# ------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = env.str('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_BOT_USERNAME = env.str('TELEGRAM_BOT_USERNAME', default='')
TELEGRAM_ADMIN_CHAT_ID = env.str('TELEGRAM_ADMIN_CHAT_ID', default='')

VERIFICATION_CODE_TTL_SECONDS = env.int('VERIFICATION_CODE_TTL_SECONDS', default=120)
VERIFICATION_CODE_MAX_ATTEMPTS = env.int('VERIFICATION_CODE_MAX_ATTEMPTS', default=3)


# ------------------------------------------------------------------
# CORS (django-cors-headers o'rnatilgach ishlaydi)
# ------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=False)


# ------------------------------------------------------------------
# Password validation
# ------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ------------------------------------------------------------------
# Internationalization
# ------------------------------------------------------------------
LANGUAGE_CODE = env.str('DJANGO_LANGUAGE_CODE', default='en-us')

TIME_ZONE = env.str('DJANGO_TIME_ZONE', default='UTC')

USE_I18N = True

USE_TZ = True


# ------------------------------------------------------------------
# Static & Media files
# ------------------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# dev: 'local', prod: 's3' (yoki 'minio') — django-storages bilan ishlatiladi
MEDIA_STORAGE = env.str('MEDIA_STORAGE', default='local')
AWS_ACCESS_KEY_ID = env.str('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = env.str('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = env.str('AWS_STORAGE_BUCKET_NAME', default='')
AWS_S3_ENDPOINT_URL = env.str('AWS_S3_ENDPOINT_URL', default='') or None
AWS_S3_REGION_NAME = env.str('AWS_S3_REGION_NAME', default='')


# ------------------------------------------------------------------
# Email
# ------------------------------------------------------------------
EMAIL_BACKEND = env.str(
    'EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = env.str('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env.str('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env.str('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env.str('DEFAULT_FROM_EMAIL', default='noreply@crm.local')


# ------------------------------------------------------------------
# Monitoring / logging
# ------------------------------------------------------------------
SENTRY_DSN = env.str('SENTRY_DSN', default='')
LOG_LEVEL = env.str('LOG_LEVEL', default='INFO')


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
