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
async def test_graph_runs_end_to_end_with_real_pdf(compiled_graph, sample_pdf) -> None:
    """Invoke the graph async with a real PDF and assert a non-empty final state."""
    final = await compiled_graph.ainvoke(
        {"drawing_path": str(sample_pdf)},
        config={"configurable": {"thread_id": "test-1"}},
    )
    # Phase 6: Reflection Loop runs up to MAX=3 times since no LLM produces status=success
    assert final["reflection_iterations"] == 3
    assert final["status"] == "needs_human"
    assert "verification_notes" in final
    # Phase 2: Spec Interpreter populated intermediate
    assert final["intermediate"]["file_type"] == "pdf"
    assert final["intermediate"]["text_blocks"][0]


@pytest.mark.asyncio
async def test_thread_id_isolates_state(compiled_graph, sample_pdf) -> None:
    """Different thread_ids should produce independent reflection_iterations counters."""
    s1 = await compiled_graph.ainvoke(
        {"drawing_path": str(sample_pdf)},
        config={"configurable": {"thread_id": "thread-A"}},
    )
    s2 = await compiled_graph.ainvoke(
        {"drawing_path": str(sample_pdf)},
        config={"configurable": {"thread_id": "thread-B"}},
    )
    # Both fresh threads should start from 0 and increment to 1 (no shared state)
    assert s1["reflection_iterations"] == 3
    assert s2["reflection_iterations"] == 3


# --- Phase 6: Reflection Loop ---


def test_should_reflect_returns_end_on_success() -> None:
    """status='success' → exit loop."""
    from langgraph.graph import END
    from deepdraw.graph import should_reflect

    state = {"status": "success", "reflection_iterations": 1}
    assert should_reflect(state) == END


def test_should_reflect_loops_back_on_conflict_under_cap() -> None:
    """status='conflict' + iter<MAX → loop back to process_recommender."""
    from deepdraw.graph import should_reflect

    state = {"status": "conflict", "reflection_iterations": 1}
    assert should_reflect(state) == "process_recommender"


def test_should_reflect_returns_end_at_max_iter() -> None:
    """iter >= MAX_REFLECTION_ITERATIONS → exit even if conflict persists."""
    from langgraph.graph import END
    from deepdraw.graph import MAX_REFLECTION_ITERATIONS, should_reflect

    state = {
        "status": "conflict",
        "reflection_iterations": MAX_REFLECTION_ITERATIONS,
    }
    assert should_reflect(state) == END


def test_should_reflect_returns_end_on_needs_human_at_cap() -> None:
    """needs_human at max iter also exits."""
    from langgraph.graph import END
    from deepdraw.graph import MAX_REFLECTION_ITERATIONS, should_reflect

    state = {
        "status": "needs_human",
        "reflection_iterations": MAX_REFLECTION_ITERATIONS,
    }
    assert should_reflect(state) == END


def test_max_reflection_iterations_is_three() -> None:
    """PRD mandates 3 rounds max."""
    from deepdraw.graph import MAX_REFLECTION_ITERATIONS

    assert MAX_REFLECTION_ITERATIONS == 3
