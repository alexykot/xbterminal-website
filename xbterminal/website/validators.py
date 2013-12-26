from django.core.exceptions import ValidationError


def validate_percent(value):
    if value > 100 or value < 0:
        raise ValidationError(u'%s is not an valid percent' % value)
