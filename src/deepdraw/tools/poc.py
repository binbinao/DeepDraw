"""PoC validation harness (Phase 7)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from deepdraw.graph import graph


@dataclass
class PoCScenario:
    """Single test scenario with ground truth annotations."""

    name: str
    pdf_path: str
    expected_material: str | None = None
    expected_thickness: float | None = None
    expected_surface_treatment: str | None = None
    expected_batch_size: int | None = None
    expected_errors: list[dict] = field(default_factory=list)
    expected_process_steps_min: int = 0


@dataclass
class PoCResult:
    """Result of running one scenario through the pipeline."""

    scenario: str
    pdf_path: str
    duration_sec: float
    reflection_iterations: int
    final_status: str
    detected_material: str | None
    detected_thickness: float | None
    detected_errors: list[dict]
    detected_process_steps: int
    rag_chunks_retrieved: int
    material_match: bool = False
    thickness_match: bool = False
    error_recall: float = 0.0
    error_precision: float = 0.0
    process_steps_match: bool = False


def load_scenarios(json_path: str | Path) -> list[PoCScenario]:
    """Load scenarios from JSON or JSONL file.

    Format is selected by file suffix:

    - ``.jsonl`` / ``.ndjson``: one scenario per line, ``#`` comments skipped,
      blank lines ignored. Easier to grow incrementally (each line is its own
      record, no array bracket framing).
    - ``.json``: a top-level JSON list. The ``Expected list`` ValueError
      contract is preserved for non-list top-level values.

    Both formats must already be valid for downstream schema validation
    (``PoCScenario(**item)``), which surfaces field-shape problems.
    """
    p = Path(json_path)
    if not p.exists():
        raise FileNotFoundError(p)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".jsonl", ".ndjson"}:
        records: list[dict] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            records.append(json.loads(stripped))
        return [PoCScenario(**item) for item in records]
    raw = json.loads(text)
    if not isinstance(raw, list):
        raise ValueError(f"Expected list of scenarios, got {type(raw).__name__}")
    return [PoCScenario(**item) for item in raw]


async def run_scenario(scenario: PoCScenario) -> PoCResult:
    """Run one scenario through the pipeline; collect metrics.

    Failures inside the graph (missing PDF, LLM error, parser crash) are
    caught and recorded as a ``needs_human`` ``PoCResult`` so one broken
    scenario can't poison the entire batch. The error message is surfaced
    via ``detected_errors`` with ``error_type="pipeline_failure"`` so the
    Markdown report makes the failure obvious.
    """
    pdf = Path(scenario.pdf_path)
    initial_state = {"drawing_path": str(pdf.absolute())}
    config = {"configurable": {"thread_id": f"poc:{scenario.name}"}}

    start = time.perf_counter()
    try:
        final = await graph.ainvoke(initial_state, config=config)
    except Exception as exc:  # graph retries already exhausted
        duration = time.perf_counter() - start
        return PoCResult(
            scenario=scenario.name,
            pdf_path=scenario.pdf_path,
            duration_sec=round(duration, 2),
            reflection_iterations=0,
            final_status="pipeline_failure",
            detected_material=None,
            detected_thickness=None,
            detected_errors=[
                {"error_type": "pipeline_failure", "message": str(exc)},
            ],
            detected_process_steps=0,
            rag_chunks_retrieved=0,
            material_match=False,
            thickness_match=False,
            error_recall=0.0,
            error_precision=0.0,
            process_steps_match=False,
        )
    duration = time.perf_counter() - start

    spec = final.get("spec", {}) or {}
    detected_errors = final.get("errors", []) or []
    process_plan = final.get("process_plan", []) or []
    rag = final.get("rag_context", []) or []

    material_match = (
        spec.get("material") == scenario.expected_material if scenario.expected_material else True
    )
    thickness_match = (
        abs((spec.get("thickness_mm") or 0) - scenario.expected_thickness) < 0.1
        if scenario.expected_thickness
        else True
    )

    expected_error_types = {e.get("error_type") for e in scenario.expected_errors}
    detected_error_types = {e.get("error_type") for e in detected_errors}
    if expected_error_types:
        intersection = expected_error_types & detected_error_types
        recall = len(intersection) / len(expected_error_types)
        precision = (
            len(intersection) / len(detected_error_types) if detected_error_types else 1.0
        )
    else:
        recall = 1.0
        precision = 1.0 if not detected_errors else 0.0

    return PoCResult(
        scenario=scenario.name,
        pdf_path=scenario.pdf_path,
        duration_sec=round(duration, 2),
        reflection_iterations=final.get("reflection_iterations", 0),
        final_status=final.get("status", "unknown"),
        detected_material=spec.get("material"),
        detected_thickness=spec.get("thickness_mm"),
        detected_errors=detected_errors,
        detected_process_steps=len(process_plan),
        rag_chunks_retrieved=len(rag),
        material_match=material_match,
        thickness_match=thickness_match,
        error_recall=round(recall, 3),
        error_precision=round(precision, 3),
        process_steps_match=len(process_plan) >= scenario.expected_process_steps_min,
    )


def aggregate(results: list[PoCResult]) -> dict:
    """Compute aggregate stats."""
    if not results:
        return {}
    n = len(results)
    return {
        "scenarios_run": n,
        "avg_duration_sec": round(sum(r.duration_sec for r in results) / n, 2),
        "total_duration_sec": round(sum(r.duration_sec for r in results), 2),
        "material_pass_rate": round(sum(r.material_match for r in results) / n, 3),
        "thickness_pass_rate": round(sum(r.thickness_match for r in results) / n, 3),
        "avg_error_recall": round(sum(r.error_recall for r in results) / n, 3),
        "avg_error_precision": round(sum(r.error_precision for r in results) / n, 3),
        "process_steps_pass_rate": round(sum(r.process_steps_match for r in results) / n, 3),
        "avg_reflection_iterations": round(sum(r.reflection_iterations for r in results) / n, 1),
        "status_distribution": dict(_status_dist(results)),
    }


def _status_dist(results: list[PoCResult]) -> Any:
    from collections import Counter

    return Counter(r.final_status for r in results).items()


async def run_poc(scenarios: list[PoCScenario]) -> list[PoCResult]:
    """Run all scenarios sequentially."""
    return [await run_scenario(s) for s in scenarios]  # sequential; Phase 7.5 adds concurrency
