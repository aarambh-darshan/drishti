"""One-time warnings for missing provider SDKs."""

from __future__ import annotations

import warnings

_WARNED: set[str] = set()


def warn_missing_sdk(provider: str, extra: str, import_name: str) -> None:
    """Warn once per provider when SDK import is missing."""
    if provider in _WARNED:
        return
    _WARNED.add(provider)
    warnings.warn(
        (
            f"[Drishti] {provider} SDK not installed ({import_name}). "
            f"Tracing for {provider} calls is disabled. Install with: pip install drishti-ai[{extra}]"
        ),
        RuntimeWarning,
        stacklevel=2,
    )


def reset_missing_sdk_warnings() -> None:
    """Test helper to clear one-time warning state."""
    _WARNED.clear()
