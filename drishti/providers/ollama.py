"""
Ollama provider interceptor.

Patches ollama.chat (sync) and ollama.AsyncClient.chat (async)
to capture LLM calls as Spans.

Ollama returns a dict-based response, unlike the pydantic-model
responses from OpenAI/Anthropic/Groq. Token info comes from
'eval_count' and 'prompt_eval_count' keys.

Cost is always $0.00 — Ollama runs locally.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

from ..collector import collector
from ..cost.calculator import calculate_cost
from ..models.span import Span, TokenUsage
from .base import BaseInterceptor


class OllamaInterceptor(BaseInterceptor):
    """Intercepts Ollama chat calls."""

    provider_name = "ollama"

    def __init__(self) -> None:
        self._original_chat = None
        self._original_async_chat = None
        self._patched = False

    def patch(self) -> None:
        """Patch Ollama SDK methods with instrumented versions."""
        if self._patched:
            return

        try:
            import ollama as ollama_module
        except ImportError:
            return  # Ollama not installed, skip silently

        # ── Sync patch ──────────────────────────────────────
        self._original_chat = ollama_module.chat

        original_sync = self._original_chat

        def patched_chat(*args: Any, **kwargs: Any) -> Any:
            if not collector.is_active:
                return original_sync(*args, **kwargs)

            model = kwargs.get("model", args[0] if args else "unknown")
            messages = kwargs.get("messages", args[1] if len(args) > 1 else [])
            perf_start = time.perf_counter()

            span = Span(
                span_id=str(uuid.uuid4()),
                step=0,
                name=f"ollama/{model}",
                provider="ollama",
                model=model,
                started_at=datetime.now(timezone.utc),
                input=messages,
            )
            span._perf_start = perf_start

            try:
                response = original_sync(*args, **kwargs)

                # Ollama returns a dict with eval_count / prompt_eval_count
                if isinstance(response, dict):
                    prompt_tokens = response.get("prompt_eval_count", 0) or 0
                    completion_tokens = response.get("eval_count", 0) or 0
                else:
                    prompt_tokens = getattr(response, "prompt_eval_count", 0) or 0
                    completion_tokens = getattr(response, "eval_count", 0) or 0

                tokens = TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                )

                cost = calculate_cost("ollama", model, tokens)  # Always $0.00
                span.finish(output=response, tokens=tokens, cost=cost)

            except Exception as e:
                span.fail(e)
                raise

            finally:
                collector.record_span(span)

            return response

        ollama_module.chat = patched_chat

        # ── Async patch ──────────────────────────────────────
        try:
            from ollama import AsyncClient

            self._original_async_chat = AsyncClient.chat

            original_async = self._original_async_chat

            async def async_patched_chat(self_sdk: Any, *args: Any, **kwargs: Any) -> Any:
                if not collector.is_active:
                    return await original_async(self_sdk, *args, **kwargs)

                model = kwargs.get("model", args[0] if args else "unknown")
                messages = kwargs.get("messages", args[1] if len(args) > 1 else [])
                perf_start = time.perf_counter()

                span = Span(
                    span_id=str(uuid.uuid4()),
                    step=0,
                    name=f"ollama/{model}",
                    provider="ollama",
                    model=model,
                    started_at=datetime.now(timezone.utc),
                    input=messages,
                )
                span._perf_start = perf_start

                try:
                    response = await original_async(self_sdk, *args, **kwargs)

                    if isinstance(response, dict):
                        prompt_tokens = response.get("prompt_eval_count", 0) or 0
                        completion_tokens = response.get("eval_count", 0) or 0
                    else:
                        prompt_tokens = getattr(response, "prompt_eval_count", 0) or 0
                        completion_tokens = getattr(response, "eval_count", 0) or 0

                    tokens = TokenUsage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=prompt_tokens + completion_tokens,
                    )

                    cost = calculate_cost("ollama", model, tokens)
                    span.finish(output=response, tokens=tokens, cost=cost)

                except Exception as e:
                    span.fail(e)
                    raise

                finally:
                    collector.record_span(span)

                return response

            AsyncClient.chat = async_patched_chat

        except (ImportError, AttributeError):
            pass  # AsyncClient not available in older ollama versions

        self._patched = True

    def unpatch(self) -> None:
        """Restore original Ollama SDK methods."""
        if not self._patched:
            return

        try:
            import ollama as ollama_module

            if self._original_chat is not None:
                ollama_module.chat = self._original_chat
        except ImportError:
            pass

        try:
            from ollama import AsyncClient

            if self._original_async_chat is not None:
                AsyncClient.chat = self._original_async_chat
        except (ImportError, AttributeError):
            pass

        self._patched = False
