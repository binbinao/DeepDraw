"""DeepDraw CLI — entry point for `deepdraw <drawing.pdf>` and `python -m deepdraw`."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.json import JSON
from rich.table import Table

from deepdraw.graph import graph
from deepdraw.tools.poc import (
    PoCScenario,
    aggregate,
    load_scenarios,
    run_poc,
)
from deepdraw.tools.poc_report import render_report

app = typer.Typer(help="DeepDraw — DFM-Copilot Squad CLI")
console = Console()

# Sub-app for PoC validation harness (Phase 7).
poc_app = typer.Typer(help="Phase 7 PoC validation harness", no_args_is_help=True)
app.add_typer(poc_app, name="poc")


@app.command()
def run(
    drawing: Path = typer.Argument(  # noqa: B008
        ...,
        help="Path to PDF/DXF drawing file",
        exists=True,
    ),
    thread_id: str = typer.Option("default", help="LangGraph thread ID for checkpointing"),
    output: Path | None = typer.Option(  # noqa: B008
        None,
        help="Optional output JSON file",
    ),
) -> None:
    """Run the 5-Agent DFM-Copilot workflow on a single drawing."""
    initial_state = {"drawing_path": str(drawing.absolute())}
    config = {"configurable": {"thread_id": thread_id}}
    console.print(f"[bold green]▶ DeepDraw:[/bold green] processing {drawing}")
    final_state = asyncio.run(graph.ainvoke(initial_state, config=config))

    intermediate = final_state.get("intermediate") or {}
    report = {
        "spec": final_state.get("spec", {}),
        "intermediate": {
            "file_type": intermediate.get("file_type"),
            "text_block_count": len(intermediate.get("text_blocks", [])),
            "image_count": len(intermediate.get("images_b64", [])),
            "entity_count": len(intermediate.get("entities", [])),
            "parsed_path": intermediate.get("parsed_path"),
        },
        "errors": final_state.get("errors", []),
        "bom": final_state.get("bom", []),
        "process_plan": final_state.get("process_plan", []),
        "verification_notes": final_state.get("verification_notes", []),
        "reflection_iterations": final_state.get("reflection_iterations", 0),
        "status": final_state.get("status", "unknown"),
        "rag_context_chunks": len(final_state.get("rag_context", [])),
    }

    if output:
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        console.print(f"[green]✓[/green] Report written to {output}")
    else:
        console.print(JSON(json.dumps(report, indent=2, ensure_ascii=False)))


@app.command()
def index() -> None:
    """Ingest PoC mock manuals + historical drawings into ChromaDB."""
    from deepdraw.tools.seed import seed_all

    console.print("[bold blue]▶ Indexing PoC data...[/bold blue]")
    result = seed_all()
    console.print(f"[green]✓[/green] Seeded: {result}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    n: int = typer.Option(3, help="Number of results"),
) -> None:
    """Search the enterprise_manuals ChromaDB collection."""
    from deepdraw.tools.rag import (
        COLLECTION_MANUALS,
        format_results,
        get_client,
        get_or_create_collection,
        query,
    )

    client = get_client(persist=True)
    coll = get_or_create_collection(client, COLLECTION_MANUALS)
    results = query(coll, query, n_results=n)
    if not results:
        console.print("[yellow]No results. Run `deepdraw index` first.[/yellow]")
        return
    console.print(f"[bold]Found {len(results)} chunks:[/bold]\n")
    console.print(format_results(results))


@app.command()
def wipe() -> None:
    """Wipe the ChromaDB persistence directory (irreversible)."""
    import shutil

    from deepdraw.tools.rag import PERSIST_DIR

    if PERSIST_DIR.exists():
        shutil.rmtree(PERSIST_DIR)
        console.print(f"[green]✓[/green] Wiped {PERSIST_DIR}")
    else:
        console.print(f"[yellow]No DB at {PERSIST_DIR}[/yellow]")


# ---------------------------------------------------------------------------
# Phase 7 — PoC validation harness
# ---------------------------------------------------------------------------


def _validate_scenario_for_validation(scenario: PoCScenario) -> list[str]:
    """Reject incomplete scenarios for `poc validate`.

    Ground-truth coverage is mandatory: every scenario must declare material,
    thickness, at least one expected_process_steps_min, and at least one
    expected error so we can compute recall / precision meaningfully.

    Returns the list of human-readable problems (empty == OK).
    """
    problems: list[str] = []
    if scenario.expected_material is None:
        problems.append("missing expected_material")
    if scenario.expected_thickness is None:
        problems.append("missing expected_thickness")
    if scenario.expected_process_steps_min <= 0:
        problems.append("expected_process_steps_min must be > 0")
    if not scenario.expected_errors:
        problems.append(
            "expected_errors is empty; cannot compute error recall / precision"
        )
    return problems


def _print_per_scenario_table(results) -> None:
    """Pretty-print per-scenario results as a Rich table."""
    table = Table(title="Per-Scenario Detail", show_lines=False)
    table.add_column("Scenario", style="bold")
    table.add_column("Status")
    table.add_column("Duration (s)", justify="right")
    table.add_column("Iter", justify="right")
    table.add_column("Material", justify="center")
    table.add_column("Thickness", justify="center")
    table.add_column("Recall", justify="right")
    table.add_column("Precision", justify="right")
    table.add_column("Steps", justify="right")
    for r in results:
        mat = "[green]✓[/green]" if r.material_match else "[red]✗[/red]"
        thk = "[green]✓[/green]" if r.thickness_match else "[red]✗[/red]"
        table.add_row(
            r.scenario,
            r.final_status,
            f"{r.duration_sec:.2f}",
            str(r.reflection_iterations),
            mat,
            thk,
            f"{r.error_recall:.3f}",
            f"{r.error_precision:.3f}",
            str(r.detected_process_steps),
        )
    console.print(table)


def _print_aggregate(agg: dict) -> None:
    table = Table(title="Aggregate Metrics", show_lines=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    for key in (
        "scenarios_run",
        "avg_duration_sec",
        "total_duration_sec",
        "avg_reflection_iterations",
        "material_pass_rate",
        "thickness_pass_rate",
        "avg_error_recall",
        "avg_error_precision",
        "process_steps_pass_rate",
    ):
        if key in agg:
            table.add_row(key, str(agg[key]))
    console.print(table)
    status_dist = agg.get("status_distribution") or {}
    if status_dist:
        dist_table = Table(title="Status Distribution")
        dist_table.add_column("Status", style="bold")
        dist_table.add_column("Count", justify="right")
        for status, count in status_dist.items():
            dist_table.add_row(status, str(count))
        console.print(dist_table)


def _run_scenarios_and_render(
    scenarios: list[PoCScenario], title: str, *, markdown_output: Path | None = None
) -> list:
    """Shared runner: load scenarios, run, print aggregate + per-scenario."""
    console.print(
        f"[bold blue]▶ Running {len(scenarios)} scenario(s)...[/bold blue]"
    )
    results = asyncio.run(run_poc(scenarios))
    agg = aggregate(results)
    _print_aggregate(agg)
    _print_per_scenario_table(results)
    if markdown_output is not None:
        markdown_output.write_text(render_report(results, title=title), encoding="utf-8")
        console.print(f"[green]✓[/green] Markdown report written to {markdown_output}")
    return results


@poc_app.command("run")
def poc_run(
    scenarios: Path = typer.Option(  # noqa: B008
        "tests/fixtures/poc_scenarios.json",
        "--scenarios",
        "-s",
        help="Path to scenarios JSON (must be a list of PoCScenario)",
        exists=True,
        readable=True,
    ),
) -> None:
    """Run PoC scenarios and print aggregate + per-scenario metrics to stdout."""
    loaded = load_scenarios(scenarios)
    _run_scenarios_and_render(loaded, title="DeepDraw PoC Run")


@poc_app.command("report")
def poc_report(
    scenarios: Path = typer.Option(  # noqa: B008
        "tests/fixtures/poc_scenarios.json",
        "--scenarios",
        "-s",
        help="Path to scenarios JSON",
        exists=True,
        readable=True,
    ),
    output: Path = typer.Option(  # noqa: B008
        Path("poc-report.md"),
        "--output",
        "-o",
        help="Where to write the Markdown report",
    ),
    title: str = typer.Option("DeepDraw PoC Report", help="Report title"),
) -> None:
    """Run PoC scenarios, print to stdout, and additionally write a Markdown report."""
    loaded = load_scenarios(scenarios)
    _run_scenarios_and_render(loaded, title=title, markdown_output=output)


@poc_app.command("validate")
def poc_validate(
    scenarios: Path = typer.Option(  # noqa: B008
        "tests/fixtures/poc_scenarios.json",
        "--scenarios",
        "-s",
        help="Path to scenarios JSON with full ground truth",
        exists=True,
        readable=True,
    ),
    output: Path = typer.Option(  # noqa: B008
        Path("poc-validation.md"),
        "--output",
        "-o",
        help="Where to write the validation Markdown report",
    ),
) -> None:
    """Run PoC scenarios with strict ground-truth checks.

    Rejects any scenario missing expected_material / expected_thickness /
    expected_process_steps_min / expected_errors so the resulting metrics
    are meaningful for PRD Phase 7 success criteria.
    """
    loaded = load_scenarios(scenarios)
    incomplete: list[tuple[str, list[str]]] = []
    for s in loaded:
        problems = _validate_scenario_for_validation(s)
        if problems:
            incomplete.append((s.name, problems))
    if incomplete:
        console.print(
            f"[red]✗ {len(incomplete)} scenario(s) lack ground-truth coverage:[/red]"
        )
        for name, problems in incomplete:
            console.print(f"  - [bold]{name}[/bold]: {', '.join(problems)}")
        raise typer.Exit(code=2)

    console.print(
        f"[green]✓[/green] All {len(loaded)} scenarios have full ground truth"
    )
    _run_scenarios_and_render(
        loaded, title="DeepDraw PoC Validation", markdown_output=output
    )


if __name__ == "__main__":
    app()
