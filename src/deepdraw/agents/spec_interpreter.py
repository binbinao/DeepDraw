"""👓 Spec Interpreter — 需求翻译官

Phase 1 placeholder: returns an empty DrawingSpec.
Phase 3 will call a real LLM with prompts/spec_interpreter.md.
"""

from __future__ import annotations

from deepdraw.state import AgentState


async def spec_interpreter_node(state: AgentState) -> dict:
    """Read drawing_path from state, return spec placeholder."""
    return {
        "spec": {
            "raw_requirements": {"drawing_path": state.get("drawing_path", "")},
        },
    }
