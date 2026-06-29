"""Shared pytest fixtures for DeepDraw tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from deepdraw.graph import graph
from deepdraw.state import AgentState


@pytest.fixture
def sample_state() -> AgentState:
    """Empty state with a dummy drawing path."""
    return {"drawing_path": "/tmp/test.pdf"}


@pytest.fixture
def compiled_graph():
    """The compiled LangGraph (with InMemorySaver)."""
    return graph


@pytest.fixture
def dummy_drawing(tmp_path: Path) -> Path:
    """Create a dummy file that stands in for a real PDF."""
    p = tmp_path / "dummy.pdf"
    p.write_text("PDF placeholder")
    return p
