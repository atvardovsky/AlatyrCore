#!/usr/bin/env python3
"""Parse and validate the AlatyrCore source worker contract."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


POLICY_SCHEMA_VERSION = 2
CAPABILITY_SCHEMA_VERSION = 2
PACKET_SCHEMA_VERSION = 1
POLICY_KIND = "alatyr-source-worker-policy"
CANONICAL_RULE = "ALATYR-DELEGATION-001"
TASK_CLASSES = {"small-task", "standard-task", "large-or-resumable"}
PREFLIGHT_DECISIONS = {
    "runtime-verification-required",
    "workstream-identification-required",
    "delegation-recommended",
    "kept-local",
    "primary-assistant",
}
COMPLETION_DECISIONS = {"delegated", "kept-local"}
DECISION_FIELDS = {
    "evaluation_status",
    "runtime_capability_status",
    "selected_workstream_ids",
    "decision",
    "reason",
    "skip_reason_id",
}
PACKET_FIELDS = {
    "schema_version",
    "packet_kind",
    "workstream_id",
    "role_id",
    "objective",
    "bounded_context",
    "conditional_context",
    "non_goals",
    "allowed_actions",
    "write_scope",
    "independent",
    "independence_key",
    "expected_evidence",
}
PRIMARY_OWNED_ACTIONS = {
    "task-profile-selection",
    "runtime-capability-verification",
    "worker-packet-approval",
    "architecture-decisions",
    "conflict-resolution",
    "logical-integrity-review",
    "result-verification",
    "final-synthesis",
    "final-validation",
    "current-scope-authorization",
    "modify",
    "commit",
    "publish",
    "live-external",
}
POLICY_FIELDS = {
    "schema_version",
    "policy_kind",
    "scope",
    "provider_neutral",
    "canonical_rule",
    "runtime_capability_owner",
    "fallback_executor",
    "runtime_capability_contract",
    "activation",
    "decision_evidence",
    "worker_packet_contract",
    "workstreams",
    "primary_owned_actions",
    "authorization_boundary",
}
WORKSTREAM_FIELDS = {
    "objective",
    "mode",
    "independent",
    "independence_key",
    "required_context",
    "conditional_context",
    "non_goals",
    "expected_evidence",
}


class SourceWorkerContractError(ValueError):
    """Raised when source worker policy or evidence violates its contract."""


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(
    value: Any,
    *,
    label: str,
    nonempty: bool = True,
    unique: bool = True,
) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise SourceWorkerContractError(f"{label} must be a non-empty list")
    if not all(_nonempty_string(item) for item in value):
        raise SourceWorkerContractError(f"{label} must contain non-empty strings")
    if unique and len(value) != len(set(value)):
        raise SourceWorkerContractError(f"{label} must contain unique values")
    return value


def _require_fields(value: dict[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(fields - set(value))
    if missing:
        raise SourceWorkerContractError(f"{label} is missing fields: {missing}")


def _require_exact_fields(
    value: dict[str, Any], fields: set[str], label: str
) -> None:
    _require_fields(value, fields, label)
    unexpected = sorted(set(value) - fields)
    if unexpected:
        raise SourceWorkerContractError(
            f"{label} has unexpected fields: {unexpected}"
        )


def _repository_path(value: str, label: str) -> Path:
    path = Path(value)
    if (
        value == "."
        or "\\" in value
        or path.is_absolute()
        or "." in path.parts
        or ".." in path.parts
        or path.as_posix() != value
    ):
        raise SourceWorkerContractError(f"{label} must be a repository-relative path")
    return path


def _is_file_inside_root(root: Path, path: Path) -> bool:
    try:
        resolved_root = root.resolve(strict=True)
        resolved = (root / path).resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, ValueError):
        return False
    return resolved.is_file()


def _parse_timestamp(value: Any, label: str) -> datetime:
    if not _nonempty_string(value):
        raise SourceWorkerContractError(f"{label} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceWorkerContractError(
            f"{label} must be an ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SourceWorkerContractError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate_worker_packet(
    packet: dict[str, Any],
    contract: dict[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Validate one provider-neutral inspect-only worker packet."""
    if not isinstance(packet, dict):
        raise SourceWorkerContractError("worker packet must be an object")
    required = set(_string_list(contract.get("required_fields"), label="packet required_fields"))
    if required != PACKET_FIELDS:
        raise SourceWorkerContractError("packet required_fields do not match schema v1")
    _require_exact_fields(packet, required, "worker packet")
    if packet.get("schema_version") != PACKET_SCHEMA_VERSION:
        raise SourceWorkerContractError("worker packet schema_version is invalid")
    if packet.get("packet_kind") not in contract["packet_kinds"]:
        raise SourceWorkerContractError("worker packet_kind is invalid")
    for field in ["workstream_id", "objective", "independence_key", "expected_evidence"]:
        if not _nonempty_string(packet.get(field)):
            raise SourceWorkerContractError(f"worker packet has invalid {field}")
    if packet.get("role_id") != contract["role_id"]:
        raise SourceWorkerContractError("worker packet role_id is invalid")
    if packet.get("allowed_actions") != contract["allowed_actions"]:
        raise SourceWorkerContractError("worker packet must be inspect-only")
    if packet.get("write_scope") != contract["write_scope"]:
        raise SourceWorkerContractError("worker packet must have no write scope")
    if packet.get("independent") is not True:
        raise SourceWorkerContractError("worker packet must be independently reviewable")
    bounded = _string_list(packet.get("bounded_context"), label="worker packet bounded_context")
    bounded_paths = [
        _repository_path(path, "worker packet bounded_context") for path in bounded
    ]
    _string_list(
        packet.get("conditional_context"),
        label="worker packet conditional_context",
        nonempty=False,
    )
    _string_list(packet.get("non_goals"), label="worker packet non_goals")
    if root is not None:
        missing = [
            value
            for value, path in zip(bounded, bounded_paths)
            if not _is_file_inside_root(root, path)
        ]
        if missing:
            raise SourceWorkerContractError(
                f"worker packet references missing bounded context: {missing}"
            )
    return packet


def _validate_runtime_contract(contract: Any) -> None:
    if not isinstance(contract, dict):
        raise SourceWorkerContractError("runtime_capability_contract must be an object")
    required_fields = {
        "schema_version",
        "status",
        "surface_id",
        "runtime_id",
        "backend_kind",
        "role_ids",
        "max_parallelism",
        "write_isolation",
        "result_delivery",
        "model_binding",
        "verified_at",
        "expires_at",
        "freshness",
        "session_id",
        "evidence",
    }
    _require_exact_fields(
        contract,
        {
            "required_fields",
            "schema_version",
            "status",
            "backend_kinds",
            "required_role_id",
            "write_isolation",
            "result_delivery",
            "freshness",
            "minimum_parallelism",
            "maximum_age_seconds",
            "maximum_validity_seconds",
            "maximum_future_skew_seconds",
        },
        "runtime_capability_contract",
    )
    if set(_string_list(contract.get("required_fields"), label="capability required_fields")) != required_fields:
        raise SourceWorkerContractError("capability required_fields do not match schema v2")
    expected = {
        "schema_version": CAPABILITY_SCHEMA_VERSION,
        "status": "available",
        "required_role_id": "read-only-auditor",
        "write_isolation": "read-only",
        "result_delivery": True,
        "freshness": "current-session",
        "minimum_parallelism": 2,
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            raise SourceWorkerContractError(
                f"runtime capability contract requires {field}={value!r}"
            )
    _string_list(contract.get("backend_kinds"), label="capability backend_kinds")
    for field in ["maximum_age_seconds", "maximum_validity_seconds", "maximum_future_skew_seconds"]:
        value = contract.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise SourceWorkerContractError(f"runtime capability {field} must be positive")
    if contract["maximum_age_seconds"] > contract["maximum_validity_seconds"]:
        raise SourceWorkerContractError(
            "runtime capability maximum_age_seconds exceeds maximum_validity_seconds"
        )


def _validate_activation(activation: Any) -> None:
    if not isinstance(activation, dict):
        raise SourceWorkerContractError("activation must be an object")
    required = {
        "task_classes",
        "minimum_independent_packets",
        "repository_audit_candidate_source",
        "task_specific_candidate_source",
        "missing_large_task_packets_decision",
        "audit_default",
        "fallback_executor",
    }
    _require_exact_fields(activation, required, "activation")
    classes = set(_string_list(activation["task_classes"], label="activation task_classes"))
    if classes != {"large-or-resumable"} or not classes <= TASK_CLASSES:
        raise SourceWorkerContractError("activation task_classes must contain large-or-resumable")
    if activation["minimum_independent_packets"] != 2:
        raise SourceWorkerContractError("activation requires two independent packets")
    expected = {
        "repository_audit_candidate_source": "built-in-workstreams",
        "task_specific_candidate_source": "explicit-worker-packets",
        "missing_large_task_packets_decision": "workstream-identification-required",
        "audit_default": "evaluate",
        "fallback_executor": "primary-assistant",
    }
    for field, value in expected.items():
        if activation.get(field) != value:
            raise SourceWorkerContractError(f"activation requires {field}={value!r}")


def _validate_decision_contract(contract: Any) -> None:
    if not isinstance(contract, dict):
        raise SourceWorkerContractError("decision_evidence must be an object")
    _require_exact_fields(
        contract,
        {
            "required_fields",
            "preflight_decisions",
            "completion_decisions",
            "skip_reason_ids",
            "decision_rules",
        },
        "decision_evidence",
    )
    if set(_string_list(contract.get("required_fields"), label="decision required_fields")) != DECISION_FIELDS:
        raise SourceWorkerContractError("decision required_fields do not match schema v2")
    if set(_string_list(contract.get("preflight_decisions"), label="preflight decisions")) != PREFLIGHT_DECISIONS:
        raise SourceWorkerContractError("preflight decision set is invalid")
    if set(_string_list(contract.get("completion_decisions"), label="completion decisions")) != COMPLETION_DECISIONS:
        raise SourceWorkerContractError("completion decision set is invalid")
    skip_reasons = set(_string_list(contract.get("skip_reason_ids"), label="skip reason IDs"))
    rules = contract.get("decision_rules")
    if not isinstance(rules, dict) or set(rules) != PREFLIGHT_DECISIONS:
        raise SourceWorkerContractError("decision_rules must cover every preflight decision")
    for decision, rule in rules.items():
        if not isinstance(rule, dict) or rule.get("skip_reason") not in {"required", "forbidden"}:
            raise SourceWorkerContractError(f"decision rule is invalid for {decision}")
        _require_exact_fields(
            rule,
            {"skip_reason", "allowed_skip_reason_ids"},
            f"decision rule {decision}",
        )
        allowed = rule.get("allowed_skip_reason_ids", [])
        allowed_set = set(_string_list(allowed, label=f"{decision} allowed skip reasons", nonempty=False))
        if not allowed_set <= skip_reasons:
            raise SourceWorkerContractError(f"decision rule references unknown skip reason for {decision}")
        if rule["skip_reason"] == "required" and not allowed_set:
            raise SourceWorkerContractError(f"decision rule requires skip reasons for {decision}")
        if rule["skip_reason"] == "forbidden" and allowed_set:
            raise SourceWorkerContractError(f"decision rule forbids skip reasons for {decision}")


def validate_decision_evidence(
    evidence: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Validate one structured preflight decision against policy rules."""
    if not isinstance(evidence, dict):
        raise SourceWorkerContractError("worker decision evidence must be an object")
    required = set(
        _string_list(contract.get("required_fields"), label="decision required_fields")
    )
    _require_fields(evidence, required, "worker decision evidence")
    decision = evidence.get("decision")
    rules = contract.get("decision_rules", {})
    rule = rules.get(decision) if isinstance(rules, dict) else None
    if not isinstance(rule, dict):
        raise SourceWorkerContractError("worker decision is invalid")
    evaluation_status = evidence.get("evaluation_status")
    if evaluation_status not in {"required", "not-required"}:
        raise SourceWorkerContractError("worker decision has invalid evaluation_status")
    if decision == "primary-assistant" and evaluation_status != "not-required":
        raise SourceWorkerContractError(
            "primary-assistant decision requires evaluation_status=not-required"
        )
    if decision != "primary-assistant" and evaluation_status != "required":
        raise SourceWorkerContractError(
            f"worker decision {decision} requires evaluation_status=required"
        )
    runtime_status = evidence.get("runtime_capability_status")
    if runtime_status not in {
        "unknown",
        "available",
        "unavailable",
    }:
        raise SourceWorkerContractError(
            "worker decision has invalid runtime_capability_status"
        )
    selected_ids = _string_list(
        evidence.get("selected_workstream_ids"),
        label="selected worker workstreams",
        nonempty=False,
    )
    if decision == "delegation-recommended":
        if runtime_status != "available" or len(selected_ids) < 2:
            raise SourceWorkerContractError(
                "delegation-recommended requires available capability and two workstreams"
            )
    elif selected_ids:
        raise SourceWorkerContractError(
            f"worker decision {decision} cannot select workstreams"
        )
    if decision == "runtime-verification-required" and runtime_status != "unknown":
        raise SourceWorkerContractError(
            "runtime-verification-required requires unknown capability"
        )
    if not _nonempty_string(evidence.get("reason")):
        raise SourceWorkerContractError("worker decision requires a concrete reason")

    skip_reason_id = evidence.get("skip_reason_id")
    allowed = set(rule.get("allowed_skip_reason_ids", []))
    if rule.get("skip_reason") == "required":
        if not _nonempty_string(skip_reason_id) or skip_reason_id not in allowed:
            raise SourceWorkerContractError(
                f"worker decision {decision} requires an applicable skip_reason_id"
            )
    elif skip_reason_id is not None:
        raise SourceWorkerContractError(
            f"worker decision {decision} forbids skip_reason_id"
        )
    return evidence


def _forbidden_runtime_bindings(value: Any) -> set[str]:
    forbidden = {
        "provider",
        "provider_id",
        "model",
        "model_id",
        "dispatch_backend",
        "executable",
    }
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(forbidden.intersection(value))
        for nested in value.values():
            found.update(_forbidden_runtime_bindings(nested))
    elif isinstance(value, list):
        for nested in value:
            found.update(_forbidden_runtime_bindings(nested))
    return found


def validate_source_worker_policy(
    policy: dict[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Validate all source worker policy fields consumed by planners/checkers."""
    if not isinstance(policy, dict):
        raise SourceWorkerContractError("source worker policy must be an object")
    _require_exact_fields(policy, POLICY_FIELDS, "source worker policy")
    expected_scalars = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "policy_kind": POLICY_KIND,
        "scope": "source-repository",
        "provider_neutral": True,
        "canonical_rule": CANONICAL_RULE,
        "runtime_capability_owner": "active-assistant",
        "fallback_executor": "primary-assistant",
    }
    for field, value in expected_scalars.items():
        if policy.get(field) != value:
            raise SourceWorkerContractError(f"source worker policy requires {field}={value!r}")

    forbidden_bindings = _forbidden_runtime_bindings(policy)
    if forbidden_bindings:
        raise SourceWorkerContractError(
            "source worker policy must not hard-code provider runtime bindings: "
            f"{sorted(forbidden_bindings)}"
        )

    _validate_runtime_contract(policy.get("runtime_capability_contract"))
    _validate_activation(policy.get("activation"))
    _validate_decision_contract(policy.get("decision_evidence"))

    packet_contract = policy.get("worker_packet_contract")
    if not isinstance(packet_contract, dict):
        raise SourceWorkerContractError("worker_packet_contract must be an object")
    _require_exact_fields(
        packet_contract,
        {
            "schema_version",
            "packet_kinds",
            "required_fields",
            "allowed_actions",
            "role_id",
            "write_scope",
            "result_requirement",
        },
        "worker_packet_contract",
    )
    if set(_string_list(packet_contract.get("required_fields"), label="packet required_fields")) != PACKET_FIELDS:
        raise SourceWorkerContractError("packet required_fields do not match schema v1")
    if packet_contract.get("schema_version") != PACKET_SCHEMA_VERSION:
        raise SourceWorkerContractError("worker packet contract schema_version is invalid")
    if packet_contract.get("packet_kinds") != ["source-read-only-workstream"]:
        raise SourceWorkerContractError("worker packet kinds are invalid")
    if packet_contract.get("allowed_actions") != ["inspect"]:
        raise SourceWorkerContractError("worker packet contract must be inspect-only")
    if packet_contract.get("role_id") != "read-only-auditor":
        raise SourceWorkerContractError("worker packet contract role_id is invalid")
    if packet_contract.get("write_scope") != "none":
        raise SourceWorkerContractError("worker packet contract must have no write scope")
    if not _nonempty_string(packet_contract.get("result_requirement")):
        raise SourceWorkerContractError("worker packet result_requirement is invalid")

    workstreams = policy.get("workstreams")
    if not isinstance(workstreams, dict) or len(workstreams) < 2:
        raise SourceWorkerContractError("source worker policy requires bounded workstreams")
    independence_keys: set[str] = set()
    for workstream_id, workstream in workstreams.items():
        if not _nonempty_string(workstream_id) or not isinstance(workstream, dict):
            raise SourceWorkerContractError("source worker workstream is invalid")
        _require_exact_fields(
            workstream,
            WORKSTREAM_FIELDS,
            f"source worker workstream {workstream_id}",
        )
        if workstream.get("mode") != "read-only":
            raise SourceWorkerContractError(
                f"source worker workstream {workstream_id} must be read-only"
            )
        packet = make_builtin_packet(policy, workstream_id)
        validate_worker_packet(packet, packet_contract, root=root)
        independence_key = packet["independence_key"]
        if independence_key in independence_keys:
            raise SourceWorkerContractError(
                "source worker independence_key values must be unique"
            )
        independence_keys.add(independence_key)

    primary_owned = set(_string_list(policy.get("primary_owned_actions"), label="primary_owned_actions"))
    if not PRIMARY_OWNED_ACTIONS <= primary_owned:
        missing = sorted(PRIMARY_OWNED_ACTIONS - primary_owned)
        raise SourceWorkerContractError(f"primary-owned actions are missing: {missing}")
    authorization_boundary = policy.get("authorization_boundary")
    if (
        not _nonempty_string(authorization_boundary)
        or "current user request" not in authorization_boundary
        or "do not grant" not in authorization_boundary
    ):
        raise SourceWorkerContractError(
            "authorization_boundary must preserve current-request authority"
        )
    return policy


def load_source_worker_policy(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    """Load and validate a source worker policy JSON file."""
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceWorkerContractError(f"cannot load source worker policy: {exc}") from exc
    return validate_source_worker_policy(policy, root=root)


def make_builtin_packet(policy: dict[str, Any], workstream_id: str) -> dict[str, Any]:
    """Project one policy workstream into the common packet contract."""
    workstream = policy.get("workstreams", {}).get(workstream_id)
    if not isinstance(workstream, dict):
        raise SourceWorkerContractError(f"unknown source workstream: {workstream_id}")
    contract = policy["worker_packet_contract"]
    return {
        "schema_version": contract["schema_version"],
        "packet_kind": contract["packet_kinds"][0],
        "workstream_id": workstream_id,
        "role_id": contract["role_id"],
        "objective": workstream.get("objective"),
        "bounded_context": workstream.get("required_context"),
        "conditional_context": workstream.get("conditional_context"),
        "non_goals": workstream.get("non_goals"),
        "allowed_actions": contract["allowed_actions"],
        "write_scope": contract["write_scope"],
        "independent": workstream.get("independent"),
        "independence_key": workstream.get("independence_key"),
        "expected_evidence": workstream.get("expected_evidence"),
    }


def validate_runtime_capability(
    record: dict[str, Any],
    contract: dict[str, Any],
    *,
    session_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate bounded, timezone-aware capability evidence for this session."""
    if not _nonempty_string(session_id):
        raise SourceWorkerContractError("worker session_id must be supplied")
    if not isinstance(record, dict):
        raise SourceWorkerContractError("worker capability record must be an object")
    required = set(_string_list(contract["required_fields"], label="capability required_fields"))
    _require_exact_fields(record, required, "worker capability record")
    expected = {
        "schema_version": contract["schema_version"],
        "status": contract["status"],
        "write_isolation": contract["write_isolation"],
        "result_delivery": contract["result_delivery"],
        "freshness": contract["freshness"],
        "session_id": session_id,
    }
    for field, value in expected.items():
        if record.get(field) != value:
            raise SourceWorkerContractError(
                f"worker capability record requires {field}={value!r}"
            )
    for field in ["surface_id", "runtime_id", "model_binding", "evidence"]:
        if not _nonempty_string(record.get(field)):
            raise SourceWorkerContractError(f"worker capability record has invalid {field}")
    if record.get("backend_kind") not in contract["backend_kinds"]:
        raise SourceWorkerContractError("worker capability record has unsupported backend_kind")
    role_ids = _string_list(record.get("role_ids"), label="worker capability role_ids")
    if contract["required_role_id"] not in role_ids:
        raise SourceWorkerContractError("worker capability record lacks the read-only audit role")
    maximum = record.get("max_parallelism")
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < contract["minimum_parallelism"]:
        raise SourceWorkerContractError("worker capability record has insufficient parallelism")

    verified_at = _parse_timestamp(record.get("verified_at"), "verified_at")
    expires_at = _parse_timestamp(record.get("expires_at"), "expires_at")
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None or reference.utcoffset() is None:
        raise SourceWorkerContractError("capability validation time must include a timezone")
    reference = reference.astimezone(timezone.utc)
    future_skew = timedelta(seconds=contract["maximum_future_skew_seconds"])
    maximum_age = timedelta(seconds=contract["maximum_age_seconds"])
    maximum_validity = timedelta(seconds=contract["maximum_validity_seconds"])
    if verified_at > reference + future_skew:
        raise SourceWorkerContractError("worker capability record is future-dated")
    if reference - verified_at > maximum_age:
        raise SourceWorkerContractError("worker capability record is stale")
    if expires_at <= reference:
        raise SourceWorkerContractError("worker capability record is expired")
    if expires_at <= verified_at or expires_at - verified_at > maximum_validity:
        raise SourceWorkerContractError("worker capability validity window is invalid")
    return record
