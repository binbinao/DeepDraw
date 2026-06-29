"""🔍 Drawing Auditor — 图纸审计员

Phase 1 placeholder: returns an empty errors list.
Phase 3 will call Vision-LLM to inspect the drawing.
"""

from __future__ import annotations

from deepdraw.state import AgentState


async def drawing_auditor_node(state: AgentState) -> dict:
    """Phase 1 placeholder: no audit performed yet."""
    return {"errors": []}
