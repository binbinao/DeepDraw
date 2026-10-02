"""Tests for Phase 7 PoC harness."""

from __future__ import annotations

from pathlib import Path

import pytest

from deepdraw.tools.poc import (
    PoCResult,
    PoCScenario,
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


# ---------------------------------------------------------------------------
# run_scenario failure containment (Phase 7 PoC harness fix)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_scenario_records_pipeline_failure_without_crashing(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """A graph crash must surface as a needs_human / pipeline_failure
    PoCResult, not propagate out of run_scenario and poison the batch."""
    from deepdraw.tools import poc as poc_mod

    async def boom(initial_state, config=None):  # noqa: ARG001
        raise RuntimeError("simulated graph crash")

    monkeypatch.setattr(poc_mod, "graph", type("G", (), {"ainvoke": staticmethod(boom)})())

    scenario = PoCScenario(
        name="crashy",
        pdf_path=str(tmp_path / "missing.pdf"),
        expected_material="Q235B",
        expected_thickness=5.0,
        expected_errors=[],
        expected_process_steps_min=1,
    )
    result = await poc_mod.run_scenario(scenario)
    assert result.final_status == "pipeline_failure"
    assert result.detected_errors and result.detected_errors[0]["error_type"] == "pipeline_failure"
    assert "simulated graph crash" in result.detected_errors[0]["message"]


@pytest.mark.asyncio
async def test_run_scenario_does_not_touch_missing_pdf(monkeypatch, tmp_path):
    """AI-cli calls with phantom PDF paths must NOT auto-create 0-byte files
    (would trigger 'No /Root object!' from pdfplumber)."""
    from deepdraw.tools import poc as poc_mod

    captured = {}

    async def capture_invoke(initial_state, config=None):
        captured["state"] = initial_state
        return {"spec": {}, "errors": [], "process_plan": [], "status": "needs_human"}

    monkeypatch.setattr(poc_mod, "graph", type("G", (), {"ainvoke": staticmethod(capture_invoke)})())

    phantom = tmp_path / "missing.pdf"
    scenario = PoCScenario(
        name="phantom",
        pdf_path=str(phantom),
        expected_material=None,
        expected_thickness=None,
        expected_errors=[],
        expected_process_steps_min=0,
    )
    await poc_mod.run_scenario(scenario)
    assert phantom.exists() is False, "phantom.pdf must not be auto-created"
    assert captured["state"]["drawing_path"] == str(phantom)


# ---------------------------------------------------------------------------
# CLI surface (Phase 7 deepdraw poc subcommands)
# ---------------------------------------------------------------------------


class TestCliPocSubcommands:
    """Typer sub-app surface for `deepdraw poc run|report|validate`."""

    def test_poc_run_prints_aggregate_and_table(self, monkeypatch, tmp_path) -> None:
        from typer.testing import CliRunner

        from deepdraw.cli import app
        from deepdraw.tools import poc as poc_mod

        async def fake_run(scenarios):
            return [
                poc_mod.PoCResult(
                    scenario=s.name,
                    pdf_path=s.pdf_path,
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
                for s in scenarios
            ]

        monkeypatch.setattr(poc_mod, "run_poc", fake_run)
        runner = CliRunner()
        result = runner.invoke(
            app, ["poc", "run", "--scenarios", str(SCENARIOS_FILE)]
        )
        assert result.exit_code == 0
        out = result.output
        assert "Aggregate Metrics" in out
        assert "Per-Scenario Detail" in out
        assert "scenarios_run" in out

    def test_poc_report_writes_markdown(self, monkeypatch, tmp_path) -> None:
        from typer.testing import CliRunner

        from deepdraw.cli import app
        from deepdraw.tools import poc as poc_mod

        async def fake_run(scenarios):
            return [
                poc_mod.PoCResult(
                    scenario=s.name,
                    pdf_path=s.pdf_path,
                    duration_sec=1.0,
                    reflection_iterations=2,
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
                for s in scenarios
            ]

        monkeypatch.setattr(poc_mod, "run_poc", fake_run)
        out_file = tmp_path / "r.md"
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["poc", "report", "--scenarios", str(SCENARIOS_FILE), "--output", str(out_file)],
        )
        assert result.exit_code == 0
        assert out_file.exists()
        text = out_file.read_text()
        assert "# DeepDraw PoC Report" in text
        assert "Per-Scenario Detail" in text

    def test_poc_validate_rejects_incomplete_scenarios(self, tmp_path) -> None:
        from typer.testing import CliRunner

        from deepdraw.cli import app

        bad = tmp_path / "incomplete.json"
        bad.write_text(
            '[{"name":"x","pdf_path":"/tmp/x.pdf",'
            '"expected_material":null,"expected_thickness":null,'
            '"expected_errors":[],"expected_process_steps_min":0}]'
        )
        runner = CliRunner()
        result = runner.invoke(app, ["poc", "validate", "--scenarios", str(bad)])
        assert result.exit_code == 2  # typer.Exit(code=2)
        assert "ground-truth coverage" in result.output
        assert "expected_material" in result.output

    def test_poc_validate_passes_when_complete(self, monkeypatch, tmp_path) -> None:
        from typer.testing import CliRunner

        from deepdraw.cli import app
        from deepdraw.tools import poc as poc_mod

        async def fake_run(scenarios):
            return [
                poc_mod.PoCResult(
                    scenario=s.name,
                    pdf_path=s.pdf_path,
                    duration_sec=1.0,
                    reflection_iterations=3,
                    final_status="success",
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
                for s in scenarios
            ]

        monkeypatch.setattr(poc_mod, "run_poc", fake_run)
        good = tmp_path / "complete.json"
        good.write_text(
            '[{"name":"x","pdf_path":"/tmp/x.pdf",'
            '"expected_material":"Q235B","expected_thickness":5.0,'
            '"expected_errors":[{"error_type":"missing_dimension"}],'
            '"expected_process_steps_min":1}]'
        )
        out_file = tmp_path / "v.md"
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["poc", "validate", "--scenarios", str(good), "--output", str(out_file)],
        )
        assert result.exit_code == 0
        assert "have full ground truth" in result.output
        assert out_file.exists()
