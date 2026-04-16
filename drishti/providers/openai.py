"""
OpenAI provider interceptor.

Patches openai.resources.chat.completions.Completions.create (sync)
and openai.resources.chat.completions.AsyncCompletions.create (async)
to capture LLM calls as Spans.
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


class OpenAIInterceptor(BaseInterceptor):
    """Intercepts OpenAI chat completion calls."""

    provider_name = "openai"

    def __init__(self) -> None:
        self._original_create = None
        self._original_async_create = None
        self._patched = False

    def patch(self) -> None:
        """Patch OpenAI SDK methods with instrumented versions."""
        if self._patched:
            return

        try:
            from openai.resources.chat.completions import AsyncCompletions, Completions
        except ImportError:
            return  # OpenAI not installed, skip silently

        # ── Sync patch ──────────────────────────────────────
        self._original_create = Completions.create

        original_sync = self._original_create

        def patched_create(self_sdk: Any, *args: Any, **kwargs: Any) -> Any:
            if not collector.is_active:
                return original_sync(self_sdk, *args, **kwargs)

            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            perf_start = time.perf_counter()

            span = Span(
                span_id=str(uuid.uuid4()),
                step=0,
                name=f"openai/{model}",
                provider="openai",
                model=model,
                started_at=datetime.now(timezone.utc),
                input=messages,
            )
            span._perf_start = perf_start

            try:
                response = original_sync(self_sdk, *args, **kwargs)

                usage = getattr(response, "usage", None)
                if usage:
                    tokens = TokenUsage(
                        prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                        completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                        total_tokens=getattr(usage, "total_tokens", 0) or 0,
                    )
                else:
                    tokens = TokenUsage()

                cost = calculate_cost("openai", model, tokens)
                span.finish(output=response, tokens=tokens, cost=cost)

            except Exception as e:
                span.fail(e)
                raise  # Always re-raise — never swallow user errors

            finally:
                collector.record_span(span)

            return response

        Completions.create = patched_create

        # ── Async patch ──────────────────────────────────────
        self._original_async_create = AsyncCompletions.create

        original_async = self._original_async_create

        async def async_patched_create(self_sdk: Any, *args: Any, **kwargs: Any) -> Any:
            if not collector.is_active:
                return await original_async(self_sdk, *args, **kwargs)

            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            perf_start = time.perf_counter()

            span = Span(
                span_id=str(uuid.uuid4()),
                step=0,
                name=f"openai/{model}",
                provider="openai",
                model=model,
                started_at=datetime.now(timezone.utc),
                input=messages,
            )
            span._perf_start = perf_start

            try:
                response = await original_async(self_sdk, *args, **kwargs)

                usage = getattr(response, "usage", None)
                if usage:
                    tokens = TokenUsage(
                        prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                        completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                        total_tokens=getattr(usage, "total_tokens", 0) or 0,
                    )
                else:
                    tokens = TokenUsage()

                cost = calculate_cost("openai", model, tokens)
                span.finish(output=response, tokens=tokens, cost=cost)

            except Exception as e:
                span.fail(e)
                raise

            finally:
                collector.record_span(span)

            return response

        AsyncCompletions.create = async_patched_create

        self._patched = True

    def unpatch(self) -> None:
        """Restore original OpenAI SDK methods."""
        if not self._patched:
            return

        try:
            from openai.resources.chat.completions import AsyncCompletions, Completions

            if self._original_create is not None:
                Completions.create = self._original_create
            if self._original_async_create is not None:
                AsyncCompletions.create = self._original_async_create
        except ImportError:
            pass

        self._patched = False
