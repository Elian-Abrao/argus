"""Application settings for the remote logger API."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://logger:logger@localhost:5432/logger_db"  # noqa: E501
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    queue_instances: str = "logger.instances"
    queue_runs: str = "logger.runs"
    queue_logs: str = "logger.logs"
    queue_snapshots: str = "logger.snapshots"
    api_prefix: str = "/api"
    app_name: str = "Logger Remote API"
    default_timezone: str = "UTC"
    email_retention_days_default: int = 7
    email_retention_cleanup_enabled: bool = True
    email_retention_cleanup_interval_seconds: int = 3600
    email_retention_cleanup_batch_size: int = 500
    run_stale_cleanup_enabled: bool = True
    run_stale_timeout_hours: float = 0.5  # 30 minutos
    run_stale_cleanup_interval_seconds: int = 300
    run_stale_cleanup_batch_size: int = 500
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "logger-email-attachments"
    minio_secure: bool = False
    schedule_checker_enabled: bool = True
    schedule_checker_interval_seconds: int = 60
    command_expiry_hours: int = 2
    command_expiry_interval_seconds: int = 300

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7
    cookie_secure: bool = False  # Set True in production (HTTPS only)

    class Config:
        env_prefix = "LOGGER_API_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
