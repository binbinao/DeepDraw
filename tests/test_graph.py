"""Tests for the compiled StateGraph."""

from __future__ import annotations

import pytest


def test_graph_compiles(compiled_graph) -> None:
    """The graph should compile without error."""
    assert compiled_graph is not None


def test_graph_has_all_5_agent_nodes(compiled_graph) -> None:
    """The 5 agent node names should be registered (LangGraph 1.x wraps in PregelNode)."""
    expected_names = {
        "spec_interpreter",
        "drawing_auditor",
        "bom_generator",
        "process_recommender",
        "chief_verifier",
    }
    actual_names = set(compiled_graph.nodes.keys())
    assert expected_names.issubset(actual_names), f"Missing nodes: {expected_names - actual_names}"


@pytest.mark.asyncio
async def test_graph_runs_end_to_end_with_placeholder_state(compiled_graph, dummy_drawing) -> None:
    """Invoke the graph async with a placeholder PDF and assert a non-empty final state."""
    final = await compiled_graph.ainvoke(
        {"drawing_path": str(dummy_drawing)},
        config={"configurable": {"thread_id": "test-1"}},
    )
    assert final["status"] == "needs_human"
    assert final["reflection_iterations"] == 1
    assert "verification_notes" in final
