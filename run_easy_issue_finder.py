#!/usr/bin/env python3
"""
Entry point for the easy_issue_finder agent.

Purpose
-------
Run the full pipeline to find one easy GitHub issue for newcomers::

    python run_easy_issue_finder.py --owner pytorch --repo pytorch \\
        --model claude-sonnet-4@20250514

Steps (in order, see ``main()``)
--------------------------------
1. ``create_chat_client``     — load MODEL + Vertex project, connect via ADC
2. ``build_start_messages``   — load triage prompt (issues empty at first)
3. ``find_easy_issues``       — agent loop: Claude fetches issues via tools
4. ``validate_and_print_result`` — check JSON and print

Testing without GCP credentials::

    python run_easy_issue_finder.py --dry-run

Auth (live runs): ``gcloud auth application-default login`` + ``ANTHROPIC_VERTEX_PROJECT_ID`` in ``.env``.
Does not import ``anthropic`` — Claude access goes through ``src/llm/``.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any


def setup_project_paths() -> Path:
    """
    Add ``src/`` and repo root to ``sys.path`` so ``llm`` and ``prompts`` import.

    Returns the project root directory.
    """
    project_root = Path(__file__).resolve().parent
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root


def load_env_file(project_root: Path) -> None:
    """Load ``.env`` from the project root if ``python-dotenv`` is installed."""
    try:
        from dotenv import load_dotenv

        load_dotenv(project_root / ".env")
    except ImportError:
        pass


def parse_args() -> argparse.Namespace:
    """Parse CLI flags for the easy issue finder pipeline."""
    parser = argparse.ArgumentParser(
        description="Find easy open GitHub issues suitable for newcomers",
    )
    parser.add_argument(
        "--owner",
        default="pytorch",
        help="GitHub repository owner (default: pytorch)",
    )
    parser.add_argument(
        "--repo",
        default="pytorch",
        help="GitHub repository name (default: pytorch)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Vertex Claude model id; overrides MODEL in .env (default: claude-sonnet-4@20250514)",
    )
    parser.add_argument(
        "--target-easy",
        type=int,
        default=1,
        help="Number of easy issues to find (default: 1)",
    )
    parser.add_argument(
        "--max-tool-rounds",
        type=int,
        default=10,
        help="Max LLM tool-call iterations before failing (default: 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print owner, repo, and model then exit (no API calls)",
    )
    return parser.parse_args()


def _phase(title: str) -> None:
    print(f"\n{title}:")


def _print_config(args: argparse.Namespace, settings: Any | None = None) -> None:
    from llm.load_model_config import DEFAULT_MODEL, DEFAULT_VERTEX_REGION

    if settings is not None:
        model = settings.model
        project = settings.vertex_project_id
        region = settings.vertex_region
        max_tokens = settings.max_tokens
    else:
        model = args.model or os.environ.get("MODEL", "").strip() or DEFAULT_MODEL
        project = os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID", "").strip() or "(not set)"
        region = os.environ.get("CLOUD_ML_REGION", "").strip() or DEFAULT_VERTEX_REGION
        max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "4096"))

    _phase("Load Config")
    print(f"  owner={args.owner}")
    print(f"  repo={args.repo}")
    print(f"  target_easy={args.target_easy}")
    print(f"  max_tool_rounds={args.max_tool_rounds}")
    print(f"  model={model}")
    print(f"  vertex_project={project}")
    print(f"  vertex_region={region}")
    print(f"  max_tokens={max_tokens}")
    print("  auth=application-default-credentials")


def print_cli_config(args: argparse.Namespace) -> None:
    """Print phased config and prompt for ``--dry-run`` (no API calls)."""
    from easy_issue_finder.build_prompt import build_initial_messages

    _print_config(args)
    print("Config loaded successfully (dry-run — no API calls)")

    messages = build_initial_messages(
        owner=args.owner,
        repo=args.repo,
        target_easy_count=args.target_easy,
    )
    _phase("Build initial message")
    print(messages[0]["content"])
    print("\nPrompt ready for the next phase (dry-run)")

    _phase("Find easy issues")
    print("Skipped — dry-run")

    _phase("Validate result")
    print("Skipped — dry-run")


def create_chat_client(args: argparse.Namespace) -> Any:
    """
    Load LLM settings from env and return a ready chat client.

    Uses ``--model`` when passed; otherwise reads ``MODEL`` from the environment.
    Requires ``ANTHROPIC_VERTEX_PROJECT_ID`` and ADC (``gcloud auth
    application-default login``) unless you only use ``--dry-run``.
    """
    from llm.create_llm_connection import establish_connection
    from llm.load_model_config import load_model_settings

    settings = load_model_settings(model=args.model)
    _print_config(args, settings)
    client = establish_connection(settings)
    print("Config loaded successfully")
    return client


def build_start_messages(args: argparse.Namespace) -> list[dict[str, Any]]:
    """
    Build the first message(s) for the agent loop (user prompt, empty issues).

    Returns provider-neutral message dicts for ``client.chat(messages)``.
    """
    from easy_issue_finder.build_prompt import build_initial_messages

    messages = build_initial_messages(
        owner=args.owner,
        repo=args.repo,
        target_easy_count=args.target_easy,
    )
    _phase("Build initial message")
    print(messages[0]["content"])
    print("\nPrompt ready for the next phase")
    return messages


def find_easy_issues(
    client: Any,
    messages: list[dict[str, Any]],
    args: argparse.Namespace,
    *,
    project_root: Path,
) -> str:
    """Run the agent loop until the model returns final JSON text or a cap is hit."""
    from easy_issue_finder.agent_loop import FinderConfig, run_finder

    _phase("Find easy issues")
    config = FinderConfig(
        owner=args.owner,
        repo=args.repo,
        target_easy_count=args.target_easy,
        max_tool_rounds=args.max_tool_rounds,
    )
    raw_result = run_finder(client, config, messages, project_root=project_root)
    print(raw_result)
    print("\nAgent loop complete — ready for validation")
    return raw_result


def validate_and_print_result(raw_result: Any) -> None:
    """
    Parse the model's JSON answer, validate schema, and print to stdout.

    Not implemented yet — Phase 4 will use ``result_validator.py``.
    """
    _phase("Validate result")
    print("Not implemented yet — Phase 4")
    sys.exit(0)


def main() -> None:
    project_root = setup_project_paths()
    load_env_file(project_root)
    args = parse_args()

    if args.dry_run:
        print_cli_config(args)
        return

    # Phase 1 SETUP: load Vertex config (MODEL, project, region) and build the
    # AnthropicVertex client. Must run first — later steps need client.chat().
    client = create_chat_client(args)

    # Phase 2 PROMPT: load user template with issues_json="[]"; provider-neutral
    # message list for client.chat() (format translation happens in the LLM layer).
    messages = build_start_messages(args)

    # Phase 3 AGENT LOOP: model calls list_issues until one easy issue or cap.
    raw_result = find_easy_issues(client, messages, args, project_root=project_root)

    # Phase 4 VALIDATE: parse JSON, check schema, pretty-print the final result.
    validate_and_print_result(raw_result)


if __name__ == "__main__":
    main()
