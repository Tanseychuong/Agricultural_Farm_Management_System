from django.db import connection


def total_harvest_yield_per_farm():
    """
    Worked example wiring a Phase 5 query into Django. Once the Phase 6
    SQL views exist in the database, swap this to a plain SELECT against
    the view name instead — no Python logic duplicated, the view stays
    the single source of truth for the aggregation.
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT f.farm_name, f.location, SUM(h.quantity) AS total_harvest_yield
            FROM farm f
            JOIN crop cr ON f.farm_id = cr.farm_id
            JOIN harvest h ON cr.crop_id = h.crop_id
            GROUP BY f.farm_id, f.farm_name, f.location
        """)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
