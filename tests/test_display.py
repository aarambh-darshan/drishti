"""Tests for display engine."""

from rich.console import Console

from drishti.display.summary import render_summary, render_summary_from_dict
from drishti.display.tree import render_trace_from_dict, render_trace_tree
from drishti.models.span import Span, SpanStatus, TokenUsage
from drishti.models.trace import Trace, TraceStatus


class TestTreeRenderer:
    def test_render_trace_tree(self, sample_trace):
        """Verify tree renders without error."""
        Console(record=True, file=open("/dev/null", "w"))
        # Just ensure it doesn't crash — output goes to /dev/null
        render_trace_tree(sample_trace)

    def test_render_trace_tree_empty(self):
        """Empty trace should still render."""
        trace = Trace(name="empty")
        render_trace_tree(trace)

    def test_render_from_dict(self):
        """Dict-based rendering should not crash."""
        data = {
            "name": "test",
            "status": "success",
            "spans": [
                {
                    "step": 1,
                    "name": "openai/gpt-4o",
                    "status": "success",
                    "tokens": {"total": 150},
                    "cost_usd": 0.001,
                    "latency_ms": 200,
                },
                {
                    "step": 2,
                    "name": "anthropic/claude",
                    "status": "error",
                    "tokens": {"total": 0},
                    "cost_usd": 0.0,
                    "latency_ms": 50,
                    "error": "API Error",
                    "error_type": "APIError",
                },
            ],
        }
        render_trace_from_dict(data)


class TestSummaryRenderer:
    def test_render_summary(self, sample_trace):
        """Verify summary renders without error."""
        render_summary(sample_trace)

    def test_render_summary_success_trace(self):
        span = Span(
            status=SpanStatus.SUCCESS,
            tokens=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            cost_usd=0.001,
        )
        trace = Trace(name="test", spans=[span], status=TraceStatus.SUCCESS)
        render_summary(trace)

    def test_render_summary_from_dict(self):
        data = {
            "name": "test",
            "status": "success",
            "summary": {
                "total_tokens": 150,
                "total_cost_usd": 0.001,
                "total_latency_ms": 200,
                "span_count": 1,
            },
        }
        render_summary_from_dict(data)
