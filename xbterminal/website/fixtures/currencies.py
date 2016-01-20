# -*- coding: utf-8 -*-

CURRENCIES = [
    {
        'id': 1,
        'name': 'GBP',
        'prefix': '£',
    },
    {
        'id': 2,
        'name': 'USD',
        'prefix': '$',
    },
    {
        'id': 3,
        'name': 'EUR',
        'prefix': '€',
    },
    {
        'id': 4,
        'name': 'CAD',
        'prefix': '$',
    },
]


def update_currencies(apps, schema_editor):
    Currency = apps.get_model('website', 'Currency')
    for item in CURRENCIES:
        Currency.objects.get_or_create(
            id=item['id'],
            defaults={
                'name': item['name'],
                'prefix': item['prefix'],
            })
