import pytest

from issuepilot.errors import InvalidIssueUrl
from issuepilot.models import IssueReference


def test_parse_issue_url() -> None:
    ref = IssueReference.from_url("https://github.com/openai/openai-python/issues/123")
    assert ref.owner == "openai"
    assert ref.repo == "openai-python"
    assert ref.number == 123


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/openai/openai-python/pull/123",
        "https://example.com/owner/repo/issues/1",
        "not-a-url",
    ],
)
def test_reject_non_issue_urls(url: str) -> None:
    with pytest.raises(InvalidIssueUrl):
        IssueReference.from_url(url)
