"""
Django settings for DreamBiz Accounting - Modern AI-Powered Accounting Platform.

DreamBiz Accounting addresses QuickBooks limitations with:
- Modern responsive UI with Tailwind CSS
- Real-time collaboration
- AI-powered insights and automation
- Unlimited users and companies
- Advanced reporting and analytics
"""

import os
from pathlib import Path
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-g2$)*0l7zf3c%(@8zh@8g@7+9a@&b$7=722@wlzk$zjapcmy(_'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1', '*', 'dreambiz.pythonanywhere.com']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'corsheaders',
    'crispy_forms',
    'crispy_tailwind',
    'django_extensions',
    
    # Local apps
    'accounts',
    'admin_panel',  # Administrative interface
    'dashboard',
    'invoicing',
    'expenses',
    'reports',
    'hr',
    'ai_insights',
    'sales',
    'bank_reconciliation',
    'inventory',
    'docs',
    'website',  # Main e-commerce website
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.CompanyIsolationMiddleware',  # Data isolation
    'accounts.middleware.BranchAccessControlMiddleware',  # Branch-based access control
]

ROOT_URLCONF = 'accuflow.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                    # Team/role permissions available in all templates
                    'accounts.context_processors.team_permissions',
                    # Cart context for e-commerce
                    'website.context_processors.cart_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'accuflow.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# Determine which database to use based on environment
USE_MYSQL = config('USE_MYSQL', default=False, cast=bool)

if USE_MYSQL:
    # PythonAnywhere MySQL Database Configuration
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='your_username$dbname'),
            'USER': config('DB_USER', default='your_username'),
            'PASSWORD': config('DB_PASSWORD', default='your_password'),
            'HOST': config('DB_HOST', default='your_username.mysql.pythonanywhere-services.com'),
            'PORT': config('DB_PORT', default='3306'),
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
            },
        }
    }
else:
    # Local SQLite Database (Development)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }



# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms Configuration
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = True  # Only for development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# AI Configuration
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')

# Email Configuration (for notifications and reports)
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=465, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='DreamBiz <dreambizaccess@gmail.com>')
SERVER_EMAIL = EMAIL_HOST_USER

# Celery Configuration (for background tasks)
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379')

# Login URLs
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Session Configuration
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# OpenAI Configuration
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
OPENAI_MODEL = config('OPENAI_MODEL', default='gpt-4o-mini')
OPENAI_MAX_TOKENS = config('OPENAI_MAX_TOKENS', default=2000, cast=int)

# Paystack Configuration
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='')
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='')
PAYSTACK_CALLBACK_URL = config('PAYSTACK_CALLBACK_URL', default='http://localhost:8000/invoicing/payment/verify/')
