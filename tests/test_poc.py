"""Tests for Phase 7 PoC harness."""

from __future__ import annotations

from pathlib import Path

import pytest

from deepdraw.tools.poc import (
    PoCResult,
    aggregate,
    load_scenarios,
)
from deepdraw.tools.poc_report import render_report

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SCENARIOS_FILE = FIXTURES_DIR / "poc_scenarios.json"


def test_load_scenarios_from_json() -> None:
    """Load 5 scenarios from the bundled JSON fixture."""
    scenarios = load_scenarios(SCENARIOS_FILE)
    assert len(scenarios) == 5
    assert scenarios[0].name == "Q235B-5mm-bracket"
    assert scenarios[0].expected_material == "Q235B"
    assert scenarios[0].expected_thickness == 5.0


def test_load_scenarios_missing_file(tmp_path) -> None:
    """Missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_scenarios(tmp_path / "nope.json")


def test_load_scenarios_invalid_json(tmp_path) -> None:
    """Non-list top-level raises ValueError."""
    bad = tmp_path / "bad.json"
    bad.write_text('{"not": "a list"}')
    with pytest.raises(ValueError, match="Expected list"):
        load_scenarios(bad)


def test_aggregate_computes_pass_rates() -> None:
    """Aggregate computes material/thickness/recall/precision correctly."""
    results = [
        PoCResult(
            scenario=f"r{i}",
            pdf_path="/tmp/x.pdf",
            duration_sec=1.0,
            reflection_iterations=3,
            final_status="needs_human",
            detected_material="Q235B",
            detected_thickness=5.0,
            detected_errors=[],
            detected_process_steps=2,
            rag_chunks_retrieved=0,
            material_match=True,
            thickness_match=True,
            error_recall=1.0,
            error_precision=1.0,
            process_steps_match=True,
        )
        for i in range(3)
    ]
    agg = aggregate(results)
    assert agg["scenarios_run"] == 3
    assert agg["material_pass_rate"] == 1.0
    assert agg["avg_error_recall"] == 1.0


def test_render_report_contains_key_metrics() -> None:
    """Markdown report includes aggregate metrics table and per-scenario table."""
    results = [
        PoCResult(
            scenario="test1",
            pdf_path="/tmp/x.pdf",
            duration_sec=2.5,
            reflection_iterations=3,
            final_status="needs_human",
            detected_material="Q235B",
            detected_thickness=5.0,
            detected_errors=[],
            detected_process_steps=2,
            rag_chunks_retrieved=3,
            material_match=True,
            thickness_match=True,
            error_recall=1.0,
            error_precision=1.0,
            process_steps_match=True,
        ),
    ]
    report = render_report(results)
    assert "# DeepDraw PoC Report" in report
    assert "Aggregate Metrics" in report
    assert "Per-Scenario Detail" in report
    assert "test1" in report
    assert "Avg duration" in report
