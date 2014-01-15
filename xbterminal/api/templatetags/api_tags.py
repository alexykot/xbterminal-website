from django import template

register = template.Library()


@register.filter
def amount(value):
    return '{0:g}'.format(float(value))
