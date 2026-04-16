"""
Provider interceptors registry.

Maintains the list of all interceptor instances. The @trace decorator
iterates this list to patch() and unpatch() all providers in one call.
"""

from .anthropic import AnthropicInterceptor
from .groq import GroqInterceptor
from .ollama import OllamaInterceptor
from .openai import OpenAIInterceptor

ALL_INTERCEPTORS = [
    OpenAIInterceptor(),
    AnthropicInterceptor(),
    GroqInterceptor(),
    OllamaInterceptor(),
]

__all__ = ["ALL_INTERCEPTORS"]
