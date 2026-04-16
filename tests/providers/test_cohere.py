"""Tests for Cohere provider interceptor."""

from unittest.mock import MagicMock, patch

from drishti.collector import collector
from drishti.models.trace import Trace
from drishti.providers.cohere import CohereInterceptor


def test_cohere_sync_interception() -> None:
    response = MagicMock()
    response.usage.tokens.input_tokens = 70
    response.usage.tokens.output_tokens = 30
    response.usage.tokens.total_tokens = 100

    mock_client = type("ClientV2", (), {})
    mock_client.chat = MagicMock(return_value=response)

    mock_async_client = type("AsyncClientV2", (), {})
    mock_async_client.chat = MagicMock()

    with patch.dict(
        "sys.modules",
        {
            "cohere": MagicMock(ClientV2=mock_client, AsyncClientV2=mock_async_client),
        },
    ):
        interceptor = CohereInterceptor()

        trace = Trace(name="test")
        collector.start_trace(trace)
        interceptor.patch()

        mock_self = MagicMock()
        mock_client.chat(
            mock_self,
            model="command-r",
            messages=[{"role": "user", "content": "hello"}],
        )

        interceptor.unpatch()
        collector.end_trace()

        assert len(trace.spans) == 1
        span = trace.spans[0]
        assert span.provider == "cohere"
        assert span.tokens.total_tokens == 100
