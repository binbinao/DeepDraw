"""LangGraph StateGraph definition for the 5-Agent DFM-Copilot Squad."""

from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from deepdraw.agents import (
    bom_generator,
    chief_verifier,
    drawing_auditor,
    process_recommender,
    spec_interpreter,
)
from deepdraw.state import AgentState

builder = StateGraph(AgentState)

# Nodes (with retry policy for transient LLM failures in later phases)
builder.add_node(
    "spec_interpreter",
    spec_interpreter.spec_interpreter_node,
    retry_policy=RetryPolicy(max_attempts=3),
)
builder.add_node(
    "drawing_auditor",
    drawing_auditor.drawing_auditor_node,
    retry_policy=RetryPolicy(max_attempts=3),
)
builder.add_node(
    "bom_generator",
    bom_generator.bom_generator_node,
    retry_policy=RetryPolicy(max_attempts=3),
)
builder.add_node(
    "process_recommender",
    process_recommender.process_recommender_node,
    retry_policy=RetryPolicy(max_attempts=3),
)
builder.add_node(
    "chief_verifier",
    chief_verifier.chief_verifier_node,
    retry_policy=RetryPolicy(max_attempts=3),
)

# Edges: Sequential main flow
builder.add_edge(START, "spec_interpreter")
builder.add_edge("spec_interpreter", "drawing_auditor")
builder.add_edge("drawing_auditor", "bom_generator")
builder.add_edge("bom_generator", "process_recommender")
builder.add_edge("process_recommender", "chief_verifier")


# Conditional edge placeholder for Reflection Loop (real logic in Phase 6)
def should_reflect(state: AgentState) -> str:
    """Decide whether to loop back for another reflection round.

    Phase 1: always ends (max_iter enforced in Phase 6).
    """
    del state  # unused
    return END


builder.add_conditional_edges("chief_verifier", should_reflect)

# Compile with in-memory checkpointer (testing) — Phase 7 swaps to SqliteSaver
graph = builder.compile(checkpointer=InMemorySaver())
