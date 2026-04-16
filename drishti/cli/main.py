"""
Drishti CLI — terminal commands for managing traces.

Commands:
    drishti list    — List all saved traces with status, cost, tokens
    drishti view    — Replay a saved trace tree from JSON
    drishti clear   — Delete all saved traces (with confirmation)
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from ..display.summary import render_summary_from_dict
from ..display.tree import render_trace_from_dict
from ..export.json import DEFAULT_TRACES_DIR

app = typer.Typer(
    name="drishti",
    help="🔍 Drishti — See what your agent thinks.",
    add_completion=False,
)
console = Console()


@app.command()
def view(
    filename: str = typer.Argument(..., help="Trace file path or trace ID prefix"),
) -> None:
    """Replay a saved trace in the terminal."""
    path = Path(filename) if Path(filename).exists() else _find_trace(filename)
    if not path or not path.exists():
        console.print(f"[red]✗ Trace not found: {filename}[/red]")
        raise typer.Exit(1)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        console.print(f"[red]✗ Invalid JSON: {path}[/red]")
        raise typer.Exit(1)

    console.print()
    render_trace_from_dict(data)
    render_summary_from_dict(data)
    console.print()


@app.command("list")
def list_traces() -> None:
    """List all saved traces."""
    traces_dir = Path(DEFAULT_TRACES_DIR)
    if not traces_dir.exists():
        console.print("[dim]No traces found. Run a traced agent first.[/dim]")
        return

    files = sorted(traces_dir.glob("*.json"), reverse=True)
    if not files:
        console.print("[dim]No traces found. Run a traced agent first.[/dim]")
        return

    console.print()
    console.print("[bold cyan]📋 Saved Traces[/bold cyan]")
    console.print()

    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            status = data.get("status", "unknown")
            status_color = "green" if status == "success" else "red"
            summary = data.get("summary", {})

            console.print(
                f"  [dim]{f.name}[/dim]  "
                f"[bold]{data.get('name', '?')}[/bold]  "
                f"[{status_color}]{status}[/{status_color}]  "
                f"[cyan]{summary.get('total_tokens', 0)} tokens[/cyan]  "
                f"[yellow]${summary.get('total_cost_usd', 0):.4f}[/yellow]"
            )
        except (json.JSONDecodeError, KeyError):
            console.print(f"  [dim]{f.name}[/dim]  [red]corrupt[/red]")

    console.print()


@app.command()
def clear() -> None:
    """Delete all saved traces."""
    traces_dir = Path(DEFAULT_TRACES_DIR)
    if not traces_dir.exists():
        console.print("[dim]Nothing to clear.[/dim]")
        return

    files = list(traces_dir.glob("*.json"))
    if not files:
        console.print("[dim]Nothing to clear.[/dim]")
        return

    confirm = typer.confirm(f"Delete {len(files)} saved trace(s)?")
    if confirm:
        for f in files:
            f.unlink()
        console.print(f"[green]✓ Deleted {len(files)} trace(s).[/green]")
    else:
        console.print("[dim]Cancelled.[/dim]")


def _find_trace(prefix: str) -> Path | None:
    """Find a trace file by ID prefix or name substring."""
    traces_dir = Path(DEFAULT_TRACES_DIR)
    if not traces_dir.exists():
        return None

    for f in sorted(traces_dir.glob("*.json"), reverse=True):
        if f.stem.startswith(prefix) or prefix in f.stem:
            return f
    return None


def main() -> None:
    """CLI entrypoint."""
    app()
