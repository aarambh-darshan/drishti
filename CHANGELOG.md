# Changelog

All notable changes to Drishti will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.2] — 2026-04-16

### Added

- Streaming interception support for OpenAI and Anthropic (`stream=True`, sync + async)
- `on_exceed` budget policy with hard-abort support and `DrishtiBudgetError`
- Stack-based nested trace context handling and patch lifecycle manager for concurrent traces
- New CLI commands: `drishti version`, `drishti diff`, `drishti stats`, `drishti export --format csv`, `drishti replay`
- Extended trace JSON schema with `schema_version`, `streaming`, `estimated_tokens`, and `request_payload`
- New provider interceptors: Mistral, Together, Cohere
- Config additions: `default_export_dir`, `quiet`, `auto_open_on_error`, `max_preview_chars`, `estimate_stream_tokens`
- `examples/multi_step_agent.py`

### Changed

- Provider missing dependency handling now emits one-time actionable warnings
- Display output now shows provider/model separately, cost color thresholds, streaming label, and truncated I/O previews
- Trace replay and diff workflows now available in CLI
- Added `py.typed` marker and updated optional dependency extras

---

## [0.1.0] — 2026-04-16

### 🎉 Initial Release — Core Foundation

The first release of Drishti — a Python library that automatically captures, visualizes, and exports traces of AI agent execution.

### Added

#### `@trace` Decorator
- `@trace` bare usage — defaults name to function name
- `@trace(name="my-agent")` with custom trace name
- Sync function support
- Async function (`async def`) support
- Correct behavior on exception — trace is still displayed and exported
- Budget warning: `@trace(budget_usd=0.05)` prints warning if cost exceeds threshold

#### Provider Interceptors
- **OpenAI** — `chat.completions.create` (sync + async)
- **Anthropic** — `messages.create` (sync + async)
- **Groq** — `chat.completions.create` (sync + async)
- **Ollama** — `chat()` (sync + async)
- Graceful skip if provider SDK is not installed (no crash)
- Zero-overhead passthrough when no trace is active

#### Data Models
- `Span` dataclass — span_id, step, provider, model, input, output, tokens, cost, latency, status, error
- `Trace` dataclass — trace_id, name, spans, status, timing
- `TokenUsage` dataclass — prompt_tokens, completion_tokens, total_tokens
- `SpanStatus` enum — PENDING, SUCCESS, ERROR
- `TraceStatus` enum — RUNNING, SUCCESS, ERROR
- Computed properties: `total_tokens`, `total_cost_usd`, `total_latency_ms`

#### Collector
- Thread-local storage for active trace (sync thread safety)
- `ContextVar` for async/coroutine safety
- `start_trace()`, `end_trace()`, `record_span()` API
- Auto-step numbering on `record_span()`

#### Cost Calculator
- Pricing table: OpenAI (gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo, o1, o1-mini, o3-mini)
- Pricing table: Anthropic (claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus, claude-sonnet-4)
- Pricing table: Groq (llama-3.3-70b, llama-3.1-8b, mixtral-8x7b)
- Local models (Ollama) always return $0.00
- Prefix matching for versioned model names (e.g. `gpt-4o-2024-11-20` → `gpt-4o`)
- Unknown model → $0.00, no crash

#### Display Engine
- Rich terminal tree view with step numbers, provider/model, tokens, cost, latency
- ✅ / ❌ / ⏳ status icons per span
- Error details shown inline under failed spans
- Summary panel: total tokens, total cost, wall time, LLM call count, status

#### Export System
- Serialize Trace → JSON
- Auto-create `.drishti/traces/` directory
- Filename format: `YYYYMMDD_HHMMSS_<name>.json`
- Full span data preserved: input, output, all metrics
- Summary block at top of JSON for quick scanning

#### CLI
- `drishti list` — list all saved traces with status, cost, tokens
- `drishti view <file|id>` — replay trace tree from JSON
- `drishti clear` — delete all traces (with confirmation prompt)
- Entrypoint registered in `pyproject.toml`

#### Configuration
- `.drishti/config.toml` support
- Options: `display`, `export`, `traces_dir`, `budget_usd`
- Defaults work without any config file (zero-config)

#### Packaging
- `pyproject.toml` with hatchling build system
- Optional dependencies: `drishti[openai]`, `drishti[anthropic]`, `drishti[groq]`, `drishti[ollama]`, `drishti[all]`
- CLI entrypoint: `drishti = "drishti.cli.main:main"`
- Python 3.10+ support

#### Tests
- 73 unit, provider, and integration tests
- 72% code coverage
- Provider interceptor tests with mocked SDKs
- Integration tests for sync and async `@trace` decorator

#### Documentation
- README with quickstart guide
- ARCHITECTURE.md with full system design
- ROADMAP.md with versioned feature plan
- Example scripts: openai_agent.py, anthropic_agent.py, async_agent.py

---

[0.1.0]: https://github.com/aarambh-darshan/drishti/releases/tag/v0.1.0
[0.2.2]: https://github.com/aarambh-darshan/drishti/releases/tag/v0.2.2
