"""Together provider interceptor."""

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
from .common import openai_usage_from_response
from .missing import warn_missing_sdk


def _jsonable(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=str, ensure_ascii=False))
    except Exception:
        return str(value)


class TogetherInterceptor(BaseInterceptor):
    """Intercept Together chat completions."""

    provider_name = "together"

    def __init__(self) -> None:
        self._original_create = None
        self._original_async_create = None
        self._patched = False

    def patch(self) -> None:
        if self._patched:
            return

        try:
            from together.resources.chat.completions import AsyncCompletions, Completions
        except ImportError:
            warn_missing_sdk("together", "together", "together")
            return

        self._original_create = Completions.create
        original_sync = self._original_create

        def patched_create(self_sdk: Any, *args: Any, **kwargs: Any) -> Any:
            if not collector.is_active:
                return original_sync(self_sdk, *args, **kwargs)

            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            span = Span(
                span_id=str(uuid.uuid4()),
                step=0,
                name=f"together/{model}",
                provider="together",
                model=model,
                started_at=datetime.now(timezone.utc),
                input=messages,
                request_payload={"method": "chat.completions.create", "kwargs": _jsonable(kwargs)},
            )
            span._perf_start = time.perf_counter()

            try:
                response = original_sync(self_sdk, *args, **kwargs)
                tokens = openai_usage_from_response(response)
                cost = calculate_cost("together", model, tokens)
                span.finish(output=response, tokens=tokens, cost=cost)
            except Exception as exc:
                span.fail(exc)
                raise
            finally:
                collector.record_span(span)

            return response

        Completions.create = patched_create

        self._original_async_create = AsyncCompletions.create
        original_async = self._original_async_create

        async def async_patched_create(self_sdk: Any, *args: Any, **kwargs: Any) -> Any:
            if not collector.is_active:
                return await original_async(self_sdk, *args, **kwargs)

            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            span = Span(
                span_id=str(uuid.uuid4()),
                step=0,
                name=f"together/{model}",
                provider="together",
                model=model,
                started_at=datetime.now(timezone.utc),
                input=messages,
                request_payload={"method": "chat.completions.create", "kwargs": _jsonable(kwargs)},
            )
            span._perf_start = time.perf_counter()

            try:
                response = await original_async(self_sdk, *args, **kwargs)
                tokens = openai_usage_from_response(response)
                cost = calculate_cost("together", model, tokens)
                span.finish(output=response, tokens=tokens, cost=cost)
            except Exception as exc:
                span.fail(exc)
                raise
            finally:
                collector.record_span(span)

            return response

        AsyncCompletions.create = async_patched_create
        self._patched = True

    def unpatch(self) -> None:
        if not self._patched:
            return

        try:
            from together.resources.chat.completions import AsyncCompletions, Completions

            if self._original_create is not None:
                Completions.create = self._original_create
            if self._original_async_create is not None:
                AsyncCompletions.create = self._original_async_create
        except ImportError:
            pass

        self._patched = False
