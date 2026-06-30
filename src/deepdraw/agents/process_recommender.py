"""⚙️ Process Recommender — recommends machining operations via LLM (Phase 4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from deepdraw.llm import get_structured_llm
from deepdraw.prompts import load_prompt
from deepdraw.state import AgentState


class ProcessStepLLM(BaseModel):
    sequence: int
    operation: Literal[
        "laser_cut",
        "bend",
        "mill",
        "drill",
        "weld",
        "surface_treat",
        "press_brake",
        "plasma_cut",
        "shear",
        "punch",
    ]
    machine: str = "TBD"
    tooling: str = "TBD"
    parameters: dict = Field(default_factory=dict)


class ProcessPlanLLMResult(BaseModel):
    """Structured output for Process Recommender LLM call."""

    steps: list[ProcessStepLLM] = []


async def process_recommender_node(state: AgentState) -> dict:
    """Read spec + errors + bom + entities → LLM → return process_plan."""
    spec = state.get("spec", {}) or {}
    errors = state.get("errors", []) or []
    bom = state.get("bom", []) or []
    intermediate = state.get("intermediate", {}) or {}
    entities = intermediate.get("entities", [])

    context = {
        "material": spec.get("material"),
        "thickness_mm": spec.get("thickness_mm"),
        "batch_size": spec.get("batch_size"),
        "surface_treatment": spec.get("surface_treatment"),
        "error_count": len(errors),
        "bom_count": len(bom),
        "entity_count": len(entities),
    }

    try:
        llm = get_structured_llm("process_recommender", ProcessPlanLLMResult)
        prompt = load_prompt("process_recommender") + "\n\n## 当前输入\n" + str(context)[:3000]
        result = await llm.ainvoke(prompt)
        return {"process_plan": [s.model_dump() for s in result.steps]}
    except Exception as e:
        return {
            "process_plan": [],
            "verification_notes": [f"[Phase4] Process Recommender LLM failed: {e!s}"],
        }
