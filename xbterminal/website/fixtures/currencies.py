# -*- coding: utf-8 -*-

CURRENCIES = [
    {
        'id': 1,
        'name': 'GBP',
        'prefix': '£',
        'is_fiat': True,
    },
    {
        'id': 2,
        'name': 'USD',
        'prefix': '$',
        'is_fiat': True,
    },
    {
        'id': 3,
        'name': 'EUR',
        'prefix': '€',
        'is_fiat': True,
    },
    {
        'id': 4,
        'name': 'CAD',
        'prefix': '$',
        'is_fiat': True,
    },
    {
        'id': 5,
        'name': 'BTC',
        'postfix': 'BTC',
        'is_fiat': False,
    },
    {
        'id': 6,
        'name': 'TBTC',
        'postfix': 'tBTC',
        'is_fiat': False,
    },
    {
        'id': 7,
        'name': 'DASH',
        'postfix': 'DASH',
        'is_fiat': False,
    },
    {
        'id': 8,
        'name': 'TDASH',
        'postfix': 'tDASH',
        'is_fiat': False,
    },
]


def update_currencies(apps, schema_editor):
    Currency = apps.get_model('website', 'Currency')
    fields = [field.name for field in Currency._meta.get_fields()]
    for item in CURRENCIES:
        # Remove values for fields which are not created yet
        currency_data = {name: item[name] for name in item
                         if name in fields}
        currency_id = currency_data.pop('id')
        Currency.objects.update_or_create(id=currency_id,
                                          defaults=currency_data)
