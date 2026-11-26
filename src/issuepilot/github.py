import base64
from urllib.parse import quote

import httpx

from issuepilot.config import Settings
from issuepilot.errors import GitHubRequestError, RepositoryTooLarge
from issuepilot.models import IssueData, IssueReference, RepositoryData, RepositoryFile

IGNORED_PATH_PARTS = {
    ".git",
    ".idea",
    ".next",
    ".venv",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "vendor",
}

IGNORED_SUFFIXES = {
    ".bmp",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".lock",
    ".min.css",
    ".min.js",
    ".pdf",
    ".png",
    ".svg",
    ".webp",
    ".zip",
}


class GitHubClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "IssuePilot/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(
            base_url=settings.github_api_url,
            headers=headers,
            timeout=20.0,
            follow_redirects=True,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def _get(self, path: str) -> dict | list:
        try:
            response = await self.client.get(path)
        except httpx.HTTPError as exc:
            raise GitHubRequestError(f"Could not reach GitHub: {exc}") from exc

        if response.status_code == 404:
            raise GitHubRequestError(
                "GitHub returned 404. Check that the repository and issue are public and exist."
            )
        if response.status_code == 403:
            remaining = response.headers.get("x-ratelimit-remaining")
            suffix = " Add GITHUB_TOKEN to increase the API limit." if remaining == "0" else ""
            raise GitHubRequestError(f"GitHub denied the request.{suffix}")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubRequestError(f"GitHub API returned status {response.status_code}.") from exc
        return response.json()

    async def fetch_issue(self, ref: IssueReference) -> IssueData:
        data = await self._get(f"/repos/{ref.owner}/{ref.repo}/issues/{ref.number}")
        if "pull_request" in data:
            raise GitHubRequestError("The URL points to a pull request, not an issue.")
        return IssueData(
            number=data["number"],
            title=data["title"],
            body=data.get("body") or "",
            state=data["state"],
            labels=[label["name"] for label in data.get("labels", [])],
            url=data["html_url"],
        )

    async def fetch_repository(self, ref: IssueReference) -> RepositoryData:
        data = await self._get(f"/repos/{ref.owner}/{ref.repo}")
        return RepositoryData(
            full_name=data["full_name"],
            description=data.get("description"),
            default_branch=data["default_branch"],
            language=data.get("language"),
            stars=data.get("stargazers_count", 0),
        )

    async def fetch_tree(self, ref: IssueReference, branch: str) -> list[RepositoryFile]:
        safe_branch = quote(branch, safe="")
        data = await self._get(f"/repos/{ref.owner}/{ref.repo}/git/trees/{safe_branch}?recursive=1")
        if data.get("truncated"):
            raise RepositoryTooLarge(
                "GitHub truncated this repository tree. Try a smaller repository for the MVP."
            )

        files: list[RepositoryFile] = []
        for item in data.get("tree", []):
            if item.get("type") != "blob":
                continue
            path = item["path"]
            parts = set(path.lower().split("/"))
            lower_path = path.lower()
            if parts & IGNORED_PATH_PARTS:
                continue
            if any(lower_path.endswith(suffix) for suffix in IGNORED_SUFFIXES):
                continue
            size = item.get("size", 0)
            if size > self.settings.max_file_bytes:
                continue
            files.append(RepositoryFile(path=path, size=size, sha=item.get("sha")))

        if len(files) > self.settings.max_repository_files:
            files = files[: self.settings.max_repository_files]
        return files

    async def fetch_file(self, ref: IssueReference, path: str, branch: str) -> str:
        safe_path = quote(path, safe="/")
        safe_branch = quote(branch, safe="")
        data = await self._get(
            f"/repos/{ref.owner}/{ref.repo}/contents/{safe_path}?ref={safe_branch}"
        )
        if not isinstance(data, dict) or data.get("encoding") != "base64":
            return ""
        try:
            raw = base64.b64decode(data.get("content", ""), validate=False)
            return raw.decode("utf-8", errors="replace")
        except (ValueError, TypeError):
            return ""
