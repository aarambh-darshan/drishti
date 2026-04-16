"""Shared test fixtures for Drishti."""

import uuid
from datetime import datetime, timezone

import pytest

from drishti.collector import collector
from drishti.config import reset_config
from drishti.models.span import Span, TokenUsage
from drishti.models.trace import Trace, TraceStatus
from drishti.providers.manager import patch_manager
from drishti.token_estimation import reset_token_estimation_warnings


@pytest.fixture(autouse=True)
def _reset_collector():
    """Ensure collector is clean before and after each test."""
    collector.end_trace()
    yield
    collector.end_trace()


@pytest.fixture(autouse=True)
def _reset_config():
    """Reset config cache between tests."""
    reset_config()
    yield
    reset_config()


@pytest.fixture(autouse=True)
def _reset_runtime_globals():
    """Reset shared global runtime state between tests."""
    patch_manager.reset()
    reset_token_estimation_warnings()
    yield
    patch_manager.reset()


@pytest.fixture
def sample_tokens() -> TokenUsage:
    """A sample TokenUsage for testing."""
    return TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)


@pytest.fixture
def sample_span(sample_tokens: TokenUsage) -> Span:
    """A completed sample Span."""
    span = Span(
        span_id=str(uuid.uuid4()),
        step=1,
        name="openai/gpt-4o",
        provider="openai",
        model="gpt-4o",
        started_at=datetime(2026, 4, 16, 12, 0, 0, tzinfo=timezone.utc),
    )
    span.finish(
        output={"choices": [{"message": {"content": "Hello!"}}]},
        tokens=sample_tokens,
        cost=0.0035,
    )
    return span


@pytest.fixture
def error_span() -> Span:
    """A failed sample Span."""
    span = Span(
        span_id=str(uuid.uuid4()),
        step=2,
        name="anthropic/claude-3-5-sonnet",
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        started_at=datetime(2026, 4, 16, 12, 0, 1, tzinfo=timezone.utc),
    )
    span.fail(ValueError("Invalid API key"))
    return span


@pytest.fixture
def sample_trace(sample_span: Span, error_span: Span) -> Trace:
    """A sample Trace with two spans."""
    trace = Trace(
        trace_id=str(uuid.uuid4()),
        name="test-agent",
        started_at=datetime(2026, 4, 16, 12, 0, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 4, 16, 12, 0, 2, tzinfo=timezone.utc),
        spans=[sample_span, error_span],
        status=TraceStatus.ERROR,
    )
    return trace
