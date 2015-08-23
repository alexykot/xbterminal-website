# -*- coding: utf-8 -*-

LANGUAGES = [
    {
        'id': 1,
        'name': 'English',
        'code': 'en',
    },
    {
        'id': 2,
        'name': 'Deutsch',
        'code': 'de',
    },
    {
        'id': 3,
        'name': 'Français',
        'code': 'fr',
    },
    {
        'id': 4,
        'name': 'Русский',
        'code': 'ru',
    },
]


def update_languages(apps, schema_editor):
    Language = apps.get_model('website', 'Language')
    for item in LANGUAGES:
        Language.objects.get_or_create(
            id=item['id'],
            defaults={
                'name': item['name'],
                'code': item['code'],
            })
