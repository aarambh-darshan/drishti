"""
Configuration system for Drishti.

Loads config from (in priority order):
1. Keyword arguments passed to @trace(...)
2. .drishti/config.toml in the current working directory
3. ~/.drishti/config.toml (user-global config)
4. Built-in defaults

Defaults work without any config file — zero configuration required.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


@dataclass
class DrishtiConfig:
    """Configuration for Drishti tracing."""

    display: bool = True  # Print trace tree to terminal
    export: bool = True  # Save traces to disk
    traces_dir: str = ".drishti/traces"  # Directory for saved traces
    budget_usd: Optional[float] = None  # Warn if a single trace exceeds this cost
    pricing_overrides: dict = field(default_factory=dict)  # Custom pricing per model


# Cached singleton
_config: Optional[DrishtiConfig] = None


def get_config() -> DrishtiConfig:
    """
    Load configuration, with caching.

    Reads from TOML config files, falling back to defaults.
    Config is cached after first load.
    """
    global _config
    if _config is not None:
        return _config

    config = DrishtiConfig()

    # Try local config first, then user-global config
    config_paths = [
        Path(".drishti/config.toml"),
        Path.home() / ".drishti" / "config.toml",
    ]

    if tomllib is None:
        _config = config
        return config

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    data = tomllib.load(f)

                drishti_data = data.get("drishti", {})

                if "display" in drishti_data:
                    config.display = bool(drishti_data["display"])
                if "export" in drishti_data:
                    config.export = bool(drishti_data["export"])
                if "traces_dir" in drishti_data:
                    config.traces_dir = str(drishti_data["traces_dir"])
                if "budget_usd" in drishti_data:
                    config.budget_usd = float(drishti_data["budget_usd"])
                if "pricing" in drishti_data:
                    config.pricing_overrides = dict(drishti_data["pricing"])

                break  # Use first found config file
            except Exception:
                pass  # Malformed config — silently use defaults

    _config = config
    return config


def reset_config() -> None:
    """Reset cached config (for testing)."""
    global _config
    _config = None
