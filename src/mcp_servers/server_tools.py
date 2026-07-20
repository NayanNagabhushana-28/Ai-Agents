"""
MCP tools for listing and fetching repository issues (Cursor and CLI agent).

Defines the FastMCP app plus ``list_issues`` and ``get_issue``.
HTTP fetch and summaries live in ``fetch_github_issues.py``.

Run via ``run_mcp_server.py`` (stdio).
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from fetch_github_issues import (
    fetch_issue,
    fetch_issues,
    format_issue_summary,
    has_open_linked_pull_request,
)

mcp = FastMCP("GitHub Issues", json_response=True)


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
    no_linked_prs: bool = False,
) -> str:
    """
    List issues from a GitHub repository. Defaults to pytorch/pytorch.

    When no_linked_prs=True, omit issues that have an open linked PR (extra API
    calls per row). The easy issue finder always enables this.
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
        for issue in issues:
            if no_linked_prs and isinstance(issue.get("number"), int):
                if has_open_linked_pull_request(owner, repo, issue["number"]):
                    continue
            summaries.append(format_issue_summary(issue))

        return json.dumps(summaries, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_issue(
    issue_number: int,
    owner: str = "pytorch",
    repo: str = "pytorch",
) -> str:
    """Get full GitHub JSON for a single issue or pull request by number."""
    try:
        issue = fetch_issue(owner=owner, repo=repo, issue_number=issue_number)
        return json.dumps(issue, indent=2, default=str)
    except ValueError as e:
        return json.dumps({"error": str(e)})
