"""
Load and fill the easy_issue_finder agent prompt template.

Prompt text lives in ``user.txt`` in this folder. Placeholders like
``<<<OWNER>>>`` and ``<<<ISSUES_JSON>>>`` are replaced at runtime.

Used by
-------
- ``scripts/run_easy_issue_finder.py`` (planned) — initial LLM message
- Manual testing — fill template and paste into Cursor chat
"""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent


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
    """
    Load ``user.txt`` and substitute runtime values for the easy_issue_finder agent.

    Parameters
    ----------
    owner, repo:
        GitHub repository for the prompt context.
    issues_json:
        JSON array string of issue summaries (from MCP or agent tools).
    target_easy_count:
        How many easy issues to ask for (v1 default: 1).
    max_issues_cap:
        Upper bound on batch size mentioned in the prompt (default 1000).
    """
    user_raw = (_PROMPTS_DIR / "user.txt").read_text(encoding="utf-8")

    mapping = {
        "OWNER": owner,
        "REPO": repo,
        "ISSUES_JSON": issues_json,
        "TARGET_EASY_COUNT": str(target_easy_count),
        "MAX_ISSUES_CAP": str(max_issues_cap),
    }

    return _fill_template(user_raw, mapping)


def load_easy_issue_picker_prompt(
    *,
    owner: str,
    repo: str,
    issues_json: str,
    target_easy_count: int = 1,
    max_issues_cap: int = 1000,
) -> str:
    """Deprecated alias — use ``load_easy_issue_finder_prompt()``."""
    return load_easy_issue_finder_prompt(
        owner=owner,
        repo=repo,
        issues_json=issues_json,
        target_easy_count=target_easy_count,
        max_issues_cap=max_issues_cap,
    )


def load_easy_issue_finder_prompts(
    *,
    owner: str,
    repo: str,
    issues_json: str,
    target_easy_count: int = 1,
    max_issues_cap: int = 1000,
) -> tuple[str, str]:
    """Returns ``("", user_prompt)`` for legacy callers expecting two messages."""
    prompt = load_easy_issue_finder_prompt(
        owner=owner,
        repo=repo,
        issues_json=issues_json,
        target_easy_count=target_easy_count,
        max_issues_cap=max_issues_cap,
    )
    return "", prompt


load_easy_issue_picker_prompts = load_easy_issue_finder_prompts
