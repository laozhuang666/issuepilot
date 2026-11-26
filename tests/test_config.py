from issuepilot.config import Settings


def test_issuepilot_prefixed_limits_are_loaded(monkeypatch) -> None:
    monkeypatch.setenv("ISSUEPILOT_MAX_AGENT_ROUNDS", "3")
    monkeypatch.setenv("ISSUEPILOT_MAX_AGENT_SEARCH_FILES", "7")

    settings = Settings()

    assert settings.max_agent_rounds == 3
    assert settings.max_agent_search_files == 7
