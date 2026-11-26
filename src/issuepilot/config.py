from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    github_token: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    github_api_url: str = "https://api.github.com"
    max_repository_files: int = Field(
        default=500,
        ge=50,
        le=5_000,
        validation_alias="ISSUEPILOT_MAX_REPOSITORY_FILES",
    )
    max_context_files: int = Field(
        default=6,
        ge=1,
        le=12,
        validation_alias="ISSUEPILOT_MAX_CONTEXT_FILES",
    )
    max_file_bytes: int = Field(
        default=120_000,
        ge=5_000,
        le=500_000,
        validation_alias="ISSUEPILOT_MAX_FILE_BYTES",
    )
    max_agent_rounds: int = Field(
        default=6,
        ge=1,
        le=12,
        validation_alias="ISSUEPILOT_MAX_AGENT_ROUNDS",
    )
    max_agent_calls_per_round: int = Field(
        default=4,
        ge=1,
        le=8,
        validation_alias="ISSUEPILOT_MAX_AGENT_CALLS_PER_ROUND",
    )
    max_agent_search_files: int = Field(
        default=20,
        ge=1,
        le=50,
        validation_alias="ISSUEPILOT_MAX_AGENT_SEARCH_FILES",
    )
    max_tool_result_chars: int = Field(
        default=12_000,
        ge=1_000,
        le=40_000,
        validation_alias="ISSUEPILOT_MAX_TOOL_RESULT_CHARS",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
