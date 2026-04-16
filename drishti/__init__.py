"""Drishti (दृष्टि) — See what your agent thinks."""

from .collector import collector
from .config import DrishtiConfig
from .errors import DrishtiBudgetError
from .models.span import Span, SpanStatus, TokenUsage
from .models.trace import Trace, TraceStatus
from .trace import trace

__version__ = "0.2.2"

__all__ = [
    "trace",
    "Span",
    "SpanStatus",
    "TokenUsage",
    "Trace",
    "TraceStatus",
    "collector",
    "DrishtiConfig",
    "DrishtiBudgetError",
]
