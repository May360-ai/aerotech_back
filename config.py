import os

class Config:
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost:5432/midb_local")
    JWT_SECRET = os.environ.get("JWT_SECRET", "clave_por_defecto_solo_desarrollo")
    IVA_PORCENTAJE = 0.15