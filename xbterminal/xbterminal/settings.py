from decimal import Decimal
import os
import sys
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TEMP_DIR = tempfile.mkdtemp(prefix='xbt')

DEBUG = False
SQL_DEBUG = False
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
    'filters': {
        'ggt': {
            '()': 'common.log.GeneratingGrammarTablesFilter',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'short',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, '..', 'logs', 'django.log'),
            'formatter': 'default',
            'filters': ['ggt'],
        },
        'rq': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, '..', 'logs', 'rq.log'),
            'formatter': 'short',
        },
        'sentry': {
            'level': 'WARNING',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file', 'sentry'],
            'level': 'DEBUG',
        },
        'django.request': {
            'handlers': ['file', 'sentry'],
            'level': 'WARNING',
            'propagate': False,
        },
        'rq.worker': {
            'handlers': ['rq', 'sentry'],
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

INSTALLED_APPS = [
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
    'localflavor',
    'django_fsm',
    'fsm_admin',
    'raven.contrib.django.raven_compat',
    'formtools',

    'website',
    'operations',
    'api',
    'wallet.apps.WalletConfig',
    'transactions.apps.TransactionsConfig',
]

MIDDLEWARE_CLASSES = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
]

SITE_ID = 1

ALLOWED_HOSTS = []

ROOT_URLCONF = 'xbterminal.urls'

APPEND_SLASH = False

LOGIN_URL = '/login/'

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
    'COERCE_DECIMAL_TO_STRING': False,
    'DEFAULT_PERMISSION_CLASSES': [],
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_RENDERER_CLASSES': [
        'api.renderers.CustomJSONRenderer',
    ],
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'xbt',
        'USER': 'xbt',
        'PASSWORD': 'xbt',
        'HOST': 'localhost',
        'PORT': '5432',
    },
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
    'low': {
        # For activation
        'URL': 'redis://127.0.0.1:6379/1',
    },
    'high': {
        # For payments and withdrawals
        'URL': 'redis://127.0.0.1:6379/1',
    },
}

RQ_EXCEPTION_HANDLERS = ['common.rq_helpers.sentry_exc_handler']

# Internationalization

LANGUAGE_CODE = 'en'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]


# Static files (CSS, JavaScript, Images)

STATIC_ROOT = os.path.join(BASE_DIR, '..', 'static')
STATIC_URL = '/static/'

# Media

MEDIA_URL = '/'

if TESTING:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_ROOT = TEMP_DIR
else:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
    AWS_DEFAULT_ACL = 'private'

# Email

EMAIL_HOST = ""
EMAIL_PORT = ""
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_SSL = True

DEFAULT_FROM_EMAIL = "no-reply@xbterminal.io"
CONTACT_EMAIL_RECIPIENTS = ["info@xbterminal.io"]

# Blockchains

BLOCKCHAINS = {
    'BTC': {
        'HOST': 'localhost',
        'PORT': 8332,
        'USER': 'xbt',
        'PASSWORD': 'xbt',
    },
    'TBTC': {
        'HOST': 'localhost',
        'PORT': 18332,
        'USER': 'xbt',
        'PASSWORD': 'xbt',
    },
    'DASH': {
        'HOST': 'localhost',
        'PORT': 9998,
        'USER': 'xbt',
        'PASSWORD': 'xbt',
    },
    'TDASH': {
        'HOST': 'localhost',
        'PORT': 19998,
        'USER': 'xbt',
        'PASSWORD': 'xbt',
    },
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
    'BLOCKCYPHER_API_TOKEN': ('', 'BlockCypher API token'),
    'CURRENT_BATCH_NUMBER': ('', 'Batch number'),
    'TX_DEFAULT_FEE': (Decimal('0.00150000'), 'Default TX fee, BTC per Kb'),
    'TX_EXPECTED_CONFIRM': (10, 'Expected max number of blocks TX should '
                                'wait before it is included in a block'),
    'TX_CONFIDENCE_THRESHOLD': (0.95, 'Transaction confidence threshold'),
    'TX_REQUIRED_CONFIRMATIONS': (6, 'Number of required confirmations for TX'),
    'POOL_TX_MAX_OUTPUT': (Decimal('0.05'),
                           'Maximum value of TX output in the pool'),
    'ENABLE_SALT': (True, 'Enable Salt integration'),
}

# Sentry

RAVEN_CONFIG = {}

# Misc

CERT_PATH = os.path.join(BASE_DIR, '..', 'certs')
PKI_KEY_FILE = None
PKI_CERTIFICATES = []

RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_PUBLIC_KEY = ''

BITCOIN_SCALE_DIVIZER = 1000

DEFAULT_BATCH_NUMBER = '00000000000000000000000000000000'

SWAGGER_SPEC_PATH = os.path.join(BASE_DIR, 'api', 'specs')


# Override default settings
try:
    from local_settings import *  # flake8: noqa
except ImportError:
    pass

if DEBUG:
    # Log to console in development mode
    LOGGING['loggers']['']['handlers'].append('console')
    LOGGING['loggers']['django.request']['handlers'].append('console')
    LOGGING['loggers']['rq.worker']['handlers'].append('console')

if SQL_DEBUG:
    LOGGING['loggers']['django.db.backends'] = {
        'level': 'DEBUG',
        'handlers': ['console'],
        'propagate': False,
    }

if TESTING:
    # Disable logging
    LOGGING['loggers']['']['handlers'] = ['null']
    LOGGING['loggers']['django.request']['handlers'] = ['null']
    LOGGING['loggers']['rq.worker']['handlers'] = ['null']
    # Disable redis cache
    CACHES['default'] = {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
    # Disable RQ
    RQ_QUEUES = {}
    # Don't connect to bitcoind
    BITCOIND_AUTH = {
        'mainnet': (None, None),
        'testnet': (None, None),
    }
    # Don't connect to Salt server
    SALT_SERVERS = {}
