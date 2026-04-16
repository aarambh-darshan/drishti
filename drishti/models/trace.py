"""Trace model — the complete record of one @trace-decorated function call."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .span import Span, SpanStatus, TokenUsage


class TraceStatus(str, Enum):
    """Status of the overall trace."""

    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


@dataclass(slots=True)
class Trace:
    """Complete record of one @trace-decorated function execution."""

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None

    spans: list[Span] = field(default_factory=list)

    status: TraceStatus = TraceStatus.RUNNING

    @property
    def total_tokens(self) -> TokenUsage:
        """Sum token usage across all spans."""
        return TokenUsage(
            prompt_tokens=sum(s.tokens.prompt_tokens for s in self.spans),
            completion_tokens=sum(s.tokens.completion_tokens for s in self.spans),
            total_tokens=sum(s.tokens.total_tokens for s in self.spans),
        )

    @property
    def total_cost_usd(self) -> float:
        """Sum cost across all spans."""
        return round(sum(s.cost_usd for s in self.spans), 6)

    @property
    def total_latency_ms(self) -> float:
        """Wall time from started_at to ended_at."""
        if self.ended_at is None:
            return 0.0
        delta = self.ended_at - self.started_at
        return delta.total_seconds() * 1000

    @property
    def span_count(self) -> int:
        """Number of spans in this trace."""
        return len(self.spans)

    @property
    def failed_spans(self) -> list[Span]:
        """List of spans that failed."""
        return [s for s in self.spans if s.status == SpanStatus.ERROR]
