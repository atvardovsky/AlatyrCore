"""Load immutable source-owned JSON contracts for target validation."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=None)
def load_source_json_object(path: Path) -> dict[str, Any]:
    """Load one source contract once without mixing it into target snapshots."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"source contract must contain a JSON object: {path}")
    return value
