# PoC Validation Runbook

> Operational guide for `deepdraw poc run|report|validate` and the 100 NG scenario generator.

## Purpose

The PoC harness replays a curated set of drawings through the full 5-agent
pipeline and reports metrics against ground-truth annotations. It serves two
distinct audiences:

- **Algorithm engineers** wiring up new LLM providers or RAG corpora who need
  fast feedback on whether changes moved the metrics.
- **Solution engineers** onboarding a customer factory who need to swap
  synthetic data for real historical NG drawings without writing code.

The current dataset is **100 synthetic** drawings generated from a Cartesian
product (5 materials × 4 thicknesses × 5 defect categories). Real NG
drawings slot in by replacing `fixtures/ng_drawings/manifest.jsonl`.

## Quick start

```bash
source .venv/bin/activate

# 1. (Re)generate the 100 NG PDFs + manifest if absent
python scripts/generate_ng_drawings.py

# 2. Run the harness; print aggregate + per-scenario table
deepdraw poc run --scenarios fixtures/ng_drawings/manifest.jsonl

# 3. Run + write a Markdown report for sharing
deepdraw poc report --scenarios fixtures/ng_drawings/manifest.jsonl \
                    --output poc-validation.md

# 4. Strict mode — refuses scenarios missing ground truth; exits 2 on failure
deepdraw poc validate --scenarios fixtures/ng_drawings/manifest.jsonl \
                      --output poc-validation.md
```

All three subcommands share the same runner; the differences are:

| Subcommand | Behavior |
|---|---|
| `poc run` | Print aggregate + per-scenario tables to stdout |
| `poc report` | Same as `run` + write a Markdown file (default `poc-report.md`) |
| `poc validate` | Same as `report` + reject scenarios missing any ground-truth field (exit 2) |

## Manifest schema

Scenarios can be **JSON list** (`.json`) or **JSON Lines** (`.jsonl`,
`.ndjson`). jsonl is recommended because real-world data engineering almost
always appends one record at a time.

```jsonl
{"name": "Q235B-5mm-missing-dim-001", "pdf_path": "fixtures/.../Q235B-5mm-missing-dim-001.pdf", "expected_material": "Q235B", "expected_thickness": 5.0, "expected_surface_treatment": "喷塑", "expected_batch_size": 100, "expected_errors": [{"error_type": "missing_dimension"}], "expected_process_steps_min": 2}
```

Field reference:

| Field | Type | Required for `poc validate` | Meaning |
|---|---|---|---|
| `name` | string | yes | Stable identifier; appears in report + thread_id |
| `pdf_path` | string | yes | Absolute or repo-relative path; must exist |
| `expected_material` | string \| null | yes | Ground-truth material code |
| `expected_thickness` | float \| null | yes | Plate thickness in mm |
| `expected_surface_treatment` | string \| null | no | "喷塑" / "镀锌" / "阳极氧化" / ... |
| `expected_batch_size` | int \| null | no | Production batch count |
| `expected_errors` | list[dict] | yes (must be non-empty) | Each entry needs `error_type` ∈ `missing_dimension` / `view_inconsistency` / `tolerance_conflict` / `unmanufacturable_feature` / `ambiguous_datum` |
| `expected_process_steps_min` | int | yes (must be > 0) | Lower bound on detected process steps |

The `poc validate` rejection rule is intentionally strict: any missing
required field produces a human-readable problem list and `exit_code=2`, so
CI can fail fast on incomplete ground truth rather than silently
report 0% pass rate.

## Generator

`scripts/generate_ng_drawings.py` produces 100 PDFs (or fewer, via
`--count`). The Cartesian product is currently:

- **5 materials**: `Q235B`, `Q345B`, `AL6061`, `SS304`, `DC01`
- **4 thicknesses**: `3.0`, `5.0`, `8.0`, `10.0` mm
- **5 defect categories** (one per PDF): `missing_dimension`,
  `view_inconsistency`, `tolerance_conflict`, `unmanufacturable_feature`,
  `ambiguous_datum`

Each PDF contains:

1. A title block with `材料 / 厚度 / 批量 / 表面处理` fields readable by
   `pdfplumber` so Spec Interpreter has structured text to extract.
2. A defect signal under `技术要求` so the downstream pipeline has a known
   defect type for recall/precision measurement.
3. Stable SHA-1 hash suffix so re-runs produce byte-identical PDFs (handy
   for diffing downstream extraction).

Flags:

```bash
python scripts/generate_ng_drawings.py \
    --output-dir fixtures/ng_drawings \  # default
    --count 100                          # default; max 100 (5×4×5)
```

Generator is **idempotent**: re-running overwrites existing files. The
PDFs are gitignored (`.gitignore`); the `manifest.jsonl` is committed.

## Reading the report

`render_report()` produces three Markdown sections:

### Aggregate Metrics

| Metric | Definition |
|---|---|
| `scenarios_run` | Count |
| `avg_duration_sec` | Wall time per scenario (excludes inter-scenario overhead) |
| `total_duration_sec` | Wall time total |
| `avg_reflection_iterations` | Mean chief_verifier loop count (caps at 3) |
| `material_pass_rate` | % scenarios where detected material == expected |
| `thickness_pass_rate` | % scenarios where |detected − expected| < 0.1 mm |
| `avg_error_recall` | Mean recall across scenarios (intersection / expected) |
| `avg_error_precision` | Mean precision (intersection / detected) |
| `process_steps_pass_rate` | % scenarios where detected process steps ≥ min |

### Status Distribution

Counts per `final_status` value:
`success` (chief_verifier satisfied), `needs_human` (LLM unreachable or
verifier unsure), `conflict` (verifier explicitly contradicted recommender),
`pipeline_failure` (graph exception caught by harness).

### Per-Scenario Detail

One row per scenario with material/thickness match symbols (✓/✗), recall,
precision, and detected step count.

### PRD Phase 7 Key Metrics

Maps aggregate numbers onto the PRD success metrics:

| PRD metric | Source |
|---|---|
| AI 审核覆盖率 > 95% | `avg_error_precision * 100` |
| 相对漏检率降低 > 50% | `avg_error_recall * 100` |
| BOM 准确率 > 98% | `material_pass_rate * 100` |
| 端到端延迟 < 300s | `avg_duration_sec` |

These are upper-bound proxies for what the real PRD metrics will be. They
become meaningful once we plug in real NG drawings with real annotations
from prior human review.

## Real-data workflow

To replace the synthetic dataset with real historical NG drawings:

1. **Collect drawings + annotations.** For each drawing:
   - PDF/DXF file (use the customer's own scanner or PDF export).
   - One record per drawing, schema-compatible with `manifest.jsonl`.
2. **Decide on `expected_errors`.** Two sources:
   - **Original human reviewer notes** — translate their free-text comments
     into the `error_type` enum (start with `missing_dimension` /
     `unmanufacturable_feature` since these are most common in our
     historical samples).
   - **Re-review** by a trusted engineer. Use as ground truth for ambiguous
     cases.
3. **QA the manifest** with `poc validate` first; it will exit 2 on any
   record missing required fields.
4. **Version the manifest.** Real-data manifests are usually updated every
   review cycle; commit each cycle as a new file under
   `fixtures/ng_drawings/<customer>_<cycle>.jsonl` so experiments are
   reproducible.
5. **Smoke first**: run 5 records, eyeball the report, then scale up.
   100 records at ~1.7s each = ~3 minutes; budget accordingly.

### Open questions (deferred to business)

- Permission/owner authentication for the source drawings (图纸涉密).
- Whether to redact `<>` pattern image text or keep verbatim.
- How to encode "the human reviewer missed this" vs "the human reviewer
  flagged this" as ground truth — affects whether recall measures model
  misses or model new-finds.

## Troubleshooting

### All scenarios show pass_rate = 0.0

Expected if you don't have API keys set. The pipeline gracefully degrades
to `needs_human` rather than crashing. Plug in keys:

```bash
export OPENAI_API_KEY=sk-...           # for spec/auditor/bom/process
export ANTHROPIC_API_KEY=sk-ant-...    # for chief_verifier
# OR a third-party OpenAI-compatible provider:
export OPENAI_COMPAT_BASE_URL=https://api.deepseek.com
export OPENAI_COMPAT_API_KEY=sk-...
export DEEPDRAW_LLM_DEFAULT=openai_compat
```

See [AGENTS.md § Runtime/Tooling Preferences](../AGENTS.md) and
`.env.example` for the full env surface.

### `PdfminerException: No /Root object!` on first scenario

Means the manifest points at a 0-byte PDF. Re-run
`python scripts/generate_ng_drawings.py` to regenerate, or check that the
PDFs were not corrupted by `git lfs` or partial transfers.

### `Failed to send telemetry event ... capture() takes 1 positional argument`

Benign. ChromaDB 1.x vs langchain-core 2.x posthocutogateway has a known
mismatch. Telemetry is off by default. Add to `.gitignore`-style suppression
later if it becomes noisy in CI logs.

### `poc validate` exits 2 immediately

One or more scenarios in the manifest are missing required fields. Run
`poc run` (which doesn't validate) and inspect the output:
`expected_errors is empty` is the most common cause when first adding
real drawings.

### Tests pass locally but CI fails on `tests/test_poc.py`

The `test_generates_100_pdfs_and_manifest` test invokes
`scripts/generate_ng_drawings.py` via `subprocess`. If your CI's
`python` doesn't resolve to one that has the dev extra installed
(`uv pip install -e '.[dev]'`), the test will fail with `ModuleNotFoundError`.
Pre-install on CI runners.

## Where this lives

```
scripts/generate_ng_drawings.py          # generator
fixtures/ng_drawings/manifest.jsonl      # 100 ground-truth records (committed)
fixtures/ng_drawings/*.pdf               # 100 PDFs (gitignored; regenerated)
tests/test_poc.py                        # 19 harness + CLI tests
src/deepdraw/tools/poc.py                # harness core (load_scenarios, run_scenario, aggregate, run_poc)
src/deepdraw/tools/poc_report.py         # Markdown renderer
src/deepdraw/cli.py                      # `deepdraw poc` sub-app
.claude/PRPs/reports/poc-validation-harness-report.md  # Phase 7 completion report
```

## Next steps

- [ ] Business-side unlock: real NG drawings + reviewer notes
- [ ] Plug into a real model provider; rerun for genuine PRD metrics
- [ ] Track `docs/poc-runbook.md` changes in the same PR as any harness
      schema change