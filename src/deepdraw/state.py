"""LangGraph State Schema for DeepDraw's 5-Agent workflow.

Designed for Sequential + Reflection Loop topology.
Phase 1 only needs the schema; Phase 3+ fills in real values.
"""

from __future__ import annotations

import operator
from typing import Annotated

from typing_extensions import TypedDict


class DrawingSpec(TypedDict, total=False):
    """Output of 👓 Spec Interpreter."""

    material: str
    thickness_mm: float
    batch_size: int
    surface_treatment: str
    raw_requirements: dict


class DrawingError(TypedDict):
    """Output of 🔍 Drawing Auditor (list element)."""

    error_type: str
    location: str
    severity: str  # "critical" | "major" | "minor"
    description: str


class BOMItem(TypedDict):
    """Output of 📒 BOM Generator (list element)."""

    part_number: str
    name: str
    quantity: int
    unit: str


class ProcessStep(TypedDict):
    """Output of ⚙️ Process Recommender (list element)."""

    sequence: int
    operation: str
    machine: str
    tooling: str
    parameters: dict


class AgentState(TypedDict, total=False):
    """Top-level state for the 5-Agent LangGraph workflow."""

    # Inputs
    drawing_path: str
    # Accumulator outputs (use operator.add reducer for list fields)
    spec: DrawingSpec
    errors: Annotated[list[DrawingError], operator.add]
    bom: Annotated[list[BOMItem], operator.add]
    process_plan: list[ProcessStep]
    # Reflection state (used by Chief Verifier ↔ Process Recommender loop)
    verification_notes: Annotated[list[str], operator.add]
    reflection_iterations: int
    # Terminal state
    final_report: dict
    status: str  # "success" | "needs_human" | "conflict"
