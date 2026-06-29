"""Smoke tests for each of the 5 Agent nodes."""

from __future__ import annotations

import pytest

from deepdraw.agents import (
    bom_generator,
    chief_verifier,
    drawing_auditor,
    process_recommender,
    spec_interpreter,
)


@pytest.mark.asyncio
async def test_spec_interpreter_node_with_pdf(sample_pdf) -> None:
    result = await spec_interpreter.spec_interpreter_node({"drawing_path": str(sample_pdf)})
    assert "intermediate" in result
    assert result["intermediate"]["file_type"] == "pdf"
    assert result["intermediate"]["text_blocks"][0]  # non-empty text from fixture
    assert "DeepDraw Test Drawing" in result["intermediate"]["text_blocks"][0]
    assert len(result["intermediate"]["images_b64"]) == 1
    assert "spec" in result
    assert result["spec"]["raw_requirements"]["file_type"] == "pdf"


@pytest.mark.asyncio
async def test_spec_interpreter_node_with_dxf(sample_dxf) -> None:
    result = await spec_interpreter.spec_interpreter_node({"drawing_path": str(sample_dxf)})
    assert result["intermediate"]["file_type"] == "dxf"
    assert len(result["intermediate"]["entities"]) >= 3  # LINE + CIRCLE + TEXT
    assert "images_b64" not in result["intermediate"]  # DXF doesn't render images


@pytest.mark.asyncio
async def test_spec_interpreter_node_handles_missing_file() -> None:
    result = await spec_interpreter.spec_interpreter_node({"drawing_path": "/tmp/nope.pdf"})
    assert "error" in result["spec"]["raw_requirements"]


@pytest.mark.asyncio
async def test_drawing_auditor_node_consumes_pdf_images() -> None:
    state = {
        "intermediate": {
            "file_type": "pdf",
            "images_b64": ["fake_png_1", "fake_png_2"],
        },
    }
    result = await drawing_auditor.drawing_auditor_node(state)
    assert "verification_notes" in result
    assert "2 page image(s) from pdf" in result["verification_notes"][0]


@pytest.mark.asyncio
async def test_drawing_auditor_node_consumes_dxf_entities() -> None:
    state = {
        "intermediate": {
            "file_type": "dxf",
            "entities": [{"type": "LINE"}, {"type": "CIRCLE"}, {"type": "TEXT"}],
        },
    }
    result = await drawing_auditor.drawing_auditor_node(state)
    assert len(result["verification_notes"]) == 2
    assert "3 geometry entities" in result["verification_notes"][1]


@pytest.mark.asyncio
async def test_bom_generator_node_returns_empty_bom() -> None:
    result = await bom_generator.bom_generator_node({})
    assert result == {"bom": []}


@pytest.mark.asyncio
async def test_process_recommender_node_returns_empty_plan() -> None:
    result = await process_recommender.process_recommender_node({})
    assert result == {"process_plan": []}


@pytest.mark.asyncio
async def test_chief_verifier_node_marks_needs_human() -> None:
    result = await chief_verifier.chief_verifier_node({})
    assert result["status"] == "needs_human"
    assert result["reflection_iterations"] == 1
    assert len(result["verification_notes"]) == 1
