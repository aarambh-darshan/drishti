<p align="center">
  <h1 align="center">🔍 Drishti (दृष्टि)</h1>
  <p align="center"><strong>See what your agent thinks.</strong></p>
  <p align="center">
    <a href="https://github.com/aarambh-darshan/drishti/actions"><img src="https://github.com/aarambh-darshan/drishti/workflows/CI/badge.svg" alt="CI"></a>
    <a href="https://pypi.org/project/drishti-ai/"><img src="https://img.shields.io/pypi/v/drishti-ai?color=blue" alt="PyPI"></a>
    <a href="https://pypi.org/project/drishti-ai/"><img src="https://img.shields.io/pypi/pyversions/drishti-ai" alt="Python"></a>
    <a href="https://github.com/aarambh-darshan/drishti/blob/main/LICENSE"><img src="https://img.shields.io/github/license/aarambh-darshan/drishti" alt="License"></a>
    <a href="https://buymeacoffee.com/aarambhdevhub"><img src="https://img.shields.io/badge/Support-Buy%20Me%20a%20Coffee-FFDD00?logo=buymeacoffee&logoColor=000000" alt="Buy Me a Coffee"></a>
    <a href="https://github.com/sponsors/aarambh-darshan"><img src="https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-ea4aaa?logo=githubsponsors&logoColor=white" alt="GitHub Sponsors"></a>
  </p>
</p>

---

**Drishti** automatically captures, visualizes, and exports traces of AI agent execution. Add one decorator — see every LLM call with tokens, cost, and latency. Zero code changes to your agent logic.

```python
from drishti import trace

@trace(name="my-agent")
def run_agent(query):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": query}],
    )
    return response.choices[0].message.content
```

```
🔍 Drishti Trace — my-agent
├── ✅ [1] openai/gpt-4o-mini   312 tokens  $0.0001  124ms
└── ✅ [2] openai/gpt-4o        891 tokens  $0.0089  387ms

╭──────────── Summary ────────────╮
│ Total Tokens  1203              │
│ Total Cost    $0.0090 USD       │
│ Wall Time     511ms             │
│ LLM Calls     2                 │
│ Status        SUCCESS           │
╰─────────────────────────────────╯
```

---

## ✨ Features

- **🔌 Zero-config auto-detection** — OpenAI, Anthropic, Groq, Ollama intercepted automatically
- **🌳 Rich terminal tree** — every LLM call with tokens, cost, and latency at a glance
- **💾 JSON export** — full traces saved to `.drishti/traces/` for sharing, diffing, and replaying
- **🖥️ CLI tool** — `drishti version`, `drishti list`, `drishti view`, `drishti diff`, `drishti stats`, `drishti export`, `drishti replay`, `drishti clear`
- **💰 Cost tracking** — real-time pricing for 15+ models across 4 providers
- **🛡️ Budget guard** — warn when cost exceeds a threshold
- **⚡ Async support** — works with `async def` functions out of the box
- **🔒 Thread-safe** — correct isolation for concurrent agents via thread-local + ContextVar
- **🪶 Zero overhead** — pure passthrough when no `@trace` context is active

---

## 🚀 Quickstart

### Install

```bash
pip install drishti-ai[openai]        # OpenAI support
# or
pip install drishti-ai[anthropic]     # Anthropic support
# or
pip install drishti-ai[all]           # All providers
```

### Trace Your Agent

```python
from drishti import trace
import openai

client = openai.OpenAI()

@trace(name="research-agent")
def research_agent(query: str) -> str:
    # Step 1: Generate search queries
    plan = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Generate 3 search queries for the topic."},
            {"role": "user", "content": query},
        ],
    )
    queries = plan.choices[0].message.content

    # Step 2: Synthesize answer with a stronger model
    answer = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Synthesize a comprehensive answer."},
            {"role": "user", "content": f"Topic: {query}\nQueries: {queries}"},
        ],
    )
    return answer.choices[0].message.content

result = research_agent("What is quantum computing?")
```

That's it. Drishti automatically:
1. **Intercepts** both LLM calls
2. **Captures** tokens, cost, latency, and full I/O
3. **Renders** a rich terminal tree
4. **Exports** the trace to `.drishti/traces/` as JSON

---

## 📦 Installation

```bash
pip install drishti-ai              # Core only (no provider SDKs)
pip install drishti-ai[openai]      # + OpenAI SDK
pip install drishti-ai[anthropic]   # + Anthropic SDK
pip install drishti-ai[groq]        # + Groq SDK
pip install drishti-ai[ollama]      # + Ollama SDK
pip install drishti-ai[all]         # All providers
```

**Requirements:** Python 3.10+

---

## 🎯 Supported Providers

| Provider | SDK Method Patched | Pricing |
|---|---|---|
| **OpenAI** | `chat.completions.create` (sync + async) | gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo, o1, o1-mini, o3-mini |
| **Anthropic** | `messages.create` (sync + async) | claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus, claude-sonnet-4 |
| **Groq** | `chat.completions.create` (sync + async) | llama-3.3-70b, llama-3.1-8b, mixtral-8x7b |
| **Ollama** | `chat()` (sync + async) | All local models — always $0.00 |

> **Provider not installed?** Drishti keeps running and prints a one-time actionable warning with the install extra.
>
> **Unknown model?** Cost defaults to $0.00. Trace still works perfectly.

---

## 🖥️ CLI

```bash
# Print installed version
drishti version

# List all saved traces
drishti list

# Replay a trace in the terminal
drishti view <file>          # by file path
drishti view <id-prefix>     # by trace ID prefix
drishti view <file> --full   # show full prompt/completion payloads

# Compare two traces
drishti diff <trace-a> <trace-b>

# Aggregate stats
drishti stats

# Export a trace as CSV
drishti export <trace> --format csv

# Replay the same LLM requests and compare deltas
drishti replay <trace>

# Delete all saved traces
drishti clear
```

**Example output of `drishti list`:**
```
📋 Saved Traces

  20260416_153042_research_agent.json  research-agent  success  1203 tokens  $0.0090
  20260416_152801_claude_agent.json    claude-agent    error    0 tokens     $0.0000
```

---

## ⚡ Async Support

Drishti auto-detects async functions and Just Works™:

```python
from drishti import trace
import openai

client = openai.AsyncOpenAI()

@trace(name="async-agent")
async def async_agent(query: str) -> str:
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": query}],
    )
    return response.choices[0].message.content
```

---

## ⚙️ Configuration

### Per-call configuration

```python
@trace(
    name="my-agent",      # Custom trace name (default: function name)
    budget_usd=0.05,      # Per-trace budget in USD
    on_exceed="warn",     # "warn" (default) or "abort"
    display=True,          # Print tree to terminal (default: True)
    export=True,           # Save JSON to disk (default: True)
)
def my_agent():
    ...
```

### Config file

Create `.drishti/config.toml` in your project root:

```toml
[drishti]
display = true              # Print trace tree to terminal
export = true               # Save traces to disk
default_export_dir = ".drishti/traces"  # Preferred export dir (traces_dir still works)
budget_usd = 0.10           # Budget threshold
on_exceed = "warn"          # "warn" or "abort"
quiet = false               # Suppress terminal tree output
auto_open_on_error = false  # Auto-open trace output on errors
max_preview_chars = 220     # Prompt/completion preview truncation length
estimate_stream_tokens = true  # Use optional tiktoken estimation for streams
```

### Decorator usage patterns

```python
# Bare decorator — name defaults to function name
@trace
def my_agent():
    ...

# With custom name
@trace(name="research-agent")
def my_agent():
    ...

# Budget guard
@trace(budget_usd=0.05)
def expensive_agent():
    ...

# Hard abort once budget is exceeded mid-run
@trace(budget_usd=0.05, on_exceed="abort")
def budget_guarded_agent():
    ...
```

---

## 🛡️ Error Handling

Drishti follows one golden rule: **never change the behavior of your agent code.**

| Scenario | Drishti Behavior |
|---|---|
| Provider SDK not installed | Skipped silently, no crash |
| LLM call raises exception | Span recorded with `status=ERROR`, exception re-raised |
| Token usage missing | Defaults to 0, no crash |
| Unknown model | Cost defaults to $0.00 |
| JSON export fails | Warning printed, agent continues |
| Display fails | Warning printed, agent continues |

---

## 📄 JSON Export Format

Traces are saved to `.drishti/traces/` as JSON:

```json
{
  "trace_id": "a1b2c3d4-...",
  "name": "research-agent",
  "started_at": "2026-04-16T15:30:42.123456+00:00",
  "ended_at": "2026-04-16T15:30:42.634567+00:00",
  "status": "success",
  "summary": {
    "total_tokens": 1203,
    "total_cost_usd": 0.009,
    "total_latency_ms": 511.0,
    "span_count": 2
  },
  "spans": [
    {
      "span_id": "...",
      "step": 1,
      "name": "openai/gpt-4o-mini",
      "provider": "openai",
      "model": "gpt-4o-mini",
      "tokens": { "prompt": 45, "completion": 267, "total": 312 },
      "cost_usd": 0.0001,
      "latency_ms": 124.0,
      "status": "success"
    }
  ]
}
```

---

## 🧪 Development

```bash
# Clone and setup
git clone https://github.com/aarambh-darshan/drishti.git
cd drishti
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,all]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=drishti --cov-report=term-missing

# Lint
ruff check drishti/ tests/
ruff format --check drishti/ tests/
```

---

## 🗺️ Roadmap

| Version | Focus | Status |
|---|---|---|
| **v0.1.0** | Core Foundation | ✅ Released |
| **v0.2.2** | Developer Experience + Replay + Concurrency + New Providers | ✅ Released |
| v0.3.0 | Web Dashboard (`drishti serve`) | 📋 Planned |
| v0.4.0 | Smart Features (prompt analysis, cost optimization) | 🔮 Future |
| v0.5.0 | Framework Integrations (LangChain, LlamaIndex) | 🔮 Future |
| v1.0.0 | Production-Stable Release | 🔮 Future |

See [ROADMAP.md](ROADMAP.md) for the full feature plan.

---

## 📐 Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the complete system design, including:
- System architecture diagram
- Data flow walkthrough
- Provider interception strategy
- Thread safety / async support design
- Error handling philosophy

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## ❤️ Support

If Drishti helps your work and you want to support ongoing development:

- [Buy Me a Coffee](https://buymeacoffee.com/aarambhdevhub)
- [GitHub Sponsors](https://github.com/sponsors/aarambh-darshan)

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<p align="center">
  <strong>Drishti (दृष्टि) — See what your agent thinks.</strong>
</p>
