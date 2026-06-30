"""LLM factory for DeepDraw agents.

Phase 1 defines the factory but does NOT use it (agents are echo).
Phase 3 uses it for Spec Interpreter / Drawing Auditor / BOM Generator.
"""

from __future__ import annotations

from langchain.chat_models import init_chat_model
from pydantic import BaseModel

# Per-agent LLM config (Phase 1 placeholders; Phase 3 tunes these)
_LLM_CONFIG: dict[str, dict] = {
    "spec_interpreter": {"model": "openai:gpt-4o", "temperature": 0.0},
    "drawing_auditor": {"model": "openai:gpt-4o", "temperature": 0.0},
    "bom_generator": {"model": "openai:gpt-4o", "temperature": 0.0},
    "process_recommender": {"model": "openai:gpt-4o", "temperature": 0.3},
    "chief_verifier": {"model": "anthropic:claude-opus-4-6", "temperature": 0.0},
}


def get_llm(agent_name: str):
    """Return a configured chat model for the given agent.

    Reads API keys from environment (OPENAI_API_KEY, ANTHROPIC_API_KEY).
    """
    if agent_name not in _LLM_CONFIG:
        raise KeyError(f"Unknown agent: {agent_name}. Known: {list(_LLM_CONFIG)}")
    return init_chat_model(**_LLM_CONFIG[agent_name])


def get_structured_llm(agent_name: str, schema: type[BaseModel]):
    """Return a chat model with structured output bound to a Pydantic schema.

    Uses the agent's configured model + temperature; wraps with with_structured_output().
    Cannot be combined with bind_tools() on the same model.
    """
    llm = get_llm(agent_name)
    return llm.with_structured_output(schema)