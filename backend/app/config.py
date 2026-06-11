import json
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode


def _parse_list_like(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []

    if value.startswith("["):
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]

    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    database_url: str = "postgresql://greenbook:greenbook_dev@db:5432/greenbook"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout_seconds: int = 30
    db_pool_recycle_seconds: int = 1800
    db_pool_pre_ping: bool = True
    redis_url: str = "redis://redis:6379/0"
    redis_cache_enabled: bool = True
    redis_cache_namespace: str = "v1"
    minio_endpoint: str = "minio:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket: str = "greenbook-media"
    auth_secret_key: str = "dev-secret-key-change-in-production"
    auth_algorithm: str = "HS256"
    auth_access_token_expire_minutes: int = Field(default=60 * 24 * 7, ge=5, le=60 * 24 * 30)
    bootstrap_admin_login: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_display_name: str | None = None
    bootstrap_admin_email: str | None = None
    # Fail-closed: без явного APP_ENV=development применяются production-проверки.
    app_env: str = "production"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    enable_dev_auth: bool = False
    media_max_upload_bytes: int = 10 * 1024 * 1024
    media_max_image_dimension: int = Field(default=2560, ge=256, le=8192)
    media_max_image_pixels: int = Field(default=24_000_000, ge=1_000_000, le=200_000_000)
    media_thumbnail_size: int = Field(default=400, ge=64, le=2048)
    media_async_processing_enabled: bool = True
    media_direct_upload_enabled: bool = True
    serve_legacy_species_pdf_media: bool = False
    media_processing_batch_size: int = Field(default=20, ge=1, le=500)
    media_processing_max_attempts: int = Field(default=3, ge=1, le=20)
    media_processing_retry_backoff_seconds: int = Field(default=30, ge=1, le=3600)
    media_allowed_content_types: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"]
    )
    api_rate_limit_per_minute: int = 120
    auth_rate_limit_per_minute: int = Field(default=10, ge=1, le=10_000)
    api_trusted_proxies: Annotated[list[str], NoDecode] = Field(default_factory=list)
    api_rate_limit_enabled: bool = True
    api_gzip_enabled: bool = True
    api_gzip_minimum_size: int = 1024
    dashboard_summary_cache_ttl_seconds: int = 20
    map_zones_cache_ttl_seconds: int = 300
    map_observations_cache_ttl_seconds: int = 10
    gamification_stats_cache_ttl_seconds: int = 30
    species_list_cache_ttl_seconds: int = 120
    validation_queue_cache_ttl_seconds: int = 15
    notification_unread_cache_ttl_seconds: int = 10
    audit_log_retention_days: int = Field(default=180, ge=1, le=36500)
    unattached_media_retention_hours: int = Field(default=24, ge=1, le=24 * 365)
    rejected_observation_media_retention_days: int = Field(default=90, ge=1, le=36500)
    privacy_notice_version: str = "2026-06-03"
    privacy_operator_name: str = "ПАО «НЛМК»"
    privacy_processing_purpose: str = (
        "Вход в приложение, обработка наблюдений, участие в рейтинге "
        "и обратная связь по отправленным материалам."
    )
    privacy_retention_text: str = (
        "Учетная запись хранится до удаления или обезличивания администратором; "
        "журнал событий хранится согласно настройке AUDIT_LOG_RETENTION_DAYS."
    )
    privacy_contact_text: str = (
        "По вопросам обработки данных обратитесь к владельцу сервиса или администратору системы."
    )
    ops_alert_on_review_threshold: int = Field(default=100, ge=0, le=1_000_000)
    ops_alert_open_incidents_threshold: int = Field(default=0, ge=0, le=1_000_000)
    ops_alert_error_rate_percent_threshold: float = Field(default=5.0, ge=0.0, le=100.0)
    ops_alert_media_pending_threshold: int = Field(default=200, ge=0, le=1_000_000)
    ops_alert_media_pending_age_seconds_threshold: int = Field(
        default=900, ge=0, le=86_400
    )
    ops_alert_media_failed_threshold: int = Field(default=0, ge=0, le=1_000_000)
    ops_alert_cache_degraded_stores_threshold: int = Field(
        default=0, ge=0, le=1_000_000
    )
    health_dependency_timeout_ms: int = Field(default=250, ge=50, le=10_000)
    health_dependency_cache_ttl_seconds: float = Field(default=3.0, ge=0.0, le=60.0)
    ymaps_config_cache_ttl_seconds: int = 3600
    log_level: str = "INFO"
    log_json: bool = True
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.0
    sentry_profiles_sample_rate: float = 0.0
    ymaps_api_key: str = ""
    uvicorn_workers: int = 2

    model_config = {"env_file": ".env"}

    @field_validator(
        "cors_origins", "media_allowed_content_types", "api_trusted_proxies", mode="before"
    )
    @classmethod
    def _coerce_list(cls, value):
        if isinstance(value, str):
            return _parse_list_like(value)
        return value

    def validate_production_config(self) -> None:
        if self.app_env in {"development", "test"}:
            return

        problems: list[str] = []
        if self.enable_dev_auth:
            problems.append("ENABLE_DEV_AUTH must be false outside development")
        if self.auth_secret_key == "dev-secret-key-change-in-production":
            problems.append("AUTH_SECRET_KEY uses insecure default value")
        if self.minio_root_user == "minioadmin":
            problems.append("MINIO_ROOT_USER uses insecure default value")
        if self.minio_root_password == "minioadmin":
            problems.append("MINIO_ROOT_PASSWORD uses insecure default value")
        if not self.cors_origins:
            problems.append("CORS_ORIGINS must not be empty")
        if "*" in self.cors_origins:
            problems.append("CORS_ORIGINS cannot contain wildcard in non-development")
        if self.media_direct_upload_enabled:
            problems.append("MEDIA_DIRECT_UPLOAD_ENABLED must be false outside development")
        if self.serve_legacy_species_pdf_media:
            problems.append("SERVE_LEGACY_SPECIES_PDF_MEDIA must be false outside development")
        if self.bootstrap_admin_login and not self.bootstrap_admin_password:
            problems.append("BOOTSTRAP_ADMIN_PASSWORD is required when BOOTSTRAP_ADMIN_LOGIN is set")
        if self.bootstrap_admin_password and len(self.bootstrap_admin_password) < 12:
            problems.append("BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters")

        if problems:
            raise RuntimeError("Invalid production configuration: " + "; ".join(problems))


settings = Settings()
