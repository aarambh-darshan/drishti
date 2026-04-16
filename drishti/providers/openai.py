"""OpenAI provider interceptor."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from ..collector import collector
from ..config import get_config
from ..cost.calculator import calculate_cost
from ..models.span import Span, SpanStatus, TokenUsage
from ..token_estimation import estimate_stream_tokens
from .base import BaseInterceptor
from .common import openai_usage_from_response, text_from_openai_chunk
from .missing import warn_missing_sdk


def _jsonable(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=str, ensure_ascii=False))
    except Exception:
        return str(value)


def _finalize_openai_stream_span(
    *,
    span: Span,
    model: str,
    messages: Any,
    usage_tokens: TokenUsage,
    output_parts: list[str],
    partial: bool,
) -> None:
    tokens = usage_tokens
    span.streaming = True

    if tokens.total_tokens == 0:
        cfg = get_config()
        estimated, estimated_flag, source = estimate_stream_tokens(
            model=model,
            input_payload=messages,
            output_text="".join(output_parts),
            enabled=cfg.estimate_stream_tokens,
        )
        if estimated_flag:
            tokens = estimated
        span.estimated_tokens = estimated_flag
        span.estimation_source = source

    cost = calculate_cost("openai", model, tokens)
    span.finish(
        output={"content": "".join(output_parts), "partial": partial},
        tokens=tokens,
        cost=cost,
    )
    collector.record_span(span)


def _instrument_openai_sync_stream(
    stream_obj: Any,
    span: Span,
    model: str,
    messages: Any,
):
    usage_tokens = TokenUsage()
    output_parts: list[str] = []
    completed = False

    try:
        for chunk in stream_obj:
            chunk_usage = openai_usage_from_response(chunk)
            if chunk_usage.total_tokens > 0:
                usage_tokens = chunk_usage

            text = text_from_openai_chunk(chunk)
            if text:
                output_parts.append(text)

            yield chunk

        _finalize_openai_stream_span(
            span=span,
            model=model,
            messages=messages,
            usage_tokens=usage_tokens,
            output_parts=output_parts,
            partial=False,
        )
        completed = True
    except Exception as exc:
        span.streaming = True
        span.fail(exc)
        collector.record_span(span)
        raise
    finally:
        if not completed and span.status == SpanStatus.PENDING:
            _finalize_openai_stream_span(
                span=span,
                model=model,
                messages=messages,
                usage_tokens=usage_tokens,
                output_parts=output_parts,
                partial=True,
            )


async def _instrument_openai_async_stream(
    stream_obj: Any,
    span: Span,
    model: str,
    messages: Any,
):
    usage_tokens = TokenUsage()
    output_parts: list[str] = []
    completed = False

    try:
        async for chunk in stream_obj:
            chunk_usage = openai_usage_from_response(chunk)
            if chunk_usage.total_tokens > 0:
                usage_tokens = chunk_usage

            text = text_from_openai_chunk(chunk)
            if text:
                output_parts.append(text)

            yield chunk

        _finalize_openai_stream_span(
            span=span,
            model=model,
            messages=messages,
            usage_tokens=usage_tokens,
            output_parts=output_parts,
            partial=False,
        )
        completed = True
    except Exception as exc:
        span.streaming = True
        span.fail(exc)
        collector.record_span(span)
        raise
    finally:
        if not completed and span.status == SpanStatus.PENDING:
            _finalize_openai_stream_span(
                span=span,
                model=model,
                messages=messages,
                usage_tokens=usage_tokens,
                output_parts=output_parts,
                partial=True,
            )


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
            warn_missing_sdk("openai", "openai", "openai")
            return

        self._original_create = Completions.create
        original_sync = self._original_create

        def patched_create(self_sdk: Any, *args: Any, **kwargs: Any) -> Any:
            if not collector.is_active:
                return original_sync(self_sdk, *args, **kwargs)

            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            is_stream = bool(kwargs.get("stream", False))
            perf_start = time.perf_counter()

            span = Span(
                span_id=str(uuid.uuid4()),
                step=0,
                name=f"openai/{model}",
                provider="openai",
                model=model,
                started_at=datetime.now(timezone.utc),
                input=messages,
                request_payload={
                    "method": "chat.completions.create",
                    "kwargs": _jsonable(kwargs),
                },
                streaming=is_stream,
            )
            span._perf_start = perf_start

            try:
                response = original_sync(self_sdk, *args, **kwargs)

                if is_stream:
                    return _instrument_openai_sync_stream(response, span, model, messages)

                tokens = openai_usage_from_response(response)
                cost = calculate_cost("openai", model, tokens)
                span.finish(output=response, tokens=tokens, cost=cost)

            except Exception as exc:
                span.fail(exc)
                raise

            finally:
                if not is_stream:
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
            is_stream = bool(kwargs.get("stream", False))
            perf_start = time.perf_counter()

            span = Span(
                span_id=str(uuid.uuid4()),
                step=0,
                name=f"openai/{model}",
                provider="openai",
                model=model,
                started_at=datetime.now(timezone.utc),
                input=messages,
                request_payload={
                    "method": "chat.completions.create",
                    "kwargs": _jsonable(kwargs),
                },
                streaming=is_stream,
            )
            span._perf_start = perf_start

            try:
                response = await original_async(self_sdk, *args, **kwargs)

                if is_stream:
                    return _instrument_openai_async_stream(response, span, model, messages)

                tokens = openai_usage_from_response(response)
                cost = calculate_cost("openai", model, tokens)
                span.finish(output=response, tokens=tokens, cost=cost)

            except Exception as exc:
                span.fail(exc)
                raise

            finally:
                if not is_stream:
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
