"""
Turn raw GitHub issue JSON into a small summary dict for lists and LLM prompts.

The GitHub API returns large issue objects. This module keeps only the fields
the triage agent and MCP ``list_issues`` tool need, using consistent key names
(``assignees``, ``open_linked_pr``, etc.).
"""

from __future__ import annotations

from typing import Any


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
    Build a compact issue row for MCP list output and future agent tools.

    Parameters
    ----------
    issue:
        Raw dict from ``github_api.fetch_issues`` or ``fetch_issue``.
    open_linked_pr:
        ``True`` / ``False`` when linkage was checked (see ``has_open_linked_pull_request``).
        ``None`` when not checked — serialized as JSON ``null``.

    Returns
    -------
    dict
        Summary with ``number``, ``title``, ``labels``, ``assignees``, ``body_excerpt``, etc.
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
