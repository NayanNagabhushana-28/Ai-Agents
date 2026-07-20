"""
Purpose: read which Claude model and Vertex project to use for a run.

The agent and CLI need configuration before they can call Claude. This file
loads that configuration from environment variables (or a ``.env`` file after
``load_dotenv()``) and validates it early, so missing settings fail with a
clear error instead of a vague API failure later.

Authentication uses Google Application Default Credentials (ADC) from
``gcloud auth application-default login`` — not an API key. Direct
``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY`` are reserved for v2.

This file does not call Anthropic — it only prepares settings. Phase 3 adds
``chat()`` in ``connect_vertex_claude.py``, using a ``ModelSettings`` object
from here.

Who calls this
--------------
- ``create_llm_connection.establish_connection()`` when no settings are passed in
- ``run_easy_issue_finder.py`` when ``--model`` overrides ``MODEL``
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Vertex model id when neither CLI ``--model`` nor env ``MODEL`` is set.
DEFAULT_MODEL = "claude-sonnet-4@20250514"
DEFAULT_VERTEX_REGION = "global"


@dataclass(frozen=True)
class ModelSettings:
    """
    Purpose: hold all settings for one Claude-on-Vertex session in one object.

    Bundles model id, GCP project/region, and generation limits for
    ``establish_connection()``. Auth comes from ADC on the machine, not from fields
    on this object.
    """

    model: str  # Vertex Claude model id, e.g. claude-sonnet-4@20250514
    vertex_project_id: str  # from ANTHROPIC_VERTEX_PROJECT_ID
    vertex_region: str = DEFAULT_VERTEX_REGION  # from CLOUD_ML_REGION
    max_tokens: int = 4096  # max tokens the model may reply with per turn


def load_model_settings(*, model: str | None = None) -> ModelSettings:
    """
    Purpose: load and validate Claude-on-Vertex settings before starting a run.

    Reads ``MODEL``, ``ANTHROPIC_VERTEX_PROJECT_ID``, and ``CLOUD_ML_REGION``
    from the environment. If neither ``model`` nor ``MODEL`` is set, uses
    ``DEFAULT_MODEL``.

    If the caller passes ``model`` (e.g. from CLI ``--model``), that value is
    used instead of ``MODEL`` so you can switch models for one run without
    editing ``.env``.

    Parameters
    ----------
    model:
        Optional Claude model id. Overrides ``MODEL`` env; if both are omitted,
        ``DEFAULT_MODEL`` is used.

    Returns
    -------
    ModelSettings
        Validated settings for ``establish_connection(settings=...)``.

    Raises
    ------
    ValueError
        If ``ANTHROPIC_VERTEX_PROJECT_ID`` is missing.
    """
    # CLI --model > MODEL in .env > DEFAULT_MODEL
    resolved_model = (model or os.environ.get("MODEL", "")).strip() or DEFAULT_MODEL
    vertex_project_id = os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID", "").strip()
    if not vertex_project_id:
        raise ValueError(
            "ANTHROPIC_VERTEX_PROJECT_ID is required. "
            "Set your team GCP project id in .env and run: "
            "gcloud auth application-default login"
        )

    vertex_region = os.environ.get("CLOUD_ML_REGION", "").strip() or DEFAULT_VERTEX_REGION
    max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "4096"))
    return ModelSettings(
        model=resolved_model,
        vertex_project_id=vertex_project_id,
        vertex_region=vertex_region,
        max_tokens=max_tokens,
    )
