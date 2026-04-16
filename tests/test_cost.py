"""Tests for cost calculator."""

from drishti.cost.calculator import calculate_cost
from drishti.models.span import TokenUsage


class TestCalculateCost:
    def test_openai_gpt4o(self):
        tokens = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        cost = calculate_cost("openai", "gpt-4o", tokens)
        # Expected: (1000/1000) * 0.0025 + (500/1000) * 0.0100 = 0.0025 + 0.005 = 0.0075
        assert cost == 0.0075

    def test_openai_gpt4o_mini(self):
        tokens = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        cost = calculate_cost("openai", "gpt-4o-mini", tokens)
        # Expected: (1000/1000) * 0.00015 + (500/1000) * 0.0006 = 0.00015 + 0.0003 = 0.00045
        assert cost == 0.00045

    def test_anthropic_sonnet(self):
        tokens = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        cost = calculate_cost("anthropic", "claude-3-5-sonnet-20241022", tokens)
        # Expected: (1000/1000) * 0.003 + (500/1000) * 0.015 = 0.003 + 0.0075 = 0.0105
        assert cost == 0.0105

    def test_groq_llama(self):
        tokens = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        cost = calculate_cost("groq", "llama-3.3-70b-versatile", tokens)
        # Expected: (1000/1000) * 0.00059 + (500/1000) * 0.00079 = 0.00059 + 0.000395 = 0.000985
        assert cost == 0.000985

    def test_prefix_matching(self):
        """Versioned model names should match via prefix."""
        tokens = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        cost = calculate_cost("openai", "gpt-4o-2024-11-20", tokens)
        # Should match "gpt-4o" pricing
        assert cost == 0.0075

    def test_unknown_model_returns_zero(self):
        tokens = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        cost = calculate_cost("openai", "gpt-99", tokens)
        assert cost == 0.0

    def test_ollama_always_free(self):
        tokens = TokenUsage(prompt_tokens=5000, completion_tokens=2000, total_tokens=7000)
        cost = calculate_cost("ollama", "llama3.2", tokens)
        assert cost == 0.0

    def test_unknown_provider_returns_zero(self):
        tokens = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        cost = calculate_cost("nonexistent", "model-x", tokens)
        assert cost == 0.0

    def test_zero_tokens(self):
        tokens = TokenUsage()
        cost = calculate_cost("openai", "gpt-4o", tokens)
        assert cost == 0.0

    def test_rounding(self):
        """Cost should be rounded to 6 decimal places."""
        tokens = TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        cost = calculate_cost("openai", "gpt-4o", tokens)
        str_cost = str(cost)
        # Should have at most 6 decimal places
        if "." in str_cost:
            assert len(str_cost.split(".")[1]) <= 6
