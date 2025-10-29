"""Configuration helpers for the AllThatStax toolchain."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

__all__ = ["load_config"]

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def _coerce_path(path: str | Path) -> Path:
    return Path(path).expanduser()


@lru_cache(maxsize=4)
def load_config(path: str | Path | None = None) -> Dict[str, Any]:
    """Load the configuration file as a dictionary.

    Parameters
    ----------
    path:
        Optional override for the configuration path. When omitted the
        repository level ``config.json`` is used.
    """

    config_path = _coerce_path(path or _DEFAULT_CONFIG_PATH)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
