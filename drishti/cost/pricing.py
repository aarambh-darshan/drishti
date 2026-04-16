"""
Pricing table — maps (provider, model) to cost per 1K tokens.

Each entry is: (provider, model) → (input_cost_per_1k_tokens, output_cost_per_1k_tokens)
All prices are in USD.

Ollama and other local models are not listed here — they return $0.00
automatically via the UNKNOWN_COST fallback.
"""

# (provider, model) → (input $/1K tokens, output $/1K tokens)
PRICING: dict[tuple[str, str], tuple[float, float]] = {
    # ─── OpenAI ──────────────────────────────────────────
    ("openai", "gpt-4o"): (0.0025, 0.0100),
    ("openai", "gpt-4o-mini"): (0.00015, 0.0006),
    ("openai", "gpt-4-turbo"): (0.0100, 0.0300),
    ("openai", "gpt-3.5-turbo"): (0.0005, 0.0015),
    ("openai", "o1"): (0.0150, 0.0600),
    ("openai", "o1-mini"): (0.0030, 0.0120),
    ("openai", "o3-mini"): (0.0011, 0.0044),
    # ─── Anthropic ───────────────────────────────────────
    ("anthropic", "claude-3-5-sonnet-20241022"): (0.003, 0.015),
    ("anthropic", "claude-3-5-haiku-20241022"): (0.0008, 0.004),
    ("anthropic", "claude-3-opus-20240229"): (0.015, 0.075),
    ("anthropic", "claude-sonnet-4-20250514"): (0.003, 0.015),
    # ─── Groq ────────────────────────────────────────────
    ("groq", "llama-3.3-70b-versatile"): (0.00059, 0.00079),
    ("groq", "llama-3.1-8b-instant"): (0.00005, 0.00008),
    ("groq", "mixtral-8x7b-32768"): (0.00024, 0.00024),
}

# Fallback for unknown / local models — always free
UNKNOWN_COST: tuple[float, float] = (0.0, 0.0)
