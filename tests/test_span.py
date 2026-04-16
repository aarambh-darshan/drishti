"""Tests for Span model."""

from drishti.models.span import Span, SpanStatus, TokenUsage


class TestTokenUsage:
    def test_default_values(self):
        t = TokenUsage()
        assert t.prompt_tokens == 0
        assert t.completion_tokens == 0
        assert t.total_tokens == 0

    def test_custom_values(self):
        t = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert t.prompt_tokens == 100
        assert t.completion_tokens == 50
        assert t.total_tokens == 150


class TestSpanStatus:
    def test_values(self):
        assert SpanStatus.PENDING == "pending"
        assert SpanStatus.SUCCESS == "success"
        assert SpanStatus.ERROR == "error"

    def test_is_string(self):
        assert isinstance(SpanStatus.SUCCESS, str)


class TestSpan:
    def test_creation_defaults(self):
        span = Span()
        assert span.span_id  # UUID generated
        assert span.step == 0
        assert span.status == SpanStatus.PENDING
        assert span.cost_usd == 0.0
        assert span.latency_ms == 0.0
        assert span.error is None
        assert span.streaming is False
        assert span.estimated_tokens is False

    def test_creation_with_values(self):
        span = Span(
            span_id="test-id",
            step=1,
            name="openai/gpt-4o",
            provider="openai",
            model="gpt-4o",
        )
        assert span.span_id == "test-id"
        assert span.step == 1
        assert span.name == "openai/gpt-4o"
        assert span.provider == "openai"
        assert span.model == "gpt-4o"

    def test_finish(self):
        span = Span(
            name="openai/gpt-4o",
            provider="openai",
            model="gpt-4o",
        )
        tokens = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        span.finish(output={"result": "ok"}, tokens=tokens, cost=0.0035)

        assert span.status == SpanStatus.SUCCESS
        assert span.output == {"result": "ok"}
        assert span.tokens.total_tokens == 150
        assert span.cost_usd == 0.0035
        assert span.ended_at is not None
        assert span.latency_ms > 0

    def test_fail(self):
        span = Span(
            name="openai/gpt-4o",
            provider="openai",
            model="gpt-4o",
        )

        span.fail(ValueError("bad request"))

        assert span.status == SpanStatus.ERROR
        assert span.error == "bad request"
        assert span.error_type == "ValueError"
        assert span.ended_at is not None
        assert span.latency_ms >= 0

    def test_latency_seconds(self):
        span = Span()
        span.latency_ms = 1500.0
        assert span.latency_seconds == 1.5

    def test_unique_span_ids(self):
        spans = [Span() for _ in range(100)]
        ids = {s.span_id for s in spans}
        assert len(ids) == 100  # All unique
