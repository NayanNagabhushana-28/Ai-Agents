"""MCP server exposing GitHub issues as tools."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from .github_client import fetch_issue, fetch_issues

mcp = FastMCP("GitHub Issues", json_response=True)


def _format_issue_summary(issue: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields for list view."""
    body = issue.get("body") or ""
    body_excerpt = body[:500] + "..." if len(body) > 500 else body
    return {
        "number": issue["number"],
        "title": issue["title"],
        "state": issue["state"],
        "labels": [l["name"] for l in issue.get("labels", [])],
        "created_at": issue["created_at"],
        "updated_at": issue["updated_at"],
        "html_url": issue["html_url"],
        "user": issue.get("user", {}).get("login") if issue.get("user") else None,
        "body_excerpt": body_excerpt,
        "is_pull_request": "pull_request" in issue,
    }


@mcp.tool()
def list_issues(
    owner: str = "pytorch",
    repo: str = "pytorch",
    state: str = "open",
    labels: str | None = None,
    sort: str = "updated",
    per_page: int = 30,
    page: int = 1,
    include_pull_requests: bool = False,
) -> str:
    """
    List issues from a GitHub repository. Defaults to pytorch/pytorch.
    Use include_pull_requests=True to also return pull requests (GitHub returns both by default).
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
        summaries = [_format_issue_summary(i) for i in issues]
        return json.dumps(summaries, indent=2)
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
