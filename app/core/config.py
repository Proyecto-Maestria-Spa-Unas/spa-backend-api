from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración tipada; se carga desde variables de entorno o archivo .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Spa de Uñas · Inventario API"
    app_env: str = Field(default="development", alias="APP_ENV")
    api_prefix: str = "/api/v1"

    db_url: str = Field(default="postgresql+psycopg://postgres:postgres@localhost:5432/spa", alias="DB_URL")

    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expires_minutes: int = Field(default=30, alias="JWT_EXPIRES_MINUTES")

    cors_origins: list[str] = Field(default=["http://localhost:5173"], alias="CORS_ORIGINS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
