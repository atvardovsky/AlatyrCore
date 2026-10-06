"""Validate target-owned runtime-observation support and concrete records."""

from __future__ import annotations

from typing import Any

from target_validation_support import is_placeholder, is_unresolved_value

from target_adapter_validation.capability import (
    CapabilityValidationContext,
    FunctionCapabilityModule,
)


CLASSIFICATIONS = {"expected", "forbidden", "tolerated", "unknown"}
DISPOSITIONS = {"resolved", "accepted", "escalated", "unresolved"}
CLAIM_STATUSES = {"supported", "narrowed", "blocked", "unverified"}
RECURRENCE_SIGNALS = {
    "failed-gate", "predecessor", "repeated-fact", "runtime-contradiction", "none"
}


def runtime_observation_failures(record: dict[str, Any]) -> list[str]:
    """Return deterministic contract failures for one concrete observation."""

    failures: list[str] = []
    if record.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if record.get("record_kind") != "alatyr-runtime-observation":
        failures.append("record_kind is invalid")
    window = record.get("window")
    if not isinstance(window, dict) or window.get("complete") is not True:
        failures.append("observation window must be complete")

    events = record.get("events")
    event_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(events, list) or not events:
        failures.append("events must be a non-empty list")
        events = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            failures.append(f"events[{index}] must be an object")
            continue
        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id.strip():
            failures.append(f"events[{index}].id must be resolved")
            continue
        if event_id in event_by_id:
            failures.append(f"duplicate event id: {event_id}")
        event_by_id[event_id] = event
        classification = event.get("classification")
        disposition = event.get("disposition")
        count = event.get("observed_count")
        refs = event.get("evidence_refs")
        if classification not in CLASSIFICATIONS:
            failures.append(f"event {event_id} classification is invalid")
        if disposition not in DISPOSITIONS:
            failures.append(f"event {event_id} disposition is invalid")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            failures.append(f"event {event_id} observed_count must be non-negative")
        if not isinstance(refs, list) or not refs or not all(
            isinstance(item, str) and item.strip() for item in refs
        ):
            failures.append(f"event {event_id} requires evidence_refs")
        if classification == "unknown" or disposition == "unresolved":
            failures.append(f"event {event_id} remains unresolved")
        if classification == "forbidden" and isinstance(count, int) and count > 0:
            failures.append(f"forbidden event {event_id} was observed")

    claims = record.get("claims")
    if not isinstance(claims, list) or not claims:
        failures.append("claims must be a non-empty list")
        claims = []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            failures.append(f"claims[{index}] must be an object")
            continue
        claim_id = claim.get("id", f"claims[{index}]")
        status = claim.get("status")
        if status not in CLAIM_STATUSES:
            failures.append(f"claim {claim_id} status is invalid")
            continue
        required = claim.get("required_event_ids")
        contradictions = claim.get("contradiction_event_ids")
        if not isinstance(required, list) or not isinstance(contradictions, list):
            failures.append(f"claim {claim_id} event references must be lists")
            continue
        unknown_refs = (set(required) | set(contradictions)) - set(event_by_id)
        if unknown_refs:
            failures.append(
                f"claim {claim_id} references unknown events: {sorted(unknown_refs)}"
            )
        if status == "supported":
            missing = [
                event_id for event_id in required
                if event_id in event_by_id
                and event_by_id[event_id].get("observed_count", 0) < 1
            ]
            observed_contradictions = [
                event_id for event_id in contradictions
                if event_id in event_by_id
                and event_by_id[event_id].get("observed_count", 0) > 0
            ]
            if missing:
                failures.append(f"supported claim {claim_id} lacks events: {missing}")
            if observed_contradictions:
                failures.append(
                    f"supported claim {claim_id} has contradictions: "
                    f"{observed_contradictions}"
                )

    recurrence = record.get("recurrence")
    if not isinstance(recurrence, dict):
        failures.append("recurrence must be an object")
    else:
        candidate = recurrence.get("candidate")
        signals = recurrence.get("signals")
        disposition = recurrence.get("disposition")
        if not isinstance(candidate, bool):
            failures.append("recurrence.candidate must be boolean")
        if not isinstance(signals, list) or not signals or not set(signals) <= RECURRENCE_SIGNALS:
            failures.append("recurrence.signals contains invalid values")
        if candidate is True and disposition in {None, "not-applicable", "unresolved"}:
            failures.append("recurrence candidate requires an incident-lineage disposition")

    post = record.get("post_result_validation")
    if not isinstance(post, dict):
        failures.append("post_result_validation must be an object")
    else:
        if post.get("adapter_validation") != "passed":
            failures.append("post-result adapter validation must pass")
        if post.get("evidence_fresh") is not True:
            failures.append("post-result evidence must be fresh")
        if post.get("result_revision") != record.get("repository_revision"):
            failures.append("post-result revision must match observed revision")
    return failures


def validate_runtime_observation(
    context: CapabilityValidationContext, manifest: Any
) -> None:
    if not context.module_validation_enabled(
        "runtime-observation",
        "RUNTIME_OBSERVATION_UNDECLARED",
        "RUNTIME_OBSERVATION_STATE_MISSING",
        "runtime observation",
    ):
        return
    required = [
        ".ai/project/runtime-observation-policy.json",
        ".ai/assistant/flows/runtime-observation.flow.md",
        ".ai/assistant/gates/runtime-observation.md",
        ".ai/assistant/templates/runtime-observation-record.json",
        ".ai/framework/runtime-observation.md",
    ]
    if any(not context.is_target_file(path) for path in required):
        for path in required:
            if not context.is_target_file(path):
                context.error(
                    "RUNTIME_OBSERVATION_FILE_MISSING",
                    "enabled runtime-observation module is incomplete",
                    path,
                )
        return

    policy_path = required[0]
    policy = context.load_json_object(context.target_path(policy_path), "RUNTIME_POLICY")
    if policy is None:
        return
    if policy.get("schema_version") != 1:
        context.error("RUNTIME_POLICY_SCHEMA", "schema_version must be 1", policy_path)
    if policy.get("policy_kind") != "target-runtime-observation-policy":
        context.error("RUNTIME_POLICY_KIND", "policy_kind is invalid", policy_path)
    for field in ["state", "owner", "last_reviewed", "evidence_revision", "redaction_policy", "retention_policy"]:
        value = policy.get(field)
        if not isinstance(value, str) or not value.strip() or is_placeholder(value) or is_unresolved_value(value):
            context.error("RUNTIME_POLICY_UNRESOLVED", f"{field} must be resolved", policy_path)
    collection = policy.get("collection")
    if not isinstance(collection, dict):
        context.error("RUNTIME_COLLECTION_SHAPE", "collection must be an object", policy_path)
    else:
        for field in ["max_compact_events", "max_samples_per_event"]:
            value = collection.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < (1 if field == "max_compact_events" else 0):
                context.error("RUNTIME_COLLECTION_BOUND", f"collection.{field} is invalid", policy_path)
        if collection.get("raw_evidence_loading") != "on-failure-or-explicit-review":
            context.error("RUNTIME_RAW_LOADING", "raw evidence must remain conditional", policy_path)
    catalog = policy.get("event_catalog")
    if not isinstance(catalog, list) or not catalog:
        context.error("RUNTIME_EVENT_CATALOG", "event_catalog must be non-empty", policy_path)
    context.info(
        "RUNTIME_OBSERVATION_EVIDENCE_LIMIT",
        "record validation proves internal consistency, not runtime truth or event classification correctness",
    )


RUNTIME_OBSERVATION_MODULE = FunctionCapabilityModule(
    check_id="check_runtime_observation",
    validator=validate_runtime_observation,
)
