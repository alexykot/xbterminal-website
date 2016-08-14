# xbt-webstatic-prod, xbt-webstatic-stage
AWS_STORAGE_BUCKET_NAME = '#AWS_STORAGE_BUCKET_NAME#'
AWS_ACCESS_KEY_ID = '#AWS_ACCESS_KEY_ID#'
AWS_SECRET_ACCESS_KEY = '#AWS_SECRET_ACCESS_KEY#'
AWS_DEFAULT_ACL = 'public'

AWS_S3_CUSTOM_DOMAIN = '%s.s3-eu-west-1.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
STATIC_URL = 'https://%s/' % AWS_S3_CUSTOM_DOMAIN

STATICFILES_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
