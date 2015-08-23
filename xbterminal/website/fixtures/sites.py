SITES = [
    {
        'id': 1,
        'domain': 'xbterminal.io',
        'name': 'XBTerminal production',
    },
    {
        'id': 2,
        'domain': 'stage.xbterminal.com',
        'name': 'XBTerminal staging',
    },
    {
        'id': 3,
        'domain': 'localhost:8000',
        'name': 'XBTerminal development',
    }
]


def update_sites(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    for item in SITES:
        Site.objects.get_or_create(
            id=item['id'],
            defaults={
                'domain': item['domain'],
                'name': item['name'],
            })
