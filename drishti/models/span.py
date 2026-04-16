"""Span model — represents a single LLM API call."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SpanStatus(str, Enum):
    """Status of a single LLM call."""

    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"


@dataclass(slots=True)
class TokenUsage:
    """Token counts for a single LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(slots=True)
class Span:
    """A single LLM API call within a trace."""

    # Identity
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    step: int = 0
    name: str = ""

    # Provider info
    provider: str = ""
    model: str = ""

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None

    # I/O
    input: Any = None
    output: Any = None

    # Replay payload (JSON-serializable normalized request shape)
    request_payload: dict[str, Any] | None = None

    # Metrics
    tokens: TokenUsage = field(default_factory=TokenUsage)
    cost_usd: float = 0.0
    latency_ms: float = 0.0

    # Streaming metadata
    streaming: bool = False
    estimated_tokens: bool = False
    estimation_source: str | None = None

    # Status
    status: SpanStatus = SpanStatus.PENDING
    error: str | None = None
    error_type: str | None = None

    # Internal timing reference (not serialized)
    _perf_start: float = field(default_factory=time.perf_counter, repr=False)

    def finish(self, output: Any, tokens: TokenUsage, cost: float) -> None:
        """Mark span as successful and fill metrics."""
        self.output = output
        self.tokens = tokens
        self.cost_usd = cost
        self.status = SpanStatus.SUCCESS
        self.ended_at = datetime.now(timezone.utc)
        self.latency_ms = (time.perf_counter() - self._perf_start) * 1000

    def fail(self, error: Exception) -> None:
        """Mark span as failed."""
        self.status = SpanStatus.ERROR
        self.error = str(error)
        self.error_type = type(error).__name__
        self.ended_at = datetime.now(timezone.utc)
        self.latency_ms = (time.perf_counter() - self._perf_start) * 1000

    @property
    def latency_seconds(self) -> float:
        """Latency in seconds."""
        return self.latency_ms / 1000
