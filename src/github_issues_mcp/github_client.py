"""GitHub API client for fetching repository issues."""

import os
import re
from typing import Any

import httpx

GITHUB_API_BASE = "https://api.github.com"

_PULL_FROM_API_URL_RE = re.compile(r"/repos/[^/]+/[^/]+/pulls/(\d+)\s*$")


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

    When include_pull_requests=False, uses the Search API (is:issue) to return
    only issues, avoiding the mixed issues+PRs from the repos endpoint.

    Args:
        owner: Repository owner (e.g., pytorch)
        repo: Repository name (e.g., pytorch)
        state: open, closed, or all
        labels: Comma-separated label names (e.g., bug,module: autograd)
        sort: created, updated, or comments
        direction: asc or desc
        per_page: Results per page (1-100)
        page: Page number
        include_pull_requests: If False, use Search API for issues only

    Returns:
        List of issue dicts from the GitHub API
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

    # Include PRs: use repos/issues endpoint
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
    """Fetch issues only via Search API (is:issue)."""
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
    """Raise ValueError on auth/not-found errors."""
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
    numbers: set[int] = set()
    for ev in events:
        if isinstance(ev.get("pull_request_url"), str):
            m = _PULL_FROM_API_URL_RE.search(ev["pull_request_url"])
            if m:
                numbers.add(int(m.group(1)))
        if ev.get("event") != "cross-referenced":
            continue
        src = ev.get("source") or {}
        inner = src.get("issue") if isinstance(src, dict) else None
        if not isinstance(inner, dict):
            continue
        # GitHub nests PR payloads under source.issue.{..., pull_request, state}
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
    Return the unified issue timeline (REST).

    Paginates until a short page or empty response.
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
        # Mirror fetch_issue-ish errors for callers
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
    """Fetch PR metadata (`state`, `merged_at`) for linkage checks."""
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
    Best-effort: True if timeline shows Linked PR refs and any fetched PR has state open.

    Scans Issue Timeline for cross-references to pull requests (`cross-referenced` with
    `source.issue.pull_request`) and timeline rows that carry `pull_request_url`
    (`reviewed`, etc.). For each distinct PR number, re-fetches `GET pulls/{id}` so
    `state`/`draft` reflects current repo truth.

    False if enrichment ran without finding any open linked PR (including timeline empty).
    Raises ValueError on auth / hard HTTP failures (same spirit as fetch_issue).

    Limits: linkage only discoverable via events GitHub emits on the timeline; very new
    or unusual links might be invisible until events exist.
    """
    timeline = iter_issue_timeline(owner, repo, issue_number)
    pulls = sorted(_gather_pull_numbers_from_timeline(timeline))

    for num in pulls:
        pr = fetch_pull_json(owner, repo, num)
        state = pr.get("state")
        if state == "open":
            return True

    return False


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
