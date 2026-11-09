import psycopg
from psycopg.rows import dict_row
from config import Config

def get_db_connection():
    """Retorna una conexión activa a Supabase usando psycopg (versión 3)."""
    return psycopg.connect(Config.DATABASE_URL, row_factory=dict_row)