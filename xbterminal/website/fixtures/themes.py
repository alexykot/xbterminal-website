from django.db import connection

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
    # Fix sequence
    with connection.cursor() as cur:
        cur.execute("""
            SELECT setval(
                'website_uitheme_id_seq',
                (SELECT max(id) + 1 FROM website_uitheme),
                FALSE);
            """)
