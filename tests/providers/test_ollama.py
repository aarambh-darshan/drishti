"""Tests for Ollama provider interceptor."""

from unittest.mock import MagicMock, patch


from drishti.collector import collector
from drishti.models.trace import Trace
from drishti.providers.ollama import OllamaInterceptor


class TestOllamaInterceptor:
    def test_provider_name(self):
        interceptor = OllamaInterceptor()
        assert interceptor.provider_name == "ollama"

    def test_skip_if_not_installed(self):
        interceptor = OllamaInterceptor()
        interceptor.patch()
        interceptor.unpatch()

    def test_sync_interception_dict_response(self):
        """Ollama returns dict responses."""
        mock_response = {
            "model": "llama3.2",
            "message": {"role": "assistant", "content": "Hello!"},
            "prompt_eval_count": 50,
            "eval_count": 30,
        }

        mock_ollama = MagicMock()
        mock_ollama.chat = MagicMock(return_value=mock_response)

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            interceptor = OllamaInterceptor()

            trace = Trace(name="test")
            collector.start_trace(trace)
            interceptor.patch()

            # Call the patched function
            mock_ollama.chat(model="llama3.2", messages=[{"role": "user", "content": "hi"}])

            interceptor.unpatch()
            collector.end_trace()

            assert len(trace.spans) == 1
            span = trace.spans[0]
            assert span.provider == "ollama"
            assert span.tokens.prompt_tokens == 50
            assert span.tokens.completion_tokens == 30
            assert span.cost_usd == 0.0  # Ollama is always free
