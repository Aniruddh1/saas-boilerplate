"""
Application configuration using Pydantic Settings.
"""

from typing import Any
from functools import lru_cache
from pydantic import Field, field_validator, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(env_prefix="DB_")

    url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/saas",
        description="PostgreSQL connection URL",
    )
    pool_size: int = Field(default=5, ge=1, le=100)
    pool_overflow: int = Field(default=10, ge=0, le=100)
    pool_timeout: int = Field(default=30, ge=1)
    echo: bool = Field(default=False, description="Echo SQL queries")


class RedisSettings(BaseSettings):
    """Redis configuration."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    max_connections: int = Field(default=10, ge=1)
    decode_responses: bool = Field(default=True)


class AuthSettings(BaseSettings):
    """Authentication and authorization configuration."""

    model_config = SettingsConfigDict(env_prefix="AUTH_")

    # JWT Settings
    secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for JWT signing",
    )
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, ge=1)
    refresh_token_expire_days: int = Field(default=7, ge=1)
    password_min_length: int = Field(default=8, ge=6)

    # Authorization Settings
    policy_engine: str = Field(
        default="simple",
        description="Policy engine: simple, rbac, casbin",
    )
    scope_provider: str = Field(
        default="none",
        description="Scope provider: none, ownership, hierarchical",
    )

    # Multi-tenancy
    multi_tenant: bool = Field(
        default=False,
        description="Enable multi-tenant data isolation",
    )
    tenant_field: str = Field(
        default="organization_id",
        description="Field name for tenant ID on models",
    )


class StorageSettings(BaseSettings):
    """
    Storage backend configuration.

    Supports 30+ cloud providers via Apache Libcloud:
    - local: Local filesystem
    - s3/aws/minio: AWS S3 or S3-compatible
    - gcs/google: Google Cloud Storage
    - azure: Azure Blob Storage
    - digitalocean/spaces: DigitalOcean Spaces
    - backblaze/b2: Backblaze B2
    - linode: Linode Object Storage
    """

    model_config = SettingsConfigDict(env_prefix="STORAGE_")

    # Provider selection
    backend: str = Field(
        default="local",
        description="local, s3, gcs, azure, digitalocean, backblaze, linode, etc.",
    )

    # Local storage
    local_path: str = Field(default="./uploads")

    # Cloud storage (universal)
    container: str = Field(default="", description="Bucket/container name")
    key: str = Field(default="", description="Access key / account name")
    secret: str = Field(default="", description="Secret key / account key")
    region: str = Field(default="", description="Region (s3, digitalocean, etc.)")
    project: str = Field(default="", description="Project ID (gcs)")
    endpoint: str | None = Field(default=None, description="Custom endpoint (MinIO)")

    # Legacy S3 settings (for backwards compatibility)
    s3_bucket: str = Field(default="")
    s3_region: str = Field(default="us-east-1")
    s3_access_key: str = Field(default="")
    s3_secret_key: str = Field(default="")
    s3_endpoint: str | None = Field(default=None)


class SearchSettings(BaseSettings):
    """Search backend configuration."""

    model_config = SettingsConfigDict(env_prefix="SEARCH_")

    backend: str = Field(default="meilisearch")
    meilisearch_url: str = Field(default="http://localhost:7700")
    meilisearch_api_key: str = Field(default="")


class EmailSettings(BaseSettings):
    """Email backend configuration."""

    model_config = SettingsConfigDict(env_prefix="EMAIL_")

    backend: str = Field(default="smtp", description="smtp, sendgrid, ses")
    from_address: str = Field(default="noreply@example.com")
    from_name: str = Field(default="SaaS App")

    # SMTP settings
    smtp_host: str = Field(default="localhost")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_tls: bool = Field(default=True)


class QueueSettings(BaseSettings):
    """Task queue configuration."""

    model_config = SettingsConfigDict(env_prefix="QUEUE_")

    backend: str = Field(default="celery")
    broker_url: str = Field(default="redis://localhost:6379/1")
    result_backend: str = Field(default="redis://localhost:6379/2")


class FeatureSettings(BaseSettings):
    """Feature flag configuration."""

    model_config = SettingsConfigDict(env_prefix="FEATURE_")

    backend: str = Field(
        default="database",
        description="Feature flag backend: database, memory",
    )
    default_enabled: bool = Field(
        default=False,
        description="Default value when flag doesn't exist",
    )
    cache_ttl: int = Field(
        default=60,
        description="Cache TTL for flag values (seconds)",
    )


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="SaaS API")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)
    environment: str = Field(default="development")

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=1)
    reload: bool = Field(default=False)

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:3000"])
    cors_allow_credentials: bool = Field(default=True)

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json", description="json or text")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests: int = Field(default=100)
    rate_limit_window: int = Field(default=60, description="Window in seconds")

    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    queue: QueueSettings = Field(default_factory=QueueSettings)
    features: FeatureSettings = Field(default_factory=FeatureSettings)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production", "testing"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    def get_backends_config(self) -> dict[str, Any]:
        """Get configuration for DI container."""
        return {
            "backends": {
                "storage": self.storage.backend,
                "cache": "redis",
                "queue": self.queue.backend,
                "search": self.search.backend,
                "email": self.email.backend,
                "events": "redis",
            },
            "storage": {
                "path": self.storage.local_path,
                "bucket": self.storage.s3_bucket,
                "region": self.storage.s3_region,
            },
            "cache": {
                "url": str(self.redis.url),
            },
            "search": {
                "url": self.search.meilisearch_url,
                "api_key": self.search.meilisearch_api_key,
            },
            "email": {
                "host": self.email.smtp_host,
                "port": self.email.smtp_port,
                "from_address": self.email.from_address,
            },
            "events": {
                "url": str(self.redis.url),
            },
        }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Shorthand
settings = get_settings()
