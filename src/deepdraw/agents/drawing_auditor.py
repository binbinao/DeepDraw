"""🔍 Drawing Auditor — 图纸审计员

Phase 2: consumes intermediate.images_b64 (PDF) or entities (DXF); records audit readiness.
Phase 3: will call Vision-LLM with these images to identify errors.
"""

from __future__ import annotations

from deepdraw.state import AgentState


async def drawing_auditor_node(state: AgentState) -> dict:
    """Read intermediate; record audit-readiness notes. Phase 2: no real audit yet."""
    intermediate = state.get("intermediate", {}) or {}
    images = intermediate.get("images_b64", [])
    file_type = intermediate.get("file_type", "unknown")
    notes = [f"[Phase2] Drawing Auditor received {len(images)} page image(s) from {file_type}"]
    if file_type == "dxf":
        entities = intermediate.get("entities", [])
        notes.append(
            f"[Phase2] DXF has {len(entities)} geometry entities (Phase 3 will check via LLM)"
        )
    return {"verification_notes": notes}
