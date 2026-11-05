"""Lifecycle policy parsing, independent of checkpoint and validator execution."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from inspect_session_context import json_object
from support_write_transaction import read_output


POLICY = ".ai/assistant/policies/lifecycle-hooks.json"


MAX_INPUT_BYTES = 64 * 1024


MAX_REMINDERS = 8


MAX_TIMESTAMP = 253402300799  # Year 9999; bound integers before float arithmetic.


PROVIDERS = {"codex", "claude", "gemini", "cursor", "copilot", "procedural"}


def identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256 or any(ord(c) < 32 for c in value):
        raise ValueError(f"{label} must be a bounded non-empty string")
    return value


def policy_failures(policy: object, *, now: float | None = None) -> list[str]:
    if not isinstance(policy, dict):
        return ["lifecycle policy must be an object"]
    required = {"schema_version", "enabled", "provider", "mode", "binding_ttl_seconds", "max_reminders", "native_evidence"}
    failures = []
    if set(policy) - {"request_guard"} != required or type(policy.get("schema_version")) is not int or policy["schema_version"] != 1:
        failures.append("lifecycle policy requires exact schema-1 fields")
    if "request_guard" in policy:
        from request_brief import guard_policy
        try:
            guard_policy(policy["request_guard"])
        except ValueError as exc:
            failures.append(str(exc))
    if type(policy.get("enabled")) is not bool:
        failures.append("lifecycle enabled must be Boolean")
    for field, allowed in (("provider", PROVIDERS), ("mode", {"observe", "checkpoint"})):
        if not isinstance(policy.get(field), str) or policy[field] not in allowed:
            failures.append(f"lifecycle {field} is invalid")
    for field, low, high in (("binding_ttl_seconds", 1, 3600), ("max_reminders", 0, MAX_REMINDERS)):
        if type(policy.get(field)) is not int or not low <= policy[field] <= high:
            failures.append(f"lifecycle {field} must be in {low}..{high}")
    evidence = policy.get("native_evidence")
    if not isinstance(evidence, dict) or set(evidence) != {"state", "client_version", "source", "verified_at", "expires_at"}:
        failures.append("lifecycle native_evidence requires state, version, source and bounded validity")
    elif not isinstance(evidence["state"], str) or evidence["state"] not in {"unverified", "observed"}:
        failures.append("lifecycle native_evidence.state is invalid")
    elif evidence["state"] == "observed":
        try:
            for field in ("client_version", "source"):
                text = identifier(evidence[field], "native_evidence." + field)
                if text.casefold() in {"unknown", "none", "unverified"} or "{" in text:
                    raise ValueError("native evidence must be resolved")
            start, end = (timestamp(evidence[field]) for field in ("verified_at", "expires_at"))
            if not start <= (time.time() if now is None else now) < end or end - start > 30 * 86400:
                raise ValueError("native evidence is expired, future-dated or exceeds 30 days")
        except ValueError as exc:
            failures.append(str(exc))
    elif any(evidence[field] is not None for field in ("client_version", "source", "verified_at", "expires_at")):
        failures.append("unverified native evidence fields must remain null")
    if policy.get("provider") == "procedural" and policy.get("mode") != "observe":
        failures.append("procedural lifecycle delivery must remain observe-only")
    return failures


def timestamp(value: object) -> float:
    if not isinstance(value, str):
        raise ValueError("lifecycle timestamp must be an aware ISO timestamp")
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("lifecycle timestamp must be an aware ISO timestamp") from exc
    if moment.tzinfo is None:
        raise ValueError("lifecycle timestamp requires a timezone")
    try:
        return moment.timestamp()
    except (OSError, OverflowError, ValueError) as exc:
        raise ValueError("lifecycle timestamp is outside the supported range") from exc


def load_policy(target: Path) -> tuple[bytes | None, dict | None]:
    raw = read_output(target, target / POLICY, max_bytes=MAX_INPUT_BYTES)
    if raw is None:
        return None, None
    return raw, parse_policy(raw)


def parse_policy(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or len(raw) > MAX_INPUT_BYTES:
        raise ValueError("lifecycle policy exceeds 64 KiB")
    policy = json_object(raw, POLICY)
    failures = policy_failures(policy)
    if failures:
        raise ValueError("; ".join(failures))
    return policy
