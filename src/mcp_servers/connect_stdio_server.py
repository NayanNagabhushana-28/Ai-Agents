"""
Purpose: connect the agent loop to the GitHub Issues MCP server over stdio.

Spawns ``run_mcp_server.py`` as a subprocess (same as ``.cursor/mcp.json``),
opens a ``ClientSession``, and bridges MCP tool schemas to the neutral dict
shape expected by ``client.chat(..., tools=...)``.
"""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _tool_definition(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    """Agent-neutral tool dict for ``client.chat(messages, tools=...)``."""
    return {"name": name, "description": description, "parameters": parameters}


@asynccontextmanager
async def open_stdio_session(server_script: str | Path) -> AsyncIterator[ClientSession]:
    """
    Spawn the MCP server subprocess, initialize the session, and yield it.

    The subprocess inherits the current environment (``GITHUB_TOKEN`` from
    ``load_dotenv`` must be set before calling this).
    """
    script_path = Path(server_script).resolve()
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(script_path)],
        env=os.environ.copy(),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def list_tool_definitions(session: ClientSession) -> list[dict[str, Any]]:
    """
    List tools from the MCP server as neutral dicts for ``client.chat()``.

    Maps MCP ``inputSchema`` to ``parameters`` for the LLM layer.
    """
    result = await session.list_tools()
    return [
        _tool_definition(
            name=tool.name,
            description=tool.description or "",
            parameters=tool.inputSchema or {"type": "object", "properties": {}},
        )
        for tool in result.tools
    ]


async def call_tool_text(
    session: ClientSession,
    name: str,
    arguments: dict[str, Any] | None = None,
) -> str:
    """
    Call an MCP tool and return its text payload.

    Used by the agent loop to feed tool output back into ``client.chat()``.
    """
    result = await session.call_tool(name, arguments or {})
    parts: list[str] = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts)
