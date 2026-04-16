"""Pricing table for supported providers."""

from __future__ import annotations

PRICING_LAST_UPDATED = "2026-04-16"

# (provider, model) -> (input $/1K tokens, output $/1K tokens)
PRICING: dict[tuple[str, str], tuple[float, float]] = {
    # OpenAI
    ("openai", "gpt-4o"): (0.0025, 0.0100),
    ("openai", "gpt-4o-mini"): (0.00015, 0.0006),
    ("openai", "gpt-4.1"): (0.0020, 0.0080),
    ("openai", "gpt-4.1-mini"): (0.0004, 0.0016),
    ("openai", "gpt-4.1-nano"): (0.0001, 0.0004),
    ("openai", "gpt-4-turbo"): (0.0100, 0.0300),
    ("openai", "gpt-3.5-turbo"): (0.0005, 0.0015),
    ("openai", "o1"): (0.0150, 0.0600),
    ("openai", "o1-mini"): (0.0030, 0.0120),
    ("openai", "o3-mini"): (0.0011, 0.0044),
    # Anthropic
    ("anthropic", "claude-3-5-sonnet-20241022"): (0.003, 0.015),
    ("anthropic", "claude-3-5-haiku-20241022"): (0.0008, 0.004),
    ("anthropic", "claude-3-opus-20240229"): (0.015, 0.075),
    ("anthropic", "claude-sonnet-4-20250514"): (0.003, 0.015),
    # Groq
    ("groq", "llama-3.3-70b-versatile"): (0.00059, 0.00079),
    ("groq", "llama-3.1-8b-instant"): (0.00005, 0.00008),
    ("groq", "mixtral-8x7b-32768"): (0.00024, 0.00024),
    # Mistral
    ("mistral", "mistral-large-latest"): (0.0020, 0.0060),
    ("mistral", "mistral-small-latest"): (0.0002, 0.0006),
    # Together (representative defaults)
    ("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"): (0.00088, 0.00088),
    ("together", "Qwen/Qwen2.5-72B-Instruct-Turbo"): (0.0012, 0.0012),
    # Cohere
    ("cohere", "command-r-plus"): (0.0030, 0.0150),
    ("cohere", "command-r"): (0.0005, 0.0015),
}

UNKNOWN_COST: tuple[float, float] = (0.0, 0.0)
