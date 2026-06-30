"""PoC mock data: 5 manuals + 10 drawing summaries (Phase 5)."""

from __future__ import annotations

from deepdraw.tools.ingest import get_default_embedding, ingest_drawing_summary, ingest_manual

MOCK_MANUALS: list[tuple[str, str, str]] = [
    (
        "laser_cutter_specs.md",
        "equipment",
        """# 激光切割机规格 (TRUMPF TruLaser 3030)

## 可加工材料
- 碳钢: 0.5-25mm
- 不锈钢: 0.5-20mm
- 铝: 0.5-12mm

## 刀具规格
- 标准喷嘴: Φ1.5mm (适合 3-6mm 板)
- 大喷嘴: Φ3.0mm (适合 8-25mm 板)
""",
    ),
    (
        "milling_machine_tools.md",
        "equipment",
        """# 铣床刀具规格 (DMG MORI NHX 5000)

## 标准立铣刀清单（仅 12mm 以下）
- Φ2, Φ3, Φ4, Φ6, Φ8, Φ10, Φ12
- 注：Φ16+ 不在库，需外购

## 表面粗糙度
- 标准: Ra 1.6 μm
- 精加工: Ra 0.8 μm
""",
    ),
    (
        "surface_treatment_handbook.md",
        "process",
        """# 表面处理手册

## 镀锌: 适用 Q235B/Q345B，不适用不锈钢
## 阳极氧化: 适用 AL6061/AL5052，不适用碳钢
## 喷塑: 板厚 ≥ 1mm，需除锈+磷化
""",
    ),
    (
        "bend_process_rules.md",
        "process",
        """# 折弯工艺规则

## 最小折弯内 R（按板厚）
- 1mm: R≥1.0mm / 3mm: R≥3.0mm / 5mm: R≥5.0mm / 10mm: R≥10mm

## 折弯回弹补偿
- 碳钢: +2°~5° / 不锈钢: +5°~8° / 铝: +1°~3°
""",
    ),
    (
        "batch_cost_table.md",
        "process",
        """# 批量-工艺成本（Q235B 5mm 激光切）

- 1-50 件: ¥80/件
- 50-500 件: ¥40/件
- 500+ 件: ¥20/件 → 推荐冲压

折弯: 不论批量 ¥15/件
""",
    ),
]

MOCK_DRAWINGS: list[tuple[str, str, list[str]]] = [
    ("BRACKET-001", "Q235B 5mm 折弯支架", ["laser_cut", "press_brake", "surface_treat"]),
    ("BRACKET-002", "Q235B 3mm 小折弯件", ["laser_cut", "press_brake"]),
    ("PLATE-100", "Q345B 10mm 钢板", ["laser_cut", "mill"]),
    ("HOUSING-200", "AL6061 阳极氧化壳体", ["mill", "surface_treat"]),
    ("FRAME-300", "Q235B 焊接框架", ["laser_cut", "press_brake", "weld", "surface_treat"]),
    ("COVER-400", "SS304 不锈钢盖板", ["laser_cut", "mill", "surface_treat"]),
    ("BRACKET-003", "Q235B 2mm 薄板", ["laser_cut", "press_brake"]),
    ("PLATE-101", "Q345B 6mm 加强板", ["laser_cut"]),
    ("HOUSING-201", "AL5052 壳体", ["mill", "surface_treat"]),
    ("FRAME-301", "Q235B 大件焊接", ["laser_cut", "weld", "surface_treat"]),
]


def seed_all() -> dict:
    """Ingest all PoC mock data. Returns {manuals_chunks: N, drawings: N}."""
    embedding_fn = get_default_embedding()
    manual_count = 0
    for name, category, content in MOCK_MANUALS:
        manual_count += ingest_manual(name, content, category, embedding_fn)
    drawing_count = 0
    for part_number, summary, plan in MOCK_DRAWINGS:
        ingest_drawing_summary(part_number, summary, plan, {"source": "mock_seed"}, embedding_fn)
        drawing_count += 1
    return {"manuals_chunks": manual_count, "drawings": drawing_count}
