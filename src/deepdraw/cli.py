"""DeepDraw CLI — entry point for `deepdraw <drawing.pdf>` and `python -m deepdraw`."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.json import JSON

from deepdraw.graph import graph

app = typer.Typer(help="DeepDraw — DFM-Copilot Squad CLI")
console = Console()


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

    # LangGraph 1.x: async node functions require ainvoke (sync invoke rejected)
    final_state = asyncio.run(graph.ainvoke(initial_state, config=config))

    report = {
        "spec": final_state.get("spec", {}),
        "errors": final_state.get("errors", []),
        "bom": final_state.get("bom", []),
        "process_plan": final_state.get("process_plan", []),
        "verification_notes": final_state.get("verification_notes", []),
        "reflection_iterations": final_state.get("reflection_iterations", 0),
        "status": final_state.get("status", "unknown"),
    }

    if output:
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        console.print(f"[green]✓[/green] Report written to {output}")
    else:
        console.print(JSON(json.dumps(report, indent=2, ensure_ascii=False)))


if __name__ == "__main__":
    app()
