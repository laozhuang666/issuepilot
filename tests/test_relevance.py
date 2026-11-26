from issuepilot.models import IssueData, RepositoryFile
from issuepilot.relevance import rank_files


def test_explicit_file_reference_ranks_first() -> None:
    issue = IssueData(
        number=7,
        title="Parser crashes on empty input",
        body="The failure appears in src/parser.py when parsing an empty document.",
        state="open",
        labels=["bug"],
        url="https://github.com/acme/demo/issues/7",
    )
    files = [
        RepositoryFile(path="src/renderer.py", size=100),
        RepositoryFile(path="tests/test_parser.py", size=100),
        RepositoryFile(path="src/parser.py", size=100),
    ]

    ranked = rank_files(issue, files, limit=3)

    assert ranked[0][0].path == "src/parser.py"
    assert "explicitly named in the issue" in ranked[0][2]


def test_falls_back_to_source_files() -> None:
    issue = IssueData(
        number=1,
        title="Unexpected behavior",
        body="No useful identifiers here.",
        state="open",
        url="https://github.com/acme/demo/issues/1",
    )
    files = [
        RepositoryFile(path="docs/guide.md", size=100),
        RepositoryFile(path="src/main.py", size=100),
    ]

    ranked = rank_files(issue, files, limit=1)

    assert ranked[0][0].path == "src/main.py"
