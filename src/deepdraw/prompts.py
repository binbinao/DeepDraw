"""Prompt template loader for DeepDraw agents."""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"

_PROMPT_MAP: dict[str, str] = {
    "spec_interpreter": "spec_interpreter.md",
    "drawing_auditor": "drawing_auditor.md",
    "bom_generator": "bom_generator.md",
    "process_recommender": "process_recommender.md",
    "chief_verifier": "chief_verifier.md",
}


def load_prompt(agent_name: str) -> str:
    """Load a prompt template by agent name. Returns raw markdown text."""
    if agent_name not in _PROMPT_MAP:
        raise KeyError(f"Unknown agent: {agent_name}. Known: {list(_PROMPT_MAP)}")
    return (PROMPTS_DIR / _PROMPT_MAP[agent_name]).read_text(encoding="utf-8")