"""Tests for Trace model."""

from datetime import datetime, timedelta, timezone

from drishti.models.span import Span, SpanStatus, TokenUsage
from drishti.models.trace import Trace, TraceStatus


class TestTraceStatus:
    def test_values(self):
        assert TraceStatus.RUNNING == "running"
        assert TraceStatus.SUCCESS == "success"
        assert TraceStatus.ERROR == "error"


class TestTrace:
    def test_creation_defaults(self):
        trace = Trace()
        assert trace.trace_id  # UUID generated
        assert trace.spans == []
        assert trace.status == TraceStatus.RUNNING

    def test_total_tokens_empty(self):
        trace = Trace()
        assert trace.total_tokens.total_tokens == 0

    def test_total_tokens_aggregation(self):
        span1 = Span(tokens=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150))
        span2 = Span(tokens=TokenUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300))
        trace = Trace(spans=[span1, span2])

        total = trace.total_tokens
        assert total.prompt_tokens == 300
        assert total.completion_tokens == 150
        assert total.total_tokens == 450

    def test_total_cost_usd(self):
        span1 = Span(cost_usd=0.0035)
        span2 = Span(cost_usd=0.0100)
        trace = Trace(spans=[span1, span2])

        assert trace.total_cost_usd == 0.0135

    def test_total_latency_ms(self):
        start = datetime(2026, 4, 16, 12, 0, 0, tzinfo=timezone.utc)
        end = start + timedelta(seconds=2)
        trace = Trace(started_at=start, ended_at=end)

        assert trace.total_latency_ms == 2000.0

    def test_total_latency_ms_no_end(self):
        trace = Trace()
        assert trace.total_latency_ms == 0.0

    def test_span_count(self):
        trace = Trace(spans=[Span(), Span(), Span()])
        assert trace.span_count == 3

    def test_failed_spans(self):
        ok_span = Span(status=SpanStatus.SUCCESS)
        err_span1 = Span(status=SpanStatus.ERROR)
        err_span2 = Span(status=SpanStatus.ERROR)
        trace = Trace(spans=[ok_span, err_span1, err_span2])

        assert len(trace.failed_spans) == 2
        assert all(s.status == SpanStatus.ERROR for s in trace.failed_spans)

    def test_failed_spans_empty(self):
        trace = Trace(spans=[Span(status=SpanStatus.SUCCESS)])
        assert len(trace.failed_spans) == 0
