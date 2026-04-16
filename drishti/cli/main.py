"""Drishti CLI — terminal commands for managing traces."""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .. import __version__
from ..config import get_config
from ..cost.calculator import calculate_cost
from ..display.summary import render_summary_from_dict
from ..display.tree import render_trace_from_dict
from ..providers.common import anthropic_usage_from_response, openai_usage_from_response

app = typer.Typer(
    name="drishti",
    help="🔍 Drishti — See what your agent thinks.",
    add_completion=False,
)
console = Console()


def _traces_dir() -> Path:
    return Path(get_config().export_dir)


def _find_trace(prefix: str) -> Path | None:
    traces_dir = _traces_dir()
    if not traces_dir.exists():
        return None

    for file_path in sorted(traces_dir.glob("*.json"), reverse=True):
        if file_path.stem.startswith(prefix) or prefix in file_path.stem:
            return file_path
    return None


def _resolve_trace(reference: str) -> Path | None:
    direct = Path(reference)
    if direct.exists():
        return direct
    return _find_trace(reference)


def _load_trace(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _coerce_messages(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [{"role": "user", "content": raw}]
    return []


def _extract_text_from_openai_response(response: Any) -> str:
    if isinstance(response, dict):
        choices = response.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        return str(message.get("content", "") or "")

    choices = getattr(response, "choices", None)
    if not choices:
        return ""
    first = choices[0]
    message = getattr(first, "message", None)
    if message is None:
        return ""
    return str(getattr(message, "content", "") or "")


def _extract_text_from_anthropic_response(response: Any) -> str:
    if isinstance(response, dict):
        content = response.get("content", [])
        if content and isinstance(content[0], dict):
            return str(content[0].get("text", "") or "")
        return ""

    content = getattr(response, "content", None)
    if not content:
        return ""
    first = content[0]
    return str(getattr(first, "text", "") or "")


def _extract_ollama_tokens(response: Any) -> tuple[int, int, int]:
    if isinstance(response, dict):
        prompt = int(response.get("prompt_eval_count", 0) or 0)
        completion = int(response.get("eval_count", 0) or 0)
        return prompt, completion, prompt + completion

    prompt = int(getattr(response, "prompt_eval_count", 0) or 0)
    completion = int(getattr(response, "eval_count", 0) or 0)
    return prompt, completion, prompt + completion


def _extract_ollama_text(response: Any) -> str:
    if isinstance(response, dict):
        message = response.get("message", {})
        if isinstance(message, dict):
            return str(message.get("content", "") or "")
        return ""

    message = getattr(response, "message", None)
    if message is None:
        return ""
    return str(getattr(message, "content", "") or "")


def _replay_span(span: dict[str, Any]) -> dict[str, Any]:
    provider = span.get("provider", "")
    model = span.get("model", "unknown")
    payload = span.get("request_payload") or {}
    kwargs = payload.get("kwargs") if isinstance(payload, dict) else {}
    if not isinstance(kwargs, dict):
        kwargs = {}

    if not kwargs:
        kwargs = {
            "model": model,
            "messages": _coerce_messages(span.get("input", [])),
        }

    start = time.perf_counter()

    if provider == "openai":
        import openai

        response = openai.OpenAI().chat.completions.create(**kwargs)
        tokens = openai_usage_from_response(response)
        text = _extract_text_from_openai_response(response)
    elif provider == "groq":
        import groq

        response = groq.Groq().chat.completions.create(**kwargs)
        tokens = openai_usage_from_response(response)
        text = _extract_text_from_openai_response(response)
    elif provider == "anthropic":
        import anthropic

        response = anthropic.Anthropic().messages.create(**kwargs)
        tokens = anthropic_usage_from_response(response)
        text = _extract_text_from_anthropic_response(response)
    elif provider == "ollama":
        import ollama

        response = ollama.chat(**kwargs)
        prompt, completion, total = _extract_ollama_tokens(response)
        from ..models.span import TokenUsage

        tokens = TokenUsage(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)
        text = _extract_ollama_text(response)
    else:
        raise RuntimeError(f"Replay not supported for provider: {provider}")

    latency_ms = (time.perf_counter() - start) * 1000
    replay_cost = calculate_cost(provider, str(model), tokens)

    original_tokens = int(span.get("tokens", {}).get("total", 0) or 0)
    original_cost = float(span.get("cost_usd", 0.0) or 0.0)
    original_latency = float(span.get("latency_ms", 0.0) or 0.0)

    return {
        "step": span.get("step", 0),
        "provider": provider,
        "model": model,
        "orig_tokens": original_tokens,
        "new_tokens": tokens.total_tokens,
        "delta_tokens": tokens.total_tokens - original_tokens,
        "orig_cost": original_cost,
        "new_cost": replay_cost,
        "delta_cost": replay_cost - original_cost,
        "orig_latency": original_latency,
        "new_latency": latency_ms,
        "delta_latency": latency_ms - original_latency,
        "output_preview": text[:120],
    }


@app.command()
def version() -> None:
    """Print installed Drishti version."""
    console.print(__version__)


@app.command()
def view(
    filename: str = typer.Argument(..., help="Trace file path or trace ID prefix"),
    full: bool = typer.Option(False, "--full", help="Show full input/output (no truncation)."),
) -> None:
    """Replay a saved trace in the terminal."""
    path = _resolve_trace(filename)
    if not path or not path.exists():
        console.print(f"[red]✗ Trace not found: {filename}[/red]")
        raise typer.Exit(1)

    try:
        data = _load_trace(path)
    except json.JSONDecodeError:
        console.print(f"[red]✗ Invalid JSON: {path}[/red]")
        raise typer.Exit(1)

    cfg = get_config()
    console.print()
    render_trace_from_dict(data, full=full, max_preview_chars=cfg.max_preview_chars)
    render_summary_from_dict(data)
    console.print()


@app.command("list")
def list_traces() -> None:
    """List all saved traces."""
    traces_dir = _traces_dir()
    if not traces_dir.exists():
        console.print("[dim]No traces found. Run a traced agent first.[/dim]")
        return

    files = sorted(traces_dir.glob("*.json"), reverse=True)
    if not files:
        console.print("[dim]No traces found. Run a traced agent first.[/dim]")
        return

    table = Table(title="Saved Traces")
    table.add_column("File", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Status")
    table.add_column("Tokens", justify="right")
    table.add_column("Cost", justify="right")

    for file_path in files:
        try:
            data = _load_trace(file_path)
            status = str(data.get("status", "unknown"))
            status_color = "green" if status == "success" else "red"
            summary = data.get("summary", {})
            table.add_row(
                file_path.name,
                str(data.get("name", "?")),
                f"[{status_color}]{status}[/{status_color}]",
                str(summary.get("total_tokens", 0)),
                f"${float(summary.get('total_cost_usd', 0.0) or 0.0):.4f}",
            )
        except Exception:
            table.add_row(file_path.name, "?", "[red]corrupt[/red]", "-", "-")

    console.print(table)


@app.command()
def clear() -> None:
    """Delete all saved traces."""
    traces_dir = _traces_dir()
    if not traces_dir.exists():
        console.print("[dim]Nothing to clear.[/dim]")
        return

    files = list(traces_dir.glob("*.json"))
    if not files:
        console.print("[dim]Nothing to clear.[/dim]")
        return

    confirm = typer.confirm(f"Delete {len(files)} saved trace(s)?")
    if confirm:
        for file_path in files:
            file_path.unlink()
        console.print(f"[green]✓ Deleted {len(files)} trace(s).[/green]")
    else:
        console.print("[dim]Cancelled.[/dim]")


@app.command()
def diff(
    trace1: str = typer.Argument(..., help="Base trace path or id"),
    trace2: str = typer.Argument(..., help="Compare trace path or id"),
) -> None:
    """Diff two traces in a compact delta table."""
    path1 = _resolve_trace(trace1)
    path2 = _resolve_trace(trace2)
    if not path1:
        console.print(f"[red]✗ Trace not found: {trace1}[/red]")
        raise typer.Exit(1)
    if not path2:
        console.print(f"[red]✗ Trace not found: {trace2}[/red]")
        raise typer.Exit(1)

    data1 = _load_trace(path1)
    data2 = _load_trace(path2)
    spans1 = data1.get("spans", [])
    spans2 = data2.get("spans", [])

    table = Table(title=f"Trace Diff: {data1.get('name')} → {data2.get('name')}")
    table.add_column("Step", justify="right")
    table.add_column("Change")
    table.add_column("Provider/Model")
    table.add_column("ΔTokens", justify="right")
    table.add_column("ΔCost", justify="right")
    table.add_column("ΔLatency", justify="right")

    max_len = max(len(spans1), len(spans2))
    for i in range(max_len):
        s1 = spans1[i] if i < len(spans1) else None
        s2 = spans2[i] if i < len(spans2) else None

        if s1 is None and s2 is not None:
            model_text = f"{s2.get('provider', '?')}/{s2.get('model', '?')}"
            table.add_row(str(i + 1), "[green]added[/green]", model_text, "+", "+", "+")
            continue

        if s2 is None and s1 is not None:
            model_text = f"{s1.get('provider', '?')}/{s1.get('model', '?')}"
            table.add_row(str(i + 1), "[red]removed[/red]", model_text, "-", "-", "-")
            continue

        assert s1 is not None and s2 is not None

        tokens1 = int(s1.get("tokens", {}).get("total", 0) or 0)
        tokens2 = int(s2.get("tokens", {}).get("total", 0) or 0)
        cost1 = float(s1.get("cost_usd", 0.0) or 0.0)
        cost2 = float(s2.get("cost_usd", 0.0) or 0.0)
        lat1 = float(s1.get("latency_ms", 0.0) or 0.0)
        lat2 = float(s2.get("latency_ms", 0.0) or 0.0)

        dt = tokens2 - tokens1
        dc = cost2 - cost1
        dl = lat2 - lat1

        unchanged = (
            s1.get("provider") == s2.get("provider")
            and s1.get("model") == s2.get("model")
            and dt == 0
            and abs(dc) < 1e-9
            and abs(dl) < 1e-9
        )
        change = "same" if unchanged else "[yellow]changed[/yellow]"

        model_text = f"{s2.get('provider', '?')}/{s2.get('model', '?')}"
        table.add_row(
            str(i + 1),
            change,
            model_text,
            f"{dt:+d}",
            f"{dc:+.4f}",
            f"{dl:+.0f}ms",
        )

    console.print(table)


@app.command()
def stats() -> None:
    """Aggregate stats across all saved traces."""
    files = sorted(_traces_dir().glob("*.json"), reverse=True)
    if not files:
        console.print("[dim]No traces found.[/dim]")
        return

    total_cost = 0.0
    total_tokens = 0
    per_agent: dict[str, float] = {}

    for file_path in files:
        try:
            data = _load_trace(file_path)
        except Exception:
            continue

        summary = data.get("summary", {})
        cost = float(summary.get("total_cost_usd", 0.0) or 0.0)
        tokens = int(summary.get("total_tokens", 0) or 0)
        name = str(data.get("name", "unknown"))

        total_cost += cost
        total_tokens += tokens
        per_agent[name] = per_agent.get(name, 0.0) + cost

    avg_tokens = total_tokens / len(files)
    expensive_agent = max(per_agent.items(), key=lambda x: x[1])[0] if per_agent else "-"

    table = Table(title="Trace Stats")
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold")
    table.add_row("Trace Count", str(len(files)))
    table.add_row("Total Tokens", str(total_tokens))
    table.add_row("Average Tokens / Trace", f"{avg_tokens:.2f}")
    table.add_row("Total Cost", f"${total_cost:.4f}")
    table.add_row("Most Expensive Agent", expensive_agent)
    console.print(table)


@app.command("export")
def export_trace_csv(
    trace: str = typer.Argument(..., help="Trace file path or trace ID prefix"),
    format: str = typer.Option("csv", "--format", help="Export format"),
    output: str | None = typer.Option(None, "--output", help="Output file path"),
) -> None:
    """Export a trace to another format."""
    if format.lower() != "csv":
        console.print("[red]Only --format csv is currently supported.[/red]")
        raise typer.Exit(1)

    path = _resolve_trace(trace)
    if not path:
        console.print(f"[red]✗ Trace not found: {trace}[/red]")
        raise typer.Exit(1)

    data = _load_trace(path)
    out_path = Path(output) if output else path.with_suffix(".csv")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "step",
                "provider",
                "model",
                "status",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "cost_usd",
                "latency_ms",
                "streaming",
                "estimated_tokens",
            ]
        )

        for span in data.get("spans", []):
            tokens = span.get("tokens", {})
            writer.writerow(
                [
                    span.get("step", 0),
                    span.get("provider", ""),
                    span.get("model", ""),
                    span.get("status", ""),
                    tokens.get("prompt", 0),
                    tokens.get("completion", 0),
                    tokens.get("total", 0),
                    span.get("cost_usd", 0.0),
                    span.get("latency_ms", 0.0),
                    span.get("streaming", False),
                    span.get("estimated_tokens", False),
                ]
            )

    console.print(f"[green]✓ Exported CSV: {out_path}[/green]")


@app.command()
def replay(
    trace: str = typer.Argument(..., help="Trace file path or trace ID prefix"),
) -> None:
    """Replay LLM spans from a saved trace and show deltas."""
    path = _resolve_trace(trace)
    if not path:
        console.print(f"[red]✗ Trace not found: {trace}[/red]")
        raise typer.Exit(1)

    data = _load_trace(path)
    spans = data.get("spans", [])
    if not spans:
        console.print("[dim]Trace has no spans to replay.[/dim]")
        return

    table = Table(title=f"Replay: {data.get('name', path.stem)}")
    table.add_column("Step", justify="right")
    table.add_column("Provider/Model")
    table.add_column("ΔTokens", justify="right")
    table.add_column("ΔCost", justify="right")
    table.add_column("ΔLatency", justify="right")
    table.add_column("Replay Output")

    for span in spans:
        try:
            result = _replay_span(span)
            table.add_row(
                str(result["step"]),
                f"{result['provider']}/{result['model']}",
                f"{result['delta_tokens']:+d}",
                f"{result['delta_cost']:+.4f}",
                f"{result['delta_latency']:+.0f}ms",
                result["output_preview"],
            )
        except Exception as exc:
            step = span.get("step", "?")
            provider = span.get("provider", "?")
            model = span.get("model", "?")
            table.add_row(str(step), f"{provider}/{model}", "-", "-", "-", f"ERROR: {exc}")

    console.print(table)


def main() -> None:
    """CLI entrypoint."""
    app()
