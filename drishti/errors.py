"""Custom exception types for Drishti."""

from __future__ import annotations

from .models.trace import Trace


class DrishtiBudgetError(RuntimeError):
    """Raised when a running trace exceeds its configured budget in abort mode."""

    def __init__(
        self, trace: Trace, budget_usd: float, actual_cost_usd: float, span_step: int
    ) -> None:
        self.trace = trace
        self.budget_usd = budget_usd
        self.actual_cost_usd = actual_cost_usd
        self.span_step = span_step
        super().__init__(
            (
                "[Drishti] Budget exceeded: "
                f"${self.actual_cost_usd:.4f} > ${self.budget_usd:.4f} at span {self.span_step}"
            )
        )
