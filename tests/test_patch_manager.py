"""Tests for global interceptor patch lifecycle manager."""

from __future__ import annotations

from drishti.providers.manager import patch_manager


class _DummyInterceptor:
    def __init__(self) -> None:
        self.patch_calls = 0
        self.unpatch_calls = 0

    def patch(self) -> None:
        self.patch_calls += 1

    def unpatch(self) -> None:
        self.unpatch_calls += 1


def test_patch_manager_reference_count(monkeypatch) -> None:
    interceptor = _DummyInterceptor()
    monkeypatch.setattr("drishti.providers.manager.ALL_INTERCEPTORS", [interceptor])
    patch_manager.reset()

    patch_manager.acquire()
    patch_manager.acquire()

    assert patch_manager.active_count == 2
    assert interceptor.patch_calls == 1

    patch_manager.release()
    assert patch_manager.active_count == 1
    assert interceptor.unpatch_calls == 0

    patch_manager.release()
    assert patch_manager.active_count == 0
    assert interceptor.unpatch_calls == 1
