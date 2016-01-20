import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DEBUG = False
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
        },
        'rq_scheduler.scheduler': {
            'level': 'WARNING',
        },
    },
}

# Applications

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
    'constance',
    'constance.backends.database',
    'django_rq',
    'oauth2_provider',
    'captcha',
    'django_fsm',
    'fsm_admin',

    'website',
    'operations',
    'api',
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

SITE_ID = 1

ALLOWED_HOSTS = []

ROOT_URLCONF = 'xbterminal.urls'

APPEND_SLASH = False

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/terminals/'

WSGI_APPLICATION = 'xbterminal.wsgi.application'

AUTH_USER_MODEL = 'website.User'

SECRET_KEY = '2d$h2q_vukyb190m^6#q)k_rc!+dn8!m5=pc!&e!vckabjqqll'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'website.context_processors.debug',
            ],
        },
    },
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': []
}

# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'xbterminal',
        'USER': 'user',
        'PASSWORD': 'password',
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
    'high': {
        # For payments and withdrawals
        'USE_REDIS_CACHE': 'default',
    },
    'low': {
        # For activation
        'USE_REDIS_CACHE': 'default',
    },
}

# Internationalization

LANGUAGE_CODE = 'en'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)


# Static files (CSS, JavaScript, Images)

STATIC_ROOT = os.path.join(BASE_DIR, '..', 'static')
STATIC_URL = '/static/'

# Media

MEDIA_ROOT = os.path.join(BASE_DIR, '..', 'media')
MEDIA_URL = '/media/'

# Email

EMAIL_HOST = ""
EMAIL_PORT = ""
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_SSL = True

DEFAULT_FROM_EMAIL = "no-reply@xbterminal.io"
CONTACT_EMAIL_RECIPIENTS = ["info@xbterminal.io"]

# Bitcoind

BITCOIND_HOST = "node.xbterminal.io"
BITCOIND_AUTH = {
    'mainnet': ('user', 'password'),
    'testnet': ('user', 'password'),
}

# Salt

SALT_SERVERS = {
    'default': {
        'HOST': 'https://sam.xbthq.co.uk/',
        'USER': 'user',
        'PASSWORD': 'password',
        'CLIENT_CERT': 'server.pem',
        'CLIENT_KEY': 'server.key',
        'CA_CERT': 'xbthq.crt',
    },
}

# Aptly

APTLY_SERVERS = {
    'default': {
        'HOST': 'https://repo.xbthq.co.uk/',
        'CLIENT_CERT': 'server.crt',
        'CLIENT_KEY': 'server.key',
        'CA_CERT': 'xbthq.crt',
    },
}

# OAuth

OAUTH2_PROVIDER = {
    'ACCESS_TOKEN_EXPIRE_SECONDS': 100000000,
}

# Constance

CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'
CONSTANCE_CONFIG = {
    'OUR_FEE_MAINNET_ADDRESS': ("1XBTerm2eRrogkbtu1kiJKv8mH6XvpnJh", 'Bitcoin address'),
    'OUR_FEE_TESTNET_ADDRESS': ("mqhQfj9e57SNEYWNvULegMWfM9DQ8UGi9b", 'Bitcoin address'),
    'OUR_FEE_SHARE': (0.005, ' '),
    'CRYPTOPAY_API_KEY': ('', 'CryptoPay API key'),
    'GOCOIN_MERCHANT_ID': ('', 'GoCoin Merchant ID'),
    'GOCOIN_AUTH_TOKEN': ('', 'GoCoin access token'),
    'TERMINAL_PRICE': (200.00, 'Terminal price'),
    'CURRENT_BATCH_NUMBER': ('', 'Batch number'),
    'TX_CONFIDENCE_THRESHOLD': (0.95, 'Transaction confidence threshold'),
}

# Misc

CERT_PATH = os.path.join(BASE_DIR, '..', 'certs')
PKI_KEY_FILE = None
PKI_CERTIFICATES = []

REPORTS_PATH = os.path.join(BASE_DIR, '..', 'reports')

BITCOIN_SCALE_DIVIZER = 1000

DEFAULT_BATCH_NUMBER = '00000000000000000000000000000000'


# Override default settings
try:
    from local_settings import *  # flake8: noqa
except ImportError:
    pass

if DEBUG:
    # Log to console in development mode
    LOGGING['loggers']['']['handlers'] = ['file', 'console']
    LOGGING['loggers']['django.request']['handlers'] = ['file', 'console']
    LOGGING['loggers']['rq.worker']['handlers'] = ['rq', 'console']

if TESTING:
    # Disable logging
    LOGGING['loggers']['']['handlers'] = ['null']
    LOGGING['loggers']['django.request']['handlers'] = ['null']
    LOGGING['loggers']['rq.worker']['handlers'] = ['null']
    # Disable redis cache
    CACHES['default'] = {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
    # Don't connect to bitcoind
    BITCOIND_AUTH = {
        'mainnet': (None, None),
        'testnet': (None, None),
    }
    # Don't connect to Salt server
    SALT_SERVERS = None
