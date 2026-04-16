"""
Cost calculator — computes USD cost for a given provider/model/token usage.

Supports exact model name matching and prefix matching for versioned models
(e.g. "gpt-4o-2024-11-20" matches "gpt-4o").
"""

from __future__ import annotations

from ..models.span import TokenUsage
from .pricing import PRICING, UNKNOWN_COST


def calculate_cost(provider: str, model: str, tokens: TokenUsage) -> float:
    """
    Calculate cost in USD for a given provider/model/token usage.

    Returns 0.0 for unknown or local models — never crashes.

    Args:
        provider: Provider name (e.g. "openai", "anthropic", "groq", "ollama")
        model: Model name (e.g. "gpt-4o", "claude-3-5-sonnet-20241022")
        tokens: Token usage with prompt and completion counts

    Returns:
        Cost in USD, rounded to 6 decimal places.
    """
    key = (provider, model)

    # Try exact match first
    price = PRICING.get(key)

    # Prefix match for versioned model names (e.g. "gpt-4o-2024-11-20" → "gpt-4o")
    if price is None:
        for (p, m), v in PRICING.items():
            if p == provider and model.startswith(m):
                price = v
                break

    # Fallback to zero cost for unknown models
    if price is None:
        price = UNKNOWN_COST

    input_cost_per_1k, output_cost_per_1k = price
    cost = (tokens.prompt_tokens / 1000) * input_cost_per_1k + (
        tokens.completion_tokens / 1000
    ) * output_cost_per_1k
    return round(cost, 6)
