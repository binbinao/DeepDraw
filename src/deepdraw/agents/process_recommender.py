"""⚙️ Process Recommender — RAG-augmented LLM (Phase 5)."""

from __future__ import annotations

import asyncio
from typing import Literal

from pydantic import BaseModel, Field

from deepdraw.llm import get_structured_llm
from deepdraw.prompts import load_prompt
from deepdraw.state import AgentState
from deepdraw.tools.rag import (
    COLLECTION_MANUALS,
    format_results,
    get_client,
    get_or_create_collection,
    query,
)


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


def _rag_query_sync(query_text: str, n_results: int = 3) -> tuple[str, list[str]]:
    """Sync RAG query. Returns (formatted_context, raw_texts_list)."""
    try:
        client = get_client(persist=True)
        coll = get_or_create_collection(client, COLLECTION_MANUALS)
        results = query(coll, query_text, n_results=n_results)
        return format_results(results), [r["text"] for r in results]
    except Exception:
        return "", []


async def process_recommender_node(state: AgentState) -> dict:
    """Read spec + entities → RAG query → LLM with RAG context → return process_plan."""
    spec = state.get("spec", {}) or {}
    errors = state.get("errors", []) or []
    bom = state.get("bom", []) or []
    intermediate = state.get("intermediate", {}) or {}
    entities = intermediate.get("entities", [])

    # Build RAG query from spec
    query_parts = [
        str(spec.get("material", "")),
        f"{spec.get('thickness_mm', '')}mm",
        str(spec.get("surface_treatment", "")),
        str(spec.get("batch_size", "")),
    ]
    query_text = " ".join(p for p in query_parts if p and p != "Nonemm")
    if not query_text:
        query_text = "钣金加工"

    rag_context, rag_raw = await asyncio.to_thread(_rag_query_sync, query_text)

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
        prompt = (
            load_prompt("process_recommender")
            + "\n\n## 企业工艺知识（RAG 召回）\n"
            + (rag_context or "（无匹配，使用通用知识）")
            + "\n\n## 当前输入\n"
            + str(context)[:3000]
        )
        result = await llm.ainvoke(prompt)
        return {
            "process_plan": [s.model_dump() for s in result.steps],
            "rag_context": rag_raw,
        }
    except Exception as e:
        return {
            "process_plan": [],
            "rag_context": rag_raw,
            "verification_notes": [f"[Phase5] Process Recommender failed: {e!s}"],
        }
