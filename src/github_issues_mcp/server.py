"""MCP server exposing GitHub issues as tools."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from .github_client import fetch_issue, fetch_issues, has_open_linked_pull_request

mcp = FastMCP("GitHub Issues", json_response=True)


def _assignee_logins(issue: dict[str, Any]) -> list[str]:
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


def _format_issue_summary(
    issue: dict[str, Any],
    *,
    open_linked_pr: bool | None = None,
) -> dict[str, Any]:
    """Extract key fields for list view."""
    body = issue.get("body") or ""
    body_excerpt = body[:500] + "..." if len(body) > 500 else body
    return {
        "number": issue["number"],
        "title": issue["title"],
        "state": issue["state"],
        "labels": [l["name"] for l in issue.get("labels", [])],
        "assignees": _assignee_logins(issue),
        "created_at": issue["created_at"],
        "updated_at": issue["updated_at"],
        "html_url": issue["html_url"],
        "user": issue.get("user", {}).get("login") if issue.get("user") else None,
        "body_excerpt": body_excerpt,
        "is_pull_request": "pull_request" in issue,
        # bool when enriched; null/MCP JSON None when timeline scan not requested
        "open_linked_pr": open_linked_pr,
    }


@mcp.tool()
def list_issues(
    owner: str = "pytorch",
    repo: str = "pytorch",
    state: str = "open",
    labels: str | None = None,
    sort: str = "created",
    per_page: int = 10,
    page: int = 1,
    include_pull_requests: bool = False,
    enrich_linked_prs: bool = False,
) -> str:
    """
    List issues from a GitHub repository. Defaults to pytorch/pytorch.
    If PR is false, it returns issues without PRs.
    Use include_pull_requests=True to also return pull requests (GitHub returns both by default).
    When enrich_linked_prs=True, each row includes open_linked_pr (bool) derived from Issue
    timeline + PR state (extra API calls per issue; authenticated token strongly recommended).
    """
    try:
        issues = fetch_issues(
            owner=owner,
            repo=repo,
            state=state,
            labels=labels,
            sort=sort,
            per_page=per_page,
            page=page,
            include_pull_requests=include_pull_requests,
        )
        summaries: list[dict[str, Any]] = []
        for i in issues:
            pr_flag: bool | None = None
            if enrich_linked_prs and isinstance(i.get("number"), int):
                pr_flag = has_open_linked_pull_request(owner, repo, i["number"])
            summaries.append(_format_issue_summary(i, open_linked_pr=pr_flag))

        return json.dumps(summaries, indent=2)
        # return summaries
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_issue(
    issue_number: int,
    owner: str = "pytorch",
    repo: str = "pytorch",
) -> str:
    """
    Get full details of a single issue or pull request by number.
    Defaults to pytorch/pytorch repository.
    """
    try:
        issue = fetch_issue(owner=owner, repo=repo, issue_number=issue_number)
        # Return full issue; GitHub response is already JSON-serializable
        return json.dumps(issue, indent=2, default=str)
    except ValueError as e:
        return json.dumps({"error": str(e)})

# Expose a tool to pull changes in a pull request - out of scope for now