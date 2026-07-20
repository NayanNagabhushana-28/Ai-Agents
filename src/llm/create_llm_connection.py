"""
Purpose: create the object agents use to talk to a language model.

Reads ``ModelSettings`` (from ``load_model_config.py``) and returns a
backend-specific connection. v1 uses Vertex Claude via
``connect_vertex_claude.py``; v2 may add direct API / OpenAI here.
"""

from __future__ import annotations

from typing import Any, Protocol

from .connect_vertex_claude import VertexClaudeClient
from .load_model_config import ModelSettings, load_model_settings
from .model_reply_dataclass import ModelReply


class ChatClient(Protocol):
    """
    Purpose: define what every model backend must support.

    The agent loop only cares about ``chat(messages, tools=...) -> ModelReply``.
    Any provider (Vertex Claude today, OpenAI later) must implement that one
    method so the loop code stays the same.
    """

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelReply:
        """
        Purpose: send the conversation so far to the model and get the next turn.

        The model may reply with plain text (done) or request tools (fetch more
        issues). The agent loop runs those tools and calls ``chat`` again.
        """
        ...


def establish_connection(settings: ModelSettings | None = None) -> VertexClaudeClient:
    """
    Purpose: establish a Vertex-backed Claude connection for the agent or CLI.

    Constructs ``AnthropicVertex`` via ADC and returns a client with ``chat()``.

    Parameters
    ----------
    settings:
        Optional pre-built settings. Use this to pass a ``--model`` override
        from the CLI without changing ``.env``.

    Returns
    -------
    VertexClaudeClient
        Ready for ``chat(messages, tools=...)`` in the agent loop.
    """
    # v1: Vertex + AnthropicVertex. v2: direct API key / OpenAI branches here.
    return VertexClaudeClient(settings or load_model_settings())
