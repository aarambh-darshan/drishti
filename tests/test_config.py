"""Tests for config loading and aliases."""

from __future__ import annotations

from pathlib import Path

from drishti.config import get_config, reset_config


def _write_toml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_default_export_dir_alias(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_toml(
        tmp_path / ".drishti" / "config.toml",
        """
[drishti]
default_export_dir = "custom/traces"
quiet = true
max_preview_chars = 400
estimate_stream_tokens = false
""",
    )

    reset_config()
    cfg = get_config()

    assert cfg.default_export_dir == "custom/traces"
    assert cfg.traces_dir == "custom/traces"
    assert cfg.export_dir == "custom/traces"
    assert cfg.quiet is True
    assert cfg.max_preview_chars == 400
    assert cfg.estimate_stream_tokens is False


def test_traces_dir_backward_compat(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_toml(
        tmp_path / ".drishti" / "config.toml",
        """
[drishti]
traces_dir = "legacy/traces"
""",
    )

    reset_config()
    cfg = get_config()

    assert cfg.traces_dir == "legacy/traces"
    assert cfg.default_export_dir == "legacy/traces"


def test_local_config_precedence_over_home(tmp_path, monkeypatch) -> None:
    local_root = tmp_path / "project"
    home_root = tmp_path / "home"
    local_root.mkdir(parents=True)
    home_root.mkdir(parents=True)

    _write_toml(
        local_root / ".drishti" / "config.toml",
        """
[drishti]
default_export_dir = "local/traces"
""",
    )
    _write_toml(
        home_root / ".drishti" / "config.toml",
        """
[drishti]
default_export_dir = "home/traces"
""",
    )

    monkeypatch.chdir(local_root)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_root))

    reset_config()
    cfg = get_config()

    assert cfg.export_dir == "local/traces"
