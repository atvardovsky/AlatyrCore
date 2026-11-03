"""Portable recorded dispatch checks, not a provider client or scheduler."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from target_validation_support import is_placeholder, is_unresolved_value

FIELDS = {"operation_id", "packet_id", "node_id", "attempt", "worker_id",
          "assignment_id", "action", "operation_name", "observed_state", "observed_at", "event_ref"}
STATES = {"queued", "running", "completed", "failed", "cancelled", "unknown"}
NO_DISPATCH = object()


def dispatch_failures(value: Any, *, operation_id: str, packet_id: str,
                      node_id: str, attempt: int, state: str, required: bool,
                      protocol: Any = None) -> list[str]:
    """Validate one explicit observation; absence never implies execution."""
    claims_execution = state in {"RUNNING", "DONE"}
    if value is NO_DISPATCH:
        return ["dispatch observation is required before claiming worker execution"] if required and claims_execution else []
    if not isinstance(value, dict) or set(value) != FIELDS:
        return ["dispatch observation must contain the exact recorded assignment fields"]
    failures = []
    for field in FIELDS - {"attempt"}:
        text = value[field]
        if not isinstance(text, str) or not text.strip() or field != "observed_state" and (is_placeholder(text) or is_unresolved_value(text)):
            failures.append(f"dispatch {field} must be a resolved string")
    for field, expected in (("operation_id", operation_id), ("packet_id", packet_id),
                            ("node_id", node_id), ("attempt", attempt)):
        if value[field] != expected or field == "attempt" and type(value[field]) is not int:
            failures.append(f"dispatch {field} differs from the current assignment")
    if not isinstance(value["action"], str) or value["action"] not in {"start", "resume"}:
        failures.append("dispatch action must start or resume work; a message is not an assignment")
    if protocol is not None or required:
        roles = protocol.get("operation_roles") if isinstance(protocol, dict) else None
        if not isinstance(protocol, dict) or set(protocol) != {"operation_roles", "evidence_ref"} or not isinstance(roles, dict) or not 1 <= len(roles) <= 16:
            failures.append("dispatch requires a bounded verified assignment protocol in the selected capability")
        elif not isinstance(protocol["evidence_ref"], str) or not protocol["evidence_ref"].strip() or is_placeholder(protocol["evidence_ref"]) or is_unresolved_value(protocol["evidence_ref"]) or any(
                not isinstance(key, str) or not key or not isinstance(role, str) or role not in {"start", "resume", "message", "status"}
                for key, role in roles.items()):
            failures.append("dispatch assignment protocol contains unresolved operations or evidence")
        elif not isinstance(value["operation_name"], str) or roles.get(value["operation_name"]) != value["action"]:
            failures.append("dispatch operation_name does not perform the declared assignment action")
    observed = value["observed_state"]
    if not isinstance(observed, str) or observed not in STATES:
        failures.append("dispatch observed_state is invalid")
    elif state == "RUNNING" and observed != "running" or state == "DONE" and observed != "completed":
        failures.append(f"dispatch observation {observed!r} cannot establish {state}")
    try:
        stamp = value["observed_at"]
        when = datetime.fromisoformat(stamp.replace("Z", "+00:00")) if isinstance(stamp, str) else None
        if when is None or when.utcoffset() is None:
            raise ValueError("timestamp needs a timezone")
    except (ValueError, TypeError, OverflowError):
        failures.append("dispatch observed_at must be a valid timezone-aware timestamp")
    return failures
