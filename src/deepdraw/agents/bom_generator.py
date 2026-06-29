"""📒 BOM Generator — 物料管家

Phase 1 placeholder: returns an empty BOM list.
Phase 3 will extract parts from drawing and match internal codes.
"""

from __future__ import annotations

from deepdraw.state import AgentState


async def bom_generator_node(state: AgentState) -> dict:
    """Phase 1 placeholder: no BOM generated yet."""
    return {"bom": []}
