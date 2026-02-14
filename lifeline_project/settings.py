from pathlib import Path
import os
import dj_database_url

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default

# Security
SECRET_KEY = 'django-insecure-change-this-to-a-secure-random-key-in-production'
DEBUG = True
ALLOWED_HOSTS = ['*']

# Applications
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Custom App
    'core',
]

# Middleware (WhiteNoise must be right after SecurityMiddleware)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.DisableClientCacheMiddleware',
]

ROOT_URLCONF = 'lifeline_project.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'lifeline_project.wsgi.application'

# Database
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600,
        ssl_require=False
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = []

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- LifeLine Specific Configurations ---

# Custom User Model
AUTH_USER_MODEL = 'core.User'

# Login/Logout Redirects
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# CSRF & Session Settings
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'https://lifeline-blood-donations.onrender.com',
]

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Email settings (file-based by default)
EMAIL_BACKEND = os.getenv(
    'DJANGO_EMAIL_BACKEND',
    'django.core.mail.backends.filebased.EmailBackend'
)
EMAIL_FILE_PATH = os.getenv(
    'DJANGO_EMAIL_FILE_PATH',
    str(BASE_DIR / 'sent_emails')
)
os.makedirs(EMAIL_FILE_PATH, exist_ok=True)

DEFAULT_FROM_EMAIL = os.getenv(
    'DJANGO_DEFAULT_FROM_EMAIL',
    'noreply@lifeline.local'
)

EMAIL_HOST = os.getenv('DJANGO_EMAIL_HOST', '')
EMAIL_PORT = env_int('DJANGO_EMAIL_PORT', 587)
EMAIL_HOST_USER = os.getenv('DJANGO_EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('DJANGO_EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('DJANGO_EMAIL_USE_TLS', True)
EMAIL_USE_SSL = env_bool('DJANGO_EMAIL_USE_SSL', False)
EMAIL_TIMEOUT = env_int('DJANGO_EMAIL_TIMEOUT', 10)
