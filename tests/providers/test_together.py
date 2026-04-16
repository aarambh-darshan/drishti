"""Tests for Together provider interceptor."""

from unittest.mock import MagicMock, patch

from drishti.collector import collector
from drishti.models.trace import Trace
from drishti.providers.together import TogetherInterceptor


def test_together_sync_interception() -> None:
    mock_response = MagicMock()
    mock_response.usage.prompt_tokens = 80
    mock_response.usage.completion_tokens = 20
    mock_response.usage.total_tokens = 100

    mock_completions_cls = type("Completions", (), {})
    mock_completions_cls.create = MagicMock(return_value=mock_response)

    mock_async_cls = type("AsyncCompletions", (), {})
    mock_async_cls.create = MagicMock()

    with patch.dict(
        "sys.modules",
        {
            "together": MagicMock(),
            "together.resources": MagicMock(),
            "together.resources.chat": MagicMock(),
            "together.resources.chat.completions": MagicMock(
                Completions=mock_completions_cls,
                AsyncCompletions=mock_async_cls,
            ),
        },
    ):
        interceptor = TogetherInterceptor()

        trace = Trace(name="test")
        collector.start_trace(trace)
        interceptor.patch()

        mock_self = MagicMock()
        mock_completions_cls.create(
            mock_self,
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
            messages=[{"role": "user", "content": "hello"}],
        )

        interceptor.unpatch()
        collector.end_trace()

        assert len(trace.spans) == 1
        span = trace.spans[0]
        assert span.provider == "together"
        assert span.tokens.total_tokens == 100
