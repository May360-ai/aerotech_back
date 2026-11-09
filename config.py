import os

class Config:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres.jnrefeeqqxlnstsdyqtj:0998872334mR@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
    )
    JWT_SECRET = os.getenv("JWT_SECRET", "clave_secreta_super_segura_uta_2026")
    IVA_PORCENTAJE = 0.15