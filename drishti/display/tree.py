"""
Tree renderer — visualizes a Trace as a Rich terminal tree.

Shows every span with step number, status icon, provider/model,
token count, cost, and latency. Error details are shown inline
under failed spans.
"""

from __future__ import annotations

from typing import Any, Dict

from rich.console import Console
from rich.text import Text
from rich.tree import Tree

from ..models.span import SpanStatus
from ..models.trace import Trace

console = Console()


def render_trace_tree(trace: Trace) -> None:
    """
    Render a Trace object as a Rich tree in the terminal.

    Args:
        trace: The completed Trace to render.
    """
    root_label = Text()
    root_label.append("🔍 Drishti Trace", style="bold cyan")
    root_label.append(f" — {trace.name}", style="bold white")

    tree = Tree(root_label)

    for span in trace.spans:
        # Status icon
        if span.status == SpanStatus.SUCCESS:
            icon = "[green]✅[/green]"
        elif span.status == SpanStatus.ERROR:
            icon = "[red]❌[/red]"
        else:
            icon = "[yellow]⏳[/yellow]"

        # Build node label
        label = (
            f"{icon} [dim][{span.step}][/dim] "
            f"[bold]{span.name}[/bold]  "
            f"[cyan]{span.tokens.total_tokens} tokens[/cyan]  "
            f"[yellow]${span.cost_usd:.4f}[/yellow]  "
            f"[dim]{span.latency_ms:.0f}ms[/dim]"
        )

        node = tree.add(label)

        # Show error detail inline under failed spans
        if span.status == SpanStatus.ERROR and span.error:
            node.add(f"[red]{span.error_type}: {span.error}[/red]")

    console.print(tree)


def render_trace_from_dict(data: Dict[str, Any]) -> None:
    """
    Render a trace from a deserialized JSON dict (for CLI 'view' command).

    Args:
        data: The trace data loaded from a JSON file.
    """
    root_label = Text()
    root_label.append("🔍 Drishti Trace", style="bold cyan")
    root_label.append(f" — {data.get('name', 'unknown')}", style="bold white")

    tree = Tree(root_label)

    for span_data in data.get("spans", []):
        status = span_data.get("status", "pending")

        if status == "success":
            icon = "[green]✅[/green]"
        elif status == "error":
            icon = "[red]❌[/red]"
        else:
            icon = "[yellow]⏳[/yellow]"

        tokens = span_data.get("tokens", {})
        total_tokens = tokens.get("total", 0)

        label = (
            f"{icon} [dim][{span_data.get('step', '?')}][/dim] "
            f"[bold]{span_data.get('name', 'unknown')}[/bold]  "
            f"[cyan]{total_tokens} tokens[/cyan]  "
            f"[yellow]${span_data.get('cost_usd', 0):.4f}[/yellow]  "
            f"[dim]{span_data.get('latency_ms', 0):.0f}ms[/dim]"
        )

        node = tree.add(label)

        if status == "error" and span_data.get("error"):
            error_type = span_data.get("error_type", "Error")
            node.add(f"[red]{error_type}: {span_data['error']}[/red]")

    console.print(tree)
