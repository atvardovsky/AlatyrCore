"""Explicit bounded historical witnesses, never current authority."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from target_validation_support import is_placeholder, is_target_relative_path, is_unresolved_value

MAX_INDEX_BYTES = 512 * 1024
MAX_WITNESS_BYTES = 4 * 1024 * 1024
MAX_ENTRIES = 256
STATUSES = {
    "approval-record": ("historical-incomplete", "historical-record"),
    "retained-plan": ("rejected-experiment", "superseded-proposal", "retained-unresolved-lineage"),
}


def _resolved(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not is_placeholder(value) and not is_unresolved_value(value)


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("historical index contains duplicate JSON fields")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"historical index contains non-JSON constant: {value}")


def _safe_file(sink: Any, label: Any, *, limit: int) -> tuple[str, bytes]:
    if (not isinstance(label, str) or not is_target_relative_path(label)
            or any(char in label for char in "*?[]\\:") or Path(label).as_posix() != label):
        raise ValueError("reference is not an exact safe target-relative path")
    path = sink.target / label
    for part in (path, *path.parents):
        if part == sink.target:
            break
        if part.is_symlink():
            raise ValueError("historical references must not traverse symlinks")
    read = sink.context.read_bytes_result(path, max_bytes=limit)
    if read.error is not None or read.value is None:
        raise ValueError(f"historical reference is missing, unsafe or exceeds {limit} bytes: {label}")
    return label, read.value


def _bound(sink: Any, ref: Any) -> str:
    if not isinstance(ref, dict) or set(ref) != {"path", "sha256"}:
        raise ValueError("historical reference must bind exactly path and sha256")
    name, _ = _safe_file(sink, ref["path"], limit=MAX_WITNESS_BYTES)
    digest = ref["sha256"]
    if (not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)
            or sink.context.content_digest(sink.target / name) != digest):
        raise ValueError(f"historical reference digest is missing or stale: {name}")
    return name


def _entry(sink: Any, entry: Any, index: str) -> tuple[str, dict[str, Any]]:
    fields = {"path", "sha256", "kind", "status", "reason", "owner", "evidence"}
    if not isinstance(entry, dict) or set(entry) != fields:
        raise ValueError("historical entry requires exact witness, kind, status, reason, owner and evidence fields")
    name = _bound(sink, {key: entry[key] for key in ("path", "sha256")})
    kind, status = entry["kind"], entry["status"]
    if not isinstance(kind, str) or kind not in STATUSES or not isinstance(status, str) or status not in STATUSES[kind]:
        raise ValueError("historical kind/status cannot imply active authority or completion")
    valid_path = (name.startswith(".ai/assistant/approvals/") and name.endswith((".json", ".md"))) if kind == "approval-record" else (
        name.startswith(".ai/assistant/change-packages/") and (name.endswith("-plan.md") or name.endswith("/plan.md")))
    if not valid_path or not _resolved(entry["reason"]):
        raise ValueError("historical kind/path or retention reason is invalid")
    owner = _bound(sink, entry["owner"])
    refs = entry["evidence"]
    if not isinstance(refs, list) or not 1 <= len(refs) <= 16:
        raise ValueError("historical entry requires 1 to 16 bound evidence references")
    witnesses = [_bound(sink, ref) for ref in refs]
    if len(set(witnesses)) != len(witnesses):
        raise ValueError("historical evidence references must be unique")
    if owner in {name, index} or name in witnesses or index in witnesses:
        raise ValueError("historical ownership and evidence must not be self-referential")
    if owner.startswith(".ai/framework/"):
        raise ValueError("historical disposition requires a target-owned owner")
    return name, entry


def load_historical_evidence(sink: Any, selected: Path) -> dict[str, dict[str, Any]]:
    """Validate every binding once in the caller's immutable repository view."""
    path = Path(selected)
    if path.is_absolute():
        path = path.relative_to(sink.target)
    name, raw = _safe_file(sink, path.as_posix(), limit=MAX_INDEX_BYTES)
    data = json.loads(raw, object_pairs_hook=_unique_fields, parse_constant=_reject_constant)
    fields = {"schema_version", "record_kind", "authority", "reviewed_by", "reviewed_at", "decision", "entries"}
    if not isinstance(data, dict) or set(data) != fields:
        raise ValueError("historical index has missing or unknown fields")
    if (type(data["schema_version"]) is not int or data["schema_version"] != 1
            or data["record_kind"] != "alatyr-historical-evidence-index" or data["authority"] != "none"):
        raise ValueError("historical index must explicitly disclaim authority")
    if not _resolved(data["reviewed_by"]) or not isinstance(data["reviewed_at"], str):
        raise ValueError("historical index requires an explicit reviewer and offset-aware review time")
    reviewed = datetime.fromisoformat(data["reviewed_at"].replace("Z", "+00:00"))
    if reviewed.tzinfo is None or reviewed > datetime.now(timezone.utc):
        raise ValueError("historical review time requires an offset and cannot be in the future")
    if _bound(sink, data["decision"]) == name:
        raise ValueError("historical review cannot bind itself")
    entries = data["entries"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_ENTRIES:
        raise ValueError(f"historical index requires 1 to {MAX_ENTRIES} explicit entries")
    result: dict[str, dict[str, Any]] = {}
    portable_names: set[str] = set()
    for entry in entries:
        witness, value = _entry(sink, entry, name)
        if witness.casefold() in portable_names:
            raise ValueError("historical index contains duplicate portable identities")
        portable_names.add(witness.casefold())
        result[witness] = value
    return result
