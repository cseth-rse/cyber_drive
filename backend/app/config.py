# app/config.py
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = "development"
    port: int = 3000
    frontend_url: str = "http://localhost:5173"

    # Database
    database_url: str

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str
    jwt_refresh_secret: str
    jwt_expires_minutes: int = 15
    jwt_refresh_expires_days: int = 7

    # Email (SMTP)
    email_host: str
    email_port: int = 587
    email_secure: bool = False
    email_user: str
    email_pass: str
    email_from: str = "Cyber Drive <no-reply@cyberdrive.app>"

    # Local file storage (used as fallback when S3 is disabled)
    upload_dir: str = "uploads"
    max_file_size_mb: int = 50

    # ── Phase 4: S3 / MinIO object storage ────────────────────────────────────
    s3_enabled: bool = False                       # set True to use S3/MinIO
    s3_endpoint: str = "http://localhost:9000"     # MinIO or AWS endpoint
    s3_region: str = "us-east-1"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "cyber-drive"
    s3_force_path_style: bool = True               # required for MinIO
    s3_presigned_url_expires: int = 900            # seconds (15 min)

    # ── Phase 4: Monitoring ────────────────────────────────────────────────────
    sentry_dsn: str = ""                           # leave empty to disable
    metrics_enabled: bool = True

    @field_validator("jwt_secret", "jwt_refresh_secret")
    @classmethod
    def secrets_must_be_long(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("JWT secrets must be at least 16 characters")
        return v

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def using_s3(self) -> bool:
        return self.s3_enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
