"""Tree renderer — visualizes a Trace as a Rich terminal tree."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.text import Text
from rich.tree import Tree

from ..models.span import SpanStatus
from ..models.trace import Trace

console = Console()


def _cost_style(cost: float) -> str:
    if cost < 0.01:
        return "green"
    if cost < 0.10:
        return "yellow"
    return "red"


def _serialize_preview(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except Exception:
        return str(value)


def _truncate(text: str, max_chars: int, full: bool) -> str:
    if full:
        return text
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def _render_span_node(
    tree: Tree,
    *,
    step: int,
    status: str,
    provider: str,
    model: str,
    total_tokens: int,
    cost_usd: float,
    latency_ms: float,
    streaming: bool,
    error: str | None,
    error_type: str | None,
    input_data: Any,
    output_data: Any,
    full: bool,
    max_preview_chars: int,
) -> None:
    if status == SpanStatus.SUCCESS.value:
        icon = "[green]✅[/green]"
    elif status == SpanStatus.ERROR.value:
        icon = "[red]❌[/red]"
    else:
        icon = "[yellow]⏳[/yellow]"

    stream_label = " [yellow]⚡ streaming[/yellow]" if streaming else ""
    cost_color = _cost_style(cost_usd)

    label = (
        f"{icon} [dim][{step}][/dim] "
        f"[bold]{provider}[/bold] "
        f"[magenta]{model}[/magenta]  "
        f"[cyan]{total_tokens} tokens[/cyan]  "
        f"[{cost_color}]${cost_usd:.4f}[/{cost_color}]  "
        f"[dim]{latency_ms:.0f}ms[/dim]"
        f"{stream_label}"
    )

    node = tree.add(label)

    preview_input = _truncate(_serialize_preview(input_data), max_preview_chars, full)
    preview_output = _truncate(_serialize_preview(output_data), max_preview_chars, full)

    if preview_input:
        node.add(f"[dim]input:[/dim] {preview_input}")
    if preview_output:
        node.add(f"[dim]output:[/dim] {preview_output}")

    if status == SpanStatus.ERROR.value and error:
        node.add(f"[red]{error_type or 'Error'}: {error}[/red]")


def render_trace_tree(trace: Trace, full: bool = False, max_preview_chars: int = 220) -> None:
    """Render a Trace object as a Rich tree in the terminal."""
    root_label = Text()
    root_label.append("🔍 Drishti Trace", style="bold cyan")
    root_label.append(f" — {trace.name}", style="bold white")

    tree = Tree(root_label)

    for span in trace.spans:
        _render_span_node(
            tree,
            step=span.step,
            status=span.status.value,
            provider=span.provider,
            model=span.model,
            total_tokens=span.tokens.total_tokens,
            cost_usd=span.cost_usd,
            latency_ms=span.latency_ms,
            streaming=span.streaming,
            error=span.error,
            error_type=span.error_type,
            input_data=span.input,
            output_data=span.output,
            full=full,
            max_preview_chars=max_preview_chars,
        )

    console.print(tree)


def render_trace_from_dict(
    data: dict[str, Any],
    full: bool = False,
    max_preview_chars: int = 220,
) -> None:
    """Render a trace from a deserialized JSON dict."""
    root_label = Text()
    root_label.append("🔍 Drishti Trace", style="bold cyan")
    root_label.append(f" — {data.get('name', 'unknown')}", style="bold white")

    tree = Tree(root_label)

    for span_data in data.get("spans", []):
        tokens = span_data.get("tokens", {})
        _render_span_node(
            tree,
            step=int(span_data.get("step", 0) or 0),
            status=str(span_data.get("status", SpanStatus.PENDING.value)),
            provider=str(span_data.get("provider", "unknown")),
            model=str(span_data.get("model", "unknown")),
            total_tokens=int(tokens.get("total", 0) or 0),
            cost_usd=float(span_data.get("cost_usd", 0.0) or 0.0),
            latency_ms=float(span_data.get("latency_ms", 0.0) or 0.0),
            streaming=bool(span_data.get("streaming", False)),
            error=span_data.get("error"),
            error_type=span_data.get("error_type"),
            input_data=span_data.get("input"),
            output_data=span_data.get("output"),
            full=full,
            max_preview_chars=max_preview_chars,
        )

    console.print(tree)
