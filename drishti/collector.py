"""Collector — global trace context registry."""

from __future__ import annotations

import asyncio
import contextvars
import threading
from dataclasses import dataclass
from typing import Literal

from .errors import DrishtiBudgetError
from .models.span import Span, SpanStatus
from .models.trace import Trace


@dataclass(slots=True)
class TraceContext:
    """Runtime context for an active trace."""

    trace: Trace
    budget_usd: float | None = None
    on_exceed: Literal["warn", "abort"] = "warn"


_trace_stack_var: contextvars.ContextVar[tuple[TraceContext, ...]] = contextvars.ContextVar(
    "drishti_trace_stack", default=()
)


class _Collector:
    """Thread-local + ContextVar trace collector with stack-based nesting support."""

    def __init__(self) -> None:
        self._local = threading.local()

    def _thread_stack(self) -> list[TraceContext]:
        stack = getattr(self._local, "trace_stack", None)
        if stack is None:
            stack = []
            self._local.trace_stack = stack
        return stack

    @staticmethod
    def _in_async_context() -> bool:
        try:
            return asyncio.current_task() is not None
        except RuntimeError:
            return False

    @property
    def active_context(self) -> TraceContext | None:
        """Get currently active trace context (nested-safe)."""
        ctx_stack = _trace_stack_var.get(())
        if ctx_stack:
            return ctx_stack[-1]

        thread_stack = self._thread_stack()
        if thread_stack:
            return thread_stack[-1]
        return None

    @property
    def active_trace(self) -> Trace | None:
        """Get currently active trace."""
        context = self.active_context
        return context.trace if context else None

    def start_trace(
        self,
        trace: Trace,
        budget_usd: float | None = None,
        on_exceed: Literal["warn", "abort"] = "warn",
    ) -> None:
        """Push a new active trace context."""
        context = TraceContext(trace=trace, budget_usd=budget_usd, on_exceed=on_exceed)

        if not self._in_async_context():
            thread_stack = self._thread_stack()
            thread_stack.append(context)

        ctx_stack = list(_trace_stack_var.get(()))
        ctx_stack.append(context)
        _trace_stack_var.set(tuple(ctx_stack))

    def end_trace(self) -> Trace | None:
        """Pop active trace context and return trace."""
        popped: TraceContext | None = None

        ctx_stack = list(_trace_stack_var.get(()))
        if ctx_stack:
            popped = ctx_stack.pop()
            _trace_stack_var.set(tuple(ctx_stack))

        if not self._in_async_context():
            thread_stack = self._thread_stack()
            if thread_stack:
                popped = thread_stack.pop()

        if popped is None:
            return None
        return popped.trace

    def record_span(self, span: Span) -> None:
        """Record a span on active trace; enforce budget abort when configured."""
        context = self.active_context
        if context is None:
            return

        trace = context.trace
        span.step = len(trace.spans) + 1
        trace.spans.append(span)

        if (
            span.status == SpanStatus.SUCCESS
            and context.budget_usd is not None
            and context.on_exceed == "abort"
            and trace.total_cost_usd > context.budget_usd
        ):
            raise DrishtiBudgetError(
                trace=trace,
                budget_usd=context.budget_usd,
                actual_cost_usd=trace.total_cost_usd,
                span_step=span.step,
            )

    @property
    def is_active(self) -> bool:
        """True when there is at least one active trace on the stack."""
        return self.active_context is not None


collector = _Collector()
