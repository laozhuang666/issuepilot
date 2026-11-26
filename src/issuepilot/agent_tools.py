import json
from collections.abc import Awaitable, Callable

from issuepilot.models import AgentTraceStep, RepositoryFile

FileReader = Callable[[str], Awaitable[str]]


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "search_paths",
        "description": "Find repository file paths containing a case-insensitive term.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Filename or path term."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["query", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read a bounded text file from the repository tree.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Exact repository-relative path."},
                "start_line": {"type": "integer", "minimum": 1},
                "line_count": {"type": "integer", "minimum": 1, "maximum": 200},
            },
            "required": ["path", "start_line", "line_count"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "search_code",
        "description": (
            "Search a literal symbol or phrase inside repository text files "
            "and return matching lines."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Literal symbol or code phrase."},
                "path_prefix": {
                    "type": "string",
                    "description": "Optional path prefix, or an empty string for all files.",
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 30},
            },
            "required": ["query", "path_prefix", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

CHAT_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            key: value for key, value in definition.items() if key not in {"type", "strict"}
        },
    }
    for definition in TOOL_DEFINITIONS
]


class AgentToolbox:
    def __init__(
        self,
        files: list[RepositoryFile],
        reader: FileReader,
        max_result_chars: int,
        max_search_files: int = 20,
    ) -> None:
        self.files = files
        self.reader = reader
        self.max_result_chars = max_result_chars
        self.max_search_files = max_search_files
        self.allowed_paths = {file.path for file in files}
        self._cache: dict[str, str] = {}
        self.trace: list[AgentTraceStep] = []

    async def execute(self, round_number: int, name: str, arguments_json: str) -> str:
        try:
            arguments = json.loads(arguments_json)
            if not isinstance(arguments, dict):
                raise ValueError("Tool arguments must be an object.")
            if name == "search_paths":
                result = self._search_paths(arguments)
            elif name == "read_file":
                result = await self._read_file(arguments)
            elif name == "search_code":
                result = await self._search_code(arguments)
            else:
                result = f"Error: unknown tool '{name}'."
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            arguments = {}
            result = f"Error: invalid tool arguments: {exc}"

        result = result[: self.max_result_chars]
        summary = result.replace("\n", " ")[:240]
        self.trace.append(
            AgentTraceStep(
                round=round_number,
                tool=name,
                arguments={
                    key: value for key, value in arguments.items() if isinstance(value, str | int)
                },
                result_summary=summary,
            )
        )
        return result

    def _search_paths(self, arguments: dict) -> str:
        query = self._bounded_query(arguments.get("query"))
        limit = self._bounded_int(arguments.get("limit"), 1, 20)
        matches = [file.path for file in self.files if query.lower() in file.path.lower()]
        return "\n".join(matches[:limit]) or "No matching paths found."

    async def _read_file(self, arguments: dict) -> str:
        path = self._allowed_path(arguments.get("path"))
        start_line = self._bounded_int(arguments.get("start_line"), 1, 1_000_000)
        line_count = self._bounded_int(arguments.get("line_count"), 1, 200)
        content = await self._content(path)
        lines = content.splitlines()
        selected = lines[start_line - 1 : start_line - 1 + line_count]
        if not selected:
            return f"{path}: no content in the requested line range."
        return "\n".join(
            f"{line_number}: {line}" for line_number, line in enumerate(selected, start=start_line)
        )

    async def _search_code(self, arguments: dict) -> str:
        query = self._bounded_query(arguments.get("query"))
        prefix = arguments.get("path_prefix", "")
        if not isinstance(prefix, str) or ".." in prefix or prefix.startswith(("/", "\\")):
            raise ValueError("path_prefix must be repository-relative.")
        limit = self._bounded_int(arguments.get("limit"), 1, 30)
        candidates = [file.path for file in self.files if file.path.startswith(prefix)]
        candidates = candidates[: self.max_search_files]
        matches: list[str] = []
        for path in candidates:
            content = await self._content(path)
            for line_number, line in enumerate(content.splitlines(), start=1):
                if query.lower() in line.lower():
                    matches.append(f"{path}:{line_number}: {line.strip()}")
                    if len(matches) >= limit:
                        return "\n".join(matches)
        return "\n".join(matches) or "No code matches found."

    async def _content(self, path: str) -> str:
        if path not in self._cache:
            self._cache[path] = await self.reader(path)
        return self._cache[path]

    def _allowed_path(self, value: object) -> str:
        if not isinstance(value, str) or value not in self.allowed_paths:
            raise ValueError("path is not in the filtered repository tree.")
        return value

    @staticmethod
    def _bounded_query(value: object) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > 100:
            raise ValueError("query must contain 1 to 100 characters.")
        return value.strip()

    @staticmethod
    def _bounded_int(value: object, minimum: int, maximum: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            raise ValueError(f"integer must be between {minimum} and {maximum}.")
        return value
