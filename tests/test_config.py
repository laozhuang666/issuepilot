from issuepilot.config import Settings


def test_issuepilot_prefixed_limits_are_loaded(monkeypatch) -> None:
    monkeypatch.setenv("ISSUEPILOT_MAX_AGENT_ROUNDS", "3")
    monkeypatch.setenv("ISSUEPILOT_MAX_AGENT_SEARCH_FILES", "7")

    settings = Settings()

    assert settings.max_agent_rounds == 3
    assert settings.max_agent_search_files == 7


def test_deepseek_provider_defaults() -> None:
    settings = Settings(llm_provider="deepseek", llm_api_key="secret")

    assert settings.agent_enabled is True
    assert settings.effective_base_url == "https://api.deepseek.com"
    assert settings.effective_model == "deepseek-flash"


def test_legacy_openai_settings_remain_supported() -> None:
    settings = Settings(openai_api_key="legacy-key", openai_model="gpt-test")

    assert settings.agent_enabled is True
    assert settings.effective_api_key == "legacy-key"
    assert settings.effective_model == "gpt-test"


def test_ollama_does_not_require_an_api_key() -> None:
    settings = Settings(llm_provider="ollama")

    assert settings.agent_enabled is True
    assert settings.effective_base_url == "http://127.0.0.1:11434/v1"
