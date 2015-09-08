BATCHES = [
    {
        'batch_number': '00000000000000000000000000000000',
        'size': 0,
        'comment': 'Default batch',
    },
]


def update_batches(apps, schema_editor):
    DeviceBatch = apps.get_model('website', 'DeviceBatch')
    for item in BATCHES:
        DeviceBatch.objects.get_or_create(
            batch_number=item['batch_number'],
            defaults={
                'size': item['size'],
                'comment': item['comment'],
            })
