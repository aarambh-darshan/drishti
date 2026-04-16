"""Configuration system for Drishti."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


@dataclass(slots=True)
class DrishtiConfig:
    """Configuration for Drishti tracing."""

    display: bool = True
    export: bool = True
    traces_dir: str = ".drishti/traces"
    default_export_dir: str = ".drishti/traces"
    budget_usd: float | None = None
    on_exceed: Literal["warn", "abort"] = "warn"

    pricing_overrides: dict[str, tuple[float, float]] = field(default_factory=dict)

    quiet: bool = False
    auto_open_on_error: bool = False
    max_preview_chars: int = 220
    estimate_stream_tokens: bool = True

    @property
    def export_dir(self) -> str:
        """Preferred export directory."""
        return self.default_export_dir or self.traces_dir


_config: DrishtiConfig | None = None


def _coerce_pricing_overrides(raw: object) -> dict[str, tuple[float, float]]:
    if not isinstance(raw, dict):
        return {}

    result: dict[str, tuple[float, float]] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            continue
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            continue
        try:
            in_price = float(value[0])
            out_price = float(value[1])
        except (TypeError, ValueError):
            continue
        result[key] = (in_price, out_price)
    return result


def _load_from_file(config_path: Path, config: DrishtiConfig) -> bool:
    if tomllib is None or not config_path.exists():
        return False

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return False

    drishti_data = data.get("drishti", {})
    if not isinstance(drishti_data, dict):
        return False

    if "display" in drishti_data:
        config.display = bool(drishti_data["display"])
    if "export" in drishti_data:
        config.export = bool(drishti_data["export"])

    if "default_export_dir" in drishti_data:
        export_dir = str(drishti_data["default_export_dir"])
        config.default_export_dir = export_dir
        config.traces_dir = export_dir
    elif "traces_dir" in drishti_data:
        export_dir = str(drishti_data["traces_dir"])
        config.traces_dir = export_dir
        config.default_export_dir = export_dir

    if "budget_usd" in drishti_data:
        try:
            config.budget_usd = float(drishti_data["budget_usd"])
        except (TypeError, ValueError):
            pass

    if drishti_data.get("on_exceed") in {"warn", "abort"}:
        config.on_exceed = drishti_data["on_exceed"]

    if "quiet" in drishti_data:
        config.quiet = bool(drishti_data["quiet"])
    if "auto_open_on_error" in drishti_data:
        config.auto_open_on_error = bool(drishti_data["auto_open_on_error"])
    if "max_preview_chars" in drishti_data:
        try:
            config.max_preview_chars = max(20, int(drishti_data["max_preview_chars"]))
        except (TypeError, ValueError):
            pass
    if "estimate_stream_tokens" in drishti_data:
        config.estimate_stream_tokens = bool(drishti_data["estimate_stream_tokens"])

    pricing = drishti_data.get("pricing", {})
    config.pricing_overrides = _coerce_pricing_overrides(pricing)

    return True


def get_config() -> DrishtiConfig:
    """Load configuration once with caching."""
    global _config
    if _config is not None:
        return _config

    config = DrishtiConfig()
    config_paths = [
        Path(".drishti/config.toml"),
        Path.home() / ".drishti" / "config.toml",
    ]

    for path in config_paths:
        if _load_from_file(path, config):
            break

    _config = config
    return config


def reset_config() -> None:
    """Reset cached config (tests)."""
    global _config
    _config = None
