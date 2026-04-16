# ARCHITECTURE.md — Drishti (दृष्टि)

> **Vision:** Give AI developers complete visibility into every LLM call their agent makes.
> **Tagline:** *See what your agent thinks.*

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Design Philosophy](#2-design-philosophy)
3. [System Architecture Overview](#3-system-architecture-overview)
4. [Folder Structure](#4-folder-structure)
5. [Core Components](#5-core-components)
   - 5.1 [Span Model](#51-span-model)
   - 5.2 [Trace Model](#52-trace-model)
   - 5.3 [Collector](#53-collector)
   - 5.4 [Provider Interceptors](#54-provider-interceptors)
   - 5.5 [@trace Decorator](#55-trace-decorator)
   - 5.6 [Cost Calculator](#56-cost-calculator)
   - 5.7 [Display Engine](#57-display-engine)
   - 5.8 [Export System](#58-export-system)
   - 5.9 [CLI](#59-cli)
6. [Data Flow](#6-data-flow)
7. [Provider Interception Strategy](#7-provider-interception-strategy)
8. [Context Propagation (Thread Safety)](#8-context-propagation-thread-safety)
9. [Async Support](#9-async-support)
10. [Configuration System](#10-configuration-system)
11. [Error Handling Strategy](#11-error-handling-strategy)
12. [Testing Strategy](#12-testing-strategy)
13. [Public API Surface](#13-public-api-surface)
14. [Key Design Decisions & Tradeoffs](#14-key-design-decisions--tradeoffs)

---

## 1. Project Overview

**Drishti** is a Python library that automatically captures, visualizes, and exports traces of AI agent execution. It works by monkey-patching LLM provider SDKs at import time, capturing every call transparently without requiring changes to agent code — beyond adding the `@trace` decorator.

**Core capabilities:**
- Zero-config auto-detection of LLM calls (OpenAI, Anthropic, Groq, Ollama)
- Rich terminal tree UI showing every step with tokens, cost, and latency
- JSON export of full traces for sharing, diffing, and replaying
- CLI tool (`drishti`) for viewing and managing saved traces
- Budget guard: abort execution if cost exceeds a threshold

**Target users:** Python developers building AI agents, pipelines, or tools using any major LLM provider SDK.

---

## 2. Design Philosophy

### Zero-friction integration
A developer should be able to add tracing to an existing agent by adding **one line** — the `@trace` decorator. No code restructuring, no dependency injection, no wrapping every LLM call manually.

### Non-invasive by default
Drishti patches SDK internals at the module level when tracing is active. When tracing is NOT active (no `@trace` context), the patch is a pure passthrough with near-zero overhead. Normal code is completely unaffected.

### Correctness over speed
Trace capture must be accurate. If Drishti cannot capture a call correctly, it should log a warning and skip it — never corrupt the captured data or crash the user's agent.

### Provider-agnostic core
The core span/trace data model knows nothing about OpenAI or Anthropic. Provider-specific logic lives entirely in the `providers/` layer. Adding a new provider should require only adding one new file.

### Human-readable output first
The terminal tree view is the primary product. JSON export is secondary. Every design decision in the display layer should prioritize clarity for a developer staring at a failing agent at 2 AM.

---

## 3. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User's Agent Code                         │
│                                                             │
│   @trace(name="my-agent")                                   │
│   def run_agent(query):                                     │
│       response = openai.chat.completions.create(...)        │
│       ...                                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │ calls
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  @trace Decorator (trace.py)                 │
│   - Creates TraceContext                                    │
│   - Activates Collector                                     │
│   - Activates provider patches                              │
│   - Runs user function                                      │
│   - Deactivates patches                                     │
│   - Triggers Display + Export                               │
└────────────┬────────────────────────────────────────────────┘
             │
     ┌───────┴────────┐
     │                │
     ▼                ▼
┌──────────┐   ┌─────────────────────────────────────────┐
│ Collector│   │         Provider Interceptors            │
│          │   │                                         │
│ Holds    │   │  openai.py   anthropic.py   groq.py     │
│ active   │◄──│  ollama.py                              │
│ TraceCtx │   │                                         │
│          │   │  Each patches SDK method.               │
│ Receives │   │  On call: creates Span, calls original, │
│ Spans    │   │  fills Span, sends to Collector.        │
└────┬─────┘   └─────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                     Trace Model                             │
│                                                             │
│   Trace                                                     │
│   ├── metadata (name, start_time, end_time, status)        │
│   └── spans: List[Span]                                    │
│       ├── Span(provider, model, input, output, tokens,     │
│       │         cost, latency, error, step_number)         │
│       ├── Span(...)                                        │
│       └── Span(...)                                        │
└────────────┬────────────────────────────────────────────────┘
             │
     ┌───────┴────────────┐
     │                    │
     ▼                    ▼
┌──────────────┐   ┌──────────────────────────────────────┐
│ Display      │   │ Export (export/json.py)               │
│ Engine       │   │                                      │
│              │   │ - Serialize Trace to JSON            │
│ tree.py      │   │ - Save to .drishti/traces/           │
│ summary.py   │   │ - Filename: YYYYMMDD_HHMMSS_name.json│
│              │   └──────────────────────────────────────┘
│ Rich terminal│
│ tree + panel │   ┌──────────────────────────────────────┐
└──────────────┘   │ CLI (cli/main.py)                    │
                   │                                      │
                   │ drishti view <file>                  │
                   │ drishti list                         │
                   │ drishti clear                        │
                   └──────────────────────────────────────┘
```

---

## 4. Folder Structure

```
drishti/
├── drishti/                         # Main Python package
│   ├── __init__.py                  # Public API exports
│   ├── trace.py                     # @trace decorator + context manager
│   ├── collector.py                 # Global trace context registry
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── span.py                  # Span dataclass (single LLM call)
│   │   └── trace.py                 # Trace dataclass (list of spans + metadata)
│   │
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py                  # BaseInterceptor ABC
│   │   ├── openai.py                # OpenAI SDK interceptor
│   │   ├── anthropic.py             # Anthropic SDK interceptor
│   │   ├── groq.py                  # Groq SDK interceptor
│   │   └── ollama.py                # Ollama SDK interceptor
│   │
│   ├── cost/
│   │   ├── __init__.py
│   │   ├── pricing.py               # Model → price per token table
│   │   └── calculator.py            # TokenUsage → USD cost
│   │
│   ├── display/
│   │   ├── __init__.py
│   │   ├── tree.py                  # Rich tree renderer
│   │   └── summary.py               # Total cost/tokens/latency panel
│   │
│   ├── export/
│   │   ├── __init__.py
│   │   └── json.py                  # Trace → JSON serializer + file writer
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py                  # Typer CLI app
│   │
│   └── config.py                    # DrishtiConfig (dataclass + loader)
│
├── tests/
│   ├── conftest.py
│   ├── test_span.py
│   ├── test_trace.py
│   ├── test_collector.py
│   ├── test_cost.py
│   ├── test_display.py
│   ├── test_export.py
│   ├── providers/
│   │   ├── test_openai.py
│   │   ├── test_anthropic.py
│   │   ├── test_groq.py
│   │   └── test_ollama.py
│   └── integration/
│       ├── test_trace_decorator.py
│       └── test_async_trace.py
│
├── examples/
│   ├── openai_agent.py              # Full working example with OpenAI
│   ├── anthropic_agent.py           # Full working example with Anthropic
│   ├── async_agent.py               # Async agent example
│   └── multi_step_agent.py          # Complex multi-step example
│
├── docs/
│   ├── ARCHITECTURE.md              # This file
│   ├── ROADMAP.md
│   └── providers.md                 # How to add a new provider
│
├── pyproject.toml
├── README.md
├── LICENSE
└── CONTRIBUTING.md
```

---

## 5. Core Components

### 5.1 Span Model

**File:** `drishti/models/span.py`

A **Span** represents a single LLM API call. It is the atomic unit of a trace.

```python
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
from enum import Enum

class SpanStatus(str, Enum):
    PENDING   = "pending"    # call started, not yet complete
    SUCCESS   = "success"    # call returned successfully
    ERROR     = "error"      # call raised an exception

@dataclass
class TokenUsage:
    prompt_tokens:     int = 0
    completion_tokens: int = 0
    total_tokens:      int = 0

@dataclass
class Span:
    # Identity
    span_id:    str            # UUID4, generated at creation
    step:       int            # 1-indexed position in trace
    name:       str            # Human label, e.g. "openai/gpt-4o"

    # Provider info
    provider:   str            # "openai" | "anthropic" | "groq" | "ollama"
    model:      str            # e.g. "gpt-4o", "claude-3-5-sonnet-20241022"

    # Timing
    started_at:  datetime
    ended_at:    Optional[datetime] = None

    # I/O (stored as raw Python objects for flexibility)
    input:       Any = None    # The messages/prompt sent to the LLM
    output:      Any = None    # The full response object

    # Metrics
    tokens:      TokenUsage = field(default_factory=TokenUsage)
    cost_usd:    float = 0.0
    latency_ms:  float = 0.0

    # Status
    status:      SpanStatus = SpanStatus.PENDING
    error:       Optional[str] = None     # Exception message if status=ERROR
    error_type:  Optional[str] = None     # Exception class name

    def finish(self, output: Any, tokens: TokenUsage, cost: float) -> None:
        """Mark span as successful and fill metrics."""
        ...

    def fail(self, error: Exception) -> None:
        """Mark span as failed."""
        ...

    @property
    def latency_seconds(self) -> float:
        return self.latency_ms / 1000
```

**Key decisions:**
- `input` and `output` are stored as raw objects (not strings). The display layer is responsible for rendering them. This preserves full fidelity for JSON export.
- `step` is set by the Collector when the span is registered, not by the interceptor. This keeps interceptors dumb.
- `span_id` is a UUID so spans are globally unique and safe to merge across traces.

---

### 5.2 Trace Model

**File:** `drishti/models/trace.py`

A **Trace** is the complete record of one `@trace`-decorated function call. It holds all spans and top-level metadata.

```python
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from enum import Enum
from .span import Span, TokenUsage

class TraceStatus(str, Enum):
    RUNNING  = "running"
    SUCCESS  = "success"
    ERROR    = "error"     # at least one span failed / function raised

@dataclass
class Trace:
    # Identity
    trace_id:   str           # UUID4
    name:       str           # from @trace(name=...) or function name

    # Timing
    started_at: datetime
    ended_at:   Optional[datetime] = None

    # Spans
    spans: List[Span] = field(default_factory=list)

    # Status
    status: TraceStatus = TraceStatus.RUNNING

    # Computed properties (not stored, computed on access)
    @property
    def total_tokens(self) -> TokenUsage:
        """Sum token usage across all spans."""
        ...

    @property
    def total_cost_usd(self) -> float:
        """Sum cost across all spans."""
        ...

    @property
    def total_latency_ms(self) -> float:
        """Wall time from started_at to ended_at."""
        ...

    @property
    def span_count(self) -> int:
        return len(self.spans)

    @property
    def failed_spans(self) -> List[Span]:
        return [s for s in self.spans if s.status == SpanStatus.ERROR]
```

**Key decisions:**
- Aggregate metrics (`total_tokens`, `total_cost_usd`) are computed properties, not stored fields. This avoids inconsistency if spans are added post-hoc.
- `status` is the trace-level status. A trace is `ERROR` if the decorated function itself raised an exception, even if all spans succeeded.

---

### 5.3 Collector

**File:** `drishti/collector.py`

The **Collector** is the global singleton that holds the currently active `Trace`. Provider interceptors call the Collector to register new spans. The `@trace` decorator activates and deactivates the Collector.

```python
import threading
from typing import Optional
from .models.trace import Trace
from .models.span import Span

class _Collector:
    """
    Thread-local singleton. Each thread has its own active trace.
    This allows multiple agents to run concurrently in different threads
    without their traces interfering.
    """
    def __init__(self):
        self._local = threading.local()

    @property
    def active_trace(self) -> Optional[Trace]:
        return getattr(self._local, "trace", None)

    def start_trace(self, trace: Trace) -> None:
        """Called by @trace decorator at entry."""
        self._local.trace = trace

    def end_trace(self) -> Optional[Trace]:
        """Called by @trace decorator at exit. Returns completed trace."""
        trace = self._local.trace
        self._local.trace = None
        return trace

    def record_span(self, span: Span) -> None:
        """Called by provider interceptors when a span is completed."""
        if self._local.trace is None:
            return  # No active trace, silently ignore
        span.step = len(self._local.trace.spans) + 1
        self._local.trace.spans.append(span)

    @property
    def is_active(self) -> bool:
        return self.active_trace is not None

# Global singleton
collector = _Collector()
```

**Key decisions:**
- Thread-local storage. Drishti must be safe when an agent framework runs multiple agents concurrently in threads (e.g., LangChain with ThreadPoolExecutor).
- Interceptors check `collector.is_active` before doing anything expensive. If no trace is active, the interceptor is a pure passthrough with no allocation.
- `record_span` is the only way for interceptors to communicate with the trace. Interceptors never hold a reference to the Trace directly.

---

### 5.4 Provider Interceptors

**File:** `drishti/providers/base.py`, `drishti/providers/openai.py`, etc.

Each provider interceptor monkey-patches a specific SDK method. It wraps the original method to:
1. Capture the call inputs as a Span
2. Call the original method
3. Fill the Span with response data (tokens, model, output)
4. Send the completed Span to the Collector

#### BaseInterceptor

```python
from abc import ABC, abstractmethod

class BaseInterceptor(ABC):
    """
    ABC for all provider interceptors.
    Subclasses implement patch() and unpatch().
    """

    @abstractmethod
    def patch(self) -> None:
        """Replace the SDK method with the instrumented version."""
        ...

    @abstractmethod
    def unpatch(self) -> None:
        """Restore the original SDK method."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...
```

#### OpenAI Interceptor (detailed example)

```python
# drishti/providers/openai.py
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from ..collector import collector
from ..models.span import Span, SpanStatus, TokenUsage
from ..cost.calculator import calculate_cost
from .base import BaseInterceptor

class OpenAIInterceptor(BaseInterceptor):
    provider_name = "openai"

    def __init__(self):
        self._original_create = None
        self._original_async_create = None

    def patch(self) -> None:
        try:
            import openai
        except ImportError:
            return  # OpenAI not installed, skip silently

        # Patch sync completions
        original = openai.chat.completions.create
        self._original_create = original

        def patched_create(*args, **kwargs) -> Any:
            if not collector.is_active:
                return original(*args, **kwargs)   # Pure passthrough

            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            started_at = datetime.now(timezone.utc)
            t0 = time.perf_counter()

            span = Span(
                span_id=str(uuid.uuid4()),
                step=0,  # Will be set by collector.record_span
                name=f"openai/{model}",
                provider="openai",
                model=model,
                started_at=started_at,
                input=messages,
            )

            try:
                response = original(*args, **kwargs)
                latency_ms = (time.perf_counter() - t0) * 1000

                usage = response.usage
                tokens = TokenUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                )
                cost = calculate_cost("openai", model, tokens)
                span.finish(
                    output=response,
                    tokens=tokens,
                    cost=cost,
                )
                span.latency_ms = latency_ms
                span.ended_at = datetime.now(timezone.utc)

            except Exception as e:
                span.fail(e)
                raise  # Always re-raise — never swallow user errors

            finally:
                collector.record_span(span)

            return response

        openai.chat.completions.create = patched_create

        # Patch async completions (same logic, async version)
        # ... (see async section for full pattern)

    def unpatch(self) -> None:
        try:
            import openai
            if self._original_create:
                openai.chat.completions.create = self._original_create
        except ImportError:
            pass
```

**Key decisions:**
- Each interceptor patches at the lowest possible SDK level — the `create()` method directly. This catches calls regardless of which wrapper (LangChain, LlamaIndex, etc.) is on top.
- Errors are ALWAYS re-raised. Drishti must never swallow exceptions or change agent behavior.
- The span is always recorded (in `finally`), even on error. This gives the developer visibility into failed calls.
- `if not collector.is_active: return original(...)` — zero overhead outside of a trace context.

#### Interceptors Registry

`drishti/providers/__init__.py` maintains a list of all interceptor instances. The `@trace` decorator iterates this list to `patch()` and `unpatch()` all providers in one call.

```python
from .openai import OpenAIInterceptor
from .anthropic import AnthropicInterceptor
from .groq import GroqInterceptor
from .ollama import OllamaInterceptor

ALL_INTERCEPTORS = [
    OpenAIInterceptor(),
    AnthropicInterceptor(),
    GroqInterceptor(),
    OllamaInterceptor(),
]
```

---

### 5.5 @trace Decorator

**File:** `drishti/trace.py`

The `@trace` decorator is the single entry point for users. It:
1. Creates a new Trace
2. Activates all provider patches
3. Runs the user function
4. Deactivates patches
5. Finalizes the trace
6. Renders the display
7. Exports to JSON (if configured)
8. Returns the function result

```python
import functools
import uuid
from datetime import datetime, timezone
from typing import Optional, Callable, Any

from .collector import collector
from .models.trace import Trace, TraceStatus
from .providers import ALL_INTERCEPTORS
from .display.tree import render_trace_tree
from .display.summary import render_summary
from .export.json import export_trace
from .config import get_config

def trace(
    name: Optional[str] = None,
    export: bool = True,
    display: bool = True,
    budget_usd: Optional[float] = None,
):
    """
    Decorator to trace all LLM calls inside the decorated function.

    Usage:
        @trace(name="my-agent")
        def run(query):
            ...

        @trace  # name defaults to function name
        def run(query):
            ...
    """
    def decorator(func: Callable) -> Callable:
        trace_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            cfg = get_config()
            t = Trace(
                trace_id=str(uuid.uuid4()),
                name=trace_name,
                started_at=datetime.now(timezone.utc),
            )

            # Activate
            collector.start_trace(t)
            for interceptor in ALL_INTERCEPTORS:
                interceptor.patch()

            result = None
            try:
                result = func(*args, **kwargs)
                t.status = TraceStatus.SUCCESS
            except Exception as e:
                t.status = TraceStatus.ERROR
                raise
            finally:
                # Always deactivate, even on exception
                for interceptor in ALL_INTERCEPTORS:
                    interceptor.unpatch()
                t.ended_at = datetime.now(timezone.utc)
                collector.end_trace()

                # Display + Export happen regardless of success/failure
                if display or cfg.display:
                    render_trace_tree(t)
                    render_summary(t)
                if export or cfg.export:
                    export_trace(t)

                # Budget guard (post-run warning for v0.1, abort in v0.2)
                if budget_usd and t.total_cost_usd > budget_usd:
                    import warnings
                    warnings.warn(
                        f"[Drishti] Budget exceeded: ${t.total_cost_usd:.4f} > ${budget_usd:.4f}"
                    )

            return result

        # Also support async functions
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # Same logic as wrapper but with `await func(...)`
            ...

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    # Handle bare @trace (no parentheses) vs @trace(...) (with args)
    if callable(name):
        func, name = name, None
        return decorator(func)
    return decorator
```

**Key decisions:**
- Supports both `@trace` (bare) and `@trace(name="foo")` usage patterns.
- Detects async functions via `asyncio.iscoroutinefunction` and returns the appropriate wrapper.
- Display and export happen in `finally`, so traces are always saved even when the agent crashes. This is critical for debugging.

---

### 5.6 Cost Calculator

**File:** `drishti/cost/pricing.py`, `drishti/cost/calculator.py`

The pricing table maps `(provider, model)` → `(input_cost_per_1k, output_cost_per_1k)` in USD.

```python
# drishti/cost/pricing.py

PRICING: dict[tuple[str, str], tuple[float, float]] = {
    # (provider, model): (input $/1K tokens, output $/1K tokens)

    # OpenAI
    ("openai", "gpt-4o"):                  (0.0025, 0.0100),
    ("openai", "gpt-4o-mini"):             (0.00015, 0.0006),
    ("openai", "gpt-4-turbo"):             (0.0100, 0.0300),
    ("openai", "gpt-3.5-turbo"):           (0.0005, 0.0015),
    ("openai", "o1"):                      (0.0150, 0.0600),
    ("openai", "o1-mini"):                 (0.0030, 0.0120),

    # Anthropic
    ("anthropic", "claude-3-5-sonnet-20241022"): (0.003, 0.015),
    ("anthropic", "claude-3-5-haiku-20241022"):  (0.0008, 0.004),
    ("anthropic", "claude-3-opus-20240229"):      (0.015, 0.075),

    # Groq (approximate)
    ("groq", "llama-3.3-70b-versatile"):   (0.00059, 0.00079),
    ("groq", "llama-3.1-8b-instant"):      (0.00005, 0.00008),
    ("groq", "mixtral-8x7b-32768"):        (0.00024, 0.00024),

    # Ollama (local, always free)
    # No entries needed; calculator returns 0.0 for unknown models
}

UNKNOWN_COST = (0.0, 0.0)  # Free / unknown models
```

```python
# drishti/cost/calculator.py

from .pricing import PRICING, UNKNOWN_COST
from ..models.span import TokenUsage

def calculate_cost(provider: str, model: str, tokens: TokenUsage) -> float:
    """
    Returns cost in USD for a given provider/model/token usage.
    Returns 0.0 for unknown or local models.
    """
    key = (provider, model)
    # Try exact match first, then prefix match for versioned models
    price = PRICING.get(key)
    if price is None:
        # Prefix match: "gpt-4o-2024-11-20" → "gpt-4o"
        for (p, m), v in PRICING.items():
            if p == provider and model.startswith(m):
                price = v
                break
    if price is None:
        price = UNKNOWN_COST

    input_cost_per_1k, output_cost_per_1k = price
    cost = (
        (tokens.prompt_tokens / 1000) * input_cost_per_1k
        + (tokens.completion_tokens / 1000) * output_cost_per_1k
    )
    return round(cost, 6)
```

**Key decisions:**
- Prefix matching handles versioned model names like `gpt-4o-2024-11-20` gracefully.
- Ollama and other local models return `0.0` — no crash, no warning, just free.
- Pricing data is a plain dict in source code. Users can override it via config for enterprise/custom pricing.

---

### 5.7 Display Engine

**File:** `drishti/display/tree.py`, `drishti/display/summary.py`

Uses the `rich` library to render a tree view and a summary panel in the terminal.

#### Tree View (`tree.py`)

```python
from rich.console import Console
from rich.tree import Tree
from rich.text import Text
from ..models.trace import Trace
from ..models.span import SpanStatus

console = Console()

def render_trace_tree(trace: Trace) -> None:
    root_label = Text()
    root_label.append("🔍 Drishti Trace", style="bold cyan")
    root_label.append(f" — {trace.name}", style="bold white")

    tree = Tree(root_label)

    for span in trace.spans:
        # Status icon
        if span.status == SpanStatus.SUCCESS:
            icon = "[green]✅[/green]"
        elif span.status == SpanStatus.ERROR:
            icon = "[red]❌[/red]"
        else:
            icon = "[yellow]⏳[/yellow]"

        # Build node label
        label = (
            f"{icon} [dim][{span.step}][/dim] "
            f"[bold]{span.name}[/bold]  "
            f"[cyan]{span.tokens.total_tokens} tokens[/cyan]  "
            f"[yellow]${span.cost_usd:.4f}[/yellow]  "
            f"[dim]{span.latency_ms:.0f}ms[/dim]"
        )

        node = tree.add(label)

        # Show error detail inline
        if span.status == SpanStatus.ERROR and span.error:
            node.add(f"[red]{span.error_type}: {span.error}[/red]")

    console.print(tree)
```

**Terminal output example:**
```
🔍 Drishti Trace — research-agent
├── ✅ [1] openai/gpt-4o-mini   312 tokens  $0.0001  124ms
├── ✅ [2] openai/gpt-4o        891 tokens  $0.0089  387ms
└── ❌ [3] anthropic/claude-3-5-sonnet  0 tokens  $0.0000  23ms
        AuthenticationError: Invalid API key
```

#### Summary Panel (`summary.py`)

```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from ..models.trace import Trace

console = Console()

def render_summary(trace: Trace) -> None:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim")
    table.add_column(style="bold")

    table.add_row("Total Tokens",  str(trace.total_tokens.total_tokens))
    table.add_row("Total Cost",    f"${trace.total_cost_usd:.4f} USD")
    table.add_row("Wall Time",     f"{trace.total_latency_ms:.0f}ms")
    table.add_row("LLM Calls",     str(trace.span_count))
    table.add_row("Status",        trace.status.value.upper())

    console.print(Panel(
        table,
        title="[bold]Summary[/bold]",
        border_style="cyan" if trace.status.value == "success" else "red",
    ))
    if trace.status.value == "success":
        console.print(
            f"[dim]Trace saved → .drishti/traces/{trace.trace_id[:8]}.json[/dim]"
        )
```

---

### 5.8 Export System

**File:** `drishti/export/json.py`

Serializes a `Trace` to a JSON file and saves it under `.drishti/traces/`.

```python
import json
import os
from datetime import datetime
from pathlib import Path
from ..models.trace import Trace
from ..models.span import Span

TRACES_DIR = Path(".drishti/traces")

def _span_to_dict(span: Span) -> dict:
    return {
        "span_id":    span.span_id,
        "step":       span.step,
        "name":       span.name,
        "provider":   span.provider,
        "model":      span.model,
        "started_at": span.started_at.isoformat(),
        "ended_at":   span.ended_at.isoformat() if span.ended_at else None,
        "tokens": {
            "prompt":     span.tokens.prompt_tokens,
            "completion": span.tokens.completion_tokens,
            "total":      span.tokens.total_tokens,
        },
        "cost_usd":   span.cost_usd,
        "latency_ms": span.latency_ms,
        "status":     span.status.value,
        "error":      span.error,
        "error_type": span.error_type,
        # Note: input/output are stored as strings to avoid
        # complex serialization of provider-specific objects
        "input":  _safe_str(span.input),
        "output": _safe_str(span.output),
    }

def _safe_str(obj) -> str:
    try:
        return json.dumps(obj, default=str)
    except Exception:
        return str(obj)

def export_trace(trace: Trace) -> Path:
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = trace.started_at.strftime("%Y%m%d_%H%M%S")
    filename = TRACES_DIR / f"{timestamp}_{trace.name[:20]}.json"

    payload = {
        "trace_id":   trace.trace_id,
        "name":       trace.name,
        "started_at": trace.started_at.isoformat(),
        "ended_at":   trace.ended_at.isoformat() if trace.ended_at else None,
        "status":     trace.status.value,
        "summary": {
            "total_tokens": trace.total_tokens.total_tokens,
            "total_cost_usd": trace.total_cost_usd,
            "total_latency_ms": trace.total_latency_ms,
            "span_count": trace.span_count,
        },
        "spans": [_span_to_dict(s) for s in trace.spans],
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return filename
```

---

### 5.9 CLI

**File:** `drishti/cli/main.py`

Built with `typer`. Three commands: `view`, `list`, `clear`.

```python
import typer
import json
from pathlib import Path
from rich.console import Console
from ..export.json import TRACES_DIR
from ..display.tree import render_trace_from_dict
from ..display.summary import render_summary_from_dict

app = typer.Typer(help="Drishti — AI Agent Tracer")
console = Console()

@app.command()
def view(filename: str = typer.Argument(..., help="Trace file or trace ID prefix")):
    """Replay a saved trace in the terminal."""
    path = Path(filename) if Path(filename).exists() else _find_trace(filename)
    if not path:
        console.print(f"[red]Trace not found: {filename}[/red]")
        raise typer.Exit(1)
    data = json.loads(path.read_text())
    render_trace_from_dict(data)
    render_summary_from_dict(data)

@app.command()
def list():
    """List all saved traces."""
    if not TRACES_DIR.exists():
        console.print("[dim]No traces found.[/dim]")
        return
    files = sorted(TRACES_DIR.glob("*.json"), reverse=True)
    for f in files:
        data = json.loads(f.read_text())
        status_color = "green" if data["status"] == "success" else "red"
        console.print(
            f"[dim]{f.name}[/dim]  "
            f"[bold]{data['name']}[/bold]  "
            f"[{status_color}]{data['status']}[/{status_color}]  "
            f"[cyan]{data['summary']['total_tokens']} tokens[/cyan]  "
            f"[yellow]${data['summary']['total_cost_usd']:.4f}[/yellow]"
        )

@app.command()
def clear():
    """Delete all saved traces."""
    if not TRACES_DIR.exists():
        console.print("[dim]Nothing to clear.[/dim]")
        return
    confirm = typer.confirm("Delete all saved traces?")
    if confirm:
        for f in TRACES_DIR.glob("*.json"):
            f.unlink()
        console.print("[green]All traces cleared.[/green]")

def _find_trace(prefix: str) -> Path | None:
    for f in TRACES_DIR.glob("*.json"):
        if f.stem.startswith(prefix) or prefix in f.stem:
            return f
    return None

def main():
    app()
```

---

## 6. Data Flow

This is the full sequence of events for a single `@trace`-decorated function call:

```
1. Developer calls run_agent("What is quantum computing?")

2. @trace wrapper fires:
   a. Creates Trace(trace_id=UUID, name="run_agent", started_at=now)
   b. collector.start_trace(trace)
   c. ALL_INTERCEPTORS → interceptor.patch()  [monkey-patch each provider SDK]
   d. Calls original run_agent("What is quantum computing?")

3. Inside run_agent, code calls openai.chat.completions.create(...)
   a. patched_create() fires instead
   b. collector.is_active → True
   c. Creates Span(span_id=UUID, provider="openai", model="gpt-4o", input=messages)
   d. Calls original openai.chat.completions.create(...)
   e. Response returns
   f. Extracts token usage from response
   g. calculate_cost("openai", "gpt-4o", tokens) → $0.0089
   h. span.finish(output=response, tokens=..., cost=0.0089)
   i. collector.record_span(span) → span.step = 1, appended to trace.spans

4. run_agent returns final result

5. @trace wrapper finally block:
   a. ALL_INTERCEPTORS → interceptor.unpatch()  [restore original methods]
   b. trace.ended_at = now
   c. trace.status = SUCCESS
   d. collector.end_trace()
   e. render_trace_tree(trace) → Rich terminal tree printed
   f. render_summary(trace) → Rich panel printed
   g. export_trace(trace) → .drishti/traces/20260416_153042_run_agent.json written

6. @trace wrapper returns the original return value from run_agent
```

---

## 7. Provider Interception Strategy

### Why monkey-patching?

The alternative approaches are:
- **Requiring users to wrap every LLM call** — too much friction, defeats the purpose
- **Middleware/proxy** — requires changing baseURL in SDK config, doesn't work with all providers
- **Subclassing SDK clients** — requires users to instantiate Drishti's version of the client

Monkey-patching at the method level is the only approach that requires **zero changes to existing agent code** beyond the decorator.

### What exactly is patched?

| Provider | Patched Method |
|---|---|
| OpenAI | `openai.chat.completions.create` (sync + async) |
| Anthropic | `anthropic.Anthropic.messages.create` (sync + async) |
| Groq | `groq.Client.chat.completions.create` (sync + async) |
| Ollama | `ollama.chat` (sync + async) |

### Patch lifecycle

Patches are applied **at the start of each `@trace` call** and removed **at the end**. They are NOT applied at import time. This means:

- Two sequential `@trace` calls work correctly
- Nested `@trace` calls (agent calls another traced agent) work correctly — the inner call's spans go to the innermost active trace
- Code outside any `@trace` call is never patched

### Nested trace handling

When a traced function calls another traced function, the Collector's thread-local storage is **overwritten** with the inner trace. This is intentional for v0.1 — inner traces are independent. A future version (v0.3+) may support nested spans under a single parent trace.

---

## 8. Context Propagation (Thread Safety)

The Collector uses `threading.local()` to store the active trace per thread. This ensures:

```python
# Thread 1: runs agent_a — its spans go to trace_a
# Thread 2: runs agent_b — its spans go to trace_b
# They never interfere.
```

**AsyncIO (single thread, multiple coroutines):**
For async agents, all coroutines run on the same thread, so `threading.local()` is insufficient. The async wrapper uses `contextvars.ContextVar` instead, which is propagated correctly by `asyncio` to child tasks.

```python
import contextvars

_active_trace: contextvars.ContextVar = contextvars.ContextVar(
    "drishti_active_trace", default=None
)
```

The `_Collector` class checks both `threading.local()` (sync) and `ContextVar` (async) and merges them in a single `active_trace` property.

---

## 9. Async Support

All four provider interceptors patch both the sync and async versions of their SDK methods. The async wrapper is structurally identical to the sync one, but uses `await`:

```python
async def async_patched_create(*args, **kwargs):
    if not collector.is_active:
        return await original_async(*args, **kwargs)
    # ... same span creation logic ...
    response = await original_async(*args, **kwargs)
    # ... same span finishing logic ...
    return response
```

The `@trace` decorator detects `asyncio.iscoroutinefunction(func)` at decoration time and returns the correct wrapper automatically.

---

## 10. Configuration System

**File:** `drishti/config.py`

Drishti reads configuration from (in priority order):
1. Keyword arguments passed to `@trace(...)`
2. `.drishti/config.toml` in the current working directory
3. `~/.drishti/config.toml` (user-global config)
4. Built-in defaults

```toml
# .drishti/config.toml

[drishti]
display = true        # Print trace tree to terminal
export = true         # Save traces to .drishti/traces/
traces_dir = ".drishti/traces"
budget_usd = 0.10     # Warn if a single trace exceeds this cost

[drishti.pricing]     # Override model prices (optional)
"openai/gpt-4o" = [0.0025, 0.010]
```

```python
# drishti/config.py
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

@dataclass
class DrishtiConfig:
    display: bool = True
    export: bool = True
    traces_dir: str = ".drishti/traces"
    budget_usd: Optional[float] = None
    pricing_overrides: dict = field(default_factory=dict)

def get_config() -> DrishtiConfig:
    """Load config from TOML files, falling back to defaults."""
    ...
```

---

## 11. Error Handling Strategy

| Scenario | Drishti Behavior |
|---|---|
| Provider SDK not installed | `patch()` returns silently, no crash |
| LLM call raises exception | Span is recorded with `status=ERROR`, exception is re-raised |
| Token usage missing from response | Span tokens default to 0, cost to 0.0, no crash |
| Unknown model in pricing table | Cost returns 0.0, span still recorded normally |
| JSON export fails (disk full, permissions) | Warning printed, trace NOT saved, no crash |
| Display fails (no TTY, import error) | Warning printed, display skipped, no crash |
| Nested traces | Inner trace is independent, both display correctly |

**The golden rule:** Drishti must **never** change the behavior of the agent code. If Drishti itself fails for any reason, the agent continues as if Drishti were not installed.

---

## 12. Testing Strategy

### Unit tests
- `test_span.py` — Span creation, finish(), fail(), property computation
- `test_trace.py` — Trace aggregation properties (total_tokens, total_cost_usd)
- `test_collector.py` — Thread safety, start/end/record cycle
- `test_cost.py` — Pricing table correctness, prefix matching, unknown models

### Provider tests (mocked)
Each provider interceptor is tested with a mocked SDK using `unittest.mock.patch`. Tests verify:
- Span is correctly created from request kwargs
- Span is correctly filled from response object
- Errors are correctly captured and re-raised
- No span recorded when `collector.is_active == False`

### Integration tests
- `test_trace_decorator.py` — Full end-to-end with mocked providers
- `test_async_trace.py` — Async decorator with mocked async providers

### Testing approach for display
Use `rich`'s `Console(record=True)` to capture terminal output and assert its content.

---

## 13. Public API Surface

Everything in `drishti/__init__.py`:

```python
from .trace import trace
from .models.span import Span, SpanStatus, TokenUsage
from .models.trace import Trace, TraceStatus
from .collector import collector
from .config import DrishtiConfig

__version__ = "0.1.0"
__all__ = [
    "trace",
    "Span", "SpanStatus", "TokenUsage",
    "Trace", "TraceStatus",
    "collector",
    "DrishtiConfig",
]
```

Minimal public surface. Everything in `providers/`, `display/`, `export/`, and `cost/` is internal and subject to change between versions.

---

## 14. Key Design Decisions & Tradeoffs

| Decision | Why | Tradeoff |
|---|---|---|
| Monkey-patch over middleware proxy | Zero user friction | Less stable if SDK internals change |
| Thread-local + ContextVar hybrid | Correct for both sync threads and async | Adds complexity to Collector |
| Patches applied per-trace, not at import | No side effects outside traces | Tiny overhead at trace entry/exit |
| Input/output stored as raw objects | Full fidelity for JSON export | Cannot serialize all provider objects trivially |
| `finally` for display+export | Always runs, even on crash | Trace always saved even for broken agents |
| Pydantic not used for models | Lighter dependency, faster | Manual validation required |
| No web UI in v0.1 | Ships faster, solves core need | Power users want dashboard |
| Nested traces are independent | Simple mental model | Cannot correlate parent/child automatically |

---

*Drishti (दृष्टि) — See what your agent thinks.*
