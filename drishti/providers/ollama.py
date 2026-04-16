"""Ollama provider interceptor."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from ..collector import collector
from ..cost.calculator import calculate_cost
from ..models.span import Span, SpanStatus, TokenUsage
from .base import BaseInterceptor
from .missing import warn_missing_sdk


def _jsonable(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=str, ensure_ascii=False))
    except Exception:
        return str(value)


def _extract_ollama_tokens(response: Any) -> TokenUsage:
    if isinstance(response, dict):
        prompt = int(response.get("prompt_eval_count", 0) or 0)
        completion = int(response.get("eval_count", 0) or 0)
        return TokenUsage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=prompt + completion,
        )

    prompt = int(getattr(response, "prompt_eval_count", 0) or 0)
    completion = int(getattr(response, "eval_count", 0) or 0)
    return TokenUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=prompt + completion,
    )


def _extract_ollama_chunk_text(chunk: Any) -> str:
    if isinstance(chunk, dict):
        message = chunk.get("message", {})
        if isinstance(message, dict):
            return str(message.get("content", "") or "")
        return ""

    message = getattr(chunk, "message", None)
    if message is None:
        return ""
    return str(getattr(message, "content", "") or "")


def _finalize_stream_span(
    span: Span,
    model: str,
    output_parts: list[str],
    latest_chunk: Any,
    partial: bool,
) -> None:
    tokens = _extract_ollama_tokens(latest_chunk) if latest_chunk is not None else TokenUsage()
    span.streaming = True
    cost = calculate_cost("ollama", model, tokens)
    span.finish(
        output={"content": "".join(output_parts), "partial": partial},
        tokens=tokens,
        cost=cost,
    )
    collector.record_span(span)


def _instrument_sync_stream(stream_obj: Any, span: Span, model: str):
    output_parts: list[str] = []
    latest_chunk: Any = None
    completed = False

    try:
        for chunk in stream_obj:
            latest_chunk = chunk
            text = _extract_ollama_chunk_text(chunk)
            if text:
                output_parts.append(text)
            yield chunk

        _finalize_stream_span(
            span=span,
            model=model,
            output_parts=output_parts,
            latest_chunk=latest_chunk,
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
            _finalize_stream_span(
                span=span,
                model=model,
                output_parts=output_parts,
                latest_chunk=latest_chunk,
                partial=True,
            )


async def _instrument_async_stream(stream_obj: Any, span: Span, model: str):
    output_parts: list[str] = []
    latest_chunk: Any = None
    completed = False

    try:
        async for chunk in stream_obj:
            latest_chunk = chunk
            text = _extract_ollama_chunk_text(chunk)
            if text:
                output_parts.append(text)
            yield chunk

        _finalize_stream_span(
            span=span,
            model=model,
            output_parts=output_parts,
            latest_chunk=latest_chunk,
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
            _finalize_stream_span(
                span=span,
                model=model,
                output_parts=output_parts,
                latest_chunk=latest_chunk,
                partial=True,
            )


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
            warn_missing_sdk("ollama", "ollama", "ollama")
            return

        self._original_chat = ollama_module.chat
        original_sync = self._original_chat

        def patched_chat(*args: Any, **kwargs: Any) -> Any:
            if not collector.is_active:
                return original_sync(*args, **kwargs)

            model = kwargs.get("model", args[0] if args else "unknown")
            messages = kwargs.get("messages", args[1] if len(args) > 1 else [])
            is_stream = bool(kwargs.get("stream", False))
            perf_start = time.perf_counter()

            span = Span(
                span_id=str(uuid.uuid4()),
                step=0,
                name=f"ollama/{model}",
                provider="ollama",
                model=str(model),
                started_at=datetime.now(timezone.utc),
                input=messages,
                request_payload={"method": "chat", "kwargs": _jsonable(kwargs)},
                streaming=is_stream,
            )
            span._perf_start = perf_start

            try:
                response = original_sync(*args, **kwargs)

                if is_stream and hasattr(response, "__iter__"):
                    return _instrument_sync_stream(response, span, str(model))

                tokens = _extract_ollama_tokens(response)
                cost = calculate_cost("ollama", str(model), tokens)
                span.finish(output=response, tokens=tokens, cost=cost)

            except Exception as exc:
                span.fail(exc)
                raise
            finally:
                if not is_stream:
                    collector.record_span(span)

            return response

        ollama_module.chat = patched_chat

        try:
            from ollama import AsyncClient

            self._original_async_chat = AsyncClient.chat
            original_async = self._original_async_chat

            async def async_patched_chat(self_sdk: Any, *args: Any, **kwargs: Any) -> Any:
                if not collector.is_active:
                    return await original_async(self_sdk, *args, **kwargs)

                model = kwargs.get("model", args[0] if args else "unknown")
                messages = kwargs.get("messages", args[1] if len(args) > 1 else [])
                is_stream = bool(kwargs.get("stream", False))
                perf_start = time.perf_counter()

                span = Span(
                    span_id=str(uuid.uuid4()),
                    step=0,
                    name=f"ollama/{model}",
                    provider="ollama",
                    model=str(model),
                    started_at=datetime.now(timezone.utc),
                    input=messages,
                    request_payload={"method": "chat", "kwargs": _jsonable(kwargs)},
                    streaming=is_stream,
                )
                span._perf_start = perf_start

                try:
                    response = await original_async(self_sdk, *args, **kwargs)

                    if is_stream and hasattr(response, "__aiter__"):
                        return _instrument_async_stream(response, span, str(model))

                    tokens = _extract_ollama_tokens(response)
                    cost = calculate_cost("ollama", str(model), tokens)
                    span.finish(output=response, tokens=tokens, cost=cost)

                except Exception as exc:
                    span.fail(exc)
                    raise
                finally:
                    if not is_stream:
                        collector.record_span(span)

                return response

            AsyncClient.chat = async_patched_chat

        except (ImportError, AttributeError):
            self._original_async_chat = None

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
