"""Shared helper utilities for provider interceptors."""

from __future__ import annotations

from typing import Any

from ..models.span import TokenUsage


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def openai_usage_from_response(response: Any) -> TokenUsage:
    """Extract OpenAI-style usage from a response object."""
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return TokenUsage()

    if isinstance(usage, dict):
        prompt = _safe_int(usage.get("prompt_tokens", 0), 0)
        completion = _safe_int(usage.get("completion_tokens", 0), 0)
        total = _safe_int(usage.get("total_tokens", prompt + completion), prompt + completion)
        return TokenUsage(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)

    prompt = _safe_int(getattr(usage, "prompt_tokens", 0), 0)
    completion = _safe_int(getattr(usage, "completion_tokens", 0), 0)
    total = _safe_int(getattr(usage, "total_tokens", prompt + completion), prompt + completion)
    return TokenUsage(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)


def anthropic_usage_from_response(response: Any) -> TokenUsage:
    """Extract Anthropic-style usage from a response object."""
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return TokenUsage()

    if isinstance(usage, dict):
        input_tokens = _safe_int(usage.get("input_tokens", 0), 0)
        output_tokens = _safe_int(usage.get("output_tokens", 0), 0)
        total = _safe_int(
            usage.get("total_tokens", input_tokens + output_tokens),
            input_tokens + output_tokens,
        )
        return TokenUsage(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=total,
        )

    input_tokens = _safe_int(getattr(usage, "input_tokens", 0), 0)
    output_tokens = _safe_int(getattr(usage, "output_tokens", 0), 0)
    total = _safe_int(
        getattr(usage, "total_tokens", input_tokens + output_tokens),
        input_tokens + output_tokens,
    )
    return TokenUsage(
        prompt_tokens=input_tokens,
        completion_tokens=output_tokens,
        total_tokens=total,
    )


def cohere_usage_from_response(response: Any) -> TokenUsage:
    """Extract Cohere token usage from response object or dict."""
    if isinstance(response, dict):
        usage = response.get("usage", {})
        tokens = usage.get("tokens", usage)
        prompt = _safe_int(tokens.get("input_tokens", tokens.get("prompt_tokens", 0)), 0)
        completion = _safe_int(tokens.get("output_tokens", tokens.get("completion_tokens", 0)), 0)
        total = _safe_int(tokens.get("total_tokens", prompt + completion), prompt + completion)
        return TokenUsage(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)

    usage = getattr(response, "usage", None)
    if usage is None:
        return TokenUsage()

    # Cohere Python objects vary; handle both nested and flat attrs.
    token_obj = getattr(usage, "tokens", usage)
    prompt = _safe_int(
        getattr(token_obj, "input_tokens", getattr(token_obj, "prompt_tokens", 0)), 0
    )
    completion = _safe_int(
        getattr(token_obj, "output_tokens", getattr(token_obj, "completion_tokens", 0)),
        0,
    )
    total = _safe_int(getattr(token_obj, "total_tokens", prompt + completion), prompt + completion)
    return TokenUsage(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)


def text_from_openai_chunk(chunk: Any) -> str:
    """Extract text delta from an OpenAI-compatible streaming chunk."""
    if isinstance(chunk, dict):
        choices = chunk.get("choices", [])
        if not choices:
            return ""
        delta = choices[0].get("delta", {})
        content = delta.get("content", "")
        if isinstance(content, list):
            return "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
        return str(content or "")

    choices = getattr(chunk, "choices", None)
    if not choices:
        return ""

    first = choices[0]
    delta = getattr(first, "delta", None)
    if delta is None:
        return ""

    content = getattr(delta, "content", "")
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            text = getattr(part, "text", None)
            if text:
                parts.append(str(text))
        return "".join(parts)
    return str(content or "")


def text_from_anthropic_chunk(chunk: Any) -> str:
    """Extract text delta from anthropic streaming events."""
    if isinstance(chunk, dict):
        if chunk.get("type") == "content_block_delta":
            delta = chunk.get("delta", {})
            return str(delta.get("text", "") or "")
        return ""

    chunk_type = getattr(chunk, "type", "")
    if chunk_type == "content_block_delta":
        delta = getattr(chunk, "delta", None)
        if delta is None:
            return ""
        return str(getattr(delta, "text", "") or "")

    if chunk_type == "message_delta":
        delta = getattr(chunk, "delta", None)
        if delta is None:
            return ""
        text = getattr(delta, "text", None)
        return str(text or "")

    return ""


def anthropic_usage_from_chunk(chunk: Any) -> TokenUsage:
    """Extract usage if present on anthropic stream chunk."""
    usage = None
    if isinstance(chunk, dict):
        usage = chunk.get("usage")
        if usage is None and chunk.get("message"):
            usage = chunk.get("message", {}).get("usage")
    else:
        usage = getattr(chunk, "usage", None)
        if usage is None:
            message = getattr(chunk, "message", None)
            usage = getattr(message, "usage", None) if message is not None else None

    if usage is None:
        return TokenUsage()

    if isinstance(usage, dict):
        in_tok = _safe_int(usage.get("input_tokens", 0), 0)
        out_tok = _safe_int(usage.get("output_tokens", 0), 0)
        total = _safe_int(usage.get("total_tokens", in_tok + out_tok), in_tok + out_tok)
        return TokenUsage(prompt_tokens=in_tok, completion_tokens=out_tok, total_tokens=total)

    in_tok = _safe_int(getattr(usage, "input_tokens", 0), 0)
    out_tok = _safe_int(getattr(usage, "output_tokens", 0), 0)
    total = _safe_int(getattr(usage, "total_tokens", in_tok + out_tok), in_tok + out_tok)
    return TokenUsage(prompt_tokens=in_tok, completion_tokens=out_tok, total_tokens=total)
