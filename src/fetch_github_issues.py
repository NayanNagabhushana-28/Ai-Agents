"""
Fetch GitHub repository issues and build compact summaries for agents and MCP.

Calls ``api.github.com`` via ``httpx``. No MCP or LLM imports here.

Authentication
--------------
Set ``GITHUB_TOKEN`` in the environment for higher rate limits (5000 req/hr vs 60).
Without a token, public repos may still work but will hit limits quickly.

Used by
-------
- ``mcp_servers/server_tools.py`` — MCP tools for Cursor and CLI agent
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

# Base URL for all GitHub REST v3 requests in this project.
GITHUB_API_BASE = "https://api.github.com"

# Extracts pull request number from URLs like .../repos/o/r/pulls/123
_PULL_FROM_API_URL_RE = re.compile(r"/repos/[^/]+/[^/]+/pulls/(\d+)\s*$")


def _get_headers() -> dict[str, str]:
    """
    Build HTTP headers for GitHub API requests.

    Adds ``Authorization: Bearer …`` when ``GITHUB_TOKEN`` is set in the environment.
    """
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
    Fetch a page of issues (and optionally PRs) from a repository.

    When ``include_pull_requests=False``, uses the Search API with ``is:issue`` so
    results never mix in pull requests (the ``/repos/.../issues`` endpoint returns both).

    Parameters
    ----------
    owner, repo:
        GitHub repository coordinates (e.g. ``pytorch``, ``pytorch``).
    state:
        ``open``, ``closed``, or ``all``.
    labels:
        Comma-separated label names to filter (optional).
    sort, direction:
        Sort field and ``asc`` / ``desc`` order.
    per_page, page:
        Pagination (GitHub max 100 per page).
    include_pull_requests:
        If ``False``, search for issues only.

    Returns
    -------
    list[dict]
        Raw issue objects as returned by GitHub (large JSON blobs).
    """
    target_count = min(max(per_page, 1), 100)

    if not include_pull_requests:
        return _fetch_issues_via_search(
            owner=owner,
            repo=repo,
            state=state,
            labels=labels,
            sort=sort,
            direction=direction,
            per_page=target_count,
            page=page,
        )

    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
    params: dict[str, Any] = {
        "state": state,
        "sort": sort,
        "direction": direction,
        "per_page": target_count,
        "page": max(page, 1),
    }
    if labels:
        params["labels"] = labels

    response = httpx.get(url, headers=_get_headers(), params=params, timeout=30.0)
    _check_response(response, owner, repo)
    items = response.json()
    return items[:target_count]


def _fetch_issues_via_search(
    owner: str,
    repo: str,
    state: str,
    labels: str | None,
    sort: str,
    direction: str,
    per_page: int,
    page: int,
) -> list[dict[str, Any]]:
    """
    Internal: list issues only via ``GET /search/issues`` (``is:issue`` qualifier).

    Avoids pull requests that appear on the repository issues endpoint.
    """
    url = f"{GITHUB_API_BASE}/search/issues"
    q_parts = [f"repo:{owner}/{repo}", "is:issue", f"state:{state}"]
    if labels:
        for label in labels.split(","):
            q_parts.append(f"label:{label.strip()}")
    params: dict[str, Any] = {
        "q": " ".join(q_parts),
        "sort": sort,
        "order": direction,
        "per_page": per_page,
        "page": max(page, 1),
    }

    response = httpx.get(url, headers=_get_headers(), params=params, timeout=30.0)
    _check_response(response, owner, repo)
    data = response.json()
    items = data.get("items", [])
    return items[:per_page]


def _check_response(response: httpx.Response, owner: str, repo: str) -> None:
    """
    Raise ``ValueError`` with a helpful message for common GitHub API failures.

    Other HTTP errors propagate via ``raise_for_status()``.
    """
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


def _gather_pull_numbers_from_timeline(events: list[dict[str, Any]]) -> set[int]:
    """
    Collect pull request numbers mentioned on an issue timeline.

    GitHub emits different event shapes; we look for:
    - ``pull_request_url`` on review-related events
    - ``cross-referenced`` events where ``source.issue`` contains ``pull_request``
    """
    numbers: set[int] = set()
    for ev in events:
        if isinstance(ev.get("pull_request_url"), str):
            match = _PULL_FROM_API_URL_RE.search(ev["pull_request_url"])
            if match:
                numbers.add(int(match.group(1)))
        if ev.get("event") != "cross-referenced":
            continue
        src = ev.get("source") or {}
        inner = src.get("issue") if isinstance(src, dict) else None
        if not isinstance(inner, dict):
            continue
        if "pull_request" not in inner:
            continue
        num = inner.get("number")
        if isinstance(num, int):
            numbers.add(num)
    return numbers


def iter_issue_timeline(
    owner: str,
    repo: str,
    issue_number: int,
    *,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    """
    Fetch the full unified timeline for one issue (paginated).

    The timeline includes comments, cross-references, labels, reviews, etc.
    Used to discover pull requests linked to an issue.
    """
    per_page = min(max(per_page, 1), 100)
    page = 1
    aggregated: list[dict[str, Any]] = []

    while True:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}/timeline"
        response = httpx.get(
            url,
            headers=_get_headers(),
            params={"per_page": per_page, "page": page},
            timeout=30.0,
        )
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
            raise ValueError(
                f"Issue #{issue_number} not found in {owner}/{repo} (timeline fetch)"
            )
        response.raise_for_status()
        batch = response.json()
        if not isinstance(batch, list):
            raise ValueError("Unexpected timeline response shape from GitHub")
        aggregated.extend(batch)
        if len(batch) < per_page:
            break
        page += 1

    return aggregated


def fetch_pull_json(owner: str, repo: str, pull_number: int) -> dict[str, Any]:
    """
    Fetch metadata for one pull request (``state``, ``draft``, etc.).

    We re-fetch PRs found on the timeline so ``state`` reflects current reality,
    not a stale snapshot embedded in a timeline event.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pull_number}"

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
        raise ValueError(
            f"Pull request #{pull_number} not found in {owner}/{repo}"
        )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Unexpected pull request response shape from GitHub")
    return payload


def has_open_linked_pull_request(owner: str, repo: str, issue_number: int) -> bool:
    """
    Return ``True`` if the issue has at least one *open* linked pull request.

    Workflow
    --------
    1. Load issue timeline events
    2. Extract linked PR numbers
    3. For each PR, call ``fetch_pull_json`` and check ``state == "open"``

    Returns ``False`` if no linked PRs or all linked PRs are closed/merged.

    Limitation: only PRs visible on GitHub's timeline are detected.
    """
    timeline = iter_issue_timeline(owner, repo, issue_number)
    pulls = sorted(_gather_pull_numbers_from_timeline(timeline))

    for num in pulls:
        pr = fetch_pull_json(owner, repo, num)
        if pr.get("state") == "open":
            return True

    return False


def fetch_issue(owner: str, repo: str, issue_number: int) -> dict[str, Any]:
    """
    Fetch one issue or pull request by number (full GitHub JSON).

    Use ``format_issue_summary`` if you need a compact list row instead.
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


def assignee_logins(issue: dict[str, Any]) -> list[str]:
    """
    Extract assignee login names from a GitHub REST issue object.

    Returns a sorted, de-duplicated list. An empty list means nobody is assigned.
    """
    assignees_payload = issue.get("assignees")
    if not assignees_payload:
        return []
    out: list[str] = []
    for item in assignees_payload:
        if isinstance(item, dict) and item.get("login"):
            out.append(str(item["login"]))
        elif isinstance(item, str) and item:
            out.append(item)
    return sorted(set(out))


def format_issue_summary(
    issue: dict[str, Any],
    *,
    open_linked_pr: bool | None = None,
) -> dict[str, Any]:
    """
    Build a compact issue row for MCP list output and agent tools.

    Parameters
    ----------
    issue:
        Raw dict from ``fetch_issues`` or ``fetch_issue``.
    open_linked_pr:
        ``True`` / ``False`` when linkage was checked (see ``has_open_linked_pull_request``).
        ``None`` when not checked — serialized as JSON ``null``.
    """
    body = issue.get("body") or ""
    body_excerpt = body[:500] + "..." if len(body) > 500 else body
    return {
        "number": issue["number"],
        "title": issue["title"],
        "state": issue["state"],
        "labels": [label["name"] for label in issue.get("labels", [])],
        "assignees": assignee_logins(issue),
        "created_at": issue["created_at"],
        "updated_at": issue["updated_at"],
        "html_url": issue["html_url"],
        "user": issue.get("user", {}).get("login") if issue.get("user") else None,
        "body_excerpt": body_excerpt,
        "is_pull_request": "pull_request" in issue,
        "open_linked_pr": open_linked_pr,
    }
