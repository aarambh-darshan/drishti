"""
Summary panel — renders aggregate trace metrics as a Rich panel.

Shows total tokens, total cost, wall time, LLM call count, and
trace status in a compact bordered panel.
"""

from __future__ import annotations

from typing import Any, Dict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..models.trace import Trace

console = Console()


def render_summary(trace: Trace) -> None:
    """
    Render a summary panel for a completed Trace.

    Args:
        trace: The completed Trace to summarize.
    """
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim")
    table.add_column(style="bold")

    table.add_row("Total Tokens", str(trace.total_tokens.total_tokens))
    table.add_row("Total Cost", f"${trace.total_cost_usd:.4f} USD")
    table.add_row("Wall Time", f"{trace.total_latency_ms:.0f}ms")
    table.add_row("LLM Calls", str(trace.span_count))
    table.add_row("Status", trace.status.value.upper())

    border_style = "cyan" if trace.status.value == "success" else "red"

    console.print(
        Panel(
            table,
            title="[bold]Summary[/bold]",
            border_style=border_style,
        )
    )


def render_summary_from_dict(data: Dict[str, Any]) -> None:
    """
    Render a summary panel from a deserialized JSON dict (for CLI 'view').

    Args:
        data: The trace data loaded from a JSON file.
    """
    summary = data.get("summary", {})

    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim")
    table.add_column(style="bold")

    table.add_row("Total Tokens", str(summary.get("total_tokens", 0)))
    table.add_row("Total Cost", f"${summary.get('total_cost_usd', 0):.4f} USD")
    table.add_row("Wall Time", f"{summary.get('total_latency_ms', 0):.0f}ms")
    table.add_row("LLM Calls", str(summary.get("span_count", 0)))
    table.add_row("Status", data.get("status", "unknown").upper())

    border_style = "cyan" if data.get("status") == "success" else "red"

    console.print(
        Panel(
            table,
            title="[bold]Summary[/bold]",
            border_style=border_style,
        )
    )
