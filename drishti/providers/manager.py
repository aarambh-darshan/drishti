"""Thread-safe lifecycle manager for provider monkey patches."""

from __future__ import annotations

import threading
import warnings

from . import ALL_INTERCEPTORS


class _PatchLifecycleManager:
    """Reference-counted patch manager.

    Concurrent traces share one global patched state. Patches are applied
    on first acquire and removed only after the last release.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._active_count = 0

    def acquire(self) -> None:
        """Acquire patch context for a trace."""
        with self._lock:
            if self._active_count == 0:
                for interceptor in ALL_INTERCEPTORS:
                    try:
                        interceptor.patch()
                    except Exception as exc:
                        warnings.warn(
                            (
                                f"[Drishti] Failed to patch provider "
                                f"'{interceptor.provider_name}': {exc}"
                            ),
                            RuntimeWarning,
                            stacklevel=2,
                        )
            self._active_count += 1

    def release(self) -> None:
        """Release patch context for a trace."""
        with self._lock:
            if self._active_count == 0:
                return
            self._active_count -= 1
            if self._active_count == 0:
                for interceptor in ALL_INTERCEPTORS:
                    try:
                        interceptor.unpatch()
                    except Exception as exc:
                        warnings.warn(
                            (
                                f"[Drishti] Failed to unpatch provider "
                                f"'{interceptor.provider_name}': {exc}"
                            ),
                            RuntimeWarning,
                            stacklevel=2,
                        )

    def reset(self) -> None:
        """Force reset manager state (tests)."""
        with self._lock:
            self._active_count = 0

    @property
    def active_count(self) -> int:
        """Current active trace count."""
        with self._lock:
            return self._active_count


patch_manager = _PatchLifecycleManager()
