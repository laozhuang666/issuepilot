from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    github_token: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    github_api_url: str = "https://api.github.com"
    max_repository_files: int = Field(default=500, ge=50, le=5_000)
    max_context_files: int = Field(default=6, ge=1, le=12)
    max_file_bytes: int = Field(default=120_000, ge=5_000, le=500_000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
