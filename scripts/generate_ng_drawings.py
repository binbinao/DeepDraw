"""Generate 100 synthetic NG drawings + a manifest.jsonl with ground truth.

Used by Phase 7 PoC validation. Each PDF contains:

- A title-block pdfplumber can extract (so Spec Interpreter breaks ground truth).
- A short body with one of five defect categories from DrawingAuditor's
  DrawingErrorItem.error_type enum.

The Cartesian product (5 materials × 4 thicknesses × 5 defect categories)
yields exactly 100 PDFs.

Run::

    python scripts/generate_ng_drawings.py                 # default: ./fixtures/ng_drawings/
    python scripts/generate_ng_drawings.py --output-dir /tmp/ng
    python scripts/generate_ng_drawings.py --count 100    # override (default 100)

The manifest can be fed straight into ``deepdraw poc run|report|validate``::

    deepdraw poc validate --scenarios fixtures/ng_drawings/manifest.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pymupdf

# ---------------------------------------------------------------------------
# Catalog: 5 × 4 × 5 = 100
# ---------------------------------------------------------------------------

MATERIALS = ["Q235B", "Q345B", "AL6061", "SS304", "DC01"]
THICKNESSES_MM = [3.0, 5.0, 8.0, 10.0]
SURFACE_TREATMENTS = ["喷塑", "镀锌", "阳极氧化", "喷漆", "本色"]
BATCH_SIZES = [50, 100, 200, 500]

DEFECT_CATEGORIES = [
    "missing_dimension",
    "view_inconsistency",
    "tolerance_conflict",
    "unmanufacturable_feature",
    "ambiguous_datum",
]

DEFECT_PROMPTS = {
    "missing_dimension": "孔径 Ø10 缺尺寸标注",
    "view_inconsistency": "主视图与左视图孔位不一致",
    "tolerance_conflict": "Ø10 H7 与 Ø10 h7 同时标注，基准冲突",
    "unmanufacturable_feature": "内圆角 R0.2 超出本厂最小折弯半径极限",
    "ambiguous_datum": "基准 A 同时指向两条边，定位模糊",
}


@dataclass(frozen=True)
class ScenarioSpec:
    """One generated scenario's parameters + deterministic id."""

    name: str
    material: str
    thickness_mm: float
    surface_treatment: str
    batch_size: int
    defect_category: str
    defect_prompt: str


def _build_scenarios() -> list[ScenarioSpec]:
    """Build the 100-drawing Cartesian product deterministically."""
    scenarios: list[ScenarioSpec] = []
    for mat_idx, material in enumerate(MATERIALS):
        for thk_idx, thickness in enumerate(THICKNESSES_MM):
            for def_idx, defect in enumerate(DEFECT_CATEGORIES):
                surface = SURFACE_TREATMENTS[(mat_idx + thk_idx) % len(SURFACE_TREATMENTS)]
                batch = BATCH_SIZES[(mat_idx + def_idx) % len(BATCH_SIZES)]
                name = (
                    f"{material}-{int(thickness)}mm-"
                    f"{defect}-{mat_idx:02d}{thk_idx:02d}{def_idx:02d}"
                )
                scenarios.append(
                    ScenarioSpec(
                        name=name,
                        material=material,
                        thickness_mm=thickness,
                        surface_treatment=surface,
                        batch_size=batch,
                        defect_category=defect,
                        defect_prompt=DEFECT_PROMPTS[defect],
                    )
                )
    return scenarios


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------


def _pdf_content(spec: ScenarioSpec) -> bytes:
    """Build a single-page A4 PDF whose text pdfplumber can extract."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4 portrait

    # Title
    page.insert_text((50, 60), "DeepDraw NG Synthetic Drawing", fontsize=14)

    # Title block (machine-readable format pdfplumber picks up cleanly)
    title_block = [
        "图号:" + spec.name,
        "材料:" + spec.material,
        "厚度:" + f"{spec.thickness_mm:g}mm",
        "批量:" + f"{spec.batch_size}",
        "表面处理:" + spec.surface_treatment,
    ]
    y = 100
    for line in title_block:
        page.insert_text((50, y), line, fontsize=11)
        y += 18

    # Notes section — embeds the defect signal
    y += 10
    page.insert_text((50, y), "技术要求 / 缺陷标注:", fontsize=11)
    y += 18
    page.insert_text(
        (50, y),
        f"缺陷类型:{spec.defect_category}",
        fontsize=11,
    )
    y += 18
    page.insert_text(
        (50, y),
        f"缺陷描述:{spec.defect_prompt}",
        fontsize=11,
    )

    # Placeholder geometry so the page isn't blank
    page.draw_rect((40, 30, 555, 812))

    # Stable hash so repeated runs produce byte-identical PDFs
    body = doc.tobytes()
    doc.close()
    h = hashlib.sha1(body).hexdigest()[:8]
    return body + f"% hash:{h}\n".encode()


# ---------------------------------------------------------------------------
# Manifest writer
# ---------------------------------------------------------------------------


def _expected_process_steps_min(material: str) -> int:
    """Heuristic floor for process steps by material category."""
    if material in {"Q235B", "Q345B", "DC01"}:
        return 2  # sheet metal: cut + bend at minimum
    if material in {"AL6061"}:
        return 3  # aluminum often needs anodize
    return 2  # stainless default


def _manifest_record(spec: ScenarioSpec, pdf_path: Path) -> dict:
    return {
        "name": spec.name,
        "pdf_path": str(pdf_path),
        "expected_material": spec.material,
        "expected_thickness": spec.thickness_mm,
        "expected_surface_treatment": spec.surface_treatment,
        "expected_batch_size": spec.batch_size,
        "expected_errors": [{"error_type": spec.defect_category}],
        "expected_process_steps_min": _expected_process_steps_min(spec.material),
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("fixtures/ng_drawings"),
        help="Where to write the 100 PDFs + manifest.jsonl (default: ./fixtures/ng_drawings)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="How many PDFs to generate (default 100; max 100 because catalog is fixed)",
    )
    args = parser.parse_args(argv)
    if args.count < 1 or args.count > 100:
        parser.error("--count must be in [1, 100]")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    scenarios = _build_scenarios()[: args.count]

    manifest_path = args.output_dir / "manifest.jsonl"
    written = 0
    with manifest_path.open("w", encoding="utf-8") as manifest:
        for spec in scenarios:
            pdf_path = args.output_dir / f"{spec.name}.pdf"
            pdf_path.write_bytes(_pdf_content(spec))
            manifest.write(json.dumps(_manifest_record(spec, pdf_path), ensure_ascii=False) + "\n")
            written += 1

    print(f"[green]✓[/green] Generated {written} PDF(s) + manifest at {args.output_dir}")
    print(
        f"  → run: deepdraw poc validate --scenarios {manifest_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
