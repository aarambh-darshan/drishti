"""Tests for Anthropic provider interceptor."""

from unittest.mock import MagicMock, patch

import pytest

from drishti.collector import collector
from drishti.models.span import SpanStatus
from drishti.models.trace import Trace
from drishti.providers.anthropic import AnthropicInterceptor


def _make_mock_response(input_tokens=100, output_tokens=50):
    """Create a mock Anthropic response object."""
    response = MagicMock()
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    response.content = [MagicMock()]
    response.content[0].text = "Hello!"
    return response


class TestAnthropicInterceptor:
    def test_provider_name(self):
        interceptor = AnthropicInterceptor()
        assert interceptor.provider_name == "anthropic"

    def test_skip_if_not_installed(self):
        interceptor = AnthropicInterceptor()
        interceptor.patch()
        interceptor.unpatch()

    def test_sync_interception(self):
        mock_response = _make_mock_response()

        mock_messages_cls = type("Messages", (), {})
        mock_messages_cls.create = MagicMock(return_value=mock_response)

        mock_async_cls = type("AsyncMessages", (), {})
        mock_async_cls.create = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "anthropic": MagicMock(),
                "anthropic.resources": MagicMock(),
                "anthropic.resources.messages": MagicMock(
                    Messages=mock_messages_cls,
                    AsyncMessages=mock_async_cls,
                ),
            },
        ):
            interceptor = AnthropicInterceptor()

            trace = Trace(name="test")
            collector.start_trace(trace)
            interceptor.patch()

            mock_self = MagicMock()
            mock_messages_cls.create(
                mock_self,
                model="claude-3-5-sonnet-20241022",
                messages=[{"role": "user", "content": "hi"}],
            )

            interceptor.unpatch()
            collector.end_trace()

            assert len(trace.spans) == 1
            span = trace.spans[0]
            assert span.provider == "anthropic"
            assert span.model == "claude-3-5-sonnet-20241022"
            assert span.status == SpanStatus.SUCCESS
            assert span.tokens.prompt_tokens == 100
            assert span.tokens.completion_tokens == 50
            assert span.tokens.total_tokens == 150

    def test_error_captured(self):
        mock_messages_cls = type("Messages", (), {})
        mock_messages_cls.create = MagicMock(side_effect=RuntimeError("Rate limited"))

        mock_async_cls = type("AsyncMessages", (), {})
        mock_async_cls.create = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "anthropic": MagicMock(),
                "anthropic.resources": MagicMock(),
                "anthropic.resources.messages": MagicMock(
                    Messages=mock_messages_cls,
                    AsyncMessages=mock_async_cls,
                ),
            },
        ):
            interceptor = AnthropicInterceptor()

            trace = Trace(name="test")
            collector.start_trace(trace)
            interceptor.patch()

            mock_self = MagicMock()
            with pytest.raises(RuntimeError):
                mock_messages_cls.create(
                    mock_self,
                    model="claude-3-5-sonnet-20241022",
                    messages=[],
                )

            interceptor.unpatch()
            collector.end_trace()

            assert trace.spans[0].status == SpanStatus.ERROR
