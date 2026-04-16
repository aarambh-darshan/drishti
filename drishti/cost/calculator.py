"""Cost calculator — computes USD cost for provider/model/token usage."""

from __future__ import annotations

from ..config import get_config
from ..models.span import TokenUsage
from .pricing import PRICING, UNKNOWN_COST


def _build_pricing_table() -> dict[tuple[str, str], tuple[float, float]]:
    table = dict(PRICING)
    config = get_config()

    for key, value in config.pricing_overrides.items():
        if "/" not in key:
            continue
        provider, model = key.split("/", 1)
        table[(provider.strip(), model.strip())] = value

    return table


def calculate_cost(provider: str, model: str, tokens: TokenUsage) -> float:
    """Calculate cost in USD for provider/model/token usage."""
    pricing = _build_pricing_table()
    key = (provider, model)

    price = pricing.get(key)
    if price is None:
        for (p, m), v in pricing.items():
            if p == provider and model.startswith(m):
                price = v
                break

    if price is None:
        price = UNKNOWN_COST

    input_cost_per_1k, output_cost_per_1k = price
    cost = (tokens.prompt_tokens / 1000) * input_cost_per_1k + (
        tokens.completion_tokens / 1000
    ) * output_cost_per_1k
    return round(cost, 6)
