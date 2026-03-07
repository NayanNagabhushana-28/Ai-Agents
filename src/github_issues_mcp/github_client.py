"""GitHub API client for fetching repository issues."""

import os
from typing import Any

import httpx

GITHUB_API_BASE = "https://api.github.com"


def _get_headers() -> dict[str, str]:
    """Build request headers with optional authentication."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: str | None = None,
    sort: str = "updated",
    direction: str = "desc",
    per_page: int = 30,
    page: int = 1,
    include_pull_requests: bool = True,
) -> list[dict[str, Any]]:
    """
    Fetch issues from a GitHub repository.

    Args:
        owner: Repository owner (e.g., pytorch)
        repo: Repository name (e.g., pytorch)
        state: open, closed, or all
        labels: Comma-separated label names (e.g., bug,module: autograd)
        sort: created, updated, or comments
        direction: asc or desc
        per_page: Results per page (1-100)
        page: Page number
        include_pull_requests: If False, filter out pull requests

    Returns:
        List of issue dicts from the GitHub API
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
    params: dict[str, Any] = {
        "state": state,
        "sort": sort,
        "direction": direction,
        "per_page": min(max(per_page, 1), 100),
        "page": max(page, 1),
    }
    if labels:
        params["labels"] = labels

    response = httpx.get(url, headers=_get_headers(), params=params, timeout=30.0)

    if response.status_code == 401:
        raise ValueError(
            "GitHub API returned 401: Invalid or missing GITHUB_TOKEN. "
            "Create a token at https://github.com/settings/tokens"
        )
    if response.status_code == 403:
        raise ValueError(
            "GitHub API returned 403: Rate limit exceeded or token lacks permissions. "
            "Authenticated requests get 5000 req/hr."
        )
    if response.status_code == 404:
        raise ValueError(f"Repository not found: {owner}/{repo}")
    response.raise_for_status()

    issues = response.json()

    if not include_pull_requests:
        issues = [i for i in issues if "pull_request" not in i]

    return issues


def fetch_issue(owner: str, repo: str, issue_number: int) -> dict[str, Any]:
    """
    Fetch a single issue by number.

    Args:
        owner: Repository owner
        repo: Repository name
        issue_number: Issue or PR number

    Returns:
        Issue dict from the GitHub API
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}"

    response = httpx.get(url, headers=_get_headers(), timeout=30.0)

    if response.status_code == 401:
        raise ValueError(
            "GitHub API returned 401: Invalid or missing GITHUB_TOKEN. "
            "Create a token at https://github.com/settings/tokens"
        )
    if response.status_code == 403:
        raise ValueError(
            "GitHub API returned 403: Rate limit exceeded or token lacks permissions."
        )
    if response.status_code == 404:
        raise ValueError(f"Issue #{issue_number} not found in {owner}/{repo}")
    response.raise_for_status()

    return response.json()
