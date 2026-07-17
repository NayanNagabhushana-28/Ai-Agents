"""
triage_agent — broader issue triage (planned, Phase 2+).

Will handle workflows beyond easy-issue discovery (e.g. prioritization,
label suggestions, maintainer routing). Shares ``github_api`` and ``llm``
with easy_issue_finder but uses its own prompts and runner.

Prompts: ``prompts/triage_agent/`` (reserved)
CLI: ``scripts/run_triage_agent.py`` (planned)
"""
