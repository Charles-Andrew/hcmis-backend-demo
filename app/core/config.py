from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "HCMIS Backend"
    app_version: str = "0.1.0"

    database_url: str = Field(
        default="postgresql+asyncpg://hcmis:hcmis@localhost:15432/hcmis",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://localhost:16379/0",
        validation_alias="REDIS_URL",
    )
    jwt_secret_key: str = Field(
        default="change-me",
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = "HS256"
    access_token_expiry_minutes: int = Field(
        default=60 * 24,
        validation_alias="ACCESS_TOKEN_EXPIRY_MINUTES",
    )
    environment: str = Field(
        default="development",
        validation_alias="ENVIRONMENT",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
