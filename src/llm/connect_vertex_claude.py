"""
Purpose: connect to Claude on Google Vertex AI.

This is the only module that imports ``anthropic``. Phase 1 constructs
``AnthropicVertex`` with Application Default Credentials (ADC).

Phase 3 adds ``VertexClaudeClient.chat()`` for the agent loop.
Direct ``Anthropic(api_key=...)`` is reserved for v2.
"""

from __future__ import annotations

from typing import Any

from anthropic import AnthropicVertex, NOT_GIVEN

from .load_model_config import ModelSettings
from .model_reply_dataclass import ModelReply, ToolRequest


class VertexClaudeClient:
    """
    Connection to Claude via Vertex AI.

    Phase 1: build ``AnthropicVertex`` from ``ModelSettings`` (no API calls).
    Phase 3: ``chat()`` sends messages and parses tool calls.
    """

    def __init__(self, settings: ModelSettings) -> None:
        self._settings = settings
        self._client = AnthropicVertex(
            project_id=settings.vertex_project_id,
            region=settings.vertex_region,
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelReply:
        """
        Send the conversation to Vertex Claude and return text plus tool calls.

        Accepts provider-neutral message dicts from the agent loop; translation
        to Anthropic format happens in private helpers below.
        """
        api_messages = _to_anthropic_messages(messages)
        api_tools = _to_anthropic_tools(tools) if tools else NOT_GIVEN

        response = self._client.messages.create(
            model=self._settings.model,
            max_tokens=self._settings.max_tokens,
            messages=api_messages,
            tools=api_tools,
        )
        return _parse_model_reply(response)


def _to_anthropic_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map provider-neutral message dicts to Anthropic ``messages`` format."""
    api_messages: list[dict[str, Any]] = []
    pending_tool_results: list[dict[str, Any]] = []

    def flush_tool_results() -> None:
        if not pending_tool_results:
            return
        api_messages.append({"role": "user", "content": pending_tool_results.copy()})
        pending_tool_results.clear()

    for message in messages:
        role = message["role"]

        if role == "tool":
            pending_tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": message["tool_call_id"],
                    "content": message["content"],
                }
            )
            continue

        flush_tool_results()

        if role == "user":
            api_messages.append({"role": "user", "content": message["content"]})
            continue

        if role == "assistant":
            content_blocks: list[dict[str, Any]] = []
            text = message.get("content", "")
            if text:
                content_blocks.append({"type": "text", "text": text})

            for tool_call in message.get("tool_calls") or []:
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": tool_call["id"],
                        "name": tool_call["name"],
                        "input": tool_call.get("arguments") or {},
                    }
                )

            if not content_blocks:
                content_blocks.append({"type": "text", "text": ""})

            api_messages.append({"role": "assistant", "content": content_blocks})
            continue

        raise ValueError(f"Unsupported message role: {role!r}")

    flush_tool_results()
    return api_messages


def _to_anthropic_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map agent ``tool_definition`` dicts to Anthropic ``tools`` format."""
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["parameters"],
        }
        for tool in tools
    ]


def _parse_model_reply(response: Any) -> ModelReply:
    """Map an Anthropic ``Message`` response to ``ModelReply``."""
    text_parts: list[str] = []
    tool_calls: list[ToolRequest] = []

    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text_parts.append(block.text)
        elif block_type == "tool_use":
            tool_calls.append(
                ToolRequest(
                    id=block.id,
                    name=block.name,
                    arguments=dict(block.input),
                )
            )

    return ModelReply(text="".join(text_parts), tool_calls=tool_calls)
