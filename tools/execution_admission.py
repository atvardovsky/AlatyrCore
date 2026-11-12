"""Bounded primary-owned plan projection; proposes work without dispatching it."""

from __future__ import annotations

import hashlib
import re
from pathlib import PurePosixPath

from resource_access import resource_conflicts, resource_failures, presence_resource_scopes
from target_validation_support import is_target_relative_path, is_unresolved_value

STATES = ("PLANNED", "READY", "RUNNING", "REVIEW_REQUIRED", "DONE", "FAILED", "CANCELLED", "BLOCKED")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
MAX_BYTES = 65536


def _ids(value, name):
    if (not isinstance(value, list) or len(value) > 64
            or any(not isinstance(item, str) or not TOKEN.fullmatch(item) or is_unresolved_value(item) for item in value)
            or len(set(value)) != len(value)):
        raise ValueError(name + " requires at most 64 unique resolved IDs")
    return set(value)


def _paths(value):
    if value is None:
        return None
    if (not isinstance(value, list) or len(value) > 64
            or any(not isinstance(path, str) or not is_target_relative_path(path)
                   or "\\" in path or any(char in path for char in "*?[")
                   or PurePosixPath(path).as_posix() != path for path in value)
            or len(set(value)) != len(value)):
        raise ValueError("write_scope requires distinct literal target-relative paths or null")
    return value


def _overlap(left, right):
    return any(a == "." or b == "." or a == b or a.startswith(b + "/") or b.startswith(a + "/")
               for a in (path.casefold() for path in left) for b in (path.casefold() for path in right))


def admission_plan(value):
    if isinstance(value, dict) and type(value.get("schema_version")) is int and value["schema_version"] == 2:
        from rolling_delivery import delivery_plan
        return delivery_plan(value, _schema1_admission_plan)
    return _schema1_admission_plan(value)


def _schema1_admission_plan(value):
    required = {"schema_version", "plan", "capacity", "max_parallel", "accepted_ids", "retry_ids", "tasks"}
    if not isinstance(value, dict) or set(value) != required or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("admission requires the exact schema-1 plan projection")
    binding = value["plan"]
    if (not isinstance(binding, dict) or set(binding) != {"path", "sha256"}
            or not isinstance(binding["path"], str) or not is_target_relative_path(binding["path"])
            or "\\" in binding["path"] or not isinstance(binding["sha256"], str)
            or re.fullmatch(r"[a-f0-9]{64}", binding["sha256"]) is None):
        raise ValueError("admission needs a target-relative plan with SHA-256")
    for name in ("capacity", "max_parallel"):
        if type(value[name]) is not int or not 1 <= value[name] <= 64:
            raise ValueError(name + " must be an integer in 1..64")
    rows = value["tasks"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 64:
        raise ValueError("admission requires 1..64 task projections")
    tasks = {}
    fields = {"id", "requires", "state", "slots", "resources", "write_scope"}
    for row in rows:
        if not isinstance(row, dict) or set(row) != fields:
            raise ValueError("task projection requires id, requires, state, slots, resources and write_scope")
        identity = row["id"]
        _ids([identity], "task id")
        if identity in tasks:
            raise ValueError("duplicate task id")
        _ids(row["requires"], "requires")
        if not isinstance(row["state"], str) or row["state"] not in STATES:
            raise ValueError("invalid task state")
        if type(row["slots"]) is not int or not 1 <= row["slots"] <= 64:
            raise ValueError("task slots must be an integer in 1..64")
        if row["resources"] is not None:
            failures = resource_failures(row["resources"])
            if failures:
                raise ValueError("; ".join(failures))
        _paths(row["write_scope"])
        tasks[identity] = row
    accepted = _ids(value["accepted_ids"], "accepted_ids")
    retries = _ids(value["retry_ids"], "retry_ids")
    if not accepted <= tasks.keys() or any(tasks[key]["state"] != "DONE" for key in accepted):
        raise ValueError("accepted_ids require known primary-accepted DONE tasks")
    if not retries <= tasks.keys() or any(tasks[key]["state"] != "FAILED" for key in retries):
        raise ValueError("retry_ids require explicitly selected FAILED tasks")
    if any(parent not in accepted for key in accepted for parent in tasks[key]["requires"]):
        raise ValueError("accepted tasks must retain accepted prerequisite closure")
    visiting, visited = set(), set()
    def visit(key):
        if key in visiting:
            raise ValueError("task dependency cycle")
        if key in visited:
            return
        visiting.add(key)
        for parent in tasks[key]["requires"]:
            if parent not in tasks:
                raise ValueError("unknown task dependency")
            visit(parent)
        visiting.remove(key)
        visited.add(key)
    for key in tasks:
        visit(key)
    held, selected = {}, []
    active = [row for row in rows if row["state"] in ("RUNNING", "REVIEW_REQUIRED")]
    if any(parent not in accepted for row in active for parent in row["requires"]):
        raise ValueError("current active allocations have unaccepted prerequisites")
    used = sum(row["slots"] for row in active if row["state"] == "RUNNING")
    running_slots = used
    if used > value["capacity"] or len(active) > value["max_parallel"]:
        raise ValueError("current allocations exceed capacity or parallel/review budget")
    for position, first in enumerate(active):
        for second in active[position + 1:]:
            if (first["resources"] is not None and second["resources"] is not None
                    and resource_conflicts(first["resources"], second["resources"])
                    or first["write_scope"] is not None and second["write_scope"] is not None
                    and _overlap(first["write_scope"], second["write_scope"])):
                raise ValueError("current active allocations conflict; reconcile before admission")
    for row in rows:
        identity, state = row["id"], row["state"]
        if identity in accepted or state in ("RUNNING", "REVIEW_REQUIRED"):
            continue
        reason = None
        if state in ("PLANNED", "DONE", "CANCELLED", "BLOCKED"):
            reason = "primary-review-or-disposition-required"
        elif state == "FAILED" and identity not in retries:
            reason = "retry-review-required"
        elif any(parent not in accepted for parent in row["requires"]):
            reason = "prerequisite-not-accepted"
        elif row["resources"] is None or row["write_scope"] is None:
            reason = "resource-or-write-scope-unknown"
        elif any(peer["resources"] is None or peer["write_scope"] is None for peer in active):
            reason = "active-allocation-unknown"
        elif any(resource_conflicts(row["resources"], peer["resources"])
                 or _overlap(row["write_scope"], peer["write_scope"]) for peer in active):
            reason = "resource-or-write-conflict"
        elif row["slots"] > value["capacity"]:
            reason = "capacity-exceeds-limit"
        elif used + row["slots"] > value["capacity"] or len(active) >= value["max_parallel"]:
            reason = "capacity-or-review-budget"
        if reason:
            held[identity] = reason
        else:
            selected.append(identity)
            active.append(row)
            used += row["slots"]
    scopes = sorted({scope for row in active if row["resources"] is not None
                     for scope in presence_resource_scopes(row["resources"])})
    return {"schema_version": 1, "view_kind": "alatyr-execution-admission", "plan": binding,
            "presence_scope_refs": scopes,
            "selected_ids": selected, "held": held, "allocated_slots": used, "running_slots": running_slots,
            "execution_authorized": False, "acceptance_granted": False,
            "limitation": "Declared primary-reviewed plan projection only, not verified task semantics, policy permission, reservation, launch or acceptance. Preserve cumulative budgets and recheck source, scope, capability and peers before dispatch."}


def inspect_admission(view, path):
    from inspect_session_context import json_object
    read = view.read_bytes_result(view.target / path, max_bytes=MAX_BYTES)
    if read.value is None:
        raise ValueError(read.error or "admission projection is unavailable")
    value = json_object(read.value, "admission projection")
    report = admission_plan(value)
    binding = report["plan"]
    plan = view.read_bytes_result(view.target / binding["path"], max_bytes=MAX_BYTES)
    if plan.value is None or hashlib.sha256(plan.value).hexdigest() != binding["sha256"]:
        raise ValueError("admission plan is unavailable, oversized or stale")
    if report["schema_version"] == 2:
        from rolling_delivery import inspect_delivery
        inspect_delivery(view, value=value, report=report)
    if view.finalize():
        raise ValueError("admission inputs changed during inspection")
    return report


def worker_admission_binding(value):
    """Validate retained preparation metadata before any dependent lookup."""
    fields = {"path", "sha256", "allocation_id", "plan", "allocation", "state", "origin",
              "input_sha256", "execution_authorized", "reservation_granted"}
    if isinstance(value, dict) and "delivery" in value:
        fields.add("delivery")
    if (not isinstance(value, dict) or set(value) != fields
            or value["execution_authorized"] is not False or value["reservation_granted"] is not False):
        raise ValueError("invalid preparation admission binding")
    _ids([value["allocation_id"]], "allocation id")
    def binding(item):
        if (not isinstance(item, dict) or set(item) != {"path", "sha256"}
                or not isinstance(item["path"], str) or not is_target_relative_path(item["path"])
                or "\\" in item["path"] or PurePosixPath(item["path"]).as_posix() != item["path"]
                or not isinstance(item["sha256"], str) or re.fullmatch(r"[a-f0-9]{64}", item["sha256"]) is None):
            raise ValueError("invalid preparation admission path/digest")
    binding({"path": value["path"], "sha256": value["sha256"]})
    binding(value["plan"])
    origin = value["origin"]
    if not isinstance(origin, dict) or set(origin) != {"sha256", "plan"}:
        raise ValueError("invalid original admission binding")
    binding({"path": value["path"], "sha256": origin["sha256"]})
    binding(origin["plan"])
    if origin["plan"]["path"] != value["plan"]["path"]:
        raise ValueError("admission continuation cannot replace its plan path")
    row = value["allocation"]
    if not isinstance(row, dict) or set(row) != {"id", "requires", "slots", "resources", "write_scope"}:
        raise ValueError("invalid retained worker allocation")
    if row["id"] != value["allocation_id"] or row["write_scope"] != []:
        raise ValueError("worker allocation identity/scope mismatch")
    _ids(row["requires"], "worker prerequisites")
    if type(row["slots"]) is not int or not 1 <= row["slots"] <= 64 or row["resources"] is None or resource_failures(row["resources"]):
        raise ValueError("worker allocation requires bounded slots and known resources")
    if not isinstance(value["state"], str) or value["state"] not in {"READY", "FAILED", "RUNNING"}:
        raise ValueError("invalid worker admission state")
    inputs = value["input_sha256"]
    expected = {value["path"]: value["sha256"], value["plan"]["path"]: value["plan"]["sha256"]}
    if len(expected) != 2:
        raise ValueError("admission projection and plan must be distinct")
    if "delivery" in value:
        from rolling_delivery import worker_delivery_binding
        extra = worker_delivery_binding(value["delivery"], value["allocation_id"])
        if set(extra) & set(expected):
            raise ValueError("delivery inputs must remain distinct from admission and plan")
        expected.update(extra)
    if not isinstance(inputs, dict) or inputs != expected:
        raise ValueError("admission requires exact current projection and plan input bindings")


def inspect_worker_admission(view, path, allocation_id, expected_sha256, policy, *, previous=None):
    """Bind a source inspect-only packet preparation to a current allocation."""
    from inspect_session_context import json_object
    if not isinstance(path, str) or not is_target_relative_path(path) or "\\" in path:
        raise ValueError("admission path must be target-relative")
    if not isinstance(expected_sha256, str) or re.fullmatch(r"[a-f0-9]{64}", expected_sha256) is None:
        raise ValueError("admission requires its current lowercase SHA-256")
    _ids([allocation_id], "allocation id")
    if previous is not None:
        worker_admission_binding(previous)
    read = view.read_bytes_result(view.target / path, max_bytes=MAX_BYTES)
    if read.value is None or read.digest != expected_sha256:
        raise ValueError("admission projection is missing, oversized or changed")
    value = json_object(read.value, "worker admission")
    report = inspect_admission(view, path)
    if value["max_parallel"] > policy["tree_policy"]["max_parallel_delegates"]:
        raise ValueError("admission exceeds the worker policy parallel limit")
    allocation = next((row for row in value["tasks"] if row["id"] == allocation_id), None)
    continuing = previous is not None and allocation is not None and allocation["state"] == "RUNNING"
    if allocation_id not in report["selected_ids"] and not continuing:
        raise ValueError("worker allocation is not currently admitted: " + str(report["held"].get(allocation_id, "not selected")))
    if allocation["write_scope"] != []:
        raise ValueError("source inspect-only worker allocation cannot carry write scope")
    stable = {key: val for key, val in allocation.items() if key != "state"}
    if previous is not None and (previous["path"] != path or previous["allocation_id"] != allocation_id
            or previous["plan"]["path"] != report["plan"]["path"] or previous["allocation"] != stable
            or previous["state"] == "RUNNING" and allocation["state"] != "RUNNING"):
        raise ValueError("expansion cannot drop or replace its original allocation binding")
    result = {"path": path, "sha256": expected_sha256, "allocation_id": allocation_id,
            "allocation": stable, "state": allocation["state"],
            "origin": previous["origin"] if previous else {"sha256": expected_sha256, "plan": report["plan"]},
            "plan": report["plan"], "input_sha256": view.content_bindings(),
            "execution_authorized": False, "reservation_granted": False}
    if value["schema_version"] == 2:
        from rolling_delivery import retained_worker_delivery
        result["delivery"] = retained_worker_delivery(value, allocation_id, result["input_sha256"], path)
    if previous is not None:
        prior_delivery, current_delivery = previous.get("delivery"), result.get("delivery")
        if ((prior_delivery is None) != (current_delivery is None)
                or prior_delivery is not None and any(prior_delivery[key] != current_delivery[key]
                    for key in ("operation_id", "item", "request_source"))):
            raise ValueError("expansion cannot replace its original delivery request or ownership binding")
    worker_admission_binding(result)
    return result
