"""Tests for src/deepdraw/tools/dxf.py."""

from __future__ import annotations

from deepdraw.tools.dxf import extract_dxf_entities


def test_extract_dxf_entities_returns_3_types(sample_dxf) -> None:
    result = extract_dxf_entities(sample_dxf)
    assert result["file_type"] == "dxf"
    types = {e["type"] for e in result["entities"]}
    assert "LINE" in types
    assert "CIRCLE" in types
    assert "TEXT" in types


def test_extract_dxf_line_has_start_end(sample_dxf) -> None:
    result = extract_dxf_entities(sample_dxf)
    line = next(e for e in result["entities"] if e["type"] == "LINE")
    assert line["start"] == [0.0, 0.0, 0.0]
    assert line["end"] == [10.0, 0.0, 0.0]


def test_extract_dxf_circle_has_radius(sample_dxf) -> None:
    result = extract_dxf_entities(sample_dxf)
    circle = next(e for e in result["entities"] if e["type"] == "CIRCLE")
    assert circle["radius"] == 2.5


def test_extract_dxf_handles_corrupt_file(tmp_path) -> None:
    bad = tmp_path / "bad.dxf"
    bad.write_bytes(b"not a dxf file")
    result = extract_dxf_entities(bad)  # should not raise
    assert result["entity_count"] == 0
