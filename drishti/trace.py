"""
@trace decorator — the single user-facing entry point for Drishti.

Usage:
    from drishti import trace

    @trace
    def run_agent(query):
        response = openai.chat.completions.create(...)
        return response

    @trace(name="my-agent", budget_usd=0.05)
    def run_agent(query):
        ...

    @trace
    async def async_agent(query):
        ...

The decorator:
1. Creates a new Trace
2. Activates all provider patches
3. Runs the user function
4. Deactivates patches
5. Finalizes the trace
6. Renders the display (if enabled)
7. Exports to JSON (if enabled)
8. Returns the function result unchanged
"""

from __future__ import annotations

import asyncio
import functools
import uuid
import warnings
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .collector import collector
from .config import get_config
from .display.summary import render_summary
from .display.tree import render_trace_tree
from .export.json import export_trace
from .models.trace import Trace, TraceStatus
from .providers import ALL_INTERCEPTORS


def trace(
    name: Optional[str] = None,
    export: bool = True,
    display: bool = True,
    budget_usd: Optional[float] = None,
):
    """
    Decorator to trace all LLM calls inside the decorated function.

    Args:
        name: Custom name for the trace. Defaults to the function name.
        export: Whether to save the trace to a JSON file.
        display: Whether to print the trace tree to the terminal.
        budget_usd: Warn if the trace cost exceeds this amount in USD.

    Supports both @trace (bare) and @trace(name="foo") (with args).
    Automatically detects async functions and returns the correct wrapper.
    """

    def decorator(func: Callable) -> Callable:
        trace_name = name or func.__name__

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            cfg = get_config()
            t = Trace(
                trace_id=str(uuid.uuid4()),
                name=trace_name,
                started_at=datetime.now(timezone.utc),
            )

            # Activate
            collector.start_trace(t)
            for interceptor in ALL_INTERCEPTORS:
                interceptor.patch()

            result = None
            try:
                result = func(*args, **kwargs)
                t.status = TraceStatus.SUCCESS
            except Exception:
                t.status = TraceStatus.ERROR
                raise
            finally:
                # Always deactivate, even on exception
                for interceptor in ALL_INTERCEPTORS:
                    interceptor.unpatch()
                t.ended_at = datetime.now(timezone.utc)
                collector.end_trace()

                # Display + Export happen regardless of success/failure
                _post_trace(t, cfg, display, export, budget_usd)

            return result

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            cfg = get_config()
            t = Trace(
                trace_id=str(uuid.uuid4()),
                name=trace_name,
                started_at=datetime.now(timezone.utc),
            )

            # Activate
            collector.start_trace(t)
            for interceptor in ALL_INTERCEPTORS:
                interceptor.patch()

            result = None
            try:
                result = await func(*args, **kwargs)
                t.status = TraceStatus.SUCCESS
            except Exception:
                t.status = TraceStatus.ERROR
                raise
            finally:
                for interceptor in ALL_INTERCEPTORS:
                    interceptor.unpatch()
                t.ended_at = datetime.now(timezone.utc)
                collector.end_trace()

                _post_trace(t, cfg, display, export, budget_usd)

            return result

        # Return the correct wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    # Handle bare @trace (no parentheses) vs @trace(...) (with args)
    if callable(name):
        # Called as @trace without parentheses — name is actually the function
        func, name = name, None
        return decorator(func)

    return decorator


def _post_trace(
    t: Trace,
    cfg: Any,
    display: bool,
    export_flag: bool,
    budget_usd: Optional[float],
) -> None:
    """Run display, export, and budget check after a trace completes."""
    try:
        if display and cfg.display:
            render_trace_tree(t)
            render_summary(t)
    except Exception:
        pass  # Display failure must never crash the user's code

    try:
        if export_flag and cfg.export:
            export_trace(t, cfg.traces_dir)
    except Exception:
        warnings.warn("[Drishti] Failed to export trace to JSON.")

    # Budget guard (post-run warning for v0.1)
    effective_budget = budget_usd or cfg.budget_usd
    if effective_budget and t.total_cost_usd > effective_budget:
        warnings.warn(
            f"[Drishti] Budget exceeded: ${t.total_cost_usd:.4f} > ${effective_budget:.4f}"
        )
