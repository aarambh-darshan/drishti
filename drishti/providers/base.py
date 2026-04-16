"""
BaseInterceptor — abstract base class for all provider interceptors.

Each provider interceptor patches a specific SDK method to capture
LLM calls as Spans. Subclasses implement patch() and unpatch().
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseInterceptor(ABC):
    """
    ABC for all provider interceptors.

    Subclasses implement patch() and unpatch() to monkey-patch
    their respective SDK methods with instrumented versions.
    """

    @abstractmethod
    def patch(self) -> None:
        """Replace the SDK method with the instrumented version."""
        ...

    @abstractmethod
    def unpatch(self) -> None:
        """Restore the original SDK method."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short name for this provider (e.g. 'openai', 'anthropic')."""
        ...
