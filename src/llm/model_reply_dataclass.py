"""
Purpose: dataclasses for one model turn (text reply and optional tool calls).

Used by ``connect_vertex_claude.py`` and the agent loop when handling what
``client.chat()`` returns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolRequest:
    """One tool call the model wants to run."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ModelReply:
    """Text and optional tool calls from one model turn."""

    text: str
    tool_calls: list[ToolRequest] = field(default_factory=list)
