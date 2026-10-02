"""End-to-end PoC harness regression baseline.

Monkeypatches the 5 agent ``get_structured_llm`` factories so each scenario's
LLM returns the **ground truth** recorded in ``manifest.jsonl``. The graph
itself, the harness, and the aggregator are all real — only the chat-model
calls are stubbed.

Expected outcome on the 100 synthetic NG scenarios::

    scenarios_run             == 100
    material_pass_rate        == 1.0
    thickness_pass_rate       == 1.0
    process_steps_pass_rate   == 1.0
    avg_error_recall          == 1.0
    avg_error_precision       == 1.0
    final_status              success for every scenario

If this drifts, either the harness's metric math or the agent↔state
contracts broke. Fix the harness, not the agents.

Real NG drawings (and any harness whose provider can't speak OpenAI-compatible)
should: defer this module's logic until business-side unlock lands.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from deepdraw.agents.bom_generator import BOMItemLLM, BOMLLMResult
from deepdraw.agents.chief_verifier import VerificationNote, VerificationResult
from deepdraw.agents.drawing_auditor import DrawingErrorItem, DrawingErrorsResult
from deepdraw.agents.process_recommender import (
    ProcessPlanLLMResult,
    ProcessStepLLM,
)
from deepdraw.agents.spec_interpreter import SpecLLMResult
from deepdraw.tools.poc import (
    PoCScenario,
    aggregate,
    load_scenarios,
    run_poc,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
# Manifest lives at the repo root (fixtures/ng_drawings/), not under tests/.
REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "fixtures" / "ng_drawings" / "manifest.jsonl"


class _GroundTruthLLM:
    """Returns ground-truth payload, looked up by scenario name in the prompt.

    Each agent's spec_interpreter / drawing_auditor / etc. node passes
    either a string or a list-of-messages prompt. The graph sets
    ``drawing_path`` per scenario, so we resolve the scenario by reading
    the prompt's file path. Falls back to first manifest row if not found.
    """

    def __init__(
        self,
        agent_name: str,
        schema: type,
        payload_factory,
        ground_truth: dict[str, dict],
    ) -> None:
        self.agent_name = agent_name
        self.schema = schema
        self._payload_factory = payload_factory
        self._ground_truth = ground_truth

    async def ainvoke(self, prompt) -> object:
        # The drawing_path is in state, not prompt. Async nodes pass `state`
        # through prompt sometimes? No, agents only see prompt. Resolve
        # ground truth from the most recently-patched state — agent nodes
        # don't pass state to LLM, so we can't bind it here. Instead, the
        # caller (the e2e harness) sets the active scenario via _ActiveScenario.
        scenario = _ActiveScenario.current
        gt = self._ground_truth.get(scenario.name, {}) if scenario else {}
        return self._payload_factory(gt)


class _ActiveScenario:
    """Tracks the current scenario during run_scenario execution."""

    current: PoCScenario | None = None


def _spec_payload(gt: dict) -> SpecLLMResult:
    return SpecLLMResult(
        material=gt.get("expected_material"),
        thickness_mm=gt.get("expected_thickness"),
        batch_size=gt.get("expected_batch_size"),
        surface_treatment=gt.get("expected_surface_treatment"),
        raw_requirements={},
    )


def _auditor_payload(gt: dict) -> DrawingErrorsResult:
    errors = gt.get("expected_errors") or []
    items = [
        DrawingErrorItem(
            error_type=e["error_type"],
            location="synthetic",
            severity="major",
            description=f"synthetic ground truth: {e['error_type']}",
        )
        for e in errors
        if "error_type" in e
    ]
    return DrawingErrorsResult(errors=items)


def _bom_payload(gt: dict) -> BOMLLMResult:
    material = gt.get("expected_material") or "UNKNOWN"
    return BOMLLMResult(
        items=[
            BOMItemLLM(
                part_number=f"SYN-{gt.get('expected_thickness', 0):g}mm",
                name=material,
                quantity=1,
                unit="件",
            ),
        ]
    )


def _process_payload(gt: dict) -> ProcessPlanLLMResult:
    min_steps = max(int(gt.get("expected_process_steps_min") or 1), 1)
    steps = [
        ProcessStepLLM(
            sequence=i + 1,
            operation="laser_cut",
            machine="synthetic",
            tooling="synthetic",
            parameters={"step": i + 1},
        )
        for i in range(min_steps)
    ]
    return ProcessPlanLLMResult(steps=steps)


def _verifier_payload(gt: dict) -> VerificationResult:
    return VerificationResult(
        notes=[
            VerificationNote(
                severity="minor",
                category="material_compat",
                description=f"synthetic match: {gt.get('expected_material', '?')}",
                recommendation="none",
            ),
        ],
        status="success",
    )


@pytest.fixture
def ground_truth_lookup():
    """Index manifest.jsonl by scenario name."""
    manifest = MANIFEST.resolve()
    if not manifest.exists():
        pytest.skip(f"{manifest} not generated yet; run scripts/generate_ng_drawings.py")
    scenarios = load_scenarios(manifest)
    return {s.name: s.__dict__ for s in scenarios}


@pytest.fixture
def patch_agents(monkeypatch, ground_truth_lookup):
    """Replace every agent's get_structured_llm with a ground-truth LLM."""
    factories = {
        "spec_interpreter": _spec_payload,
        "drawing_auditor": _auditor_payload,
        "bom_generator": _bom_payload,
        "process_recommender": _process_payload,
        "chief_verifier": _verifier_payload,
    }
    payloads_by_agent = {name: [] for name in factories}

    def make_factory(agent_name: str):
        def factory(agent_arg: str, schema: type):
            fake = _GroundTruthLLM(
                agent_arg, schema, factories[agent_arg], ground_truth_lookup
            )
            payloads_by_agent[agent_arg].append(fake)
            return fake

        return factory

    for agent_name in factories:
        monkeypatch.setattr(
            f"deepdraw.agents.{agent_name}.get_structured_llm", make_factory(agent_name)
        )

    return {
        "factories": factories,
        "payloads_by_agent": payloads_by_agent,
    }


@pytest.mark.asyncio
async def test_e2e_100_scenarios_hit_full_pass(monkeypatch, patch_agents) -> None:
    """Ground-truth LLMs drive all 100 scenarios to 100% pass rate."""
    scenarios = load_scenarios(MANIFEST.resolve())
    assert len(scenarios) == 100, "manifest must contain exactly 100 scenarios"

    # Wrap run_scenario so each scenario is marked active during execution.
    from deepdraw.tools import poc as poc_mod

    original_run_scenario = poc_mod.run_scenario

    async def tracked(scenario: PoCScenario):
        _ActiveScenario.current = scenario
        try:
            return await original_run_scenario(scenario)
        finally:
            _ActiveScenario.current = None

    monkeypatch.setattr(poc_mod, "run_scenario", tracked)

    results = await run_poc(scenarios)
    agg = aggregate(results)

    assert agg["scenarios_run"] == 100
    assert agg["material_pass_rate"] == 1.0, agg
    assert agg["thickness_pass_rate"] == 1.0, agg
    assert agg["process_steps_pass_rate"] == 1.0, agg
    assert agg["avg_error_recall"] == 1.0, agg
    assert agg["avg_error_precision"] == 1.0, agg

    # Every scenario's reflection loop converged to status=success on the
    # first iteration (verifier returned success → END immediately).
    success = [r for r in results if r.final_status == "success"]
    assert len(success) == 100, f"only {len(success)}/100 reached success"


@pytest.mark.asyncio
async def test_e2e_partial_ground_truth_drops_recall(
    monkeypatch, patch_agents, ground_truth_lookup
) -> None:
    """Sanity: mutating one scenario's expected_errors is a precision-walker.
    Recall drops proportionally; other 99 scenarios still hit 100%.
    """
    scenarios = load_scenarios(MANIFEST.resolve())
    # Pick scenario #0 and add a phantom expected error.
    target = scenarios[0]
    target.expected_errors = [
        {"error_type": "missing_dimension"},
        {"error_type": "tolerance_conflict"},  # synthetic extra
    ]

    from deepdraw.tools import poc as poc_mod

    original_run_scenario = poc_mod.run_scenario

    async def tracked(scenario: PoCScenario):
        _ActiveScenario.current = scenario
        try:
            return await original_run_scenario(scenario)
        finally:
            _ActiveScenario.current = None

    monkeypatch.setattr(poc_mod, "run_scenario", tracked)

    results = await run_poc(scenarios)
    agg = aggregate(results)

    # 99 scenarios hit recall=1.0; the mutated one hits recall=0.5
    # (intersection = {missing_dimension}; expected = 2).
    expected_recall = (99 * 1.0 + 0.5) / 100
    assert agg["avg_error_recall"] == pytest.approx(expected_recall, abs=1e-3)


def test_ground_truth_lookup_indexes_correctly(ground_truth_lookup) -> None:
    """The lookup fixture covers every scenario in the manifest."""
    scenarios = load_scenarios(MANIFEST.resolve())
    assert len(ground_truth_lookup) == len(scenarios) == 100
    # Spot-check one entry
    s = scenarios[0]
    gt = ground_truth_lookup[s.name]
    assert gt["expected_material"] == s.expected_material
    assert gt["expected_thickness"] == s.expected_thickness
