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


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Generate a minimal single-page PDF with text + simple graphics."""
    import pymupdf

    p = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4
    page.insert_text((72, 72), "DeepDraw Test Drawing", fontsize=14)
    page.insert_text((72, 100), "Material: Q235B", fontsize=10)
    page.insert_text((72, 115), "Thickness: 5mm", fontsize=10)
    page.draw_rect(pymupdf.Rect(72, 200, 200, 400))
    doc.save(p)
    doc.close()
    return p


@pytest.fixture
def sample_dxf(tmp_path: Path) -> Path:
    """Generate a minimal DXF with LINE, CIRCLE, TEXT entities."""
    import ezdxf

    p = tmp_path / "sample.dxf"
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 0))
    msp.add_circle((5, 5), radius=2.5)
    msp.add_text("DeepDraw Test", dxfattribs={"insert": (0, 10)})
    doc.saveas(p)
    return p
