from functools import lru_cache
from typing import Literal

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
    llm_provider: Literal["openai", "deepseek", "openrouter", "ollama"] = "openai"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None

    # Backward-compatible aliases for existing v0.2 installations.
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

    @property
    def effective_api_key(self) -> str | None:
        key = (self.llm_api_key or "").strip()
        if key:
            return key
        if self.llm_provider == "openai":
            return (self.openai_api_key or "").strip() or None
        return None

    @property
    def effective_model(self) -> str:
        configured = (self.llm_model or "").strip()
        if configured:
            return configured
        defaults = {
            "openai": self.openai_model,
            "deepseek": "deepseek-flash",
            "openrouter": "openai/gpt-5-mini",
            "ollama": "qwen3:8b",
        }
        return defaults[self.llm_provider]

    @property
    def effective_base_url(self) -> str | None:
        configured = (self.llm_base_url or "").strip()
        if configured:
            return configured.rstrip("/")
        defaults = {
            "openai": None,
            "deepseek": "https://api.deepseek.com",
            "openrouter": "https://openrouter.ai/api/v1",
            "ollama": "http://127.0.0.1:11434/v1",
        }
        return defaults[self.llm_provider]

    @property
    def agent_enabled(self) -> bool:
        return self.llm_provider == "ollama" or self.effective_api_key is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()
