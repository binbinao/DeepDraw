"""🔍 Drawing Auditor — identifies drawing errors via Vision-LLM (Phase 3)."""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from deepdraw.llm import get_structured_llm
from deepdraw.prompts import load_prompt
from deepdraw.state import AgentState


class DrawingErrorItem(BaseModel):
    error_type: Literal[
        "missing_dimension",
        "view_inconsistency",
        "tolerance_conflict",
        "unmanufacturable_feature",
    ]
    location: str
    severity: Literal["critical", "major", "minor"]
    description: str


class DrawingErrorsResult(BaseModel):
    """Structured output for Drawing Auditor LLM call (one per page)."""

    errors: list[DrawingErrorItem] = []


async def drawing_auditor_node(state: AgentState) -> dict:
    """Read intermediate.images_b64 → Vision-LLM → return errors."""
    intermediate = state.get("intermediate", {}) or {}
    images = intermediate.get("images_b64", [])
    file_type = intermediate.get("file_type", "unknown")
    all_errors: list[dict] = []
    notes: list[str] = []

    if images:
        try:
            llm = get_structured_llm("drawing_auditor", DrawingErrorsResult)
            prompt_text = load_prompt("drawing_auditor")
            for page_num, img_b64 in enumerate(images, start=1):
                msg = HumanMessage(
                    content=[
                        {"type": "text", "text": prompt_text.format(page_num=page_num)},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                        },
                    ],
                )
                result = await llm.ainvoke([msg])
                all_errors.extend(e.model_dump() for e in result.errors)
        except Exception as e:
            notes.append(f"[Phase3] Drawing Auditor LLM failed: {e!s}")
    else:
        notes.append(f"[Phase3] Drawing Auditor: no images in intermediate (file_type={file_type})")

    if file_type == "dxf":
        entities = intermediate.get("entities", [])
        notes.append(f"[Phase3] DXF has {len(entities)} geometry entities (audit pending Phase 4)")

    return {"errors": all_errors, "verification_notes": notes}
