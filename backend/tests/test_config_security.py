import pytest

from app.config import Settings


def test_production_config_validation_passes_with_secure_values():
    settings = Settings(
        app_env="production",
        enable_dev_auth=False,
        auth_secret_key="prod-secret",
        minio_root_user="prod-minio-user",
        minio_root_password="prod-minio-pass",
        cors_origins=["https://greenbook.nlmk.example"],
    )

    settings.validate_production_config()


def test_production_config_validation_fails_on_insecure_defaults():
    settings = Settings(
        app_env="production",
        enable_dev_auth=True,
        auth_secret_key="dev-secret-key-change-in-production",
        minio_root_user="minioadmin",
        minio_root_password="minioadmin",
        cors_origins=["*"],
    )

    with pytest.raises(RuntimeError):
        settings.validate_production_config()


def test_settings_parse_csv_lists():
    settings = Settings(
        cors_origins="http://localhost:5173,http://localhost:4173",
        media_allowed_content_types="image/jpeg,image/png",
    )

    assert settings.cors_origins == ["http://localhost:5173", "http://localhost:4173"]
    assert settings.media_allowed_content_types == ["image/jpeg", "image/png"]


def test_settings_parse_json_lists():
    settings = Settings(
        cors_origins='["http://localhost:5173"]',
        media_allowed_content_types='["image/jpeg","image/webp"]',
    )

    assert settings.cors_origins == ["http://localhost:5173"]
    assert settings.media_allowed_content_types == ["image/jpeg", "image/webp"]
