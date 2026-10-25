"""Opt-in execution controls shared by contract and registered validation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from resource_access import resource_conflicts, resource_failures
from target_validation_support import is_target_relative_path, is_unresolved_value

CONTROL_KEYS = ("selection_contract", "timing_qualification")
MAX_PEERS = 64


def policy_control_failures(policy: dict) -> list[str]:
    failures = []
    for command in policy["commands"]:
        execution = command["execution"]
        for name in CONTROL_KEYS:
            value = execution.get(name, "not-required")
            if not isinstance(value, str) or value not in {"required", "not-required"}:
                failures.append(f"{command['id']}: invalid {name}")
            elif value == "required" and policy["execution_contract"]["schema_version"] != 3:
                failures.append(f"{command['id']}: required {name} needs execution contract version 3")
        if execution.get("timing_qualification") == "required" and not any(row.get("access") == "exclusive" for row in execution["resources"]):
            failures.append(f"{command['id']}: timing qualification needs an enclosing exclusive resource claim")
    return failures


def _window(value: Any) -> tuple[datetime, datetime, str]:
    if not isinstance(value, dict):
        raise ValueError("qualification window must be an object")
    points = []
    for name in ("started_at", "finished_at"):
        text = value.get(name)
        if not isinstance(text, str) or len(text) > 64:
            raise ValueError(f"qualification window {name} requires an observed timestamp")
        point = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if point.tzinfo is None or point > datetime.now(timezone.utc):
            raise ValueError(f"qualification window {name} must be offset-aware and not future")
        points.append(point)
    clock = value.get("clock_id")
    if not isinstance(clock, str) or not clock.strip() or is_unresolved_value(clock) or len(clock) > 128:
        raise ValueError("qualification window needs a resolved comparable clock_id")
    if points[0] >= points[1]:
        raise ValueError("qualification window must have a positive observed duration")
    return points[0], points[1], clock


def qualification_failures(record: dict) -> list[str]:
    if not isinstance(record, dict) or resource_failures(record.get("resources")):
        return ["qualification requires valid observed resources"]
    value = record.get("qualification_window")
    try:
        start, finish, clock = _window(value)
        if set(value) != {"started_at", "finished_at", "clock_id", "peer_coverage", "peer_windows"}:
            raise ValueError("qualification window has missing or unknown fields")
        if value["peer_coverage"] != "complete-observed-set":
            raise ValueError("exclusive timing requires a complete declared observed peer set; unreported peers remain outside the proof")
        peers = value["peer_windows"]
        if not isinstance(peers, list) or len(peers) > MAX_PEERS:
            raise ValueError(f"qualification requires at most {MAX_PEERS} observed peer windows")
        identities = set()
        for peer in peers:
            if not isinstance(peer, dict) or set(peer) != {"run_id", "started_at", "finished_at", "clock_id", "resources"}:
                raise ValueError("peer window requires exact identity, boundaries, clock and resources")
            identity = peer["run_id"]
            if not isinstance(identity, str) or not identity.strip() or is_unresolved_value(identity) or identity in identities:
                raise ValueError("peer run IDs must be resolved and unique")
            identities.add(identity)
            other_start, other_finish, other_clock = _window(peer)
            if resource_failures(peer["resources"]):
                raise ValueError("peer resources are malformed")
            if other_clock != clock:
                raise ValueError("peer windows do not use a comparable observed clock")
            if max(start, other_start) < min(finish, other_finish) and resource_conflicts(record["resources"], peer["resources"]):
                raise ValueError("qualification overlaps a conflicting observed resource window")
    except (ValueError, OverflowError) as exc:
        return [str(exc)]
    return []


def record_control_failures(record: dict, command: dict, contract: dict) -> list[str]:
    failures = []
    if record["command_id"] != command["id"]:
        failures.append("evidence command_id differs from the selected canonical command")
    for name, field in (("selection_contract", "selection_evidence"), ("timing_qualification", "qualification_window")):
        required = command["execution"].get(name) == "required"
        supplied = record.get(field)
        if required and (contract["schema_version"] != 3 or record["schema_version"] != 3):
            failures.append(f"{name} requires policy and evidence execution contract version 3")
        if required and record["counts"]["executed"] > 0 and supplied is None:
            failures.append(f"required {field} is missing")
        if not required and supplied is not None:
            failures.append(f"{field} cannot establish an unadopted command control")
    binding = record.get("selection_evidence")
    if isinstance(binding, dict):
        request = binding.get("request")
        if not isinstance(request, dict) or not isinstance(request.get("path"), str) or not is_target_relative_path(request["path"]) or record["input_sha256"].get(request["path"]) != request.get("sha256"):
            failures.append("selection request must bind a contained current input hash")
    return failures


def selected_control_failures(view: Any, record: dict, execution: dict) -> list[str]:
    """Read the actual bound result once for all adopted observation controls."""
    from test_selection import read_selection_json, selected_execution_failures
    from repair_qualification import pointer_value
    try:
        reference = record["result_artifact"]
        if reference is None:
            raise ValueError("adopted execution controls require the actual result artifact")
        artifact = read_selection_json(view, reference["path"], reference["sha256"])
        failures = []
        if execution.get("selection_contract") == "required":
            failures.extend(selected_execution_failures(view, record, artifact=artifact))
        if execution.get("timing_qualification") == "required":
            binding = record.get("qualification_window")
            if binding is None:
                failures.append("required qualification_window is missing")
            else:
                observed = pointer_value(artifact, binding["observations_pointer"])
                failures.extend(qualification_failures({**record, "qualification_window": observed}))
        return failures
    except (ValueError, UnicodeError, RecursionError) as exc:
        return [str(exc)]
