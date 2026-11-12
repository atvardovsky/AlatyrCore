"""Optional bounded admission view; declarations never establish delivery or authority."""

from __future__ import annotations

import hashlib
import re
from pathlib import PurePosixPath

from target_validation_support import is_target_relative_path, is_unresolved_value

MAX_ITEMS = 64
MAX_SOURCE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 8 * MAX_SOURCE_BYTES
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")


def _fields(value, names, label):
    if not isinstance(value, dict) or set(value) != set(names):
        raise ValueError(label + " requires exact fields: " + ", ".join(sorted(names)))
    return value


def _id(value, label):
    if not isinstance(value, str) or not TOKEN.fullmatch(value) or is_unresolved_value(value):
        raise ValueError(label + " requires a resolved bounded ID")
    return value


def _ids(value, label, *, minimum=0):
    if not isinstance(value, list) or not minimum <= len(value) <= MAX_ITEMS:
        raise ValueError(label + " requires a bounded ID list")
    for item in value:
        _id(item, label)
    if len(value) != len(set(value)):
        raise ValueError(label + " contains duplicate IDs")
    return set(value)


def _binding(value, label):
    _fields(value, {"path", "sha256"}, label)
    if (not isinstance(value["path"], str) or len(value["path"]) > 1024 or not is_target_relative_path(value["path"])
            or "\\" in value["path"] or PurePosixPath(value["path"]).as_posix() != value["path"]
            or not isinstance(value["sha256"], str)
            or not HASH.fullmatch(value["sha256"])):
        raise ValueError(label + " requires a target-relative path and lowercase SHA-256")
    return value


def _item(row):
    _fields(row, {"task_id", "request_id", "outcome_ids", "owner_ref"}, "delivery item")
    _id(row["task_id"], "item task_id")
    _id(row["request_id"], "item request_id")
    _ids(row["outcome_ids"], "item outcomes", minimum=1)
    owner = row["owner_ref"]
    if not isinstance(owner, str) or not owner.strip() or len(owner) > 256 or is_unresolved_value(owner):
        raise ValueError("item owner_ref requires a resolved reference of at most 256 characters")


def delivery_plan(value, canonical):
    base_fields = {"schema_version", "plan", "capacity", "max_parallel", "accepted_ids", "retry_ids", "tasks"}
    _fields(value, base_fields | {"delivery"}, "schema-2 admission")
    result = canonical({**{key: value[key] for key in base_fields}, "schema_version": 1})
    _binding(value["plan"], "delivery plan")
    delivery = _fields(value["delivery"], {"operation_id", "requests", "items", "active_wave", "final_barrier"}, "delivery")
    _id(delivery["operation_id"], "operation_id")
    requests = delivery["requests"]
    if not isinstance(requests, list) or not 1 <= len(requests) <= 16:
        raise ValueError("delivery requests requires 1..16 request bindings")
    request_ids, paths = set(), set()
    for row in requests:
        _fields(row, {"id", "source"}, "delivery request")
        _id(row["id"], "request id")
        _binding(row["source"], "request source")
        if row["source"]["path"].casefold() == value["plan"]["path"].casefold():
            raise ValueError("request source must be distinct from the admission plan")
        if row["id"] in request_ids or row["source"]["path"].casefold() in paths:
            raise ValueError("delivery request identity/source must be unique")
        request_ids.add(row["id"])
        paths.add(row["source"]["path"].casefold())
    tasks = {row["id"]: row for row in value["tasks"]}
    items = delivery["items"]
    if not isinstance(items, list) or len(items) != len(tasks):
        raise ValueError("delivery items must cover every admission task exactly once")
    seen, used_requests = set(), set()
    for row in items:
        _item(row)
        if row["task_id"] not in tasks or row["task_id"] in seen or row["request_id"] not in request_ids:
            raise ValueError("delivery item has a duplicate or unknown task/request")
        seen.add(row["task_id"])
        used_requests.add(row["request_id"])
    if used_requests != request_ids:
        raise ValueError("every bound request must have delivery items")
    wave = delivery["active_wave"]
    wave_ids = set()
    if wave is not None:
        _fields(wave, {"id", "task_ids", "manifest"}, "active wave")
        _id(wave["id"], "wave id")
        wave_ids = _ids(wave["task_ids"], "wave task_ids", minimum=1)
        _binding(wave["manifest"], "wave manifest")
        if not wave_ids <= set(value["accepted_ids"]):
            raise ValueError("wave requires primary-accepted local task results; this is not delivery acceptance")
        if wave["manifest"]["path"].casefold() in paths | {value["plan"]["path"].casefold()}:
            raise ValueError("wave manifest must be distinct from request and plan sources")
    barrier = delivery["final_barrier"]
    barrier_view = None
    if barrier is not None:
        _fields(barrier, {"task_id", "requires"}, "final barrier")
        identity = _id(barrier["task_id"], "barrier task_id")
        required = _ids(barrier["requires"], "barrier requires", minimum=1)
        if (identity not in tasks or required != set(tasks) - {identity}
                or required != set(tasks[identity]["requires"]) or identity in wave_ids):
            raise ValueError("final barrier requires the explicit complete task snapshot and cannot belong to the wave")
        barrier_view = {"task_id": identity, "unsettled_local_ids": sorted(required - set(value["accepted_ids"])),
                        "delivery_prerequisites_verified": False, "primary_review_required": True}
        if identity in result["selected_ids"]:
            result["selected_ids"].remove(identity)
            result["allocated_slots"] -= tasks[identity]["slots"]
            result["held"][identity] = "final-barrier-coordinator-review-required"
    reviews = [row["id"] for row in value["tasks"] if row["state"] == "REVIEW_REQUIRED"]
    result.update(schema_version=2, delivery={
        "operation_id": delivery["operation_id"], "source_state": "not-verified",
        "item_count": len(items), "request_count": len(requests), "review_due_ids": reviews,
        "wave": {"id": wave["id"], "task_ids": wave["task_ids"], "input_state": "not-verified"} if wave else None,
        "final_barrier": barrier_view,
        "next_decision": "review-returned-results" if reviews else "review-admitted-work" if result["selected_ids"] else
                         "review-final-barrier" if barrier_view and not barrier_view["unsettled_local_ids"] else "review-holds",
        "authority": "none", "delivery_acceptance_granted": False,
        "limitation": "Bound declarations and input identity only. Original request capture, owner assignment, semantic relevance, execution, outcome acceptance and publication remain primary-reviewed."})
    bound_delivery_view(result)
    return result


def inspect_delivery(view, *, value, report):
    from inspect_session_context import json_object
    from request_brief import MAX_BRIEF_BYTES, parse_brief

    total = 0
    verified = {}

    def read(binding, label, limit):
        nonlocal total
        path = binding["path"]
        prior = verified.get(path)
        if prior is not None:
            if prior[0] != binding["sha256"]:
                raise ValueError("conflicting delivery hashes for " + path)
            return prior[1]
        result = view.read_bytes_result(view.target / path, max_bytes=min(limit, MAX_TOTAL_BYTES - total))
        if result.value is None or hashlib.sha256(result.value).hexdigest() != binding["sha256"]:
            raise ValueError(label + " is unavailable, oversized or stale: " + path)
        total += len(result.value)
        if total > MAX_TOTAL_BYTES:
            raise ValueError("delivery verification exceeds its total byte budget")
        verified[path] = (binding["sha256"], result.value)
        return result.value

    delivery = value["delivery"]
    for source in delivery["requests"]:
        brief = parse_brief(read(source["source"], "delivery request", MAX_BRIEF_BYTES))
        if brief["request_id"] != source["id"]:
            raise ValueError("delivery request ID differs from its canonical brief")
        expected = {row["id"] for row in brief["outcomes"]}
        captured = {outcome for row in delivery["items"] if row["request_id"] == source["id"] for outcome in row["outcome_ids"]}
        if captured != expected:
            raise ValueError("delivery item outcomes differ from the complete bound request")
    wave = delivery["active_wave"]
    if wave is not None:
        manifest = json_object(read(wave["manifest"], "wave manifest", 65536), "wave manifest")
        _fields(manifest, {"schema_version", "record_kind", "operation_id", "wave_id", "task_ids", "items", "requests", "inputs"}, "wave manifest")
        frozen_items = [next(row for row in delivery["items"] if row["task_id"] == identity) for identity in wave["task_ids"]]
        selected_requests = {row["request_id"] for row in frozen_items}
        frozen_requests = [row for row in delivery["requests"] if row["id"] in selected_requests]
        if (type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1
                or manifest["record_kind"] != "alatyr-delivery-wave"
                or manifest["operation_id"] != delivery["operation_id"] or manifest["wave_id"] != wave["id"]
                or manifest["task_ids"] != wave["task_ids"]
                or manifest["items"] != frozen_items or manifest["requests"] != frozen_requests):
            raise ValueError("wave manifest identity, ordered membership, ownership or request mapping differs from its frozen binding")
        inputs = manifest["inputs"]
        if not isinstance(inputs, list) or not 1 <= len(inputs) <= MAX_ITEMS:
            raise ValueError("wave inputs requires 1..64 material input bindings")
        seen = set()
        for item in inputs:
            _binding(item, "wave input")
            if item["path"].casefold() in seen | {wave["manifest"]["path"].casefold()}:
                raise ValueError("wave inputs contain duplicate or self-referential paths")
            seen.add(item["path"].casefold())
            read(item, "wave input", MAX_SOURCE_BYTES)
        if report["delivery"].get("wave") is not None:
            report["delivery"]["wave"]["input_state"] = "current-declared-inputs"
    report["delivery"]["source_state"] = "current-bound-requests"
    bound_delivery_view(report)


def coordination_hold(report, reason):
    if "delivery" in report:
        report["delivery"] = {**report["delivery"], "next_decision": "coordinate-before-work",
                              "coordination_hold": reason}
        bound_delivery_view(report)


def bound_delivery_view(report):
    from analysis_strategy_contract import canonical_utf8_size, structured_word_count
    delivery = report["delivery"]
    if canonical_utf8_size(delivery) > 8192 or structured_word_count(delivery) > 800:
        report["delivery"] = {"operation_id": delivery["operation_id"], "state": "reference-required",
            "source_state": delivery["source_state"], "item_count": delivery["item_count"],
            "request_count": delivery["request_count"], "review_due_count": len(delivery.get("review_due_ids", [])),
            "plan": report["plan"], "next_decision": "coordinate-before-work" if "coordination_hold" in delivery else "read-bound-plan",
            **({"coordination_hold": delivery["coordination_hold"]} if "coordination_hold" in delivery else {}),
            "authority": "none", "delivery_acceptance_granted": False,
            "limitation": "Delivery view exceeds 8 KiB or 800 words; no duties or constraints were truncated into actionable advice."}


def retained_worker_delivery(value, allocation_id, inputs, admission_path):
    delivery = value["delivery"]
    item = next(row for row in delivery["items"] if row["task_id"] == allocation_id)
    source = next(row["source"] for row in delivery["requests"] if row["id"] == item["request_id"])
    return {"operation_id": delivery["operation_id"], "item": item, "request_source": source,
            "inputs": {path: sha for path, sha in inputs.items() if path not in {admission_path, value["plan"]["path"]}}}


def worker_delivery_binding(value, allocation_id):
    _fields(value, {"operation_id", "item", "request_source", "inputs"}, "retained worker delivery")
    _id(value["operation_id"], "retained operation_id")
    _item(value["item"])
    if value["item"]["task_id"] != allocation_id:
        raise ValueError("retained delivery item differs from worker allocation")
    source = _binding(value["request_source"], "retained request source")
    inputs = value["inputs"]
    if not isinstance(inputs, dict) or not 1 <= len(inputs) <= 81:
        raise ValueError("retained delivery inputs requires 1..81 bindings")
    for path, sha in inputs.items():
        _binding({"path": path, "sha256": sha}, "retained delivery input")
    if inputs.get(source["path"]) != source["sha256"]:
        raise ValueError("retained delivery inputs must include the exact request source")
    return inputs
