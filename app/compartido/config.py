"""Configuración tipada (Pydantic Settings). Se lee de variables de entorno o de `.env`.

Los nombres coinciden con los de Vercel y con `.env.example`. Ningún valor real va en el repositorio.
"""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Spa de Uñas · Inventario API"
    app_env: str = Field(default="development", alias="APP_ENV")
    api_prefix: str = "/api/v1"

    # Base de datos (S0 · Datos). En Vercel: pooler de transacciones de Supabase, puerto 6543.
    db_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/postgres",
        alias="DB_URL",
    )

    # JWT: S1 lo firma; todos los módulos lo verifican.
    jwt_secret: SecretStr = Field(default=SecretStr("cambiar-en-local"), alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expires_minutes: int = Field(default=30, alias="JWT_EXPIRES_MINUTES")

    cors_origins: list[str] = Field(default=["http://localhost:5173"], alias="CORS_ORIGINS")

    # Solo el adaptador de Supabase Auth de S1 puede leer la clave secreta (salta RLS).
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_secret_key: SecretStr | None = Field(default=None, alias="SUPABASE_SECRET_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()
