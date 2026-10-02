"""Prompt template loader for DeepDraw agents.

Templates use ``string.Template`` syntax (``$name`` placeholders) rather than
``str.format`` so that JSON-looking fences like `` `material` `` inside
prompts stay literal — ``str.format`` would try to resolve them as field
references and raise ``KeyError``.
"""

from __future__ import annotations

from pathlib import Path
from string import Template

PROMPTS_DIR = Path(__file__).parent

_PROMPT_MAP: dict[str, str] = {
    "spec_interpreter": "spec_interpreter.md",
    "drawing_auditor": "drawing_auditor.md",
    "bom_generator": "bom_generator.md",
    "process_recommender": "process_recommender.md",
    "chief_verifier": "chief_verifier.md",
}


def load_prompt(agent_name: str) -> Template:
    """Load a prompt template by agent name. Returns a ``string.Template``.

    Callers substitute variables with ``t.safe_substitute(foo=bar)`` —
    unknown placeholders are left as literal ``$name`` instead of raising.
    """
    if agent_name not in _PROMPT_MAP:
        raise KeyError(f"Unknown agent: {agent_name}. Known: {list(_PROMPT_MAP)}")
    raw = (PROMPTS_DIR / _PROMPT_MAP[agent_name]).read_text(encoding="utf-8")
    return Template(raw)
