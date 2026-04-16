"""Tests for budget policies and DrishtiBudgetError."""

from __future__ import annotations

import pytest

from drishti import trace
from drishti.collector import collector
from drishti.errors import DrishtiBudgetError
from drishti.models.span import Span, TokenUsage


def _expensive_span() -> Span:
    span = Span(name="openai/gpt-4o", provider="openai", model="gpt-4o")
    tokens = TokenUsage(prompt_tokens=1000, completion_tokens=1000, total_tokens=2000)
    span.finish(output={"ok": True}, tokens=tokens, cost=0.0125)
    return span


def test_budget_abort_raises_error_mid_execution() -> None:
    @trace(display=False, export=False, budget_usd=0.001, on_exceed="abort")
    def run() -> None:
        collector.record_span(_expensive_span())

    with pytest.raises(DrishtiBudgetError) as exc:
        run()

    assert exc.value.span_step == 1
    assert exc.value.actual_cost_usd > exc.value.budget_usd
    assert exc.value.trace.span_count == 1


def test_budget_warn_keeps_execution_running() -> None:
    @trace(display=False, export=False, budget_usd=0.001, on_exceed="warn")
    def run() -> str:
        collector.record_span(_expensive_span())
        return "ok"

    with pytest.warns(RuntimeWarning, match="Budget exceeded"):
        result = run()

    assert result == "ok"
