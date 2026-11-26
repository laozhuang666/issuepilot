from issuepilot.agent_tools import AgentToolbox
from issuepilot.models import RepositoryFile


async def test_toolbox_searches_and_reads_only_known_files() -> None:
    contents = {
        "src/parser.py": "def parse(value):\n    return value\n",
        "tests/test_parser.py": "def test_parse():\n    assert parse('ok')\n",
    }

    async def reader(path: str) -> str:
        return contents[path]

    toolbox = AgentToolbox(
        files=[RepositoryFile(path=path) for path in contents],
        reader=reader,
        max_result_chars=2_000,
    )

    paths = await toolbox.execute(1, "search_paths", '{"query":"parser","limit":10}')
    code = await toolbox.execute(
        2,
        "search_code",
        '{"query":"def parse","path_prefix":"src/","limit":5}',
    )
    denied = await toolbox.execute(
        3,
        "read_file",
        '{"path":"../secrets.txt","start_line":1,"line_count":10}',
    )

    assert "src/parser.py" in paths
    assert "src/parser.py:1" in code
    assert "not in the filtered repository tree" in denied
    assert len(toolbox.trace) == 3


async def test_toolbox_bounds_read_ranges() -> None:
    async def reader(path: str) -> str:
        return "one\ntwo\nthree\n"

    toolbox = AgentToolbox(
        files=[RepositoryFile(path="src/data.txt")],
        reader=reader,
        max_result_chars=2_000,
    )

    result = await toolbox.execute(
        1,
        "read_file",
        '{"path":"src/data.txt","start_line":2,"line_count":2}',
    )

    assert result == "2: two\n3: three"
