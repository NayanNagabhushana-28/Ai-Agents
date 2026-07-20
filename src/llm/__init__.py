"""
LLM chat wrapper (Claude on Vertex AI in v1).

Requires ``ANTHROPIC_VERTEX_PROJECT_ID`` in ``.env`` and ADC from
``gcloud auth application-default login``. Direct API keys are v2.

Import submodules explicitly, e.g.::

    from llm.create_llm_connection import establish_connection
    from llm.load_model_config import load_model_settings
    from llm.build_chat_messages import user_message
"""
