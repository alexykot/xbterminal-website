"""
Django settings for xbterminal project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '2d$h2q_vukyb190m^6#q)k_rc!+dn8!m5=pc!&e!vckabjqqll'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
TEMPLATE_DEBUG = False

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

    'south',
    'bootstrapform',
    'bootstrap3',
    'rest_framework',
    'qrcode',
    'constance',
    'constance.backends.database',

    'website',
    'api'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'xbterminal.urls'

WSGI_APPLICATION = 'xbterminal.wsgi.application'


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

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'
# need to set absolute path, because it use in pdf generating
STATIC_ROOT = os.path.join(BASE_DIR, '..', 'static')

DEFAULT_FROM_EMAIL = "no-reply@xbterminal.com"
CONTACT_EMAIL_RECIPIENTS = ["info@xbterminal.com"]

APPEND_SLASH = True

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/devices/'

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
    'OUR_FEE_BITCOIN_ADDRESS': ("mqhQfj9e57SNEYWNvULegMWfM9DQ8UGi9b", ' '),
    'OUR_FEE_SHARE': (0.005, ' '),
}

FIRMWARE_PATH = os.path.join(BASE_DIR, '..', 'firmware')

# Override default settings
try:
    from local_settings import *
except ImportError:
    pass
