"""Tests for JSON export."""

import json
import shutil
from pathlib import Path

import pytest

from drishti.export.json import export_trace
from drishti.models.span import Span, SpanStatus, TokenUsage
from drishti.models.trace import Trace, TraceStatus


TEST_TRACES_DIR = ".drishti/test_traces"


@pytest.fixture(autouse=True)
def cleanup_test_traces():
    """Clean up test traces dir after each test."""
    yield
    test_dir = Path(TEST_TRACES_DIR)
    if test_dir.exists():
        shutil.rmtree(test_dir)


class TestExportTrace:
    def test_creates_directory(self):
        trace = Trace(name="test-export", status=TraceStatus.SUCCESS)
        path = export_trace(trace, traces_dir=TEST_TRACES_DIR)

        assert Path(TEST_TRACES_DIR).exists()
        assert path.exists()

    def test_filename_format(self):
        trace = Trace(name="my-agent", status=TraceStatus.SUCCESS)
        path = export_trace(trace, traces_dir=TEST_TRACES_DIR)

        # Should be YYYYMMDD_HHMMSS_my_agent.json
        assert path.suffix == ".json"
        assert "my_agent" in path.stem or "my-agent" in path.stem

    def test_json_structure(self):
        span = Span(
            step=1,
            name="openai/gpt-4o",
            provider="openai",
            model="gpt-4o",
            status=SpanStatus.SUCCESS,
            tokens=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            cost_usd=0.0035,
            latency_ms=200.0,
        )
        trace = Trace(
            name="test-export",
            spans=[span],
            status=TraceStatus.SUCCESS,
        )

        path = export_trace(trace, traces_dir=TEST_TRACES_DIR)
        data = json.loads(path.read_text())

        # Top-level fields
        assert "trace_id" in data
        assert data["name"] == "test-export"
        assert data["status"] == "success"

        # Summary block
        assert "summary" in data
        assert data["summary"]["total_tokens"] == 150
        assert data["summary"]["span_count"] == 1

        # Spans
        assert len(data["spans"]) == 1
        assert data["spans"][0]["provider"] == "openai"
        assert data["spans"][0]["model"] == "gpt-4o"
        assert data["spans"][0]["tokens"]["total"] == 150

    def test_error_span_serialization(self):
        span = Span(
            step=1,
            name="openai/gpt-4o",
            provider="openai",
            model="gpt-4o",
            status=SpanStatus.ERROR,
            error="Connection timeout",
            error_type="TimeoutError",
        )
        trace = Trace(name="error-test", spans=[span], status=TraceStatus.ERROR)

        path = export_trace(trace, traces_dir=TEST_TRACES_DIR)
        data = json.loads(path.read_text())

        assert data["spans"][0]["status"] == "error"
        assert data["spans"][0]["error"] == "Connection timeout"
        assert data["spans"][0]["error_type"] == "TimeoutError"

    def test_multiple_exports(self):
        trace1 = Trace(name="agent-1", status=TraceStatus.SUCCESS)
        trace2 = Trace(name="agent-2", status=TraceStatus.SUCCESS)

        path1 = export_trace(trace1, traces_dir=TEST_TRACES_DIR)
        path2 = export_trace(trace2, traces_dir=TEST_TRACES_DIR)

        assert path1.exists()
        assert path2.exists()
        assert path1 != path2
