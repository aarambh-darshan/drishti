"""
Drishti (दृष्टि) — See what your agent thinks.

Automatically captures, visualizes, and exports traces of AI agent execution.

Usage:
    from drishti import trace

    @trace
    def my_agent(query):
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": query}],
        )
        return response.choices[0].message.content
"""

from .collector import collector
from .config import DrishtiConfig
from .models.span import Span, SpanStatus, TokenUsage
from .models.trace import Trace, TraceStatus
from .trace import trace

__version__ = "0.1.0"

__all__ = [
    "trace",
    "Span",
    "SpanStatus",
    "TokenUsage",
    "Trace",
    "TraceStatus",
    "collector",
    "DrishtiConfig",
]
