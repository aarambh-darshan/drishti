"""Tests for Mistral provider interceptor."""

from unittest.mock import MagicMock, patch

from drishti.collector import collector
from drishti.models.trace import Trace
from drishti.providers.mistral import MistralInterceptor


def test_mistral_sync_interception() -> None:
    mock_response = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150

    mock_completions_cls = type("Completions", (), {})
    mock_completions_cls.create = MagicMock(return_value=mock_response)

    mock_async_cls = type("AsyncCompletions", (), {})
    mock_async_cls.create = MagicMock()

    with patch.dict(
        "sys.modules",
        {
            "mistralai": MagicMock(),
            "mistralai.resources": MagicMock(),
            "mistralai.resources.chat": MagicMock(),
            "mistralai.resources.chat.completions": MagicMock(
                Completions=mock_completions_cls,
                AsyncCompletions=mock_async_cls,
            ),
        },
    ):
        interceptor = MistralInterceptor()

        trace = Trace(name="test")
        collector.start_trace(trace)
        interceptor.patch()

        mock_self = MagicMock()
        mock_completions_cls.create(
            mock_self,
            model="mistral-large-latest",
            messages=[{"role": "user", "content": "hi"}],
        )

        interceptor.unpatch()
        collector.end_trace()

        assert len(trace.spans) == 1
        span = trace.spans[0]
        assert span.provider == "mistral"
        assert span.model == "mistral-large-latest"
        assert span.tokens.total_tokens == 150
