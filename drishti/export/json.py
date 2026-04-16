"""JSON export — serializes Traces to JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models.span import Span
from ..models.trace import Trace

DEFAULT_TRACES_DIR = ".drishti/traces"
SCHEMA_VERSION = "0.2.2"


def _safe_json_obj(obj: Any) -> Any:
    """Best-effort conversion into JSON-serializable structure."""
    if obj is None:
        return None
    try:
        return json.loads(json.dumps(obj, default=str, ensure_ascii=False))
    except Exception:
        return str(obj)


def _span_to_dict(span: Span) -> dict[str, Any]:
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
        "streaming": span.streaming,
        "estimated_tokens": span.estimated_tokens,
        "estimation_source": span.estimation_source,
        "request_payload": _safe_json_obj(span.request_payload),
        "input": _safe_json_obj(span.input),
        "output": _safe_json_obj(span.output),
    }


def export_trace(trace: Trace, traces_dir: str = DEFAULT_TRACES_DIR) -> Path:
    """Serialize a Trace to JSON and save it to disk."""
    dir_path = Path(traces_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    timestamp = trace.started_at.strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in trace.name[:20])
    filename = dir_path / f"{timestamp}_{safe_name}.json"

    payload = {
        "schema_version": SCHEMA_VERSION,
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
