"""Tests for Collector."""

import threading

from drishti.collector import collector
from drishti.models.span import Span
from drishti.models.trace import Trace


class TestCollector:
    def test_not_active_by_default(self):
        assert not collector.is_active
        assert collector.active_trace is None

    def test_start_and_end_trace(self):
        trace = Trace(name="test")
        collector.start_trace(trace)

        assert collector.is_active
        assert collector.active_trace is trace

        returned = collector.end_trace()
        assert returned is trace
        assert not collector.is_active

    def test_record_span_auto_step(self):
        trace = Trace(name="test")
        collector.start_trace(trace)

        span1 = Span(name="span-1")
        span2 = Span(name="span-2")
        span3 = Span(name="span-3")

        collector.record_span(span1)
        collector.record_span(span2)
        collector.record_span(span3)

        assert span1.step == 1
        assert span2.step == 2
        assert span3.step == 3
        assert len(trace.spans) == 3

    def test_record_span_no_active_trace(self):
        span = Span(name="orphan")
        # Should not raise — silently ignores
        collector.record_span(span)
        assert span.step == 0  # Not assigned

    def test_thread_isolation(self):
        """Verify that two threads have independent traces."""
        results = {}

        def thread_fn(name):
            trace = Trace(name=name)
            collector.start_trace(trace)
            span = Span(name=f"span-{name}")
            collector.record_span(span)
            results[name] = {
                "trace_name": collector.active_trace.name,
                "span_count": len(collector.active_trace.spans),
            }
            collector.end_trace()

        t1 = threading.Thread(target=thread_fn, args=("thread-1",))
        t2 = threading.Thread(target=thread_fn, args=("thread-2",))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results["thread-1"]["trace_name"] == "thread-1"
        assert results["thread-2"]["trace_name"] == "thread-2"
        assert results["thread-1"]["span_count"] == 1
        assert results["thread-2"]["span_count"] == 1

    def test_end_trace_returns_none_when_no_trace(self):
        result = collector.end_trace()
        assert result is None
