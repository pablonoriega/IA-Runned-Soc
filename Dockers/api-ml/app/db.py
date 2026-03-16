import os
import psycopg2
import psycopg2.extras

PG_HOST = os.getenv("PG_HOST", "soc-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "socdb")
PG_USER = os.getenv("PG_USER", "soc")
PG_PASS = os.getenv("PG_PASS", "socpass")


def get_conn():
    """
    Conexión Postgres con RealDictCursor (rows como dict).
    """
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )