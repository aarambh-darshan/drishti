"""
Span model — represents a single LLM API call.

A Span is the atomic unit of a trace. It captures everything about one
LLM invocation: provider, model, input/output, token usage, cost,
latency, and error state.
"""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class SpanStatus(str, Enum):
    """Status of a single LLM call."""

    PENDING = "pending"  # call started, not yet complete
    SUCCESS = "success"  # call returned successfully
    ERROR = "error"  # call raised an exception


@dataclass
class TokenUsage:
    """Token counts for a single LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class Span:
    """
    A single LLM API call within a trace.

    Created by provider interceptors when an LLM SDK method is called.
    The interceptor fills in inputs before the call, then completes the
    span with outputs/metrics after the call returns (or fails).
    """

    # Identity
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    step: int = 0  # 1-indexed position in trace, set by Collector
    name: str = ""  # Human label, e.g. "openai/gpt-4o"

    # Provider info
    provider: str = ""  # "openai" | "anthropic" | "groq" | "ollama"
    model: str = ""  # e.g. "gpt-4o", "claude-3-5-sonnet-20241022"

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None

    # I/O (stored as raw Python objects for flexibility)
    input: Any = None  # The messages/prompt sent to the LLM
    output: Any = None  # The full response object

    # Metrics
    tokens: TokenUsage = field(default_factory=TokenUsage)
    cost_usd: float = 0.0
    latency_ms: float = 0.0

    # Status
    status: SpanStatus = SpanStatus.PENDING
    error: Optional[str] = None  # Exception message if status=ERROR
    error_type: Optional[str] = None  # Exception class name

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
