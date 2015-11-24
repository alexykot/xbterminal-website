from django.db import connection


def fix_sequence(model, field='id'):
    sql = """
        SELECT setval(
            '{table}_{field}_seq',
            (SELECT max({field}) + 1 FROM {table}),
            FALSE);
        """.format(table=model._meta.db_table, field=field)
    with connection.cursor() as cur:
        cur.execute(sql)
