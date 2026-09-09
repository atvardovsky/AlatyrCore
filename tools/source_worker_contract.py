#!/usr/bin/env python3
"""Parse and validate the AlatyrCore source worker contract."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


POLICY_SCHEMA_VERSION = 4
CAPABILITY_SCHEMA_VERSION = 2
PACKET_SCHEMA_VERSION = 3
EXECUTION_TREE_SCHEMA_VERSION = 1
POLICY_KIND = "alatyr-source-worker-policy"
CANONICAL_RULE = "ALATYR-DELEGATION-001"
TREE_KIND = "alatyr-delegation-execution-tree"
MAX_TOTAL_DELEGATES = 8
MAX_CHILDREN_PER_PARENT = 4
MAX_CONTEXT_WORDS_TOTAL = 24000
MAX_RETRIES_TOTAL = 2
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
    "parent_packet_id",
    "depth",
    "remaining_worker_budget",
    "coverage_key",
    "child_proposal_policy",
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
    "semantic_scope",
    "changed_fact_ids",
    "canonical_owner_refs",
    "surface_refs",
    "relationship_refs",
    "overlap_decision",
    "expected_evidence",
}
EXECUTION_TREE_FIELDS = {
    "schema_version",
    "tree_kind",
    "operation_id",
    "base_revision",
    "current_user_authorization",
    "task_profile",
    "policy_revision",
    "capability_evidence",
    "aggregate_budget",
    "root_node_id",
    "nodes",
    "edges",
    "primary_convergence",
}
EXECUTION_TREE_BUDGET_FIELDS = {
    "max_total_delegates",
    "max_parallel_delegates",
    "max_children_per_parent",
    "max_context_words_total",
    "max_retries_total",
    "used_total_delegates",
    "used_parallel_delegates",
    "used_context_words",
    "used_retries",
}
EXECUTION_TREE_NODE_FIELDS = {
    "node_id",
    "parent_node_id",
    "packet_id",
    "result_id",
    "depth",
    "status",
    "role_id",
    "assistant_surface",
    "dispatch_backend",
    "implementation_level",
    "coverage_key",
    "semantic_scope",
    "changed_fact_ids",
    "canonical_owner_refs",
    "surface_refs",
    "relationship_refs",
    "allowed_actions",
    "write_scope",
    "context_words",
    "attempt",
    "result_status",
    "stop_reason_id",
    "child_proposals",
    "overlap_decision",
}
EXECUTION_TREE_CONVERGENCE_FIELDS = {
    "status",
    "reviewed_result_ids",
    "rejected_result_ids",
    "combined_validation",
    "logical_integrity_review",
    "residual_risk",
    "final_stop_reason_id",
}
EXECUTION_TREE_EDGE_FIELDS = {"parent_node_id", "child_node_id", "edge_kind"}
NODE_STATUSES = {
    "PLANNED",
    "BLOCKED",
    "READY",
    "RUNNING",
    "REVIEW_REQUIRED",
    "DONE",
    "FAILED",
    "CANCELLED",
    "REJECTED",
}
TERMINAL_NODE_STATUSES = {
    "BLOCKED",
    "REVIEW_REQUIRED",
    "DONE",
    "FAILED",
    "CANCELLED",
    "REJECTED",
}
RESULT_STATUS_BY_NODE_STATUS = {
    "BLOCKED": "blocked",
    "REVIEW_REQUIRED": "requires-review",
    "DONE": "succeeded",
    "FAILED": "failed",
    "CANCELLED": "cancelled",
    "REJECTED": "rejected",
}
OVERLAP_DECISIONS = {
    "disjoint",
    "primary-reconciled-overlap",
    "rejected-overlap",
    "not-applicable",
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
    "tree_policy",
    "stop_policy",
    "runtime_capability_contract",
    "activation",
    "decision_evidence",
    "execution_tree_contract",
    "worker_packet_contract",
    "workstreams",
    "primary_owned_actions",
    "authorization_boundary",
}
STOP_REASON_IDS = {
    "scope-covered",
    "evidence-sufficient",
    "coordination-cost-exceeds-benefit",
    "maximum-depth-reached",
    "worker-budget-reached",
    "context-budget-reached",
    "semantic-decision-required",
    "overlapping-scope",
    "primary-critical-path",
    "capability-unavailable",
    "user-restricted",
    "cancelled-by-primary",
}
WORKSTREAM_FIELDS = {
    "objective",
    "mode",
    "independent",
    "independence_key",
    "required_context",
    "conditional_context",
    "non_goals",
    "semantic_scope",
    "changed_fact_ids",
    "canonical_owner_refs",
    "surface_refs",
    "relationship_refs",
    "overlap_decision",
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


def _nonnegative_integer(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise SourceWorkerContractError(f"{label} must be a non-negative integer")
    return value


def _positive_integer(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise SourceWorkerContractError(f"{label} must be a positive integer")
    return value


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
        raise SourceWorkerContractError("packet required_fields do not match schema v3")
    _require_exact_fields(packet, required, "worker packet")
    if packet.get("schema_version") != PACKET_SCHEMA_VERSION:
        raise SourceWorkerContractError("worker packet schema_version is invalid")
    if packet.get("packet_kind") not in contract["packet_kinds"]:
        raise SourceWorkerContractError("worker packet_kind is invalid")
    if packet.get("parent_packet_id") is not None and not _nonempty_string(
        packet.get("parent_packet_id")
    ):
        raise SourceWorkerContractError("worker packet parent_packet_id is invalid")
    depth = packet.get("depth")
    if not isinstance(depth, int) or isinstance(depth, bool) or depth != 1:
        raise SourceWorkerContractError("source worker packet depth must be 1")
    remaining = packet.get("remaining_worker_budget")
    if not isinstance(remaining, int) or isinstance(remaining, bool) or remaining < 0:
        raise SourceWorkerContractError(
            "worker packet remaining_worker_budget must be non-negative"
        )
    if not _nonempty_string(packet.get("coverage_key")):
        raise SourceWorkerContractError("worker packet coverage_key is invalid")
    if packet.get("child_proposal_policy") != contract["child_proposal_policy"]:
        raise SourceWorkerContractError(
            "worker packet child_proposal_policy must be propose-only"
        )
    for field in [
        "workstream_id",
        "objective",
        "independence_key",
        "semantic_scope",
        "expected_evidence",
    ]:
        if not _nonempty_string(packet.get(field)):
            raise SourceWorkerContractError(f"worker packet has invalid {field}")
    _string_list(
        packet.get("changed_fact_ids"),
        label="worker packet changed_fact_ids",
        nonempty=False,
    )
    _string_list(
        packet.get("canonical_owner_refs"),
        label="worker packet canonical_owner_refs",
    )
    _string_list(packet.get("surface_refs"), label="worker packet surface_refs")
    _string_list(
        packet.get("relationship_refs"),
        label="worker packet relationship_refs",
        nonempty=False,
    )
    if packet.get("overlap_decision") not in OVERLAP_DECISIONS:
        raise SourceWorkerContractError("worker packet overlap_decision is invalid")
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


def _validate_tree_and_stop_policy(tree: Any, stop: Any) -> None:
    if not isinstance(tree, dict):
        raise SourceWorkerContractError("tree_policy must be an object")
    _require_exact_fields(
        tree,
        {
            "dispatch_owner",
            "worker_child_behavior",
            "default_max_depth",
            "hard_max_depth",
            "max_total_delegates",
            "max_parallel_delegates",
            "max_children_per_parent",
            "max_context_words_total",
            "max_retries_total",
            "require_disjoint_coverage_keys",
        },
        "tree_policy",
    )
    expected = {
        "dispatch_owner": "primary-assistant",
        "worker_child_behavior": "propose-only",
        "default_max_depth": 1,
        "hard_max_depth": 1,
        "require_disjoint_coverage_keys": True,
    }
    for field, value in expected.items():
        if tree.get(field) != value:
            raise SourceWorkerContractError(
                f"tree_policy requires {field}={value!r}"
            )
    for field, minimum in {
        "max_total_delegates": 1,
        "max_parallel_delegates": 1,
        "max_children_per_parent": 1,
        "max_context_words_total": 1,
        "max_retries_total": 0,
    }.items():
        value = tree.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            raise SourceWorkerContractError(
                f"tree_policy {field} must be an integer >= {minimum}"
            )
    maximums = {
        "max_total_delegates": MAX_TOTAL_DELEGATES,
        "max_parallel_delegates": MAX_TOTAL_DELEGATES,
        "max_children_per_parent": MAX_CHILDREN_PER_PARENT,
        "max_context_words_total": MAX_CONTEXT_WORDS_TOTAL,
        "max_retries_total": MAX_RETRIES_TOTAL,
    }
    for field, maximum in maximums.items():
        if tree[field] > maximum:
            raise SourceWorkerContractError(
                f"tree_policy {field} exceeds portable maximum {maximum}"
            )
    if tree["max_children_per_parent"] > tree["max_total_delegates"]:
        raise SourceWorkerContractError(
            "tree_policy max_children_per_parent exceeds total delegates"
        )
    if tree["max_parallel_delegates"] > tree["max_total_delegates"]:
        raise SourceWorkerContractError(
            "tree_policy max_parallel_delegates exceeds total delegates"
        )

    if not isinstance(stop, dict):
        raise SourceWorkerContractError("stop_policy must be an object")
    _require_exact_fields(
        stop,
        {"require_stop_reason", "evidence_saturation", "stop_reason_ids"},
        "stop_policy",
    )
    if stop.get("require_stop_reason") is not True:
        raise SourceWorkerContractError("stop_policy must require a stop reason")
    if stop.get("evidence_saturation") != (
        "stop-when-acceptance-and-required-evidence-are-covered"
    ):
        raise SourceWorkerContractError("stop_policy evidence_saturation is invalid")
    if set(_string_list(stop.get("stop_reason_ids"), label="stop reason IDs")) != STOP_REASON_IDS:
        raise SourceWorkerContractError("stop_policy stop_reason_ids are incomplete")


def _validate_execution_tree_contract(contract: Any) -> None:
    if not isinstance(contract, dict):
        raise SourceWorkerContractError("execution_tree_contract must be an object")
    _require_exact_fields(
        contract,
        {
            "schema_version",
            "tree_kind",
            "template_path",
            "required_budget_fields",
            "required_node_fields",
        },
        "execution_tree_contract",
    )
    if contract.get("schema_version") != EXECUTION_TREE_SCHEMA_VERSION:
        raise SourceWorkerContractError("execution tree contract schema_version is invalid")
    if contract.get("tree_kind") != TREE_KIND:
        raise SourceWorkerContractError("execution tree contract kind is invalid")
    if contract.get("template_path") != (
        "templates/target/.ai/assistant/templates/delegation-execution-tree.json"
    ):
        raise SourceWorkerContractError("execution tree template path is invalid")
    if set(
        _string_list(
            contract.get("required_budget_fields"),
            label="execution tree required_budget_fields",
        )
    ) != EXECUTION_TREE_BUDGET_FIELDS:
        raise SourceWorkerContractError("execution tree budget fields are incomplete")
    if set(
        _string_list(
            contract.get("required_node_fields"),
            label="execution tree required_node_fields",
        )
    ) != EXECUTION_TREE_NODE_FIELDS:
        raise SourceWorkerContractError("execution tree node fields are incomplete")


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
    tree_policy = policy.get("tree_policy")
    activation = policy.get("activation")
    _validate_tree_and_stop_policy(tree_policy, policy.get("stop_policy"))
    _validate_activation(activation)
    minimum_packets = activation["minimum_independent_packets"]
    for field in [
        "max_total_delegates",
        "max_parallel_delegates",
        "max_children_per_parent",
    ]:
        if tree_policy[field] < minimum_packets:
            raise SourceWorkerContractError(
                f"tree_policy {field} is below activation minimum packets"
            )
    _validate_decision_contract(policy.get("decision_evidence"))
    _validate_execution_tree_contract(policy.get("execution_tree_contract"))

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
            "child_proposal_policy",
            "result_requirement",
        },
        "worker_packet_contract",
    )
    if set(_string_list(packet_contract.get("required_fields"), label="packet required_fields")) != PACKET_FIELDS:
        raise SourceWorkerContractError("packet required_fields do not match schema v3")
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
    if packet_contract.get("child_proposal_policy") != "propose-only":
        raise SourceWorkerContractError(
            "worker packet child_proposal_policy must be propose-only"
        )
    if not _nonempty_string(packet_contract.get("result_requirement")):
        raise SourceWorkerContractError("worker packet result_requirement is invalid")

    workstreams = policy.get("workstreams")
    if not isinstance(workstreams, dict) or len(workstreams) < 2:
        raise SourceWorkerContractError("source worker policy requires bounded workstreams")
    independence_keys: set[str] = set()
    semantic_scopes: set[str] = set()
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
        semantic_scope = packet["semantic_scope"]
        if semantic_scope in semantic_scopes:
            raise SourceWorkerContractError(
                "source worker semantic_scope values must be unique"
            )
        semantic_scopes.add(semantic_scope)

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


def validate_delegation_execution_tree(
    tree: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Validate cumulative source delegation-tree evidence."""
    validate_source_worker_policy(policy)
    if not isinstance(tree, dict):
        raise SourceWorkerContractError("delegation execution tree must be an object")
    _require_exact_fields(tree, EXECUTION_TREE_FIELDS, "delegation execution tree")
    if tree.get("schema_version") != EXECUTION_TREE_SCHEMA_VERSION:
        raise SourceWorkerContractError("delegation execution tree schema_version is invalid")
    if tree.get("tree_kind") != TREE_KIND:
        raise SourceWorkerContractError("delegation execution tree kind is invalid")
    for field in [
        "operation_id",
        "base_revision",
        "task_profile",
        "policy_revision",
        "capability_evidence",
        "root_node_id",
    ]:
        if not _nonempty_string(tree.get(field)):
            raise SourceWorkerContractError(f"delegation execution tree has invalid {field}")
    if not isinstance(tree.get("current_user_authorization"), dict):
        raise SourceWorkerContractError(
            "delegation execution tree requires current_user_authorization"
        )

    budget = tree.get("aggregate_budget")
    if not isinstance(budget, dict):
        raise SourceWorkerContractError("delegation execution tree aggregate_budget must be an object")
    _require_exact_fields(budget, EXECUTION_TREE_BUDGET_FIELDS, "aggregate_budget")
    policy_tree = policy["tree_policy"]
    packet_contract = policy["worker_packet_contract"]
    _validate_budget_value(
        budget,
        "max_total_delegates",
        maximum=policy_tree["max_total_delegates"],
    )
    _validate_budget_value(
        budget,
        "max_children_per_parent",
        maximum=policy_tree["max_children_per_parent"],
    )
    _validate_budget_value(
        budget,
        "max_context_words_total",
        maximum=policy_tree["max_context_words_total"],
    )
    _validate_budget_value(
        budget,
        "max_retries_total",
        maximum=policy_tree["max_retries_total"],
        allow_zero=True,
    )
    _validate_budget_value(
        budget,
        "max_parallel_delegates",
        maximum=policy_tree["max_parallel_delegates"],
    )
    if budget["max_parallel_delegates"] > budget["max_total_delegates"]:
        raise SourceWorkerContractError(
            "aggregate_budget.max_parallel_delegates exceeds max_total_delegates"
        )
    if budget["max_children_per_parent"] > budget["max_total_delegates"]:
        raise SourceWorkerContractError(
            "aggregate_budget.max_children_per_parent exceeds max_total_delegates"
        )
    for used, maximum in [
        ("used_total_delegates", "max_total_delegates"),
        ("used_parallel_delegates", "max_parallel_delegates"),
        ("used_context_words", "max_context_words_total"),
        ("used_retries", "max_retries_total"),
    ]:
        used_value = _nonnegative_integer(budget.get(used), f"aggregate_budget.{used}")
        if used_value > budget[maximum]:
            raise SourceWorkerContractError(
                f"aggregate_budget.{used} exceeds {maximum}"
            )

    nodes = tree.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise SourceWorkerContractError("delegation execution tree nodes must be a non-empty list")
    node_by_id: dict[str, dict[str, Any]] = {}
    children_by_parent: dict[str, list[str]] = {}
    coverage_keys: set[str] = set()
    semantic_scopes: dict[str, str] = {}
    delegate_count = 0
    context_words = 0
    retries = 0
    for raw_node in nodes:
        node = _validate_execution_node(raw_node, policy_tree, packet_contract)
        node_id = node["node_id"]
        if node_id in node_by_id:
            raise SourceWorkerContractError(f"duplicate delegation node {node_id}")
        node_by_id[node_id] = node
        parent_id = node.get("parent_node_id")
        if parent_id is not None:
            children_by_parent.setdefault(parent_id, []).append(node_id)
            delegate_count += 1
        if node["depth"] > 0:
            coverage_key = node["coverage_key"]
            if coverage_key in coverage_keys:
                raise SourceWorkerContractError(
                    f"duplicate delegation coverage key {coverage_key}"
                )
            coverage_keys.add(coverage_key)
            semantic_scope = node["semantic_scope"]
            previous = semantic_scopes.get(semantic_scope)
            if previous is not None and node["overlap_decision"] != "primary-reconciled-overlap":
                raise SourceWorkerContractError(
                    f"semantic scope {semantic_scope} overlaps {previous} without primary reconciliation"
                )
            semantic_scopes[semantic_scope] = node_id
        context_words += node["context_words"]
        retries += node["attempt"]

    root_node_id = tree["root_node_id"]
    if root_node_id not in node_by_id:
        raise SourceWorkerContractError("delegation execution tree root node is missing")
    root_node = node_by_id[root_node_id]
    if root_node["parent_node_id"] is not None or root_node["depth"] != 0:
        raise SourceWorkerContractError("delegation execution tree root node is invalid")

    for node_id, node in node_by_id.items():
        parent_id = node.get("parent_node_id")
        if parent_id is not None:
            parent = node_by_id.get(parent_id)
            if parent is None:
                raise SourceWorkerContractError(f"delegation node {node_id} has missing parent")
            if node["depth"] != parent["depth"] + 1:
                raise SourceWorkerContractError(f"delegation node {node_id} has invalid depth")
    _reject_parent_cycles(root_node_id, node_by_id)

    for parent_id, child_ids in children_by_parent.items():
        if len(child_ids) > policy_tree["max_children_per_parent"]:
            raise SourceWorkerContractError(
                f"delegation node {parent_id} exceeds child budget"
            )

    parallel_width = _parallel_width(node_by_id)
    if delegate_count != budget["used_total_delegates"]:
        raise SourceWorkerContractError("aggregate delegate usage does not match nodes")
    if parallel_width != budget["used_parallel_delegates"]:
        raise SourceWorkerContractError(
            "aggregate parallel usage does not match tree width"
        )
    if context_words != budget["used_context_words"]:
        raise SourceWorkerContractError("aggregate context usage does not match nodes")
    if retries != budget["used_retries"]:
        raise SourceWorkerContractError("aggregate retry usage does not match nodes")

    _validate_execution_edges(tree.get("edges"), node_by_id)
    terminal_result_ids = {
        node["result_id"]
        for node in node_by_id.values()
        if node["status"] in TERMINAL_NODE_STATUSES
    }
    _validate_primary_convergence(tree.get("primary_convergence"), terminal_result_ids)
    return tree


def _validate_budget_value(
    budget: dict[str, Any],
    field: str,
    *,
    maximum: int,
    allow_zero: bool = False,
) -> int:
    minimum = 0 if allow_zero else 1
    value = budget.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise SourceWorkerContractError(
            f"aggregate_budget.{field} must be an integer >= {minimum}"
        )
    if value > maximum:
        raise SourceWorkerContractError(
            f"aggregate_budget.{field} exceeds policy maximum {maximum}"
        )
    return value


def _validate_execution_node(
    raw_node: Any,
    policy_tree: dict[str, Any],
    packet_contract: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(raw_node, dict):
        raise SourceWorkerContractError("delegation execution node must be an object")
    _require_exact_fields(raw_node, EXECUTION_TREE_NODE_FIELDS, "delegation execution node")
    for field in [
        "node_id",
        "role_id",
        "assistant_surface",
        "dispatch_backend",
        "implementation_level",
        "coverage_key",
        "semantic_scope",
        "write_scope",
    ]:
        if not _nonempty_string(raw_node.get(field)):
            raise SourceWorkerContractError(f"delegation execution node has invalid {field}")
    parent_node_id = raw_node.get("parent_node_id")
    if parent_node_id is not None and not _nonempty_string(parent_node_id):
        raise SourceWorkerContractError("delegation execution node parent_node_id is invalid")
    for field in ["packet_id", "result_id", "result_status", "stop_reason_id"]:
        value = raw_node.get(field)
        if value is not None and not _nonempty_string(value):
            raise SourceWorkerContractError(f"delegation execution node has invalid {field}")
    depth = _nonnegative_integer(raw_node.get("depth"), "delegation execution node.depth")
    if depth > policy_tree["hard_max_depth"]:
        raise SourceWorkerContractError("delegation execution node exceeds maximum depth")
    if depth > 0:
        if depth != 1:
            raise SourceWorkerContractError("source execution worker nodes must be depth 1")
        if raw_node.get("packet_id") is None:
            raise SourceWorkerContractError("source execution worker node requires a packet_id")
        if raw_node.get("role_id") != packet_contract["role_id"]:
            raise SourceWorkerContractError("source execution worker node role violates packet contract")
        if raw_node.get("allowed_actions") != packet_contract["allowed_actions"]:
            raise SourceWorkerContractError("source execution worker node must be inspect-only")
        if raw_node.get("write_scope") != packet_contract["write_scope"]:
            raise SourceWorkerContractError("source execution worker node must have no write scope")
    status = raw_node.get("status")
    if status not in NODE_STATUSES:
        raise SourceWorkerContractError("delegation execution node status is invalid")
    if status in TERMINAL_NODE_STATUSES:
        if raw_node.get("stop_reason_id") not in STOP_REASON_IDS:
            raise SourceWorkerContractError("terminal delegation node requires a stop reason")
        expected_result_status = RESULT_STATUS_BY_NODE_STATUS[status]
        if raw_node.get("result_id") is None:
            raise SourceWorkerContractError("terminal delegation node requires a result_id")
        if raw_node.get("result_status") != expected_result_status:
            raise SourceWorkerContractError(
                "terminal delegation node result_status does not match status"
            )
    elif (
        raw_node.get("result_id") is not None
        or raw_node.get("result_status") is not None
        or raw_node.get("stop_reason_id") is not None
    ):
        raise SourceWorkerContractError(
            "non-terminal delegation node must not claim result or stop evidence"
        )
    _string_list(
        raw_node.get("changed_fact_ids"),
        label="delegation execution node.changed_fact_ids",
        nonempty=False,
    )
    _string_list(
        raw_node.get("canonical_owner_refs"),
        label="delegation execution node.canonical_owner_refs",
    )
    _string_list(raw_node.get("surface_refs"), label="delegation execution node.surface_refs")
    _string_list(
        raw_node.get("relationship_refs"),
        label="delegation execution node.relationship_refs",
        nonempty=False,
    )
    _string_list(raw_node.get("allowed_actions"), label="delegation execution node.allowed_actions")
    child_proposals = raw_node.get("child_proposals")
    if not isinstance(child_proposals, list):
        raise SourceWorkerContractError("delegation execution node child_proposals must be a list")
    context_words = _nonnegative_integer(
        raw_node.get("context_words"), "delegation execution node.context_words"
    )
    attempt = _nonnegative_integer(
        raw_node.get("attempt"), "delegation execution node.attempt"
    )
    if raw_node.get("overlap_decision") not in OVERLAP_DECISIONS:
        raise SourceWorkerContractError("delegation execution node overlap_decision is invalid")
    raw_node["depth"] = depth
    raw_node["context_words"] = context_words
    raw_node["attempt"] = attempt
    return raw_node


def _parallel_width(node_by_id: dict[str, dict[str, Any]]) -> int:
    width_by_depth: dict[int, int] = {}
    for node in node_by_id.values():
        if node["parent_node_id"] is None:
            continue
        depth = node["depth"]
        width_by_depth[depth] = width_by_depth.get(depth, 0) + 1
    return max(width_by_depth.values(), default=0)


def _reject_parent_cycles(
    root_node_id: str,
    node_by_id: dict[str, dict[str, Any]],
) -> None:
    for node_id in node_by_id:
        seen: set[str] = set()
        current = node_id
        while current is not None:
            if current in seen:
                raise SourceWorkerContractError("delegation execution tree contains a cycle")
            seen.add(current)
            parent = node_by_id[current]["parent_node_id"]
            current = parent
        if root_node_id not in seen:
            raise SourceWorkerContractError(
                f"delegation node {node_id} is not connected to the root"
            )


def _validate_execution_edges(
    edges: Any,
    node_by_id: dict[str, dict[str, Any]],
) -> None:
    if not isinstance(edges, list):
        raise SourceWorkerContractError("delegation execution tree edges must be a list")
    expected_edges = {
        (node["parent_node_id"], node_id)
        for node_id, node in node_by_id.items()
        if node["parent_node_id"] is not None
    }
    if len(edges) != len(expected_edges):
        raise SourceWorkerContractError(
            "delegation execution tree must contain one edge per non-root node"
        )
    seen_edges: set[tuple[str, str]] = set()
    seen_children: set[str] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            raise SourceWorkerContractError("delegation execution edge must be an object")
        _require_exact_fields(edge, EXECUTION_TREE_EDGE_FIELDS, "delegation execution edge")
        parent = edge.get("parent_node_id")
        child = edge.get("child_node_id")
        if (parent, child) in seen_edges or child in seen_children:
            raise SourceWorkerContractError("duplicate delegation execution edge")
        seen_edges.add((parent, child))
        seen_children.add(child)
        if parent not in node_by_id or child not in node_by_id:
            raise SourceWorkerContractError("delegation execution edge references missing node")
        if node_by_id[child].get("parent_node_id") != parent:
            raise SourceWorkerContractError("delegation execution edge disagrees with child parent")
        if edge.get("edge_kind") != "primary-approved-dispatch":
            raise SourceWorkerContractError("delegation execution edge kind is invalid")
    if seen_edges != expected_edges:
        raise SourceWorkerContractError(
            "delegation execution edges do not match tree topology"
        )


def _validate_primary_convergence(
    convergence: Any,
    terminal_result_ids: set[str],
) -> None:
    if not isinstance(convergence, dict):
        raise SourceWorkerContractError("primary_convergence must be an object")
    _require_exact_fields(
        convergence,
        EXECUTION_TREE_CONVERGENCE_FIELDS,
        "primary_convergence",
    )
    if convergence.get("status") not in {
        "pending",
        "completed",
        "blocked",
        "cancelled",
    }:
        raise SourceWorkerContractError("primary_convergence status is invalid")
    reviewed_result_ids = set(_string_list(
        convergence.get("reviewed_result_ids"),
        label="primary_convergence.reviewed_result_ids",
        nonempty=False,
    ))
    rejected_result_ids = set(_string_list(
        convergence.get("rejected_result_ids"),
        label="primary_convergence.rejected_result_ids",
        nonempty=False,
    ))
    unknown_reviewed = reviewed_result_ids - terminal_result_ids
    if unknown_reviewed:
        raise SourceWorkerContractError(
            "primary_convergence reviewed unknown result IDs"
        )
    unknown_rejected = rejected_result_ids - terminal_result_ids
    if unknown_rejected:
        raise SourceWorkerContractError(
            "primary_convergence rejected unknown result IDs"
        )
    if rejected_result_ids - reviewed_result_ids:
        raise SourceWorkerContractError(
            "primary_convergence rejected results must also be reviewed"
        )
    if (
        convergence.get("status") == "completed"
        and reviewed_result_ids != terminal_result_ids
    ):
        raise SourceWorkerContractError(
            "completed primary_convergence must review every terminal result"
        )
    for field in ["combined_validation", "logical_integrity_review", "residual_risk"]:
        if not _nonempty_string(convergence.get(field)):
            raise SourceWorkerContractError(f"primary_convergence has invalid {field}")
    final_stop = convergence.get("final_stop_reason_id")
    if final_stop is not None and final_stop not in STOP_REASON_IDS:
        raise SourceWorkerContractError("primary_convergence final stop reason is invalid")
    if convergence.get("status") != "pending" and final_stop is None:
        raise SourceWorkerContractError(
            "terminal primary_convergence requires a final stop reason"
        )


def make_builtin_packet(policy: dict[str, Any], workstream_id: str) -> dict[str, Any]:
    """Project one policy workstream into the common packet contract."""
    workstream = policy.get("workstreams", {}).get(workstream_id)
    if not isinstance(workstream, dict):
        raise SourceWorkerContractError(f"unknown source workstream: {workstream_id}")
    contract = policy["worker_packet_contract"]
    return {
        "schema_version": contract["schema_version"],
        "packet_kind": contract["packet_kinds"][0],
        "parent_packet_id": None,
        "depth": 1,
        "remaining_worker_budget": max(
            policy["tree_policy"]["max_total_delegates"] - 1, 0
        ),
        "coverage_key": workstream.get("independence_key"),
        "child_proposal_policy": contract["child_proposal_policy"],
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
        "semantic_scope": workstream.get("semantic_scope"),
        "changed_fact_ids": workstream.get("changed_fact_ids"),
        "canonical_owner_refs": workstream.get("canonical_owner_refs"),
        "surface_refs": workstream.get("surface_refs"),
        "relationship_refs": workstream.get("relationship_refs"),
        "overlap_decision": workstream.get("overlap_decision"),
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
