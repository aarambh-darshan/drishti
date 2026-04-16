"""Cohere provider interceptor."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from ..collector import collector
from ..cost.calculator import calculate_cost
from ..models.span import Span
from .base import BaseInterceptor
from .common import cohere_usage_from_response
from .missing import warn_missing_sdk


def _jsonable(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=str, ensure_ascii=False))
    except Exception:
        return str(value)


class CohereInterceptor(BaseInterceptor):
    """Intercept Cohere chat calls."""

    provider_name = "cohere"

    def __init__(self) -> None:
        self._original_chat = None
        self._original_async_chat = None
        self._patched = False

    def patch(self) -> None:
        if self._patched:
            return

        try:
            from cohere import AsyncClientV2, ClientV2
        except ImportError:
            warn_missing_sdk("cohere", "cohere", "cohere")
            return

        self._original_chat = ClientV2.chat
        original_sync = self._original_chat

        def patched_chat(self_sdk: Any, *args: Any, **kwargs: Any) -> Any:
            if not collector.is_active:
                return original_sync(self_sdk, *args, **kwargs)

            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            span = Span(
                span_id=str(uuid.uuid4()),
                step=0,
                name=f"cohere/{model}",
                provider="cohere",
                model=model,
                started_at=datetime.now(timezone.utc),
                input=messages,
                request_payload={"method": "chat", "kwargs": _jsonable(kwargs)},
            )
            span._perf_start = time.perf_counter()

            try:
                response = original_sync(self_sdk, *args, **kwargs)
                tokens = cohere_usage_from_response(response)
                cost = calculate_cost("cohere", model, tokens)
                span.finish(output=response, tokens=tokens, cost=cost)
            except Exception as exc:
                span.fail(exc)
                raise
            finally:
                collector.record_span(span)

            return response

        ClientV2.chat = patched_chat

        self._original_async_chat = AsyncClientV2.chat
        original_async = self._original_async_chat

        async def async_patched_chat(self_sdk: Any, *args: Any, **kwargs: Any) -> Any:
            if not collector.is_active:
                return await original_async(self_sdk, *args, **kwargs)

            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            span = Span(
                span_id=str(uuid.uuid4()),
                step=0,
                name=f"cohere/{model}",
                provider="cohere",
                model=model,
                started_at=datetime.now(timezone.utc),
                input=messages,
                request_payload={"method": "chat", "kwargs": _jsonable(kwargs)},
            )
            span._perf_start = time.perf_counter()

            try:
                response = await original_async(self_sdk, *args, **kwargs)
                tokens = cohere_usage_from_response(response)
                cost = calculate_cost("cohere", model, tokens)
                span.finish(output=response, tokens=tokens, cost=cost)
            except Exception as exc:
                span.fail(exc)
                raise
            finally:
                collector.record_span(span)

            return response

        AsyncClientV2.chat = async_patched_chat

        self._patched = True

    def unpatch(self) -> None:
        if not self._patched:
            return

        try:
            from cohere import AsyncClientV2, ClientV2

            if self._original_chat is not None:
                ClientV2.chat = self._original_chat
            if self._original_async_chat is not None:
                AsyncClientV2.chat = self._original_async_chat
        except ImportError:
            pass

        self._patched = False
