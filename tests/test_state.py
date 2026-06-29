"""Tests for AgentState schema fields."""

from __future__ import annotations

from deepdraw.state import AgentState


def test_agent_state_has_required_fields() -> None:
    annotations = AgentState.__annotations__
    expected = {
        "drawing_path",
        "spec",
        "errors",
        "bom",
        "process_plan",
        "verification_notes",
        "reflection_iterations",
        "final_report",
        "status",
    }
    assert expected.issubset(annotations.keys()), f"Missing fields: {expected - annotations.keys()}"


def test_agent_state_empty_construction() -> None:
    state: AgentState = {}
    assert state.get("drawing_path") is None
    assert state.get("errors") is None


def test_agent_state_has_intermediate_field() -> None:
    """Phase 2 added `intermediate` for parsed drawing data."""
    assert "intermediate" in AgentState.__annotations__
