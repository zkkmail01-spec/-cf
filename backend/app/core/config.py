from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: Literal["local", "test", "production"] = "local"
    database_url: str | None = None
    allow_mock_identity: bool = False
    api_prefix: str = "/api/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_environment(self) -> "Settings":
        if self.app_env == "local" and not self.database_url:
            self.database_url = "sqlite+aiosqlite:///./family_menu.db"
        if self.app_env != "local" and not self.database_url:
            raise ValueError("DATABASE_URL is required outside local mode")
        if self.app_env != "local" and self.allow_mock_identity:
            raise ValueError("mock identity is allowed only in local mode")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
