"""
Worker configuration.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Worker settings."""

    broker_url: str = "redis://localhost:6379/1"
    result_backend: str = "redis://localhost:6379/2"

    # Database (for tasks that need DB access)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/saas"

    # Email settings
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    email_from: str = "noreply@example.com"

    # Webhook settings
    webhook_timeout: int = 30
    webhook_max_retries: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
