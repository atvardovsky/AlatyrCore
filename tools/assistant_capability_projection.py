"""Project assistant-surface capability records from one canonical template."""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOT = ROOT / "templates" / "target"
SURFACES_PATH = ROOT / "conformance" / "runs" / "assistant-surfaces.json"
BASE_RECORD_PATH = (
    TARGET_ROOT / ".ai" / "assistant" / "assistant-capabilities" / "generic.json"
)
RECORD_PREFIX = Path(".ai/assistant/assistant-capabilities")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return value


@lru_cache(maxsize=1)
def surface_ids() -> tuple[str, ...]:
    values = load_object(SURFACES_PATH).get("surfaces")
    if not isinstance(values, list):
        raise ValueError("assistant surfaces must be a list")
    raw_ids = [item.get("id") if isinstance(item, dict) else None for item in values]
    if not all(isinstance(surface_id, str) and surface_id for surface_id in raw_ids):
        raise ValueError("assistant surface has no valid ID")
    if len(set(raw_ids)) != len(raw_ids):
        raise ValueError("assistant surface IDs must be unique")
    return tuple(sorted(raw_ids))


def record_path(surface_id: str) -> Path:
    return RECORD_PREFIX / f"{surface_id}.json"


def build_surface_record(surface_id: str) -> dict[str, Any]:
    if surface_id not in surface_ids():
        raise ValueError(f"unknown assistant surface: {surface_id}")
    record = copy.deepcopy(load_object(BASE_RECORD_PATH))
    record["assistant_surface"] = surface_id
    return record


def render_surface_record(surface_id: str) -> str:
    return json.dumps(build_surface_record(surface_id), indent=2) + "\n"


def surface_id_for_path(path: Path | str) -> str | None:
    relpath = Path(path)
    if relpath.parent != RECORD_PREFIX or relpath.suffix != ".json":
        return None
    surface_id = relpath.stem
    return surface_id if surface_id in surface_ids() else None


def virtual_record_contents(paths: Iterable[Path | str]) -> dict[Path, str]:
    result: dict[Path, str] = {}
    for path in paths:
        relpath = Path(path)
        surface_id = surface_id_for_path(relpath)
        if surface_id is not None:
            result[relpath] = render_surface_record(surface_id)
    return result
