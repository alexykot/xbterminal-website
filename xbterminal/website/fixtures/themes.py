from website.fixtures import fix_sequence

THEMES = [
    {
        'id': 1,
        'name': 'default',
    },
]


def update_themes(apps, schema_editor):
    UITheme = apps.get_model('website', 'UITheme')
    for theme in THEMES:
        UITheme.objects.get_or_create(
            id=theme['id'],
            defaults={
                'name': theme['name'],
            })
    fix_sequence(UITheme)
