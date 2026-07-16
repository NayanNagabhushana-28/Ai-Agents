"""Load and fill prompt templates for the easy-issue picker workflow."""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent


def _fill(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace(f"<<<{key}>>>", value)
    leftover = [line for line in out.splitlines() if "<<<" in line and ">>>" in line]
    if leftover:
        unresolved = ", ".join({s.strip() for s in leftover[:5]})
        raise ValueError(f"Unresolved placeholders remain in prompt (first hits): {unresolved}")
    return out


def load_easy_issue_picker_prompt(
    *,
    owner: str,
    repo: str,
    issues_json: str,
    target_easy_count: int = 5,
    max_issues_cap: int = 1000,
) -> str:
    """
    Load the triage prompt with placeholders substituted.

    Returns:
        Single user message suitable for Claude / LangChain Chat APIs.
    """
    user_raw = (_PROMPTS_DIR / "user.txt").read_text(encoding="utf-8")

    mapping = {
        "OWNER": owner,
        "REPO": repo,
        "ISSUES_JSON": issues_json,
        "TARGET_EASY_COUNT": str(target_easy_count),
        "MAX_ISSUES_CAP": str(max_issues_cap),
    }

    return _fill(user_raw, mapping)


def load_easy_issue_picker_prompts(
    *,
    owner: str,
    repo: str,
    issues_json: str,
    target_easy_count: int = 5,
    max_issues_cap: int = 1000,
) -> tuple[str, str]:
    """
    Deprecated: returns ("", user_prompt). Prefer load_easy_issue_picker_prompt().
    """
    prompt = load_easy_issue_picker_prompt(
        owner=owner,
        repo=repo,
        issues_json=issues_json,
        target_easy_count=target_easy_count,
        max_issues_cap=max_issues_cap,
    )
    return "", prompt
