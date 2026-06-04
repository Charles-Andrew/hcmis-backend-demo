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
    app_timezone: str = Field(
        default="Asia/Manila",
        validation_alias="APP_TIMEZONE",
    )
    shared_resources_max_file_size_mb: int = Field(
        default=50,
        validation_alias="SHARED_RESOURCES_MAX_FILE_SIZE_MB",
    )
    supabase_storage_region: str = Field(
        default="ap-southeast-1",
        validation_alias="SUPABASE_STORAGE_REGION",
    )
    supabase_storage_endpoint_url: str | None = Field(
        default=None,
        validation_alias="SUPABASE_STORAGE_ENDPOINT_URL",
    )
    supabase_storage_access_key_id: str | None = Field(
        default=None,
        validation_alias="SUPABASE_STORAGE_ACCESS_KEY_ID",
    )
    supabase_storage_secret_access_key: str | None = Field(
        default=None,
        validation_alias="SUPABASE_STORAGE_SECRET_ACCESS_KEY",
    )
    shared_resources_s3_bucket: str = Field(
        default="",
        validation_alias="SHARED_RESOURCES_S3_BUCKET",
    )
    shared_resources_s3_public_base_url: str | None = Field(
        default=None,
        validation_alias="SHARED_RESOURCES_S3_PUBLIC_BASE_URL",
    )
    shared_resources_s3_prefix: str = Field(
        default="shared-resources",
        validation_alias="SHARED_RESOURCES_S3_PREFIX",
    )
    shared_resources_signed_url_ttl_seconds: int = Field(
        default=900,
        validation_alias="SHARED_RESOURCES_SIGNED_URL_TTL_SECONDS",
    )
    training_attachments_max_file_size_mb: int = Field(
        default=50,
        validation_alias="TRAINING_ATTACHMENTS_MAX_FILE_SIZE_MB",
    )
    training_attachments_s3_bucket: str = Field(
        default="training-attachments",
        validation_alias="TRAINING_ATTACHMENTS_S3_BUCKET",
    )
    training_attachments_s3_prefix: str = Field(
        default="training-attachments",
        validation_alias="TRAINING_ATTACHMENTS_S3_PREFIX",
    )
    training_attachments_signed_url_ttl_seconds: int = Field(
        default=900,
        validation_alias="TRAINING_ATTACHMENTS_SIGNED_URL_TTL_SECONDS",
    )
    profile_photos_max_file_size_mb: int = Field(
        default=5,
        validation_alias="PROFILE_PHOTOS_MAX_FILE_SIZE_MB",
    )
    profile_photos_s3_bucket: str = Field(
        default="",
        validation_alias="PROFILE_PHOTOS_S3_BUCKET",
    )
    profile_photos_s3_public_base_url: str | None = Field(
        default=None,
        validation_alias="PROFILE_PHOTOS_S3_PUBLIC_BASE_URL",
    )
    profile_photos_s3_prefix: str = Field(
        default="profile-photos",
        validation_alias="PROFILE_PHOTOS_S3_PREFIX",
    )
    profile_photos_signed_url_ttl_seconds: int = Field(
        default=900,
        validation_alias="PROFILE_PHOTOS_SIGNED_URL_TTL_SECONDS",
    )
    bridge_agent_key: str = Field(
        default="",
        validation_alias="BRIDGE_AGENT_KEY",
    )
    bridge_device_timezone: str = Field(
        default="Asia/Manila",
        validation_alias="BRIDGE_DEVICE_TIMEZONE",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
