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


if __name__ == "__main__":
    app()
