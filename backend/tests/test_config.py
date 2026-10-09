import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_local_settings_default_to_sqlite(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ALLOW_MOCK_IDENTITY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_env == "local"
    assert settings.database_url == "sqlite+aiosqlite:///./family_menu.db"
    assert settings.allow_mock_identity is False


def test_production_requires_database_url(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None)


def test_mock_identity_is_rejected_outside_local_mode(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://db/app")
    monkeypatch.setenv("ALLOW_MOCK_IDENTITY", "true")

    with pytest.raises(ValidationError, match="mock identity"):
        Settings(_env_file=None)
