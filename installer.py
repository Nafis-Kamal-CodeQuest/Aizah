import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# SECURITY
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'VzVP3u76yc9W8vv9rAnK-xX6d4eN2bK1pXRtnP-ikDprPicKKRg8DibQ5Bu9mw3Qpmo'
)

# Set to True during testing; set to False once site loads without errors
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [
    'site-qa1x5w.hostnin.com',
    '91.98.176.112',            # Server IP
    'aizahfood.net',
    'www.aizahfood.net',
    'localhost',
    '127.0.0.1',
]

CSRF_TRUSTED_ORIGINS = [
    'https://site-qa1x5w.hostnin.com',
    'http://site-qa1x5w.hostnin.com',
    'http://91.98.176.112',
    'https://aizahfood.net',
    'http://aizahfood.net',
    'https://www.aizahfood.net',
    'http://www.aizahfood.net',
]

# ---------------------------------------------------------------------------
# APPLICATIONS
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'accounts',
]

# ---------------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise serves static files directly via WSGI
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'aizaah.urls'

# ---------------------------------------------------------------------------
# TEMPLATES
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'aizaah.wsgi.application'

# ---------------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------------

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,
        },
    }
}

# ---------------------------------------------------------------------------
# PASSWORD VALIDATION
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# INTERNATIONALISATION
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# STATIC FILES (WhiteNoise)
# ---------------------------------------------------------------------------

# Prefix paths with /~siteqaxw/ for cPanel IP preview testing
STATIC_URL = '/~siteqaxw/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Non-strict storage so missing static references don't crash collectstatic
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# ---------------------------------------------------------------------------
# MEDIA FILES
# ---------------------------------------------------------------------------

MEDIA_URL = '/~siteqaxw/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------------
# DEFAULT PRIMARY KEY
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# SECURITY HEADERS
# ---------------------------------------------------------------------------

if not DEBUG:
    SECURE_SSL_REDIRECT = False  # Enable when custom SSL certificate is active
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True

# ---------------------------------------------------------------------------
# SESSION
# ---------------------------------------------------------------------------

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 1 day

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}