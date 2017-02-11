from website.fixtures import fix_sequence

GROUPS = [
    {
        'id': 1,
        'name': 'controllers',
    },
]


def update_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for group_info in GROUPS:
        group, created = Group.objects.get_or_create(
            id=group_info['id'],
            defaults={
                'name': group_info['name'],
            })
        if not created:
            group.name = group_info['name']
    fix_sequence(Group)
