"""
Django settings for xbterminal project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '2d$h2q_vukyb190m^6#q)k_rc!+dn8!m5=pc!&e!vckabjqqll'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
TEMPLATE_DEBUG = False

TESTING = 'test' in sys.argv

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s %(name)s [%(levelname)s] :: %(message)s',
        },
        'short': {
            'format': '%(asctime)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'short',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, '..', 'logs', 'django.log'),
            'formatter': 'default',
        },
        'rq': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, '..', 'logs', 'rq.log'),
            'formatter': 'short',
        },
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'rq.worker': {
            'handlers': ['rq'],
            'level': 'WARNING',
            'propagate': False,
        },
        'requests.packages.urllib3.connectionpool': {
            'level': 'WARNING',
        }
    },
}


ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'bootstrap3',
    'rest_framework',
    'qrcode',
    'constance',
    'constance.backends.database',
    'django_rq',
    'oauth2_provider',
    'ckeditor',
    'captcha',

    'website',
    'operations',
    'api',
    'blog',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'website.views.ServerErrorMiddleware',
)

ROOT_URLCONF = 'xbterminal.urls'

WSGI_APPLICATION = 'xbterminal.wsgi.application'

AUTH_USER_MODEL = 'website.User'

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.contrib.messages.context_processors.messages',
    'website.context_processors.debug',
)

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'xbterminal',
        'USER': 'xbterm_usr',
        'PASSWORD': 'zx#213_Op',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

# Cache & RQ

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

RQ_QUEUES = {
    'default': {
        'USE_REDIS_CACHE': 'default',
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, '..', 'static')
STATIC_URL = '/static/'

# Media
# https://docs.djangoproject.com/en/1.6/topics/files/

MEDIA_ROOT = os.path.join(BASE_DIR, '..', 'media')
MEDIA_URL = '/media/'


DEFAULT_FROM_EMAIL = "no-reply@xbterminal.io"
CONTACT_EMAIL_RECIPIENTS = ["info@xbterminal.io"]

APPEND_SLASH = False

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/terminals/'

SITE_ID = 1

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': []
}

BITCOIN_SCALE_DIVIZER = 1000

# Email
# https://docs.djangoproject.com/en/1.6/topics/email/

EMAIL_BACKEND = 'django_smtp_ssl.SSLEmailBackend'

EMAIL_HOST = ""
EMAIL_PORT = ""
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = True

CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'
CONSTANCE_CONFIG = {
    'OUR_FEE_MAINNET_ADDRESS': ("1XBTerm2eRrogkbtu1kiJKv8mH6XvpnJh", 'Bitcoin address'),
    'OUR_FEE_TESTNET_ADDRESS': ("mqhQfj9e57SNEYWNvULegMWfM9DQ8UGi9b", 'Bitcoin address'),
    'OUR_FEE_SHARE': (0.005, ' '),
    'CRYPTOPAY_API_KEY': ('', 'CryptoPay API key'),
    'GOCOIN_MERCHANT_ID': ('', 'GoCoin Merchant ID'),
    'GOCOIN_AUTH_TOKEN': ('', 'GoCoin access token'),
    'TERMINAL_PRICE': (200.00, 'Terminal price'),
}

REPORTS_PATH = os.path.join(BASE_DIR, '..', 'reports')

CERT_PATH = os.path.join(BASE_DIR, '..', 'certs')
PKI_KEY_FILE = None
PKI_CERTIFICATES = []

BITCOIND_HOST = "node.xbterminal.io"
BITCOIND_AUTH = {
    "testnet": ("root", "password"),
}

# OAuth
OAUTH2_PROVIDER = {
    'ACCESS_TOKEN_EXPIRE_SECONDS': 100000000,
}

# CKEditor
CKEDITOR_UPLOAD_PATH = "blog/"
CKEDITOR_JQUERY_URL = "/static/lib/jquery.min.js"

# Override default settings
try:
    from local_settings import *  # flake8: noqa
except ImportError:
    pass

if DEBUG:
    # Log to console in development mode
    LOGGING['loggers']['']['handlers'] = ['console']
    LOGGING['loggers']['django.request']['handlers'] = ['console']
    LOGGING['loggers']['rq.worker']['handlers'] = ['console']

if TESTING:
    # Disable logging
    LOGGING['loggers']['']['handlers'] = ['null']
    LOGGING['loggers']['django.request']['handlers'] = ['null']
    LOGGING['loggers']['rq.worker']['handlers'] = ['null']
    # Don't connect to bitcoind
    BITCOIND_AUTH = {
        'mainnet': (None, None),
        'testnet': (None, None),
    }
