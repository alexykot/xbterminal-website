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
    {
        'id': 5,
        'name': 'BTC',
        'postfix': 'BTC',
    },
    {
        'id': 6,
        'name': 'TBTC',
        'postfix': 'tBTC',
    },
]


def update_currencies(apps, schema_editor):
    Currency = apps.get_model('website', 'Currency')
    for item in CURRENCIES:
        Currency.objects.get_or_create(
            id=item['id'],
            defaults={
                'name': item['name'],
                'prefix': item.get('prefix', ''),
                'postfix': item.get('postfix', ''),
            })
