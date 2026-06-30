"""👓 Spec Interpreter — extracts structured spec from PDF/DXF via LLM (Phase 3)."""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path

from pydantic import BaseModel, Field

from deepdraw.llm import get_structured_llm
from deepdraw.prompts import load_prompt
from deepdraw.state import AgentState
from deepdraw.tools.dxf import extract_dxf_entities
from deepdraw.tools.file_detect import detect_file_type
from deepdraw.tools.pdf import extract_pdf_images, extract_pdf_text


class SpecLLMResult(BaseModel):
    """Structured output for Spec Interpreter LLM call."""

    material: str | None = None
    thickness_mm: float | None = None
    batch_size: int | None = None
    surface_treatment: str | None = None
    raw_requirements: dict = Field(default_factory=dict)


async def spec_interpreter_node(state: AgentState) -> dict:
    """Parse drawing → intermediate → LLM-extract spec → return partial update."""
    drawing_path = state.get("drawing_path", "")
    if not drawing_path or not Path(drawing_path).exists():
        return {
            "spec": {
                "raw_requirements": {"drawing_path": drawing_path, "error": "file not found"},
            },
        }

    file_type = detect_file_type(drawing_path)
    intermediate: dict = {
        "file_type": file_type,
        "parsed_path": str(Path(drawing_path).absolute()),
    }

    if file_type == "pdf":
        text_result = await asyncio.to_thread(extract_pdf_text, drawing_path)
        intermediate["text_blocks"] = [p["text"] for p in text_result["pages"]]
        images = await asyncio.to_thread(extract_pdf_images, drawing_path, 150)
        intermediate["images_b64"] = [base64.b64encode(img).decode("ascii") for img in images]
    elif file_type == "dxf":
        dxf_result = await asyncio.to_thread(extract_dxf_entities, drawing_path)
        intermediate["entities"] = dxf_result["entities"]

    spec_result = SpecLLMResult()
    if intermediate.get("text_blocks"):
        pdf_text = "\n\n".join(intermediate["text_blocks"])[:4000]
        try:
            llm = get_structured_llm("spec_interpreter", SpecLLMResult)
            prompt = load_prompt("spec_interpreter").format(pdf_text=pdf_text)
            spec_result = await llm.ainvoke(prompt)
        except Exception as e:
            intermediate.setdefault("llm_errors", []).append(f"spec_interpreter: {e!s}")

    return {
        "intermediate": intermediate,
        "spec": {
            "material": spec_result.material,
            "thickness_mm": spec_result.thickness_mm,
            "batch_size": spec_result.batch_size,
            "surface_treatment": spec_result.surface_treatment,
            "raw_requirements": spec_result.raw_requirements,
        },
    }
