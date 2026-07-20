"""
Purpose: load the easy_issue_finder prompt and return opening messages for the agent.

Reads ``prompts/easy_issue_finder/user.txt``, fills placeholders, and returns
provider-neutral message dicts (``role`` / ``content``) for ``client.chat()``.

Who calls this
--------------
- ``run_easy_issue_finder.py`` — ``build_start_messages()``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from llm.build_chat_messages import user_message

_USER_TXT = (
    Path(__file__).resolve().parents[2] / "prompts" / "easy_issue_finder" / "user.txt"
)


def _fill_template(template: str, mapping: dict[str, str]) -> str:
    """Replace ``<<<KEY>>>`` placeholders; raise if any remain."""
    out = template
    for key, value in mapping.items():
        out = out.replace(f"<<<{key}>>>", value)
    leftover = [line for line in out.splitlines() if "<<<" in line and ">>>" in line]
    if leftover:
        unresolved = ", ".join({line.strip() for line in leftover[:5]})
        raise ValueError(f"Unresolved placeholders remain in prompt (first hits): {unresolved}")
    return out


def load_easy_issue_finder_prompt(
    *,
    owner: str,
    repo: str,
    issues_json: str,
    target_easy_count: int = 1,
    max_issues_cap: int = 1000,
) -> str:
    """Load ``user.txt`` and substitute runtime values."""
    user_raw = _USER_TXT.read_text(encoding="utf-8")
    mapping = {
        "OWNER": owner,
        "REPO": repo,
        "ISSUES_JSON": issues_json,
        "TARGET_EASY_COUNT": str(target_easy_count),
        "MAX_ISSUES_CAP": str(max_issues_cap),
    }
    return _fill_template(user_raw, mapping)


def build_initial_messages(
    *,
    owner: str,
    repo: str,
    target_easy_count: int = 1,
    max_issues_cap: int = 1000,
) -> list[dict[str, Any]]:
    """
    Return the first turn of conversation for an easy_issue_finder run.

    Agentic v1 starts with an empty issues list; the model fetches evidence via
    tools in Phase 3.
    """
    prompt = load_easy_issue_finder_prompt(
        owner=owner,
        repo=repo,
        issues_json="[]",
        target_easy_count=target_easy_count,
        max_issues_cap=max_issues_cap,
    )
    return [user_message(prompt)]
