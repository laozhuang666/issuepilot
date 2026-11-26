import json
from types import SimpleNamespace

from issuepilot.agent_tools import AgentToolbox
from issuepilot.config import Settings
from issuepilot.models import FileEvidence, IssueData, RepositoryData, RepositoryFile
from issuepilot.planner import Planner


class FakeResponses:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self.queue = responses
        self.requests: list[dict] = []

    async def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.queue.pop(0)


async def test_agent_calls_tool_then_returns_validated_plan() -> None:
    function_call = SimpleNamespace(
        type="function_call",
        name="read_file",
        arguments='{"path":"src/parser.py","start_line":1,"line_count":20}',
        call_id="call-1",
    )
    plan = {
        "summary": "Fix empty input parsing",
        "root_cause_hypothesis": "parse does not guard empty input",
        "steps": [
            {
                "order": 1,
                "title": "Guard input",
                "details": "Handle empty input before parsing.",
                "files": ["src/parser.py"],
            }
        ],
        "verification": ["Run parser tests."],
        "risks": ["May change empty-input compatibility."],
        "open_questions": [],
        "confidence": "high",
    }
    fake_responses = FakeResponses(
        [
            SimpleNamespace(id="response-1", output=[function_call], output_text=""),
            SimpleNamespace(id="response-2", output=[], output_text=json.dumps(plan)),
        ]
    )
    fake_client = SimpleNamespace(responses=fake_responses)

    async def reader(path: str) -> str:
        return "def parse(value):\n    return value[0]\n"

    toolbox = AgentToolbox(
        files=[RepositoryFile(path="src/parser.py")],
        reader=reader,
        max_result_chars=2_000,
    )
    planner = Planner(
        Settings(openai_api_key="test-key", max_agent_rounds=3),
        client=fake_client,
    )
    issue = IssueData(
        number=1,
        title="Parser fails on empty input",
        body="Calling parse with an empty string raises an error.",
        state="open",
        url="https://github.com/acme/demo/issues/1",
    )
    repository = RepositoryData(full_name="acme/demo", default_branch="main")
    evidence = [FileEvidence(path="src/parser.py", score=10, reasons=["issue term"])]

    result, planner_name, trace = await planner.create_plan(
        issue,
        repository,
        evidence,
        toolbox,
    )

    assert planner_name == "agent"
    assert result.confidence == "high"
    assert trace[0].tool == "read_file"
    assert fake_responses.requests[1]["previous_response_id"] == "response-1"
    assert fake_responses.requests[1]["input"][0]["type"] == "function_call_output"
