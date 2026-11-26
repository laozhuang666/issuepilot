class IssuePilotError(Exception):
    """Base exception for errors safe to show to an API client."""


class InvalidIssueUrl(IssuePilotError):
    pass


class GitHubRequestError(IssuePilotError):
    pass


class RepositoryTooLarge(IssuePilotError):
    pass
