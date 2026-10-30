"""Pure, bounded comparison of untrusted handoff and build-capacity observations."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from target_validation_support import is_unresolved_value
from session_presence_contract import uid, scope_reference

INTENT_FIELDS = ("resource_id", "publisher_uid", "approval_ref", "candidate_revision",
                 "origin_id", "expected_previous_pin", "expected_pin_generation")


def decode_observation(raw: bytes) -> dict:
    if len(raw) > 256 * 1024:
        raise ValueError("observation input exceeds 256 KiB")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate observation key: {key}")
            result[key] = value
        return result
    def constant(value):
        raise ValueError(f"non-finite observation number: {value}")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=constant)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("invalid bounded UTF-8 observation JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("observation input must be an object")
    return value


def intent_digest(intent: dict) -> str:
    return hashlib.sha256(json.dumps(intent, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode("utf-8")).hexdigest()


def handoff_resource_scope(identity: Any) -> str | None:
    if not isinstance(identity, str) or not identity or len(identity) > 111:
        return None
    reference = "resource:" + identity
    try:
        scope_reference(reference)
    except ValueError:
        return None
    return reference


def text(value: Any) -> bool:
    return (isinstance(value, str) and 0 < len(value) <= 1024
            and not any(ord(char) < 32 for char in value) and not is_unresolved_value(value))


def revision(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value) is not None


def positive(value: Any, *, zero: bool = False) -> bool:
    return type(value) is int and (0 if zero else 1) <= value <= 2 ** 63 - 1


def observed_at(value: Any, now: datetime, max_age: int) -> bool:
    if not isinstance(value, str) or len(value) > 64:
        return False
    try:
        when = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return when.tzinfo is not None and 0 <= (now - when).total_seconds() <= max_age
    except (ValueError, OverflowError, TypeError):
        return False


def report(kind: str) -> dict:
    return {"report_kind": kind, "state": "unresolved", "findings": [],
            "authorization_granted": False, "execution_performed": False,
            "limitation": "Caller-supplied observations, not authenticated authority, a reservation, a lock, live verification or an execution guarantee."}


def handoff_report(record: Any, current: Any, *, now: datetime | None = None) -> dict:
    result = report("alatyr-publication-handoff")
    findings = result["findings"]
    def fail(path, message):
        findings.append({"code": "HANDOFF_BINDING", "path": path, "message": message})
    if not isinstance(record, dict) or not isinstance(current, dict):
        fail("handoff", "record and independent current inputs must be objects")
        return result
    if type(record.get("schema_version")) is not int or record["schema_version"] != 1:
        fail("schema_version", "unsupported handoff schema")
    max_age = current.get("max_age_seconds")
    if not positive(max_age) or max_age > 86400:
        fail("max_age_seconds", "select an explicit freshness bound in 1..86400 seconds")
        return result
    now = now or datetime.now(timezone.utc)
    intent, selected = record.get("intent"), current.get("intent")
    if not isinstance(intent, dict) or not isinstance(selected, dict):
        fail("intent", "both recorded and independent current intent are required")
        return result
    for name in INTENT_FIELDS:
        check = revision if name in {"candidate_revision", "expected_previous_pin"} else text
        if not check(intent.get(name)) or not check(selected.get(name)) or intent.get(name) != selected.get(name):
            fail("intent." + name, "required recorded and current bindings must be resolved and identical")
    try:
        uid(intent.get("publisher_uid"))
    except ValueError:
        fail("intent.publisher_uid", "publisher must name a canonical session UUID v4")
    if handoff_resource_scope(intent.get("resource_id")) is None:
        fail("intent.resource_id", "resource must be a stable presence-compatible identity of at most 111 characters")
    if set(intent) != set(INTENT_FIELDS) or set(selected) != set(INTENT_FIELDS):
        fail("intent", "intent requires exactly the supported bindings")
    if findings:
        return result
    acknowledgement = record.get("acknowledgement")
    if not isinstance(acknowledgement, dict):
        fail("acknowledgement", "nominated publisher acknowledgement is missing")
    else:
        if acknowledgement.get("publisher_uid") != intent["publisher_uid"] or acknowledgement.get("intent_sha256") != intent_digest(intent):
            fail("acknowledgement", "publisher and digest must acknowledge the entire unchanged intent")
        if not text(acknowledgement.get("evidence_ref")) or not observed_at(acknowledgement.get("recorded_at"), now, max_age):
            fail("acknowledgement", "fresh bounded acknowledgement and evidence reference are required")
    availability = record.get("availability")
    if not isinstance(availability, dict):
        fail("availability", "exact candidate availability at the intended origin is unobserved")
    else:
        if (availability.get("candidate_revision") != intent["candidate_revision"]
                or availability.get("origin_id") != intent["origin_id"]
                or availability.get("state") != "available"):
            fail("availability", "candidate is not reported available at the selected origin")
        if not text(availability.get("evidence_ref")) or not observed_at(availability.get("observed_at"), now, max_age):
            fail("availability", "fresh availability observation and evidence reference are required")
    pin = current.get("pin")
    if not isinstance(pin, dict):
        fail("pin", "current pin observation is missing")
    else:
        if pin.get("revision") != intent["expected_previous_pin"] or pin.get("generation") != intent["expected_pin_generation"]:
            fail("pin", "current pin or generation changed; reconcile and obtain a new acknowledgement")
        if not text(pin.get("evidence_ref")) or not observed_at(pin.get("observed_at"), now, max_age):
            fail("pin", "fresh current pin observation and evidence reference are required")
    result["state"] = "reported-consistent" if not findings else "unresolved"
    result["activation_order_verified"] = False
    result["next_action"] = "reobserve immediately before separately authorized conditional publication; do not activate an unavailable candidate"
    return result


def capacity_report(value: Any, *, now: datetime | None = None) -> dict:
    result = report("alatyr-build-capacity")
    findings = result["findings"]
    def fail(path, message):
        findings.append({"code": "CAPACITY_OBSERVATION", "path": path, "message": message})
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        fail("capacity", "capacity input requires schema 1")
        return result
    age = value.get("max_age_seconds")
    domains, builds = value.get("domains"), value.get("builds")
    if (not positive(age) or age > 86400 or not isinstance(domains, list) or not 1 <= len(domains) <= 64
            or not isinstance(builds, list) or not 1 <= len(builds) <= 64):
        fail("capacity", "select explicit freshness and 1..64 domains/build instances")
        return result
    now = now or datetime.now(timezone.utc)
    by_id = {}
    for index, domain in enumerate(domains):
        path = f"domains[{index}]"
        if not isinstance(domain, dict) or not text(domain.get("domain_id")):
            fail(path, "domain requires a resolved identity")
            continue
        identity = domain["domain_id"]
        if identity in by_id:
            fail(path, "duplicate capacity domain")
            continue
        by_id[identity] = domain
        if not positive(domain.get("headroom_bytes"), zero=True) or not positive(domain.get("cpu_slots"), zero=True):
            fail(path, "available headroom and CPU slots must be known nonnegative integers, not total capacity")
        if not observed_at(domain.get("observed_at"), now, age) or not text(domain.get("evidence_ref")):
            fail(path, "fresh headroom observation and evidence reference are required")
    instances = set()
    sums = {identity: [0, 0] for identity in by_id}
    for index, build in enumerate(builds):
        path = f"builds[{index}]"
        if not isinstance(build, dict) or not text(build.get("instance_id")) or not text(build.get("domain_id")):
            fail(path, "each build instance requires explicit identity and placement")
            continue
        if build["instance_id"] in instances:
            fail(path, "duplicate build instance")
        instances.add(build["instance_id"])
        if build["domain_id"] not in by_id:
            fail(path, "build placement has no observed capacity domain")
            continue
        if (not positive(build.get("process_tree_peak_bytes")) or not positive(build.get("cpu_slots"))
                or build.get("basis") != "process-tree-peak-estimate" or not text(build.get("evidence_ref"))
                or not observed_at(build.get("observed_at"), now, age)):
            fail(path, "fresh process-tree peak estimate and CPU demand are required; heap target alone is insufficient")
            continue
        sums[build["domain_id"]][0] += build["process_tree_peak_bytes"]
        sums[build["domain_id"]][1] += build["cpu_slots"]
    totals = []
    for identity, (memory, cpu) in sums.items():
        domain = by_id[identity]
        totals.append({"domain_id": identity, "demand_bytes": memory, "demand_cpu_slots": cpu})
        if positive(domain.get("headroom_bytes"), zero=True) and positive(domain.get("cpu_slots"), zero=True):
            if memory > domain["headroom_bytes"] or cpu > domain["cpu_slots"]:
                fail(identity, "aggregate demand exceeds observed headroom; serialize or reduce the selected concurrency")
    result["domains"] = totals
    result["state"] = "estimated-fit" if not findings else "unresolved"
    result["next_action"] = "recheck estimates and coordinate existing workloads; estimated fit cannot guarantee absence of OOM"
    return result
