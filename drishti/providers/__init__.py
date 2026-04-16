"""Provider interceptors registry."""

from .anthropic import AnthropicInterceptor
from .cohere import CohereInterceptor
from .groq import GroqInterceptor
from .mistral import MistralInterceptor
from .ollama import OllamaInterceptor
from .openai import OpenAIInterceptor
from .together import TogetherInterceptor

ALL_INTERCEPTORS = [
    OpenAIInterceptor(),
    AnthropicInterceptor(),
    GroqInterceptor(),
    OllamaInterceptor(),
    MistralInterceptor(),
    TogetherInterceptor(),
    CohereInterceptor(),
]

__all__ = ["ALL_INTERCEPTORS"]
