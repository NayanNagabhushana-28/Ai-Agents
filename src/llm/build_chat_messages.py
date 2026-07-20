"""
Purpose: build provider-neutral message dicts for ``client.chat()``.

Small helpers that return plain dicts in a consistent shape for the agent loop.
"""

from __future__ import annotations

from typing import Any


def user_message(text: str) -> dict[str, Any]:
    """
    Build a user turn for the conversation history.

    Returns ``{"role": "user", "content": text}``.
    """
    return {"role": "user", "content": text}


def assistant_message(
    text: str = "",
    *,
    tool_calls: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Record an assistant turn, optionally including tool calls from the model."""
    msg: dict[str, Any] = {"role": "assistant", "content": text}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg


def tool_result(tool_call_id: str, content: str) -> dict[str, Any]:
    """Send tool output back to the model on the next ``client.chat()`` turn."""
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}
