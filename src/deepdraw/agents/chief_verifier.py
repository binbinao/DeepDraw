"""🛡️ Chief Verifier — cross-agent consistency check via LLM (Phase 4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from deepdraw.llm import get_structured_llm
from deepdraw.prompts import load_prompt
from deepdraw.state import AgentState


class VerificationNote(BaseModel):
    severity: Literal["critical", "major", "minor"]
    category: Literal[
        "material_compat",
        "tooling_size",
        "batch_cost",
        "standard_consistency",
        "surface_treat",
        "thickness_bend",
    ]
    description: str
    recommendation: str = ""


class VerificationResult(BaseModel):
    notes: list[VerificationNote] = []
    status: Literal["success", "needs_human", "conflict"] = "needs_human"


def _format_note(n: VerificationNote) -> str:
    icon = {"critical": "❌", "major": "⚠️", "minor": "ℹ️"}[n.severity]
    base = f"{icon} [{n.category}] {n.description}"
    return base + (f" → {n.recommendation}" if n.recommendation else "")


async def chief_verifier_node(state: AgentState) -> dict:
    """Read spec/errors/bom/process_plan → LLM (Claude) → return notes + status."""
    spec = state.get("spec", {}) or {}
    errors = state.get("errors", []) or []
    bom = state.get("bom", []) or []
    process_plan = state.get("process_plan", []) or []

    context = {
        "spec": spec,
        "errors_count": len(errors),
        "bom_count": len(bom),
        "process_steps": len(process_plan),
        "bom_summary": bom[:5],
        "process_summary": process_plan[:5],
    }

    notes: list[str] = []
    status = "needs_human"

    try:
        llm = get_structured_llm("chief_verifier", VerificationResult)
        prompt = load_prompt("chief_verifier") + "\n\n## 当前 4 Agent 输出\n" + str(context)[:3000]
        result = await llm.ainvoke(prompt)
        notes.extend(_format_note(n) for n in result.notes)
        status = result.status
    except Exception as e:
        notes.append(f"[Phase4] Chief Verifier LLM failed: {e!s}")
        status = "needs_human"

    reflection_iterations = state.get("reflection_iterations", 0) + 1

    return {
        "verification_notes": notes,
        "reflection_iterations": reflection_iterations,
        "status": status,
    }
