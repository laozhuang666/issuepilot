import re
from pathlib import PurePosixPath

from issuepilot.models import IssueData, RepositoryFile

STOP_WORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "before",
    "could",
    "does",
    "from",
    "have",
    "into",
    "issue",
    "should",
    "that",
    "their",
    "there",
    "these",
    "this",
    "when",
    "where",
    "with",
    "would",
}

SOURCE_SUFFIXES = {
    ".c",
    ".cpp",
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
}


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower())
    return {word for word in words if word not in STOP_WORDS}


def rank_files(
    issue: IssueData,
    files: list[RepositoryFile],
    limit: int,
) -> list[tuple[RepositoryFile, float, list[str]]]:
    issue_tokens = tokenize(f"{issue.title}\n{issue.body}\n{' '.join(issue.labels)}")
    explicitly_named = {
        match.replace("\\", "/")
        for match in re.findall(
            r"(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]+|[\w.-]+\.[A-Za-z0-9]+",
            f"{issue.title}\n{issue.body}",
        )
    }

    ranked: list[tuple[RepositoryFile, float, list[str]]] = []
    for file in files:
        path = file.path.lower()
        path_tokens = tokenize(path.replace("/", " ").replace(".", " "))
        overlap = sorted(issue_tokens & path_tokens)
        score = float(len(overlap) * 3)
        reasons: list[str] = []

        if overlap:
            reasons.append(f"path matches issue terms: {', '.join(overlap[:4])}")
        if any(path.endswith(name.lower()) for name in explicitly_named):
            score += 15
            reasons.append("explicitly named in the issue")

        suffix = PurePosixPath(path).suffix
        if suffix in SOURCE_SUFFIXES:
            score += 1.5
            reasons.append("source file")
        if "test" in path:
            score += 1
            reasons.append("test coverage candidate")
        if PurePosixPath(path).name.lower() in {"readme.md", "contributing.md"}:
            score += 0.25

        if score > 0:
            ranked.append((file, score, reasons))

    ranked.sort(key=lambda item: (-item[1], item[0].path))
    if ranked:
        return ranked[:limit]

    fallback = [file for file in files if PurePosixPath(file.path).suffix in SOURCE_SUFFIXES]
    fallback.sort(key=lambda file: (file.path.count("/"), file.path))
    return [(file, 0.5, ["fallback source-file candidate"]) for file in fallback[:limit]]
