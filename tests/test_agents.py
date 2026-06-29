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
async def test_spec_interpreter_node_returns_spec() -> None:
    result = await spec_interpreter.spec_interpreter_node({"drawing_path": "/tmp/x.pdf"})
    assert "spec" in result
    assert result["spec"]["raw_requirements"]["drawing_path"] == "/tmp/x.pdf"


@pytest.mark.asyncio
async def test_drawing_auditor_node_returns_empty_errors() -> None:
    result = await drawing_auditor.drawing_auditor_node({})
    assert result == {"errors": []}


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
