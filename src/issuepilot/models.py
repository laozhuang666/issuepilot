import re
from typing import Literal

from pydantic import BaseModel, Field

from issuepilot.errors import InvalidIssueUrl

ISSUE_URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?github\.com/"
    r"(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/issues/(?P<number>\d+)/?$"
)


class IssueReference(BaseModel):
    owner: str
    repo: str
    number: int = Field(gt=0)

    @classmethod
    def from_url(cls, url: str) -> "IssueReference":
        match = ISSUE_URL_PATTERN.match(url.strip())
        if not match:
            raise InvalidIssueUrl(
                "Expected a public GitHub issue URL such as "
                "https://github.com/owner/repository/issues/123"
            )
        return cls(
            owner=match.group("owner"),
            repo=match.group("repo"),
            number=int(match.group("number")),
        )


class AnalysisRequest(BaseModel):
    issue_url: str


class IssueData(BaseModel):
    number: int
    title: str
    body: str
    state: str
    labels: list[str] = Field(default_factory=list)
    url: str


class RepositoryData(BaseModel):
    full_name: str
    description: str | None = None
    default_branch: str
    language: str | None = None
    stars: int = 0


class RepositoryFile(BaseModel):
    path: str
    size: int = 0
    sha: str | None = None


class FileEvidence(BaseModel):
    path: str
    score: float
    reasons: list[str]
    preview: str = ""


class PlanStep(BaseModel):
    order: int
    title: str
    details: str
    files: list[str] = Field(default_factory=list)


class ActionPlan(BaseModel):
    summary: str
    root_cause_hypothesis: str
    steps: list[PlanStep]
    verification: list[str]
    risks: list[str]
    open_questions: list[str]
    confidence: Literal["low", "medium", "high"]


class AgentTraceStep(BaseModel):
    round: int
    tool: Literal["search_paths", "read_file", "search_code"]
    arguments: dict[str, str | int]
    result_summary: str


class AnalysisResponse(BaseModel):
    issue: IssueData
    repository: RepositoryData
    relevant_files: list[FileEvidence]
    plan: ActionPlan
    planner: Literal["heuristic", "agent"]
    agent_trace: list[AgentTraceStep] = Field(default_factory=list)
    notice: str
