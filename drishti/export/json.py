"""
JSON export — serializes Traces to JSON files.

Traces are saved to .drishti/traces/ with filenames in the format:
    YYYYMMDD_HHMMSS_<name>.json

The JSON includes a summary block at the top for quick scanning,
followed by the full spans array with all metrics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models.span import Span
from ..models.trace import Trace

DEFAULT_TRACES_DIR = ".drishti/traces"


def _safe_str(obj: Any) -> str:
    """Safely serialize any object to a JSON-compatible string."""
    if obj is None:
        return ""
    try:
        return json.dumps(obj, default=str)
    except Exception:
        return str(obj)


def _span_to_dict(span: Span) -> dict:
    """Convert a Span to a serializable dictionary."""
    return {
        "span_id": span.span_id,
        "step": span.step,
        "name": span.name,
        "provider": span.provider,
        "model": span.model,
        "started_at": span.started_at.isoformat(),
        "ended_at": span.ended_at.isoformat() if span.ended_at else None,
        "tokens": {
            "prompt": span.tokens.prompt_tokens,
            "completion": span.tokens.completion_tokens,
            "total": span.tokens.total_tokens,
        },
        "cost_usd": span.cost_usd,
        "latency_ms": span.latency_ms,
        "status": span.status.value,
        "error": span.error,
        "error_type": span.error_type,
        "input": _safe_str(span.input),
        "output": _safe_str(span.output),
    }


def export_trace(trace: Trace, traces_dir: str = DEFAULT_TRACES_DIR) -> Path:
    """
    Serialize a Trace to JSON and save it to disk.

    Args:
        trace: The completed Trace to export.
        traces_dir: Directory to save the trace file.

    Returns:
        Path to the saved JSON file.
    """
    dir_path = Path(traces_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    timestamp = trace.started_at.strftime("%Y%m%d_%H%M%S")
    # Sanitize trace name for filename safety
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in trace.name[:20])
    filename = dir_path / f"{timestamp}_{safe_name}.json"

    payload = {
        "trace_id": trace.trace_id,
        "name": trace.name,
        "started_at": trace.started_at.isoformat(),
        "ended_at": trace.ended_at.isoformat() if trace.ended_at else None,
        "status": trace.status.value,
        "summary": {
            "total_tokens": trace.total_tokens.total_tokens,
            "total_cost_usd": trace.total_cost_usd,
            "total_latency_ms": trace.total_latency_ms,
            "span_count": trace.span_count,
        },
        "spans": [_span_to_dict(s) for s in trace.spans],
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return filename
