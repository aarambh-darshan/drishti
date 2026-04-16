"""
Anthropic provider interceptor.

Patches anthropic.resources.messages.Messages.create (sync)
and anthropic.resources.messages.AsyncMessages.create (async)
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


class AnthropicInterceptor(BaseInterceptor):
    """Intercepts Anthropic messages.create calls."""

    provider_name = "anthropic"

    def __init__(self) -> None:
        self._original_create = None
        self._original_async_create = None
        self._patched = False

    def patch(self) -> None:
        """Patch Anthropic SDK methods with instrumented versions."""
        if self._patched:
            return

        try:
            from anthropic.resources.messages import AsyncMessages, Messages
        except ImportError:
            return  # Anthropic not installed, skip silently

        # ── Sync patch ──────────────────────────────────────
        self._original_create = Messages.create

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
                name=f"anthropic/{model}",
                provider="anthropic",
                model=model,
                started_at=datetime.now(timezone.utc),
                input=messages,
            )
            span._perf_start = perf_start

            try:
                response = original_sync(self_sdk, *args, **kwargs)

                # Anthropic uses response.usage.input_tokens / output_tokens
                usage = getattr(response, "usage", None)
                if usage:
                    input_tokens = getattr(usage, "input_tokens", 0) or 0
                    output_tokens = getattr(usage, "output_tokens", 0) or 0
                    tokens = TokenUsage(
                        prompt_tokens=input_tokens,
                        completion_tokens=output_tokens,
                        total_tokens=input_tokens + output_tokens,
                    )
                else:
                    tokens = TokenUsage()

                cost = calculate_cost("anthropic", model, tokens)
                span.finish(output=response, tokens=tokens, cost=cost)

            except Exception as e:
                span.fail(e)
                raise

            finally:
                collector.record_span(span)

            return response

        Messages.create = patched_create

        # ── Async patch ──────────────────────────────────────
        self._original_async_create = AsyncMessages.create

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
                name=f"anthropic/{model}",
                provider="anthropic",
                model=model,
                started_at=datetime.now(timezone.utc),
                input=messages,
            )
            span._perf_start = perf_start

            try:
                response = await original_async(self_sdk, *args, **kwargs)

                usage = getattr(response, "usage", None)
                if usage:
                    input_tokens = getattr(usage, "input_tokens", 0) or 0
                    output_tokens = getattr(usage, "output_tokens", 0) or 0
                    tokens = TokenUsage(
                        prompt_tokens=input_tokens,
                        completion_tokens=output_tokens,
                        total_tokens=input_tokens + output_tokens,
                    )
                else:
                    tokens = TokenUsage()

                cost = calculate_cost("anthropic", model, tokens)
                span.finish(output=response, tokens=tokens, cost=cost)

            except Exception as e:
                span.fail(e)
                raise

            finally:
                collector.record_span(span)

            return response

        AsyncMessages.create = async_patched_create

        self._patched = True

    def unpatch(self) -> None:
        """Restore original Anthropic SDK methods."""
        if not self._patched:
            return

        try:
            from anthropic.resources.messages import AsyncMessages, Messages

            if self._original_create is not None:
                Messages.create = self._original_create
            if self._original_async_create is not None:
                AsyncMessages.create = self._original_async_create
        except ImportError:
            pass

        self._patched = False
