"""Validate target-owned runtime-observation support and concrete records."""

from __future__ import annotations

from datetime import datetime
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


def _resolved_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not is_placeholder(value) and not is_unresolved_value(value)


def _immutable_revision(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) in {40, 64}
        and all(character in "0123456789abcdef" for character in value)
    )


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def runtime_observation_failures(
    record: dict[str, Any], *, allowed_event_ids: set[str] | None = None
) -> list[str]:
    """Return deterministic contract failures for one concrete observation."""

    failures: list[str] = []
    if record.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if record.get("record_kind") != "alatyr-runtime-observation":
        failures.append("record_kind is invalid")
    for field in ["observation_id", "operation_id"]:
        if not _resolved_text(record.get(field)):
            failures.append(f"{field} must be resolved")
    if not _immutable_revision(record.get("repository_revision")):
        failures.append("repository_revision must be an immutable full Git commit id")
    window = record.get("window")
    if not isinstance(window, dict):
        failures.append("window must be an object")
    else:
        started = _timestamp(window.get("started_at"))
        ended = _timestamp(window.get("ended_at"))
        if started is None:
            failures.append("window.started_at must be a timezone-aware ISO-8601 timestamp")
        if ended is None:
            failures.append("window.ended_at must be a timezone-aware ISO-8601 timestamp")
        if started is not None and ended is not None and ended < started:
            failures.append("window.ended_at must not precede window.started_at")
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
        if allowed_event_ids is not None and event_id not in allowed_event_ids:
            failures.append(f"event {event_id} is absent from the target event catalog")
        classification = event.get("classification")
        disposition = event.get("disposition")
        count = event.get("observed_count")
        refs = event.get("evidence_refs")
        if classification not in CLASSIFICATIONS:
            failures.append(f"event {event_id} classification is invalid")
        if disposition not in DISPOSITIONS:
            failures.append(f"event {event_id} disposition is invalid")
        valid_count = isinstance(count, int) and not isinstance(count, bool) and count >= 0
        if not valid_count:
            failures.append(f"event {event_id} observed_count must be non-negative")
        if not isinstance(refs, list) or not refs or not all(
            isinstance(item, str) and item.strip() for item in refs
        ):
            failures.append(f"event {event_id} requires evidence_refs")
        if classification == "unknown" or disposition == "unresolved":
            failures.append(f"event {event_id} remains unresolved")
        if classification == "forbidden" and valid_count and count > 0:
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
        if not _resolved_text(claim_id):
            failures.append(f"claims[{index}].id must be resolved")
            claim_id = f"claims[{index}]"
        status = claim.get("status")
        if status not in CLAIM_STATUSES:
            failures.append(f"claim {claim_id} status is invalid")
            continue
        required = claim.get("required_event_ids")
        contradictions = claim.get("contradiction_event_ids")
        if not isinstance(required, list) or not isinstance(contradictions, list):
            failures.append(f"claim {claim_id} event references must be lists")
            continue
        if not all(_resolved_text(item) for item in [*required, *contradictions]):
            failures.append(f"claim {claim_id} event references must be resolved strings")
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
                and isinstance(event_by_id[event_id].get("observed_count"), int)
                and not isinstance(event_by_id[event_id].get("observed_count"), bool)
                and event_by_id[event_id].get("observed_count", 0) < 1
            ]
            observed_contradictions = [
                event_id for event_id in contradictions
                if event_id in event_by_id
                and isinstance(event_by_id[event_id].get("observed_count"), int)
                and not isinstance(event_by_id[event_id].get("observed_count"), bool)
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
        if not isinstance(signals, list) or not signals or not all(
            isinstance(item, str) and item in RECURRENCE_SIGNALS for item in signals
        ):
            failures.append("recurrence.signals contains invalid values")
        if candidate is True and disposition in {None, "not-applicable", "unresolved"}:
            failures.append("recurrence candidate requires an incident-lineage disposition")

    post = record.get("post_result_validation")
    if not isinstance(post, dict):
        failures.append("post_result_validation must be an object")
    else:
        result_revision = post.get("result_revision")
        repository_revision = record.get("repository_revision")
        if not _immutable_revision(result_revision):
            failures.append("post-result revision must be an immutable full Git commit id")
        if post.get("adapter_validation_request") != "required-current-run":
            failures.append("post-result adapter validation must be requested from the current run")
        if post.get("evidence_fresh") is not True:
            failures.append("post-result evidence must be fresh")
        if _immutable_revision(result_revision) and _immutable_revision(repository_revision) and result_revision != repository_revision:
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
        ".ai/project/runtime-observations/index.json",
        ".ai/project/runtime-observations/records/README.md",
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
    if policy.get("state") not in {"enabled", "required"}:
        context.error("RUNTIME_POLICY_STATE", "enabled module requires enabled or required policy state", policy_path)
    if policy.get("live_access_requires_approval") is not True:
        context.error("RUNTIME_POLICY_LIVE_APPROVAL", "live access must require approval", policy_path)
    collection = policy.get("collection")
    if not isinstance(collection, dict):
        context.error("RUNTIME_COLLECTION_SHAPE", "collection must be an object", policy_path)
    else:
        for field in ["max_compact_events", "max_samples_per_event"]:
            value = collection.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < (1 if field == "max_compact_events" else 0):
                context.error("RUNTIME_COLLECTION_BOUND", f"collection.{field} is invalid", policy_path)
        for field in ["commands", "sources"]:
            values = collection.get(field)
            if not isinstance(values, list) or not values or not all(_resolved_text(item) for item in values):
                context.error("RUNTIME_COLLECTION_SOURCE", f"collection.{field} must contain resolved values", policy_path)
        if not _resolved_text(collection.get("default_window")):
            context.error("RUNTIME_COLLECTION_WINDOW", "collection.default_window must be resolved", policy_path)
        if collection.get("raw_evidence_loading") != "on-failure-or-explicit-review":
            context.error("RUNTIME_RAW_LOADING", "raw evidence must remain conditional", policy_path)
    catalog = policy.get("event_catalog")
    if not isinstance(catalog, list) or not catalog:
        context.error("RUNTIME_EVENT_CATALOG", "event_catalog must be non-empty", policy_path)
        catalog = []
    event_catalog_ids: set[str] = set()
    for position, event in enumerate(catalog):
        event_id = event.get("id") if isinstance(event, dict) else None
        if not _resolved_text(event_id):
            context.error("RUNTIME_EVENT_CATALOG_ENTRY", f"event_catalog[{position}].id must be resolved", policy_path)
            continue
        if event_id in event_catalog_ids:
            context.error("RUNTIME_EVENT_CATALOG_DUPLICATE", f"duplicate event catalog id: {event_id}", policy_path)
        event_catalog_ids.add(str(event_id))
        if isinstance(event, dict):
            for field in ["meaning", "owner"]:
                if not _resolved_text(event.get(field)):
                    context.error("RUNTIME_EVENT_CATALOG_ENTRY", f"event_catalog[{position}].{field} must be resolved", policy_path)
            if event.get("default_classification") not in CLASSIFICATIONS:
                context.error("RUNTIME_EVENT_CATALOG_ENTRY", f"event_catalog[{position}].default_classification is invalid", policy_path)

    index_path = required[1]
    index = context.load_json_object(context.target_path(index_path), "RUNTIME_INDEX")
    if index is None:
        return
    if index.get("schema_version") != 1 or index.get("index_kind") != "target-runtime-observation-index":
        context.error("RUNTIME_INDEX_CONTRACT", "runtime observation index contract is invalid", index_path)
    record_required = index.get("required_for_current_change")
    current_operation_id = index.get("current_operation_id")
    records = index.get("current_records")
    if not isinstance(record_required, bool):
        context.error("RUNTIME_INDEX_REQUIRED_STATE", "required_for_current_change must be boolean", index_path)
    if not isinstance(records, list):
        context.error("RUNTIME_INDEX_RECORDS_SHAPE", "current_records must be a list", index_path)
        records = []
    if record_required is True and not records:
        context.error("RUNTIME_OBSERVATION_REQUIRED_MISSING", "current change requires at least one runtime observation record", index_path)
    if records and not _resolved_text(current_operation_id):
        context.error("RUNTIME_INDEX_OPERATION", "selected records require a resolved current_operation_id", index_path)
    seen: set[str] = set()
    prefix = ".ai/project/runtime-observations/records/"
    head_revision = context.git.head_revision() if context.git is not None else None
    for position, entry in enumerate(records):
        if not isinstance(entry, dict):
            context.error("RUNTIME_RECORD_ENTRY", f"current_records[{position}] must be an object", index_path)
            continue
        relpath = entry.get("record_path")
        operation_id = entry.get("operation_id")
        expected_sha256 = entry.get("sha256")
        if not _resolved_text(relpath) or not str(relpath).startswith(prefix) or str(relpath).endswith("/README.md"):
            context.error("RUNTIME_RECORD_PATH", f"current_records[{position}] must select a concrete record under {prefix}", index_path)
            continue
        if not _resolved_text(operation_id) or operation_id != current_operation_id:
            context.error("RUNTIME_RECORD_OPERATION", f"current_records[{position}] operation_id must match current_operation_id", index_path)
        if not isinstance(expected_sha256, str) or len(expected_sha256) != 64 or any(character not in "0123456789abcdef" for character in expected_sha256):
            context.error("RUNTIME_RECORD_DIGEST", f"current_records[{position}].sha256 must be a lowercase SHA-256", index_path)
        relpath = str(relpath)
        if relpath in seen:
            context.error("RUNTIME_RECORD_DUPLICATE", f"duplicate current runtime record: {relpath}", index_path)
            continue
        seen.add(relpath)
        if not context.is_target_file(relpath):
            context.error("RUNTIME_RECORD_MISSING", "selected runtime observation record is missing", relpath)
            continue
        actual_sha256 = context.content_digest(context.target_path(relpath))
        if actual_sha256 != expected_sha256:
            context.error("RUNTIME_RECORD_DIGEST_MISMATCH", "selected runtime observation record differs from its index digest", relpath)
        record = context.load_json_object(context.target_path(relpath), "RUNTIME_RECORD")
        if record is None:
            continue
        if record.get("operation_id") != operation_id:
            context.error("RUNTIME_RECORD_OPERATION_MISMATCH", "record operation_id differs from its index entry", relpath)
        observed_revision = record.get("repository_revision")
        resolved_revision = (
            context.git.resolve_ref(observed_revision)
            if context.git is not None and _resolved_text(observed_revision)
            else None
        )
        if head_revision is None or resolved_revision is None:
            context.error("RUNTIME_RECORD_REVISION_UNVERIFIED", "current Git HEAD is unavailable for runtime evidence binding", relpath)
        elif observed_revision != resolved_revision:
            context.error("RUNTIME_RECORD_REVISION_UNVERIFIED", "record repository_revision must be the immutable full commit ID returned by Git", relpath)
        elif context.git.is_ancestor(resolved_revision, head_revision) is not True:
            context.error("RUNTIME_RECORD_REVISION_STALE", "record repository_revision is not an ancestor of current Git HEAD", relpath)
        else:
            intervening = context.git.changed_files(resolved_revision)
            allowed_prefix = ".ai/project/runtime-observations/"
            if intervening is None or any(
                not path.startswith(allowed_prefix) for path in intervening
            ):
                context.error("RUNTIME_RECORD_REVISION_STALE", "committed, staged, unstaged, or untracked non-evidence paths changed after the observed runtime revision", relpath)
        for failure in runtime_observation_failures(record, allowed_event_ids=event_catalog_ids):
            context.error("RUNTIME_OBSERVATION_RECORD_INVALID", failure, relpath)
    context.info(
        "RUNTIME_OBSERVATION_EVIDENCE_LIMIT",
        "record validation proves internal consistency, not runtime truth or event classification correctness",
    )


RUNTIME_OBSERVATION_MODULE = FunctionCapabilityModule(
    check_id="check_runtime_observation",
    validator=validate_runtime_observation,
)
