"""
Purpose: run the easy issue finder agent loop (LLM + MCP tools).

Opens ``run_mcp_server.py`` as a subprocess, lists MCP tools, and loops on
``client.chat()`` until the model returns final text or ``max_tool_rounds`` is hit.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llm.build_chat_messages import assistant_message, tool_result
from llm.create_llm_connection import ChatClient
from llm.model_reply_dataclass import ToolRequest
from mcp_servers.connect_stdio_server import (
    call_tool_text,
    list_tool_definitions,
    open_stdio_session,
)


@dataclass
class FinderConfig:
    """Settings for one ``run_finder`` invocation."""

    owner: str
    repo: str
    target_easy_count: int = 1
    max_tool_rounds: int = 10
    per_page: int = 10


def run_finder(
    client: ChatClient,
    config: FinderConfig,
    messages: list[dict[str, Any]],
    *,
    project_root: Path,
) -> str:
    """
    Run the tool loop through MCP and return the model's final text reply.

    Mutates ``messages`` in place with assistant and tool turns.
    """
    return asyncio.run(
        _run_finder_async(client, config, messages, project_root=project_root)
    )


async def _run_finder_async(
    client: ChatClient,
    config: FinderConfig,
    messages: list[dict[str, Any]],
    *,
    project_root: Path,
) -> str:
    server_script = project_root / "src" / "mcp_servers" / "run_mcp_server.py"

    async with open_stdio_session(server_script) as session:
        tools = await list_tool_definitions(session)
        round_num = 0

        while round_num < config.max_tool_rounds:
            round_num += 1
            reply = client.chat(messages, tools=tools)

            if not reply.tool_calls:
                return reply.text.strip()

            tool_calls = [
                {"id": call.id, "name": call.name, "arguments": call.arguments}
                for call in reply.tool_calls
            ]
            messages.append(assistant_message(reply.text, tool_calls=tool_calls))

            for call in reply.tool_calls:
                args = _merge_tool_args(config, call)
                payload = await call_tool_text(session, call.name, args)
                _print_tool_progress(round_num, call, args, payload)
                messages.append(tool_result(call.id, payload))

    raise RuntimeError("max_tool_rounds exceeded without final JSON from model")


def _merge_tool_args(config: FinderConfig, call: ToolRequest) -> dict[str, Any]:
    """Inject run config into MCP tool arguments."""
    args = {**call.arguments}
    args.setdefault("owner", config.owner)
    args.setdefault("repo", config.repo)
    if call.name == "list_issues":
        args.setdefault("no_linked_prs", True)
        args.setdefault("per_page", config.per_page)
    return args


def _print_tool_progress(
    round_num: int,
    call: ToolRequest,
    args: dict[str, Any],
    payload: str,
) -> None:
    if call.name != "list_issues":
        print(f"  Tool round {round_num}: {call.name}")
        return

    count = 0
    try:
        parsed = json.loads(payload)
        if isinstance(parsed, list):
            count = len(parsed)
    except json.JSONDecodeError:
        pass

    page = args.get("page", 1)
    print(f"  Tool round {round_num}: list_issues page={page} → {count} issues")
