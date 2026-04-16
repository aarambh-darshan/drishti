"""Utilities for optional stream token estimation."""

from __future__ import annotations

import json
import warnings
from typing import Any

from .models.span import TokenUsage

_WARNED_NO_TIKTOKEN = False


def _serialize_for_estimation(payload: Any) -> str:
    try:
        return json.dumps(payload, default=str, ensure_ascii=False)
    except Exception:
        return str(payload)


def estimate_stream_tokens(
    *,
    model: str,
    input_payload: Any,
    output_text: str,
    enabled: bool,
) -> tuple[TokenUsage, bool, str | None]:
    """Estimate token usage for streaming responses.

    Returns (tokens, estimated_flag, estimation_source).
    """
    if not enabled:
        return TokenUsage(), False, "disabled"

    try:
        import tiktoken  # type: ignore[import-not-found]
    except ImportError:
        global _WARNED_NO_TIKTOKEN
        if not _WARNED_NO_TIKTOKEN:
            warnings.warn(
                "[Drishti] tiktoken not installed; stream token estimation disabled.",
                RuntimeWarning,
                stacklevel=2,
            )
            _WARNED_NO_TIKTOKEN = True
        return TokenUsage(), False, "tiktoken_unavailable"

    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")

    prompt_text = _serialize_for_estimation(input_payload)
    prompt_tokens = len(encoding.encode(prompt_text))
    completion_tokens = len(encoding.encode(output_text or ""))
    tokens = TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    return tokens, True, "tiktoken"


def reset_token_estimation_warnings() -> None:
    """Test helper for warning state."""
    global _WARNED_NO_TIKTOKEN
    _WARNED_NO_TIKTOKEN = False
