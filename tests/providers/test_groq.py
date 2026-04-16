"""Tests for Groq provider interceptor."""

from unittest.mock import MagicMock, patch


from drishti.collector import collector
from drishti.models.trace import Trace
from drishti.providers.groq import GroqInterceptor


class TestGroqInterceptor:
    def test_provider_name(self):
        interceptor = GroqInterceptor()
        assert interceptor.provider_name == "groq"

    def test_skip_if_not_installed(self):
        interceptor = GroqInterceptor()
        interceptor.patch()
        interceptor.unpatch()

    def test_sync_interception(self):
        mock_response = MagicMock()
        mock_response.usage.prompt_tokens = 200
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 300

        mock_completions_cls = type("Completions", (), {})
        mock_completions_cls.create = MagicMock(return_value=mock_response)

        mock_async_cls = type("AsyncCompletions", (), {})
        mock_async_cls.create = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "groq": MagicMock(),
                "groq.resources": MagicMock(),
                "groq.resources.chat": MagicMock(),
                "groq.resources.chat.completions": MagicMock(
                    Completions=mock_completions_cls,
                    AsyncCompletions=mock_async_cls,
                ),
            },
        ):
            interceptor = GroqInterceptor()

            trace = Trace(name="test")
            collector.start_trace(trace)
            interceptor.patch()

            mock_self = MagicMock()
            mock_completions_cls.create(
                mock_self,
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "hello"}],
            )

            interceptor.unpatch()
            collector.end_trace()

            assert len(trace.spans) == 1
            span = trace.spans[0]
            assert span.provider == "groq"
            assert span.model == "llama-3.3-70b-versatile"
            assert span.tokens.total_tokens == 300
