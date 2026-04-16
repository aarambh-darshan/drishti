# ROADMAP.md — Drishti (दृष्टि)

> **Mission:** Give every AI developer complete visibility into their agent's execution — tokens, cost, latency, and errors — with zero code changes.

---

## Versioning Strategy

Drishti follows **Semantic Versioning (SemVer)**: `MAJOR.MINOR.PATCH`

- `PATCH` — Bug fixes, pricing updates, doc improvements
- `MINOR` — New features, new provider support, backward-compatible
- `MAJOR` — Breaking API changes (rare)

**Development phases:**
- `v0.1.x` — Core (the foundation, ships first)
- `v0.2.x` — Developer Experience (make it great to use)
- `v0.3.x` — Web UI (visual dashboard)
- `v0.4.x` — Smart Features (AI-powered insights)
- `v0.5.x` — Integrations (LangChain, LlamaIndex, etc.)
- `v1.0.0` — Production-stable public release

---

## Release Timeline

```
v0.1.0  ████████  Core foundation
v0.2.0      ████████  Developer experience
v0.3.0          ████████  Web dashboard
v0.4.0              ████████  Smart features
v0.5.0                  ████████  Framework integrations
v1.0.0                      ██  Stable release
```

---

## v0.1.0 — Core Foundation

**Goal:** Minimal but complete. A developer adds `@trace` and immediately sees a tree of every LLM call with tokens, cost, and latency. Works out of the box.

**Status:** ✅ Released

### Features

#### `@trace` Decorator
- [x] `@trace` bare usage (no arguments) — defaults name to function name
- [x] `@trace(name="my-agent")` with custom name
- [x] Sync function support
- [x] Async function (`async def`) support
- [x] Correct behavior on exception — trace still displayed and exported
- [x] Budget warning: `@trace(budget_usd=0.05)` prints warning if exceeded

#### Provider Interceptors
- [x] **OpenAI** — `chat.completions.create` (sync + async)
- [x] **Anthropic** — `messages.create` (sync + async)
- [x] **Groq** — `chat.completions.create` (sync + async)
- [x] **Ollama** — `chat()` (sync + async)
- [x] Graceful skip if provider not installed (no crash)
- [x] Correct passthrough when no trace is active (zero overhead)

#### Data Models
- [x] `Span` dataclass — span_id, step, provider, model, input, output, tokens, cost, latency, status, error
- [x] `Trace` dataclass — trace_id, name, spans, status, timing
- [x] `TokenUsage` dataclass
- [x] `SpanStatus` enum (PENDING, SUCCESS, ERROR)
- [x] `TraceStatus` enum (RUNNING, SUCCESS, ERROR)
- [x] Computed properties: `total_tokens`, `total_cost_usd`, `total_latency_ms`

#### Collector
- [x] Thread-local storage for active trace
- [x] `ContextVar` for async/coroutine safety
- [x] `start_trace()`, `end_trace()`, `record_span()` API
- [x] Auto-step numbering on `record_span()`

#### Cost Calculator
- [x] Pricing table: OpenAI (gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo, o1, o1-mini)
- [x] Pricing table: Anthropic (claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus)
- [x] Pricing table: Groq (llama-3.3-70b, llama-3.1-8b, mixtral-8x7b)
- [x] Local models (Ollama) always return $0.00
- [x] Prefix matching for versioned model names (e.g. `gpt-4o-2024-11-20`)
- [x] Unknown model → $0.00, no crash

#### Display Engine
- [x] Rich terminal tree view with step numbers, provider, tokens, cost, latency
- [x] ✅ / ❌ status icons per span
- [x] Error details shown inline under failed spans
- [x] Summary panel: total tokens, total cost, wall time, call count, status
- [x] Trace save path shown at bottom

#### Export System
- [x] Serialize Trace → JSON
- [x] Auto-create `.drishti/traces/` directory
- [x] Filename format: `YYYYMMDD_HHMMSS_<name>.json`
- [x] Full span data preserved: input (as string), output (as string), all metrics
- [x] Summary block at top of JSON for quick scanning

#### CLI
- [x] `drishti list` — list all saved traces with status, cost, tokens
- [x] `drishti view <file|id>` — replay trace tree from JSON
- [x] `drishti clear` — delete all traces (with confirmation prompt)
- [x] Entrypoint registered in `pyproject.toml`

#### Configuration
- [x] `.drishti/config.toml` support
- [x] `display`, `export`, `traces_dir`, `budget_usd` options
- [x] Defaults work without any config file

#### Packaging
- [x] `pyproject.toml` with `[build-system]`, `[project]`, `[project.optional-dependencies]`
- [x] Optional dependencies: `drishti[openai]`, `drishti[anthropic]`, `drishti[groq]`, `drishti[ollama]`, `drishti[all]`
- [x] CLI entrypoint: `drishti = "drishti.cli.main:main"`
- [ ] Published to PyPI as `drishti`

#### Tests
- [x] Unit tests for all core models
- [x] Provider interceptor tests (mocked SDKs)
- [x] Integration test: full end-to-end with mocked OpenAI
- [x] Integration test: full end-to-end with mocked Anthropic
- [x] Integration test: async agent

#### Documentation
- [x] README with quickstart (install → `@trace` → output screenshot)
- [x] `ARCHITECTURE.md` (this file's companion)
- [x] `examples/openai_agent.py`
- [x] `examples/anthropic_agent.py`
- [x] `examples/async_agent.py`


---

## v0.1.x — Patch Releases

### v0.1.1
- [ ] Fix: Handle OpenAI streaming responses (`stream=True`)
- [ ] Fix: Handle Anthropic streaming responses
- [ ] Pricing: Keep pricing table up to date with latest models

### v0.1.2
- [ ] Add `drishti version` CLI command
- [ ] Improve error messages when SDK is not installed
- [ ] Add `examples/multi_step_agent.py` with a realistic research agent

---

## v0.2.0 — Developer Experience

**Goal:** Make Drishti a joy to use daily. Trace diffing, budget enforcement, streaming support, and smarter output formatting.

**Status:** 📋 Planned

### Features

#### Trace Diffing
- [ ] `drishti diff <trace1.json> <trace2.json>` CLI command
- [ ] Side-by-side comparison: steps, tokens, cost, latency
- [ ] Highlights: which steps are new, which changed, which got faster/slower/cheaper
- [ ] Use case: compare two versions of your agent prompt to see token impact

#### Budget Guard (Hard Abort)
- [ ] `@trace(budget_usd=0.05, on_exceed="abort")` — raises `DrishtiBudgetError` mid-execution
- [ ] `on_exceed="warn"` (default, existing behavior) vs `"abort"`
- [ ] Budget check happens after each span, not just at the end
- [ ] `DrishtiBudgetError` includes trace up to the point of abort

#### Streaming Support
- [ ] OpenAI streaming: `stream=True` — capture chunks, count tokens at end
- [ ] Anthropic streaming — same
- [ ] Show streaming spans in tree with a `⚡ streaming` label
- [ ] Token count from streaming: use tiktoken for client-side estimation when usage not provided

#### `.drishti/config.toml` — Full Implementation
- [ ] Custom pricing overrides per model
- [ ] `default_export_dir` — save traces to a custom path
- [ ] `auto_open_on_error = true` — auto-run `drishti view` on the last trace when an error occurs
- [ ] `quiet = true` — suppress display output (keep export only)

#### Output Quality
- [ ] Truncate long prompt/completion in tree view (configurable max chars)
- [ ] `drishti view --full` to show full input/output in terminal
- [ ] Color-code cost: green ($0.00–$0.01), yellow ($0.01–$0.10), red ($0.10+)
- [ ] Show model name and provider separately in tree

#### New CLI Commands
- [ ] `drishti stats` — aggregate stats across all saved traces (total cost, avg tokens, most expensive agent)
- [ ] `drishti export <trace.json> --format csv` — export trace as CSV for spreadsheet analysis

#### Packaging
- [ ] Python 3.10 compatibility (currently targeting 3.11+)
- [ ] Type stubs (`py.typed` marker, full type annotations)

---

## v0.2.x — Patch Releases

### v0.2.1
- [ ] Add Mistral AI provider interceptor
- [ ] Add Together AI provider interceptor
- [ ] Add Cohere provider interceptor

### v0.2.2
- [ ] Fix edge cases in thread-safety under heavy concurrent load
- [ ] Add `drishti replay <trace.json>` — resend the exact same prompts and compare results

---

## v0.3.0 — Web Dashboard

**Goal:** A beautiful local web UI for browsing, filtering, and comparing traces. Starts with `drishti serve`.

**Status:** 📋 Planned

### Features

#### Local Web Server
- [ ] `drishti serve` — starts a local web server (default `http://localhost:7821`)
- [ ] Built with FastAPI + Jinja2 templates (no npm/Node.js dependency)
- [ ] Reads from `.drishti/traces/` directory
- [ ] Auto-refreshes when new traces are saved (SSE or polling)

#### Trace List Page
- [ ] Table of all traces: name, date, status, tokens, cost, latency
- [ ] Filter by: status, date range, agent name, model
- [ ] Sort by: cost, tokens, latency, date
- [ ] Search by trace name

#### Trace Detail Page
- [ ] Visual tree of spans (HTML/CSS, not just terminal)
- [ ] Each span: expandable to show full input/output
- [ ] Cost breakdown bar chart per span
- [ ] Latency waterfall chart (shows which LLM calls took longest)
- [ ] Token usage breakdown: prompt vs completion per span

#### Diff View
- [ ] Select two traces → side-by-side diff
- [ ] Highlight changed spans, added spans, removed spans
- [ ] Delta shown: Δtokens, Δcost, Δlatency

#### Stats Dashboard
- [ ] Total cost over time (line chart by day)
- [ ] Most called models (pie chart)
- [ ] Average cost per agent
- [ ] Error rate by agent

---

## v0.4.0 — Smart Features

**Goal:** Use AI to help developers understand and improve their agents, not just observe them.

**Status:** 🔮 Future

### Features

#### Automatic Prompt Analysis
- [ ] Detect redundant context in prompt (same text repeated across steps)
- [ ] Estimate tokens that could be saved by compressing system prompt
- [ ] Flag excessively long prompts (>75% of context window used)

#### Cost Optimization Suggestions
- [ ] Suggest cheaper model alternatives for each span ("This step used gpt-4o but gpt-4o-mini could work for classification tasks")
- [ ] Identify spans where output is short (likely doesn't need a large model)
- [ ] Show projected monthly cost if agent runs N times/day

#### Anomaly Detection
- [ ] Alert when a span takes 3x longer than its historical average
- [ ] Alert when token count spikes unexpectedly between runs
- [ ] Alert when model returns empty/very short output (possible prompt issue)

#### `drishti explain <trace.json>`
- [ ] Use an LLM (via Anthropic API) to explain what each step of the agent did, in plain English
- [ ] Identify the "critical path" — which steps took the most tokens/cost

---

## v0.5.0 — Framework Integrations

**Goal:** First-class integration with popular agent frameworks. Zero config required.

**Status:** 🔮 Future

### LangChain Integration
- [ ] `DrishtiCallbackHandler` that plugs into LangChain's callback system
- [ ] Captures chain steps, tool calls, and LLM calls as spans
- [ ] Preserves LangChain-specific metadata (chain name, tool name)
- [ ] Published as `drishti[langchain]`

### LlamaIndex Integration
- [ ] `DrishtiObservabilityPlugin` for LlamaIndex's instrumentation system
- [ ] Captures query engine steps, retrieval results, and LLM calls
- [ ] Published as `drishti[llamaindex]`

### AutoGen / CrewAI
- [ ] Monkey-patch at the LLM client level (already works via provider interceptors)
- [ ] Add agent-name metadata from framework internals
- [ ] Example notebooks for both frameworks

### OpenAI Agents SDK
- [ ] Native integration with the OpenAI Agents SDK tracing hooks
- [ ] Capture tool calls and agent handoffs as spans

---

## v1.0.0 — Production-Stable Release

**Goal:** Drishti is ready for production use. Stable API, comprehensive docs, battle-tested.

**Status:** 🔮 Future

### Stability
- [ ] Public API frozen — no breaking changes without major version bump
- [ ] `CHANGELOG.md` fully maintained
- [ ] 90%+ test coverage across all modules
- [ ] Tested on Python 3.10, 3.11, 3.12, 3.13

### Documentation
- [ ] Full documentation site (MkDocs or Sphinx)
- [ ] Getting Started guide (5-minute quickstart)
- [ ] Provider guides (OpenAI, Anthropic, Groq, Ollama)
- [ ] Framework integration guides
- [ ] API Reference (auto-generated from docstrings)
- [ ] FAQ: "Why are my tokens 0?", "How do I add a custom provider?", etc.

### Community
- [ ] `CONTRIBUTING.md` with full contribution guide
- [ ] Issue templates: bug report, feature request, provider request
- [ ] PR template
- [ ] GitHub Discussions enabled

### Performance
- [ ] Benchmark: overhead of `@trace` with 0 LLM calls < 1ms
- [ ] Benchmark: overhead per span < 0.5ms
- [ ] Memory: trace object < 1MB for 100-span traces

---

## Feature Backlog (Unscheduled)

These are ideas not yet assigned to a version:

- **Trace sharing** — `drishti share <trace.json>` uploads to a public paste service and returns a URL
- **GitHub Actions integration** — upload trace as artifact in CI, comment on PR with cost delta
- **Pytest plugin** — `pytest --drishti` automatically traces all LLM calls in test runs and fails if cost > threshold
- **`.env` cost alerts** — set `DRISHTI_BUDGET_USD=1.00` env var as a global budget
- **Multi-agent tracing** — parent/child trace relationships for agents that spawn sub-agents
- **Replay** — re-execute a saved trace with the same inputs and compare outputs
- **Trace tags** — `@trace(tags=["production", "search-agent"])` for filtering in the dashboard
- **Webhook on error** — `@trace(on_error_webhook="https://...")` POSTs trace JSON to a URL when a span fails
- **OpenTelemetry export** — emit spans as OTLP traces for integration with Jaeger/Grafana

---

## Breaking Changes Policy

- **v0.x.y → v0.x.(y+1)** — No breaking changes. Bug fixes and additive features only.
- **v0.x.y → v0.(x+1).0** — May include breaking changes. Documented in `CHANGELOG.md` with migration guide.
- **v0.x.y → v1.0.0** — Final breaking change window. API frozen after this.

---

## How to Contribute

1. Pick any unchecked item above
2. Open an issue to discuss before starting large features
3. Follow the coding style in `CONTRIBUTING.md`
4. All new features require tests and a working `examples/` script

---

*Drishti (दृष्टि) — See what your agent thinks.*
