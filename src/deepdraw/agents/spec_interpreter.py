"""👓 Spec Interpreter — 需求翻译官

Phase 2: parses PDF/DXF, populates intermediate.text_blocks / entities.
Phase 3: will call a real LLM with prompts/spec_interpreter.md to extract spec.
"""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path

from deepdraw.state import AgentState
from deepdraw.tools.dxf import extract_dxf_entities
from deepdraw.tools.file_detect import detect_file_type
from deepdraw.tools.pdf import extract_pdf_images, extract_pdf_text


async def spec_interpreter_node(state: AgentState) -> dict:
    """Parse the drawing file and populate `intermediate` + basic `spec`.

    Phase 2 returns raw text/entity counts; Phase 3 will LLM-extract structured spec.
    """
    drawing_path = state.get("drawing_path", "")
    if not drawing_path or not Path(drawing_path).exists():
        return {
            "spec": {
                "raw_requirements": {
                    "drawing_path": drawing_path,
                    "error": "file not found",
                },
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
    # else: unknown → leave intermediate empty

    return {
        "intermediate": intermediate,
        "spec": {
            "raw_requirements": {
                "drawing_path": drawing_path,
                "file_type": file_type,
                "page_count": len(intermediate.get("text_blocks", [])),
                "entity_count": len(intermediate.get("entities", [])),
            },
        },
    }
