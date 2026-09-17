#!/usr/bin/env python3
"""Parse and validate the AlatyrCore source worker contract."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


POLICY_SCHEMA_VERSION = 7
CAPABILITY_SCHEMA_VERSION = 2
PACKET_SCHEMA_VERSION = 6
EXECUTION_TREE_SCHEMA_VERSION = 3
POLICY_KIND = "alatyr-source-worker-policy"
CANONICAL_RULE = "ALATYR-DELEGATION-001"
TREE_KIND = "alatyr-delegation-execution-tree"
MAX_TOTAL_DELEGATES = 8
MAX_CHILDREN_PER_PARENT = 4
MAX_CONTEXT_WORDS_TOTAL = 24000
MAX_RESULT_WORDS_TOTAL = 12000
MAX_PRIMARY_SUMMARY_WORDS_TOTAL = 4000
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
    "child_dispatch_mode",
    "branch_envelope_sha256",
    "workstream_id",
    "role_id",
    "objective",
    "bounded_context",
    "max_initial_words",
    "max_result_words",
    "max_summary_words",
    "parent_context_packet_sha256",
    "context_delta",
    "conditional_context",
    "non_goals",
    "allowed_actions",
    "write_scope",
    "independent",
    "independence_key",
    "semantic_scope",
    "changed_fact_ids",
    "proof_obligation_ids",
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
    "recorded_at",
    "base_revision",
    "current_user_authorization",
    "task_profile",
    "analysis_strategy_id",
    "problem_model_sha256",
    "policy_revision",
    "capability_evidence",
    "capability_evidence_sha256",
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
    "max_result_words_total",
    "max_primary_summary_words_total",
    "max_retries_total",
    "used_total_delegates",
    "used_parallel_delegates",
    "used_context_words",
    "used_result_words",
    "used_primary_summary_words",
    "used_retries",
}
EXECUTION_TREE_NODE_FIELDS = {
    "node_id",
    "parent_node_id",
    "packet_id",
    "parent_packet_id",
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
    "proof_obligation_ids",
    "canonical_owner_refs",
    "surface_refs",
    "relationship_refs",
    "allowed_actions",
    "write_scope",
    "context_evidence",
    "context_words",
    "max_result_words",
    "max_summary_words",
    "dispatch_group_id",
    "branch_envelope",
    "branch_envelope_sha256",
    "branch_checkpoint",
    "branch_checkpoint_sha256",
    "result_evidence",
    "accepted_summary_evidence",
    "summary_covers_result_ids",
    "satisfied_acceptance_ids",
    "satisfied_proof_obligation_ids",
    "produced_evidence_ids",
    "attempt",
    "result_status",
    "stop_reason_id",
    "child_proposals",
    "overlap_decision",
}
EXECUTION_TREE_CONVERGENCE_FIELDS = {
    "status",
    "required_acceptance_ids",
    "required_evidence_ids",
    "required_proof_obligation_ids",
    "satisfied_proof_obligation_ids",
    "reviewed_result_ids",
    "indirect_result_ids",
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
    "context_compaction",
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
    "result-budget-reached",
    "primary-context-budget-reached",
    "checkpoint-required",
    "checkpoint-invalid",
    "context-digest-stale",
    "evidence-digest-mismatch",
    "branch-envelope-violation",
    "validation-regression",
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
    "max_initial_words",
    "max_result_words",
    "max_summary_words",
    "conditional_context",
    "non_goals",
    "semantic_scope",
    "changed_fact_ids",
    "proof_obligation_ids",
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
        raise SourceWorkerContractError("packet required_fields do not match schema v6")
    _require_exact_fields(packet, required, "worker packet")
    if packet.get("schema_version") != PACKET_SCHEMA_VERSION:
        raise SourceWorkerContractError("worker packet schema_version is invalid")
    if packet.get("packet_kind") not in contract["packet_kinds"]:
        raise SourceWorkerContractError("worker packet_kind is invalid")
    parent_packet_id = packet.get("parent_packet_id")
    if parent_packet_id is not None and not _nonempty_string(parent_packet_id):
        raise SourceWorkerContractError("worker packet parent_packet_id is invalid")
    depth = packet.get("depth")
    if not isinstance(depth, int) or isinstance(depth, bool) or depth not in {1, 2}:
        raise SourceWorkerContractError("source worker packet depth must be 1 or 2")
    if depth == 1 and parent_packet_id is not None:
        raise SourceWorkerContractError("depth-1 source packet cannot have a parent packet")
    if depth == 2 and parent_packet_id is None:
        raise SourceWorkerContractError("depth-2 source packet requires a parent packet")
    remaining = packet.get("remaining_worker_budget")
    if not isinstance(remaining, int) or isinstance(remaining, bool) or remaining < 0:
        raise SourceWorkerContractError(
            "worker packet remaining_worker_budget must be non-negative"
        )
    if not _nonempty_string(packet.get("coverage_key")):
        raise SourceWorkerContractError("worker packet coverage_key is invalid")
    child_mode = packet.get("child_dispatch_mode")
    if child_mode not in contract["child_dispatch_modes"]:
        raise SourceWorkerContractError("worker packet child_dispatch_mode is invalid")
    envelope_sha = packet.get("branch_envelope_sha256")
    if child_mode == "primary-preauthorized-read-only" or depth == 2:
        if not isinstance(envelope_sha, str) or len(envelope_sha) != 64 or any(
            character not in "0123456789abcdef" for character in envelope_sha
        ):
            raise SourceWorkerContractError(
                "recursive worker packet requires a lowercase branch envelope SHA-256"
            )
    elif envelope_sha is not None:
        raise SourceWorkerContractError(
            "non-recursive worker packet must not claim a branch envelope"
        )
    if depth == 2 and child_mode != "none":
        raise SourceWorkerContractError("depth-2 source packet cannot dispatch children")
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
        packet.get("proof_obligation_ids"),
        label="worker packet proof_obligation_ids",
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
    max_initial_words = _positive_integer(
        packet.get("max_initial_words"), "worker packet max_initial_words"
    )
    _positive_integer(packet.get("max_result_words"), "worker packet max_result_words")
    max_summary_words = _positive_integer(
        packet.get("max_summary_words"), "worker packet max_summary_words"
    )
    if max_summary_words > packet["max_result_words"]:
        raise SourceWorkerContractError(
            "worker packet max_summary_words exceeds max_result_words"
        )
    context_digest = packet.get("parent_context_packet_sha256")
    if context_digest is not None and (
        not isinstance(context_digest, str)
        or len(context_digest) != 64
        or any(character not in "0123456789abcdef" for character in context_digest)
    ):
        raise SourceWorkerContractError(
            "worker packet parent_context_packet_sha256 is invalid"
        )
    context_delta = packet.get("context_delta")
    if not isinstance(context_delta, dict) or set(context_delta) != {"add", "remove"}:
        raise SourceWorkerContractError("worker packet context_delta is invalid")
    _string_list(context_delta["add"], label="worker packet context_delta.add", nonempty=False)
    _string_list(context_delta["remove"], label="worker packet context_delta.remove", nonempty=False)
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
        initial_words = sum(
            len((root / path).read_text(encoding="utf-8").split())
            for path in bounded_paths
        )
        if initial_words > max_initial_words:
            raise SourceWorkerContractError(
                "worker packet bounded context exceeds max_initial_words: "
                f"{initial_words} > {max_initial_words}"
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
        "worker_child_behavior": "primary-preauthorized-read-only",
        "default_max_depth": 1,
        "hard_max_depth": 2,
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
        "stop-when-acceptance-required-evidence-and-assigned-proof-obligations-are-covered"
    ):
        raise SourceWorkerContractError("stop_policy evidence_saturation is invalid")
    if set(_string_list(stop.get("stop_reason_ids"), label="stop reason IDs")) != STOP_REASON_IDS:
        raise SourceWorkerContractError("stop_policy stop_reason_ids are incomplete")


def _validate_context_compaction(contract: Any) -> None:
    if not isinstance(contract, dict):
        raise SourceWorkerContractError("context_compaction must be an object")
    expected = {
        "mode": "hierarchical-summary",
        "raw_result_loading": "reference-only-unless-review-triggered",
        "summary_propagation": "accepted-summary-only",
        "digest_algorithm": "sha256",
        "require_measured_result_artifacts": True,
        "deduplicate_inherited_context": True,
        "max_result_words_total": MAX_RESULT_WORDS_TOTAL,
        "max_primary_summary_words_total": MAX_PRIMARY_SUMMARY_WORDS_TOTAL,
    }
    _require_exact_fields(contract, set(expected), "context_compaction")
    for field, value in expected.items():
        if contract.get(field) != value:
            raise SourceWorkerContractError(
                f"context_compaction requires {field}={value!r}"
            )


def _validate_execution_tree_contract(contract: Any) -> None:
    if not isinstance(contract, dict):
        raise SourceWorkerContractError("execution_tree_contract must be an object")
    _require_exact_fields(
        contract,
        {
            "schema_version",
            "tree_kind",
            "template_path",
            "required_tree_fields",
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
            contract.get("required_tree_fields"),
            label="execution tree required_tree_fields",
        )
    ) != EXECUTION_TREE_FIELDS:
        raise SourceWorkerContractError(
            "execution tree required_tree_fields are incomplete"
        )
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
    context_compaction = policy.get("context_compaction")
    _validate_context_compaction(context_compaction)
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
            "child_dispatch_modes",
            "result_requirement",
        },
        "worker_packet_contract",
    )
    if set(_string_list(packet_contract.get("required_fields"), label="packet required_fields")) != PACKET_FIELDS:
        raise SourceWorkerContractError("packet required_fields do not match schema v6")
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
    if packet_contract.get("child_dispatch_modes") != [
        "none",
        "propose-only",
        "primary-preauthorized-read-only",
    ]:
        raise SourceWorkerContractError("worker packet child dispatch modes are invalid")
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
        if workstream["max_initial_words"] > tree_policy["max_context_words_total"]:
            raise SourceWorkerContractError(
                f"source worker workstream {workstream_id} initial budget exceeds "
                "the aggregate context budget"
            )
        if workstream["max_result_words"] > context_compaction["max_result_words_total"]:
            raise SourceWorkerContractError(
                f"source worker workstream {workstream_id} result budget exceeds "
                "the aggregate result budget"
            )
        if workstream["max_summary_words"] > context_compaction[
            "max_primary_summary_words_total"
        ]:
            raise SourceWorkerContractError(
                f"source worker workstream {workstream_id} summary budget exceeds "
                "the aggregate primary-summary budget"
            )
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
    *,
    artifact_root: Path,
) -> dict[str, Any]:
    """Validate measured source delegation evidence through the shared contract."""
    from delegation_evidence import (
        DelegationEvidenceError,
        validate_execution_tree,
    )

    validate_source_worker_policy(policy)
    try:
        return validate_execution_tree(tree, policy, artifact_root=artifact_root)
    except DelegationEvidenceError as exc:
        raise SourceWorkerContractError(str(exc)) from exc


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
        "child_dispatch_mode": "propose-only",
        "branch_envelope_sha256": None,
        "workstream_id": workstream_id,
        "role_id": contract["role_id"],
        "objective": workstream.get("objective"),
        "bounded_context": workstream.get("required_context"),
        "max_initial_words": workstream.get("max_initial_words"),
        "max_result_words": workstream.get("max_result_words"),
        "max_summary_words": workstream.get("max_summary_words"),
        "parent_context_packet_sha256": None,
        "context_delta": {"add": [], "remove": []},
        "conditional_context": workstream.get("conditional_context"),
        "non_goals": workstream.get("non_goals"),
        "allowed_actions": contract["allowed_actions"],
        "write_scope": contract["write_scope"],
        "independent": workstream.get("independent"),
        "independence_key": workstream.get("independence_key"),
        "semantic_scope": workstream.get("semantic_scope"),
        "changed_fact_ids": workstream.get("changed_fact_ids"),
        "proof_obligation_ids": workstream.get("proof_obligation_ids"),
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
