"""Safe YAML loading with optional LibYAML acceleration."""

from __future__ import annotations

from typing import Any

import yaml


SAFE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def safe_load(stream: Any) -> Any:
    """Load YAML safely, using LibYAML when the installed build provides it."""

    return yaml.load(stream, Loader=SAFE_LOADER)


def safe_compose(stream: Any) -> yaml.Node | None:
    """Compose safe YAML nodes while retaining source marks for diagnostics."""

    return yaml.compose(stream, Loader=SAFE_LOADER)
