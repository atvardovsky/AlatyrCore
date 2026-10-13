"""Bounded, advisory session-presence data; no task or authorization ownership."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any


POLICY_PATH = ".ai/assistant/policies/session-continuity.json"
FLOW_PATH = ".ai/assistant/flows/session-presence.flow.md"
MAX_BYTES = 131072
MAX_SESSIONS = 64
ACTIVITIES = ("inspecting", "editing", "building", "reviewing", "blocked")
DEFAULT_PRESENCE = {
    "schema_version": 1,
    "enabled": False,
    "flow": FLOW_PATH,
    "stale_after_seconds": 3600,
}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("presence JSON contains a duplicate key")
        result[key] = value
    return result


def decode_json(raw: bytes) -> Any:
    if len(raw) > MAX_BYTES:
        raise ValueError(f"presence JSON exceeds {MAX_BYTES} bytes")
    try:
        return json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite JSON number")),
        )
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("presence JSON is not valid bounded UTF-8 JSON") from exc


def presence_policy(continuity: Any) -> dict[str, Any]:
    if not isinstance(continuity, dict):
        raise ValueError("continuity policy must be an object")
    value = continuity.get("presence", DEFAULT_PRESENCE)
    if not isinstance(value, dict) or set(value) != set(DEFAULT_PRESENCE):
        raise ValueError("presence policy requires schema_version, enabled, flow, stale_after_seconds")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("presence policy schema_version must be 1")
    if type(value["enabled"]) is not bool:
        raise ValueError("presence policy enabled must be a boolean")
    if value["flow"] != FLOW_PATH:
        raise ValueError("presence policy must reference the canonical presence flow")
    stale = value["stale_after_seconds"]
    if type(stale) is not int or not 60 <= stale <= 86400:
        raise ValueError("presence stale_after_seconds must be an integer from 60 to 86400")
    return dict(value)


def presence_route(continuity: Any) -> dict[str, Any]:
    policy = presence_policy(continuity)
    return {"enabled": policy["enabled"], "policy": POLICY_PATH + "#presence"}


def uid(value: Any, field: str = "session_uid") -> str:
    try:
        if not isinstance(value, str) or str(uuid.UUID(value, version=4)) != value:
            raise ValueError()
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"{field} must be a canonical UUID v4") from exc
    return value


def text(value: Any, field: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} must be non-empty text of at most {limit} characters")
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"{field} must not contain control characters")
    return value


def timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z") or len(value) != 20:
        raise ValueError(f"{field} must be a UTC timestamp YYYY-MM-DDTHH:MM:SSZ")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid UTC timestamp") from exc
    return parsed


def now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_entry(entry: Any) -> None:
    fields = {"session_uid", "parent_uid", "worktree", "task", "scope", "activity", "started_at", "updated_at", "version"}
    if not isinstance(entry, dict) or set(entry) != fields:
        raise ValueError("presence entry has missing or unsupported fields")
    uid(entry["session_uid"])
    if entry["parent_uid"] is not None:
        uid(entry["parent_uid"], "parent_uid")
        if entry["parent_uid"] == entry["session_uid"]:
            raise ValueError("parent_uid must differ from session_uid")
    text(entry["worktree"], "worktree", 4096)
    text(entry["task"], "task", 240)
    scope = entry["scope"]
    if not isinstance(scope, list) or not 1 <= len(scope) <= 8:
        raise ValueError("scope must contain from 1 to 8 short references")
    for item in scope:
        text(item, "scope reference", 120)
    if len(set(scope)) != len(scope):
        raise ValueError("scope references must be unique")
    if not isinstance(entry["activity"], str) or entry["activity"] not in ACTIVITIES:
        raise ValueError("activity is unsupported")
    if timestamp(entry["updated_at"], "updated_at") < timestamp(entry["started_at"], "started_at"):
        raise ValueError("updated_at precedes started_at")
    if type(entry["version"]) is not int or entry["version"] < 1:
        raise ValueError("entry version must be a positive integer")


def validate_registry(value: Any, repository_id: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schema_version", "repository_id", "sessions"}:
        raise ValueError("presence registry has missing or unsupported fields")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("presence registry schema_version must be 1")
    if value["repository_id"] != repository_id:
        raise ValueError("presence registry belongs to a different Git common directory")
    sessions = value["sessions"]
    if not isinstance(sessions, dict) or len(sessions) > MAX_SESSIONS:
        raise ValueError(f"sessions must be an object with at most {MAX_SESSIONS} entries")
    for key, entry in sessions.items():
        uid(key)
        validate_entry(entry)
        if entry["session_uid"] != key:
            raise ValueError("presence entry UID does not match its key")
    return value


def encoded_registry(value: Any, repository_id: str) -> bytes:
    validate_registry(value, repository_id)
    raw = (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ValueError(f"presence registry exceeds {MAX_BYTES} serialized bytes")
    return raw
