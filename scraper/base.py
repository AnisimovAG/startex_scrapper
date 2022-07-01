from django.db import connection


def truncate_table(table: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(f'truncate partners_{table}product restart identity')