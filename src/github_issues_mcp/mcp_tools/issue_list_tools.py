"""
MCP tools for listing and fetching GitHub issues.

Register these on a FastMCP app via ``register_issue_list_tools(mcp)``.
More tool groups (labels, PRs, etc.) can live in sibling modules under ``mcp_tools/``.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..github_api import fetch_issue, fetch_issues, has_open_linked_pull_request
from ..issue_summary import format_issue_summary


def register_issue_list_tools(mcp: FastMCP) -> None:
    """
    Attach ``list_issues`` and ``get_issue`` to the given MCP server instance.

    Called once from ``mcp_server.py`` at startup.
    """

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

        When enrich_linked_prs=True, each row includes open_linked_pr (extra API calls).
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
                open_linked: bool | None = None
                if enrich_linked_prs and isinstance(issue.get("number"), int):
                    open_linked = has_open_linked_pull_request(owner, repo, issue["number"])
                summaries.append(format_issue_summary(issue, open_linked_pr=open_linked))

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
