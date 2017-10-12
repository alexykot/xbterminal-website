from django.apps import apps
from django.db import connection


def lock_table(model):
    """
    Block model table for the duration of transaction
    Accepts:
        model: Model instance or string in 'app.ModelName' format
    """
    if isinstance(model, basestring):
        model = apps.get_model(model)
    table_name = model._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(
            'LOCK TABLE {table_name}'.format(table_name=table_name))


def refresh_for_update(obj):
    model = obj._meta.model
    new_obj = model.objects.select_for_update().get(pk=obj.pk)
    # Make original object immutable
    obj.save = None
    return new_obj
