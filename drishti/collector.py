"""
Collector — global trace context registry.

The Collector holds the currently active Trace. Provider interceptors call
the Collector to register new spans. The @trace decorator activates and
deactivates the Collector.

Uses both threading.local() (for sync threads) and contextvars.ContextVar
(for async coroutines) to ensure correct isolation in all concurrency modes.
"""

from __future__ import annotations

import contextvars
import threading
from typing import Optional

from .models.span import Span
from .models.trace import Trace


# ContextVar for async coroutine safety
_active_trace_var: contextvars.ContextVar[Optional[Trace]] = contextvars.ContextVar(
    "drishti_active_trace", default=None
)


class _Collector:
    """
    Thread-local + ContextVar singleton.

    Each thread has its own active trace (via threading.local).
    Each async coroutine has its own active trace (via ContextVar).
    This allows multiple agents to run concurrently without interference.
    """

    def __init__(self) -> None:
        self._local = threading.local()

    @property
    def active_trace(self) -> Optional[Trace]:
        """Get the currently active trace, checking ContextVar first, then thread-local."""
        # ContextVar takes priority (covers async case)
        trace = _active_trace_var.get(None)
        if trace is not None:
            return trace
        # Fall back to thread-local (sync case)
        return getattr(self._local, "trace", None)

    def start_trace(self, trace: Trace) -> None:
        """Called by @trace decorator at entry. Sets the active trace in both stores."""
        self._local.trace = trace
        _active_trace_var.set(trace)

    def end_trace(self) -> Optional[Trace]:
        """Called by @trace decorator at exit. Returns completed trace and clears state."""
        trace = self.active_trace
        self._local.trace = None
        _active_trace_var.set(None)
        return trace

    def record_span(self, span: Span) -> None:
        """
        Called by provider interceptors when a span is completed.

        Auto-assigns step number and appends to the active trace.
        Silently ignored if no trace is active (pure passthrough mode).
        """
        trace = self.active_trace
        if trace is None:
            return  # No active trace, silently ignore
        span.step = len(trace.spans) + 1
        trace.spans.append(span)

    @property
    def is_active(self) -> bool:
        """True if there is an active trace context."""
        return self.active_trace is not None


# Global singleton — import this everywhere
collector = _Collector()
