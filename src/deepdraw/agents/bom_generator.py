"""📒 BOM Generator — extracts parts list via LLM (Phase 3)."""

from __future__ import annotations

from pydantic import BaseModel

from deepdraw.llm import get_structured_llm
from deepdraw.prompts import load_prompt
from deepdraw.state import AgentState


class BOMItemLLM(BaseModel):
    part_number: str
    name: str
    quantity: int
    unit: str = "件"


class BOMLLMResult(BaseModel):
    """Structured output for BOM Generator LLM call."""

    items: list[BOMItemLLM] = []


async def bom_generator_node(state: AgentState) -> dict:
    """Read intermediate.text_blocks → LLM → return BOM list."""
    intermediate = state.get("intermediate", {}) or {}
    text_blocks = intermediate.get("text_blocks", [])

    if not text_blocks:
        return {"bom": []}

    try:
        llm = get_structured_llm("bom_generator", BOMLLMResult)
        prompt = load_prompt("bom_generator").format(
            pdf_text="\n\n".join(text_blocks)[:4000],
        )
        result = await llm.ainvoke(prompt)
        return {"bom": [item.model_dump() for item in result.items]}
    except Exception as e:
        return {
            "bom": [],
            "verification_notes": [f"[Phase3] BOM extraction failed: {e!s}"],
        }
