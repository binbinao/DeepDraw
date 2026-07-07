"""PoC report generator: Markdown summary + per-scenario detail (Phase 7)."""

from __future__ import annotations

from deepdraw.tools.poc import PoCResult, aggregate


def render_report(results: list[PoCResult], title: str = "DeepDraw PoC Report") -> str:
    """Generate Markdown report."""
    agg = aggregate(results)
    lines = [
        f"# {title}",
        "",
        f"_Generated from {len(results)} scenarios._",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Scenarios run | {agg.get('scenarios_run', 0)} |",
        f"| Avg duration (sec) | {agg.get('avg_duration_sec', 0)} |",
        f"| Total duration (sec) | {agg.get('total_duration_sec', 0)} |",
        f"| Avg reflection iterations | {agg.get('avg_reflection_iterations', 0)} |",
        f"| Material pass rate | {agg.get('material_pass_rate', 0)} |",
        f"| Thickness pass rate | {agg.get('thickness_pass_rate', 0)} |",
        f"| Avg error recall | {agg.get('avg_error_recall', 0)} |",
        f"| Avg error precision | {agg.get('avg_error_precision', 0)} |",
        f"| Process steps pass rate | {agg.get('process_steps_pass_rate', 0)} |",
        "",
        "### Status Distribution",
        "",
    ]
    status_dist = agg.get("status_distribution", {})
    if status_dist:
        for status, count in status_dist.items():
            lines.append(f"- **{status}**: {count}")
    else:
        lines.append("- (no results)")

    lines += [
        "",
        "## Per-Scenario Detail",
        "",
        "| Scenario | Status | Duration (s) | Iter | Material | Thickness | Recall | Precision | Steps |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        mat = "✓" if r.material_match else "✗"
        thk = "✓" if r.thickness_match else "✗"
        lines.append(
            f"| {r.scenario} | {r.final_status} | {r.duration_sec} | "
            f"{r.reflection_iterations} | {mat} | {thk} | "
            f"{r.error_recall} | {r.error_precision} | {r.detected_process_steps} |"
        )

    lines += [
        "",
        "## PRD Phase 7 Key Metrics",
        "",
        "| Target | Required | Achieved |",
        "| --- | --- | --- |",
        f"| AI 审核覆盖率 | > 95% | {agg.get('avg_error_precision', 0) * 100:.1f}% |",
        f"| 相对漏检率降低 | > 50% | {agg.get('avg_error_recall', 0) * 100:.1f}% |",
        f"| BOM 准确率 | > 98% | {agg.get('material_pass_rate', 0) * 100:.1f}% |",
        f"| 端到端延迟 | < 300s | {agg.get('avg_duration_sec', 0)}s avg |",
        "",
        "_Note: AI coverage / recall metrics require API key + real drawings._",
        "",
    ]
    return "\n".join(lines)
