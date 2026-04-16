"""Tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from typer.testing import CliRunner

from drishti import __version__
from drishti.cli.main import app

runner = CliRunner()


def _write_trace(path: Path, name: str, cost: float, tokens: int, latency: float) -> None:
    payload = {
        "schema_version": "0.2.2",
        "trace_id": f"{name}-id",
        "name": name,
        "status": "success",
        "summary": {
            "total_tokens": tokens,
            "total_cost_usd": cost,
            "total_latency_ms": latency,
            "span_count": 1,
        },
        "spans": [
            {
                "step": 1,
                "name": "openai/gpt-4o-mini",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "status": "success",
                "tokens": {"prompt": tokens // 2, "completion": tokens // 2, "total": tokens},
                "cost_usd": cost,
                "latency_ms": latency,
                "streaming": False,
                "estimated_tokens": False,
                "request_payload": {
                    "method": "chat.completions.create",
                    "kwargs": {
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": "hello"}],
                    },
                },
                "input": [{"role": "user", "content": "hello"}],
                "output": {"choices": [{"message": {"content": "hi"}}]},
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_diff_stats_and_export_csv(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    traces = tmp_path / ".drishti" / "traces"
    traces.mkdir(parents=True)

    first = traces / "20260101_000000_a.json"
    second = traces / "20260101_000001_b.json"
    _write_trace(first, "agent-a", cost=0.01, tokens=100, latency=100.0)
    _write_trace(second, "agent-b", cost=0.02, tokens=200, latency=200.0)

    diff_result = runner.invoke(app, ["diff", str(first), str(second)])
    assert diff_result.exit_code == 0
    assert "changed" in diff_result.output or "same" in diff_result.output

    stats_result = runner.invoke(app, ["stats"])
    assert stats_result.exit_code == 0
    assert "Trace Count" in stats_result.output

    export_result = runner.invoke(app, ["export", str(first), "--format", "csv"])
    assert export_result.exit_code == 0
    assert first.with_suffix(".csv").exists()


def test_replay_command_with_mocked_openai(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    traces = tmp_path / ".drishti" / "traces"
    traces.mkdir(parents=True)

    trace_file = traces / "20260101_000000_replay.json"
    _write_trace(trace_file, "replay-agent", cost=0.01, tokens=100, latency=100.0)

    response = MagicMock()
    response.usage.prompt_tokens = 60
    response.usage.completion_tokens = 40
    response.usage.total_tokens = 100
    response.choices = [SimpleNamespace(message=SimpleNamespace(content="replayed"))]

    openai_module = MagicMock()
    client = MagicMock()
    client.chat.completions.create.return_value = response
    openai_module.OpenAI.return_value = client

    monkeypatch.setitem(__import__("sys").modules, "openai", openai_module)

    result = runner.invoke(app, ["replay", str(trace_file)])
    assert result.exit_code == 0
    assert "Replay" in result.output


def test_replay_legacy_trace_without_request_payload(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    traces = tmp_path / ".drishti" / "traces"
    traces.mkdir(parents=True)

    legacy = {
        "trace_id": "legacy-id",
        "name": "legacy",
        "status": "success",
        "summary": {
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "total_latency_ms": 0.0,
            "span_count": 1,
        },
        "spans": [
            {
                "step": 1,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "tokens": {"prompt": 0, "completion": 0, "total": 0},
                "cost_usd": 0.0,
                "latency_ms": 0.0,
                "input": [{"role": "user", "content": "hello"}],
            }
        ],
    }
    trace_file = traces / "legacy.json"
    trace_file.write_text(json.dumps(legacy), encoding="utf-8")

    response = MagicMock()
    response.usage.prompt_tokens = 1
    response.usage.completion_tokens = 1
    response.usage.total_tokens = 2
    response.choices = [SimpleNamespace(message=SimpleNamespace(content="ok"))]
    openai_module = MagicMock()
    client = MagicMock()
    client.chat.completions.create.return_value = response
    openai_module.OpenAI.return_value = client
    monkeypatch.setitem(__import__("sys").modules, "openai", openai_module)

    result = runner.invoke(app, ["replay", str(trace_file)])
    assert result.exit_code == 0
