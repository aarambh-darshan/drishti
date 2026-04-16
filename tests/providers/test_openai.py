"""Tests for OpenAI provider interceptor."""

from unittest.mock import MagicMock, patch

import pytest

from drishti.collector import collector
from drishti.models.span import SpanStatus
from drishti.models.trace import Trace
from drishti.providers.openai import OpenAIInterceptor


def _make_mock_response(prompt_tokens=100, completion_tokens=50, total_tokens=150):
    """Create a mock OpenAI response object."""
    response = MagicMock()
    response.usage.prompt_tokens = prompt_tokens
    response.usage.completion_tokens = completion_tokens
    response.usage.total_tokens = total_tokens
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Hello!"
    return response


class TestOpenAIInterceptor:
    def test_provider_name(self):
        interceptor = OpenAIInterceptor()
        assert interceptor.provider_name == "openai"

    def test_skip_if_not_installed(self):
        """Should not crash if openai is not installed."""
        interceptor = OpenAIInterceptor()
        # This will attempt to import openai — if not installed, should skip
        interceptor.patch()
        interceptor.unpatch()

    def test_sync_interception(self):
        """Test that sync calls are intercepted and spans recorded."""
        mock_response = _make_mock_response()

        # Create a mock Completions class
        mock_completions_cls = type("Completions", (), {})
        mock_completions_cls.create = MagicMock(return_value=mock_response)

        mock_async_cls = type("AsyncCompletions", (), {})
        mock_async_cls.create = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "openai": MagicMock(),
                "openai.resources": MagicMock(),
                "openai.resources.chat": MagicMock(),
                "openai.resources.chat.completions": MagicMock(
                    Completions=mock_completions_cls,
                    AsyncCompletions=mock_async_cls,
                ),
            },
        ):
            interceptor = OpenAIInterceptor()

            trace = Trace(name="test")
            collector.start_trace(trace)

            interceptor.patch()

            # Call the patched method
            mock_self = MagicMock()
            mock_completions_cls.create(
                mock_self, model="gpt-4o", messages=[{"role": "user", "content": "hi"}]
            )

            interceptor.unpatch()
            collector.end_trace()

            # Verify span was recorded
            assert len(trace.spans) == 1
            span = trace.spans[0]
            assert span.provider == "openai"
            assert span.model == "gpt-4o"
            assert span.status == SpanStatus.SUCCESS
            assert span.tokens.total_tokens == 150

    def test_passthrough_when_not_active(self):
        """When no trace is active, calls should pure passthrough."""
        mock_response = _make_mock_response()

        mock_completions_cls = type("Completions", (), {})
        mock_completions_cls.create = MagicMock(return_value=mock_response)

        mock_async_cls = type("AsyncCompletions", (), {})
        mock_async_cls.create = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "openai": MagicMock(),
                "openai.resources": MagicMock(),
                "openai.resources.chat": MagicMock(),
                "openai.resources.chat.completions": MagicMock(
                    Completions=mock_completions_cls,
                    AsyncCompletions=mock_async_cls,
                ),
            },
        ):
            interceptor = OpenAIInterceptor()
            interceptor.patch()

            # No active trace — should passthrough
            assert not collector.is_active

            mock_self = MagicMock()
            mock_completions_cls.create(mock_self, model="gpt-4o", messages=[])

            interceptor.unpatch()

            # No spans should be recorded
            # (collector has no trace to record to)

    def test_error_captured_and_reraised(self):
        """Errors should be captured in span and re-raised."""
        mock_completions_cls = type("Completions", (), {})
        mock_completions_cls.create = MagicMock(side_effect=ValueError("API Error"))

        mock_async_cls = type("AsyncCompletions", (), {})
        mock_async_cls.create = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "openai": MagicMock(),
                "openai.resources": MagicMock(),
                "openai.resources.chat": MagicMock(),
                "openai.resources.chat.completions": MagicMock(
                    Completions=mock_completions_cls,
                    AsyncCompletions=mock_async_cls,
                ),
            },
        ):
            interceptor = OpenAIInterceptor()

            trace = Trace(name="test")
            collector.start_trace(trace)
            interceptor.patch()

            mock_self = MagicMock()
            with pytest.raises(ValueError, match="API Error"):
                mock_completions_cls.create(mock_self, model="gpt-4o", messages=[])

            interceptor.unpatch()
            collector.end_trace()

            assert len(trace.spans) == 1
            assert trace.spans[0].status == SpanStatus.ERROR
            assert "API Error" in trace.spans[0].error
