from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://greenbook:greenbook_dev@db:5432/greenbook"
    redis_url: str = "redis://redis:6379/0"
    minio_endpoint: str = "minio:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket: str = "greenbook-media"
    auth_secret_key: str = "dev-secret-key-change-in-production"
    auth_algorithm: str = "HS256"
    app_env: str = "development"

    model_config = {"env_file": ".env"}


settings = Settings()
