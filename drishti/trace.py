"""@trace decorator — the single user-facing entry point for Drishti."""

from __future__ import annotations

import asyncio
import functools
import json
import uuid
import warnings
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from .collector import collector
from .config import DrishtiConfig, get_config
from .display.summary import render_summary, render_summary_from_dict
from .display.tree import render_trace_from_dict, render_trace_tree
from .errors import DrishtiBudgetError
from .export.json import export_trace
from .models.trace import Trace, TraceStatus
from .providers.manager import patch_manager


def trace(
    name: str | None = None,
    export: bool = True,
    display: bool = True,
    budget_usd: float | None = None,
    on_exceed: Literal["warn", "abort"] = "warn",
):
    """Decorator to trace all LLM calls inside the decorated function."""

    if on_exceed not in {"warn", "abort"}:
        raise ValueError("on_exceed must be 'warn' or 'abort'")

    def decorator(func: Callable) -> Callable:
        trace_name = name or func.__name__

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            cfg = get_config()
            effective_budget = budget_usd if budget_usd is not None else cfg.budget_usd
            effective_on_exceed = on_exceed or cfg.on_exceed

            t = Trace(
                trace_id=str(uuid.uuid4()),
                name=trace_name,
                started_at=datetime.now(timezone.utc),
            )

            collector.start_trace(t, budget_usd=effective_budget, on_exceed=effective_on_exceed)
            patch_manager.acquire()

            result: Any = None
            try:
                result = func(*args, **kwargs)
                t.status = TraceStatus.SUCCESS
            except Exception:
                t.status = TraceStatus.ERROR
                raise
            finally:
                patch_manager.release()
                t.ended_at = datetime.now(timezone.utc)
                collector.end_trace()

                _post_trace(
                    trace=t,
                    cfg=cfg,
                    display=display,
                    export_flag=export,
                    budget_usd=effective_budget,
                    on_exceed=effective_on_exceed,
                )

            return result

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            cfg = get_config()
            effective_budget = budget_usd if budget_usd is not None else cfg.budget_usd
            effective_on_exceed = on_exceed or cfg.on_exceed

            t = Trace(
                trace_id=str(uuid.uuid4()),
                name=trace_name,
                started_at=datetime.now(timezone.utc),
            )

            collector.start_trace(t, budget_usd=effective_budget, on_exceed=effective_on_exceed)
            patch_manager.acquire()

            result: Any = None
            try:
                result = await func(*args, **kwargs)
                t.status = TraceStatus.SUCCESS
            except Exception:
                t.status = TraceStatus.ERROR
                raise
            finally:
                patch_manager.release()
                t.ended_at = datetime.now(timezone.utc)
                collector.end_trace()

                _post_trace(
                    trace=t,
                    cfg=cfg,
                    display=display,
                    export_flag=export,
                    budget_usd=effective_budget,
                    on_exceed=effective_on_exceed,
                )

            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    if callable(name):
        func, name = name, None
        return decorator(func)

    return decorator


def _post_trace(
    *,
    trace: Trace,
    cfg: DrishtiConfig,
    display: bool,
    export_flag: bool,
    budget_usd: float | None,
    on_exceed: Literal["warn", "abort"],
) -> None:
    """Run display, export, and post-run budget checks after a trace completes."""
    displayed = False
    if display and cfg.display and not cfg.quiet:
        try:
            render_trace_tree(trace, full=False, max_preview_chars=cfg.max_preview_chars)
            render_summary(trace)
            displayed = True
        except Exception:
            pass

    exported_path = None
    if export_flag and cfg.export:
        try:
            exported_path = export_trace(trace, cfg.export_dir)
        except Exception:
            warnings.warn("[Drishti] Failed to export trace to JSON.", RuntimeWarning, stacklevel=2)

    if (
        trace.status == TraceStatus.ERROR
        and cfg.auto_open_on_error
        and exported_path is not None
        and not cfg.quiet
        and not displayed
    ):
        try:
            data = json.loads(exported_path.read_text(encoding="utf-8"))
            render_trace_from_dict(data, full=False, max_preview_chars=cfg.max_preview_chars)
            render_summary_from_dict(data)
        except Exception:
            pass

    if on_exceed == "warn" and budget_usd is not None and trace.total_cost_usd > budget_usd:
        warnings.warn(
            f"[Drishti] Budget exceeded: ${trace.total_cost_usd:.4f} > ${budget_usd:.4f}",
            RuntimeWarning,
            stacklevel=2,
        )


__all__ = ["trace", "DrishtiBudgetError"]
