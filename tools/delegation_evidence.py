#!/usr/bin/env python3
"""Validate measured, hash-bound delegation execution evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any


TREE_FIELDS = {
    "schema_version", "tree_kind", "operation_id", "recorded_at", "base_revision",
    "current_user_authorization", "task_profile", "policy_revision",
    "analysis_strategy_id", "problem_model_sha256",
    "capability_evidence", "capability_evidence_sha256", "aggregate_budget",
    "root_node_id", "nodes", "edges", "primary_convergence",
}
BUDGET_FIELDS = {
    "max_total_delegates", "max_parallel_delegates",
    "max_children_per_parent", "max_context_words_total",
    "max_result_words_total", "max_primary_summary_words_total",
    "max_retries_total", "used_total_delegates", "used_parallel_delegates",
    "used_context_words", "used_result_words", "used_primary_summary_words",
    "used_retries",
}
NODE_FIELDS = {
    "node_id", "parent_node_id", "packet_id", "parent_packet_id", "result_id",
    "depth", "status", "role_id", "assistant_surface", "dispatch_backend",
    "implementation_level", "coverage_key", "semantic_scope",
    "changed_fact_ids", "canonical_owner_refs", "surface_refs",
    "relationship_refs", "allowed_actions", "write_scope", "context_evidence",
    "context_words",
    "max_result_words", "max_summary_words", "dispatch_group_id",
    "branch_envelope", "branch_envelope_sha256", "result_evidence",
    "branch_checkpoint", "branch_checkpoint_sha256",
    "accepted_summary_evidence", "summary_covers_result_ids",
    "satisfied_acceptance_ids", "proof_obligation_ids",
    "satisfied_proof_obligation_ids", "produced_evidence_ids", "attempt",
    "result_status", "stop_reason_id", "child_proposals", "overlap_decision",
}
CONVERGENCE_FIELDS = {
    "status", "required_acceptance_ids", "required_evidence_ids",
    "required_proof_obligation_ids", "satisfied_proof_obligation_ids",
    "reviewed_result_ids", "indirect_result_ids", "rejected_result_ids",
    "combined_validation", "logical_integrity_review", "residual_risk",
    "final_stop_reason_id",
}
ARTIFACT_FIELDS = {"path", "word_count", "character_count", "sha256"}
TERMINAL_STATUSES = {
    "BLOCKED", "REVIEW_REQUIRED", "DONE", "FAILED", "CANCELLED", "REJECTED"
}
NODE_STATUSES = TERMINAL_STATUSES | {"PLANNED", "READY", "RUNNING"}
RESULT_STATUS_BY_NODE = {
    "BLOCKED": "blocked", "REVIEW_REQUIRED": "requires-review",
    "DONE": "succeeded", "FAILED": "failed", "CANCELLED": "cancelled",
    "REJECTED": "rejected",
}
EDGE_KINDS = {"primary-approved-dispatch", "primary-envelope-dispatch"}
SHA256_LENGTH = 64
PORTABLE_MAX_DEPTH = 2
PORTABLE_MAX_DELEGATES = 8
PORTABLE_MAX_CHILDREN = 4
PORTABLE_MAX_CONTEXT_WORDS = 24000
PORTABLE_MAX_RESULT_WORDS = 12000
PORTABLE_MAX_PRIMARY_SUMMARY_WORDS = 4000
PORTABLE_MAX_RETRIES = 2
PRIMARY_ANALYSIS_STRATEGIES = {
    "direct-local",
    "invariant-first",
    "hypothesis-driven",
    "architecture-comparison",
    "evidence-synthesis",
    "exploratory-design",
}


class DelegationEvidenceError(ValueError):
    """Raised when delegation evidence violates its portable contract."""


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DelegationEvidenceError(f"{label} must be an object")
    return value


def _exact(value: dict[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(fields - set(value))
    extra = sorted(set(value) - fields)
    if missing or extra:
        raise DelegationEvidenceError(
            f"{label} fields differ: missing={missing}, unexpected={extra}"
        )


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DelegationEvidenceError(f"{label} must be a non-empty string")
    return value


def _strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise DelegationEvidenceError(f"{label} must be a string list")
    if len(value) != len(set(value)):
        raise DelegationEvidenceError(f"{label} must not contain duplicates")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0, maximum: int) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < minimum
        or value > maximum
    ):
        raise DelegationEvidenceError(
            f"{label} must be an integer from {minimum} through {maximum}"
        )
    return value


def _sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != SHA256_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DelegationEvidenceError(f"{label} must be a lowercase SHA-256")
    return value


def _timestamp(value: Any, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(_string(value, label).replace("Z", "+00:00"))
    except ValueError as exc:
        raise DelegationEvidenceError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DelegationEvidenceError(f"{label} needs a timezone")
    return parsed.astimezone(timezone.utc)


def _canonical_sha256(value: dict[str, Any], excluded_field: str) -> str:
    payload = {key: item for key, item in value.items() if key != excluded_field}
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _matches_surface(surface: str, selectors: list[str]) -> bool:
    """Match one normalized target-relative surface against envelope selectors."""
    if surface.startswith("/") or "\\" in surface or ".." in PurePosixPath(surface).parts:
        return False
    return any(fnmatchcase(surface, selector) for selector in selectors)


def _contained_file(root: Path, relpath: Any, label: str) -> Path:
    raw = _string(relpath, label)
    posix = PurePosixPath(raw)
    if posix.is_absolute() or ".." in posix.parts or "\\" in raw:
        raise DelegationEvidenceError(f"{label} must be a target-relative path")
    candidate = root.joinpath(*posix.parts)
    try:
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise DelegationEvidenceError(f"{label} is not readable: {raw}") from exc
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise DelegationEvidenceError(
            f"{label} escapes its artifact root: {raw}"
        ) from exc
    if not resolved.is_file():
        raise DelegationEvidenceError(f"{label} escapes its artifact root: {raw}")
    return resolved


def _measure_file(path: Path, label: str) -> tuple[str, int, int]:
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DelegationEvidenceError(f"{label} must be UTF-8 text") from exc
    return digest, len(text.split()), len(text)


def validate_artifact(
    value: Any,
    *,
    artifact_root: Path,
    label: str,
) -> dict[str, Any]:
    artifact = _object(value, label)
    _exact(artifact, ARTIFACT_FIELDS, label)
    path = _contained_file(artifact_root, artifact.get("path"), f"{label}.path")
    digest, words, characters = _measure_file(path, label)
    if _sha256(artifact.get("sha256"), f"{label}.sha256") != digest:
        raise DelegationEvidenceError(f"{label} SHA-256 does not match content")
    if artifact.get("word_count") != words:
        raise DelegationEvidenceError(f"{label} word_count does not match content")
    if artifact.get("character_count") != characters:
        raise DelegationEvidenceError(
            f"{label} character_count does not match content"
        )
    return artifact


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        return _object(json.loads(path.read_text(encoding="utf-8")), label)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DelegationEvidenceError(f"cannot load {label}: {path}: {exc}") from exc


def validate_branch_envelope(
    path: Path,
    *,
    expected_sha256: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    envelope = load_json_object(path, "branch envelope")
    required = {
        "schema_version", "envelope_kind", "envelope_id", "operation_id",
        "root_packet_id", "parent_node_id", "issued_by", "base_revision",
        "authorized_phases", "max_depth", "max_children", "max_context_words",
        "max_result_words", "max_summary_words", "max_retries",
        "allowed_actions", "write_scope", "allowed_tools", "allowed_surface_refs",
        "semantic_scope", "coverage_prefix", "context_packet_sha256",
        "proof_obligation_ids",
        "capability_evidence_sha256", "required_validation", "expires_at",
        "envelope_sha256",
    }
    _exact(envelope, required, "branch envelope")
    if envelope.get("schema_version") != 2 or envelope.get("envelope_kind") != (
        "alatyr-delegation-branch-envelope"
    ):
        raise DelegationEvidenceError("branch envelope identity is invalid")
    for field in [
        "envelope_id", "operation_id", "root_packet_id", "parent_node_id",
        "base_revision", "semantic_scope", "coverage_prefix",
    ]:
        _string(envelope.get(field), f"branch envelope.{field}")
    if envelope.get("issued_by") != "primary-assistant":
        raise DelegationEvidenceError("branch envelope must be primary-issued")
    if envelope.get("authorized_phases") != ["inspect"]:
        raise DelegationEvidenceError("branch envelope phases must be inspect-only")
    if envelope.get("allowed_actions") != ["inspect"] or envelope.get("write_scope") != "none":
        raise DelegationEvidenceError("branch envelope must be read-only")
    if envelope.get("max_depth") != 2:
        raise DelegationEvidenceError("branch envelope max_depth must be 2")
    _integer(envelope.get("max_children"), "branch envelope.max_children", minimum=1, maximum=PORTABLE_MAX_CHILDREN)
    _integer(envelope.get("max_context_words"), "branch envelope.max_context_words", minimum=1, maximum=PORTABLE_MAX_CONTEXT_WORDS)
    max_result_words = _integer(envelope.get("max_result_words"), "branch envelope.max_result_words", minimum=1, maximum=PORTABLE_MAX_RESULT_WORDS)
    max_summary_words = _integer(envelope.get("max_summary_words"), "branch envelope.max_summary_words", minimum=1, maximum=PORTABLE_MAX_PRIMARY_SUMMARY_WORDS)
    if max_summary_words > max_result_words:
        raise DelegationEvidenceError(
            "branch envelope summary budget exceeds its result budget"
        )
    _integer(envelope.get("max_retries"), "branch envelope.max_retries", maximum=PORTABLE_MAX_RETRIES)
    allowed_tools = _strings(
        envelope.get("allowed_tools"), "branch envelope.allowed_tools"
    )
    allowed_surfaces = _strings(
        envelope.get("allowed_surface_refs"),
        "branch envelope.allowed_surface_refs",
    )
    required_validation = _strings(
        envelope.get("required_validation"),
        "branch envelope.required_validation",
    )
    _strings(
        envelope.get("proof_obligation_ids"),
        "branch envelope.proof_obligation_ids",
    )
    if not allowed_tools or not allowed_surfaces or not required_validation:
        raise DelegationEvidenceError(
            "branch envelope tools, surfaces, and validation must be non-empty"
        )
    for selector in allowed_surfaces:
        selector_path = PurePosixPath(selector)
        if selector_path.is_absolute() or ".." in selector_path.parts or "\\" in selector:
            raise DelegationEvidenceError(
                "branch envelope surface selectors must be target-relative"
            )
    optional_context = envelope.get("context_packet_sha256")
    if optional_context is not None:
        _sha256(optional_context, "branch envelope.context_packet_sha256")
    _sha256(envelope.get("capability_evidence_sha256"), "branch envelope.capability_evidence_sha256")
    actual_digest = _canonical_sha256(envelope, "envelope_sha256")
    declared_digest = _sha256(envelope.get("envelope_sha256"), "branch envelope.envelope_sha256")
    if actual_digest != declared_digest or (
        expected_sha256 is not None and declared_digest != expected_sha256
    ):
        raise DelegationEvidenceError("branch envelope digest is invalid")
    expires = _timestamp(envelope.get("expires_at"), "branch envelope.expires_at")
    if now is not None and expires <= now.astimezone(timezone.utc):
        raise DelegationEvidenceError("branch envelope is expired")
    return envelope


def validate_branch_checkpoint(
    path: Path,
    *,
    artifact_root: Path,
    expected_sha256: str,
    envelope: dict[str, Any],
    node: dict[str, Any],
    allowed_stop_reasons: set[str],
) -> dict[str, Any]:
    checkpoint = load_json_object(path, "branch checkpoint")
    fields = {
        "schema_version", "checkpoint_kind", "checkpoint_id",
        "previous_checkpoint_id", "operation_id", "node_id",
        "branch_envelope_sha256", "base_revision", "accepted_result_ids",
        "accepted_result_sha256", "rejected_result_ids",
        "completed_coverage_keys", "accepted_summary", "context_packet_sha256",
        "completed_proof_obligation_ids", "open_proof_obligation_ids",
        "semantic_guidance_sha256", "evidence_manifest_sha256",
        "validation_sha256", "unresolved_escalations", "next_ready_action",
        "stop_reason_id", "checkpoint_sha256",
    }
    _exact(checkpoint, fields, "branch checkpoint")
    if checkpoint.get("schema_version") != 2 or checkpoint.get("checkpoint_kind") != (
        "alatyr-delegation-branch-checkpoint"
    ):
        raise DelegationEvidenceError("branch checkpoint identity is invalid")
    previous_checkpoint_id = checkpoint.get("previous_checkpoint_id")
    if previous_checkpoint_id is not None:
        _string(
            previous_checkpoint_id,
            "branch checkpoint.previous_checkpoint_id",
        )
    if checkpoint.get("operation_id") != envelope["operation_id"] or checkpoint.get("node_id") != node["node_id"]:
        raise DelegationEvidenceError("branch checkpoint identity disagrees with its branch")
    if checkpoint.get("base_revision") != envelope["base_revision"]:
        raise DelegationEvidenceError("branch checkpoint base_revision is stale")
    if checkpoint.get("branch_envelope_sha256") != envelope["envelope_sha256"]:
        raise DelegationEvidenceError("branch checkpoint envelope digest is stale")
    actual = _canonical_sha256(checkpoint, "checkpoint_sha256")
    declared = _sha256(checkpoint.get("checkpoint_sha256"), "branch checkpoint.checkpoint_sha256")
    if declared != actual or declared != expected_sha256:
        raise DelegationEvidenceError("branch checkpoint digest is invalid")
    validate_artifact(
        checkpoint.get("accepted_summary"),
        artifact_root=artifact_root,
        label="branch checkpoint accepted_summary",
    )
    for field in [
        "accepted_result_ids", "rejected_result_ids", "completed_coverage_keys",
        "completed_proof_obligation_ids", "open_proof_obligation_ids",
        "unresolved_escalations",
    ]:
        _strings(checkpoint.get(field), f"branch checkpoint.{field}")
    completed_obligations = set(checkpoint["completed_proof_obligation_ids"])
    open_obligations = set(checkpoint["open_proof_obligation_ids"])
    assigned_obligations = set(envelope["proof_obligation_ids"])
    if completed_obligations & open_obligations or (
        completed_obligations | open_obligations
    ) != assigned_obligations:
        raise DelegationEvidenceError(
            "branch checkpoint must partition its assigned proof obligations"
        )
    for field in ["accepted_result_sha256"]:
        for index, digest in enumerate(_strings(checkpoint.get(field), f"branch checkpoint.{field}")):
            _sha256(digest, f"branch checkpoint.{field}[{index}]")
    for field in ["branch_envelope_sha256", "evidence_manifest_sha256", "validation_sha256"]:
        _sha256(checkpoint.get(field), f"branch checkpoint.{field}")
    for field in ["context_packet_sha256", "semantic_guidance_sha256"]:
        value = checkpoint.get(field)
        if value is not None:
            _sha256(value, f"branch checkpoint.{field}")
    _string(checkpoint.get("next_ready_action"), "branch checkpoint.next_ready_action")
    stop_reason = _string(
        checkpoint.get("stop_reason_id"), "branch checkpoint.stop_reason_id"
    )
    if stop_reason not in allowed_stop_reasons:
        raise DelegationEvidenceError("branch checkpoint stop_reason_id is unknown")
    return checkpoint


def validate_worker_result(
    path: Path,
    *,
    artifact_root: Path,
    node: dict[str, Any],
    expected_base_revision: str,
    allowed_stop_reasons: set[str],
) -> tuple[dict[str, Any], int, int]:
    result = load_json_object(path, "worker result")
    fields = {
        "schema_version", "result_kind", "result_id", "packet_id",
        "parent_packet_id", "node_id", "depth", "base_revision", "status",
    "measurement_state", "input_context_packet_sha256", "raw_payload",
        "accepted_summary", "summary_covers_result_ids", "child_result_sha256",
        "evidence_manifest", "touched_surfaces", "tools_used", "scope_violation",
        "authorization_concern", "proof_obligation_ids",
        "satisfied_proof_obligation_ids", "validation", "stop_reason_id",
        "subtree_sha256",
    }
    _exact(result, fields, "worker result")
    if result.get("schema_version") != 2 or result.get("result_kind") != (
        "alatyr-normalized-worker-result"
    ):
        raise DelegationEvidenceError("worker result identity is invalid")
    comparisons = {
        "result_id": "result_id", "packet_id": "packet_id",
        "parent_packet_id": "parent_packet_id", "node_id": "node_id",
        "depth": "depth",
        "status": "result_status", "stop_reason_id": "stop_reason_id",
    }
    for result_field, node_field in comparisons.items():
        if result.get(result_field) != node.get(node_field):
            raise DelegationEvidenceError(
                f"worker result {result_field} disagrees with execution node"
            )
    if result.get("base_revision") != expected_base_revision:
        raise DelegationEvidenceError("worker result base_revision is stale")
    if result.get("measurement_state") != "observed":
        raise DelegationEvidenceError("accepted worker result must be observed")
    if result.get("stop_reason_id") not in allowed_stop_reasons:
        raise DelegationEvidenceError("worker result stop_reason_id is unknown")
    if result.get("status") == "succeeded" and (
        result.get("scope_violation") != "none"
        or result.get("authorization_concern") != "none"
    ):
        raise DelegationEvidenceError(
            "successful worker result cannot contain a scope or authorization concern"
        )
    raw = validate_artifact(result.get("raw_payload"), artifact_root=artifact_root, label="worker result raw_payload")
    summary = validate_artifact(result.get("accepted_summary"), artifact_root=artifact_root, label="worker result accepted_summary")
    if raw["word_count"] > node["max_result_words"]:
        raise DelegationEvidenceError("worker result exceeds node max_result_words")
    if summary["word_count"] > node["max_summary_words"]:
        raise DelegationEvidenceError("worker summary exceeds node max_summary_words")
    if summary["word_count"] > raw["word_count"]:
        raise DelegationEvidenceError("accepted summary is larger than raw result")
    if result.get("accepted_summary") != node.get("accepted_summary_evidence"):
        raise DelegationEvidenceError("worker summary disagrees with execution node")
    if result.get("summary_covers_result_ids") != node.get("summary_covers_result_ids"):
        raise DelegationEvidenceError("worker summary coverage disagrees with execution node")
    result_obligations = set(
        _strings(result.get("proof_obligation_ids"), "worker result.proof_obligation_ids")
    )
    satisfied_obligations = set(
        _strings(
            result.get("satisfied_proof_obligation_ids"),
            "worker result.satisfied_proof_obligation_ids",
        )
    )
    if result_obligations != set(node["proof_obligation_ids"]):
        raise DelegationEvidenceError(
            "worker result proof obligations disagree with execution node"
        )
    if not satisfied_obligations <= result_obligations or (
        satisfied_obligations != set(node["satisfied_proof_obligation_ids"])
    ):
        raise DelegationEvidenceError(
            "worker result satisfied proof obligations are invalid"
        )
    for index, digest in enumerate(_strings(result.get("child_result_sha256"), "worker result.child_result_sha256")):
        _sha256(digest, f"worker result.child_result_sha256[{index}]")
    touched_surfaces = _strings(
        result.get("touched_surfaces"), "worker result.touched_surfaces"
    )
    if any(
        not _matches_surface(surface, node["surface_refs"])
        for surface in touched_surfaces
    ):
        raise DelegationEvidenceError(
            "worker result reports a surface outside its execution node"
        )
    _strings(result.get("tools_used"), "worker result.tools_used")
    validation = _strings(result.get("validation"), "worker result.validation")
    if result.get("status") == "succeeded" and not validation:
        raise DelegationEvidenceError(
            "successful worker result requires validation evidence"
        )
    _sha256(result.get("subtree_sha256"), "worker result.subtree_sha256")
    if result["subtree_sha256"] != _canonical_sha256(result, "subtree_sha256"):
        raise DelegationEvidenceError("worker result subtree_sha256 is invalid")
    evidence_manifest = result.get("evidence_manifest")
    if not isinstance(evidence_manifest, list):
        raise DelegationEvidenceError("worker result.evidence_manifest must be a list")
    for index, item in enumerate(evidence_manifest):
        item = _object(item, f"worker result.evidence_manifest[{index}]")
        _exact(item, {"path", "revision", "sha256", "validation"}, f"worker result.evidence_manifest[{index}]")
        evidence_path = _contained_file(artifact_root, item.get("path"), f"worker result.evidence_manifest[{index}].path")
        digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        if _sha256(item.get("sha256"), f"worker result.evidence_manifest[{index}].sha256") != digest:
            raise DelegationEvidenceError("worker result evidence digest does not match content")
        _string(item.get("revision"), f"worker result.evidence_manifest[{index}].revision")
        _string(item.get("validation"), f"worker result.evidence_manifest[{index}].validation")
    return result, raw["word_count"], summary["word_count"]


def _validate_nodes(
    tree: dict[str, Any],
    *,
    hard_depth: int,
    allowed_stop_reasons: set[str],
) -> dict[str, dict[str, Any]]:
    raw_nodes = tree.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise DelegationEvidenceError("execution tree.nodes must be a non-empty list")
    nodes: dict[str, dict[str, Any]] = {}
    packet_ids: set[str] = set()
    result_ids: set[str] = set()
    coverage_keys: set[str] = set()
    for raw in raw_nodes:
        node = _object(raw, "execution node")
        _exact(node, NODE_FIELDS, "execution node")
        node_id = _string(node.get("node_id"), "execution node.node_id")
        if node_id in nodes:
            raise DelegationEvidenceError(f"duplicate execution node: {node_id}")
        nodes[node_id] = node
        depth = _integer(
            node.get("depth"), f"execution node {node_id}.depth", maximum=hard_depth
        )
        if node.get("status") not in NODE_STATUSES:
            raise DelegationEvidenceError(f"execution node {node_id} status is invalid")
        _integer(
            node.get("context_words"),
            f"execution node {node_id}.context_words",
            maximum=PORTABLE_MAX_CONTEXT_WORDS,
        )
        _integer(
            node.get("max_result_words"),
            f"execution node {node_id}.max_result_words",
            maximum=PORTABLE_MAX_RESULT_WORDS,
        )
        _integer(
            node.get("max_summary_words"),
            f"execution node {node_id}.max_summary_words",
            maximum=PORTABLE_MAX_PRIMARY_SUMMARY_WORDS,
        )
        if node["max_summary_words"] > node["max_result_words"]:
            raise DelegationEvidenceError(
                f"execution node {node_id} summary limit exceeds result limit"
            )
        _integer(
            node.get("attempt"),
            f"execution node {node_id}.attempt",
            maximum=PORTABLE_MAX_RETRIES,
        )
        for field in [
            "role_id", "assistant_surface", "dispatch_backend",
            "implementation_level", "coverage_key", "semantic_scope",
            "write_scope",
        ]:
            _string(node.get(field), f"execution node {node_id}.{field}")
        for field in [
            "changed_fact_ids", "canonical_owner_refs", "surface_refs",
            "relationship_refs", "allowed_actions", "summary_covers_result_ids",
            "satisfied_acceptance_ids", "proof_obligation_ids",
            "satisfied_proof_obligation_ids", "produced_evidence_ids",
        ]:
            _strings(node.get(field), f"execution node {node_id}.{field}")
        if node.get("overlap_decision") not in {
            "disjoint", "primary-reconciled-overlap", "rejected-overlap",
            "not-applicable",
        }:
            raise DelegationEvidenceError(
                f"execution node {node_id}.overlap_decision is invalid"
            )
        if not isinstance(node.get("child_proposals"), list):
            raise DelegationEvidenceError(
                f"execution node {node_id}.child_proposals must be a list"
            )
        if depth > 0:
            packet_id = _string(
                node.get("packet_id"), f"execution node {node_id}.packet_id"
            )
            if packet_id in packet_ids:
                raise DelegationEvidenceError(f"duplicate packet_id: {packet_id}")
            packet_ids.add(packet_id)
            coverage = node["coverage_key"]
            if coverage in coverage_keys:
                raise DelegationEvidenceError(f"duplicate coverage_key: {coverage}")
            coverage_keys.add(coverage)
            _string(
                node.get("dispatch_group_id"),
                f"execution node {node_id}.dispatch_group_id",
            )
        elif any(
            node.get(field) is not None
            for field in [
                "parent_node_id", "packet_id", "parent_packet_id",
                "dispatch_group_id", "context_evidence",
            ]
        ):
            raise DelegationEvidenceError("root execution node has worker identity fields")
        result_id = node.get("result_id")
        if result_id is not None:
            result_id = _string(result_id, f"execution node {node_id}.result_id")
            if result_id in result_ids:
                raise DelegationEvidenceError(f"duplicate result_id: {result_id}")
            result_ids.add(result_id)
        terminal = node.get("status") in TERMINAL_STATUSES
        if depth > 0 and terminal:
            if node.get("result_status") != RESULT_STATUS_BY_NODE.get(node.get("status")):
                raise DelegationEvidenceError(
                    f"execution node {node_id} result status is invalid"
                )
            if result_id is None:
                raise DelegationEvidenceError(
                    f"execution node {node_id} has no result_id"
                )
            if node.get("stop_reason_id") not in allowed_stop_reasons:
                raise DelegationEvidenceError(
                    f"execution node {node_id} stop_reason_id is unknown"
                )
        elif depth == 0 and terminal:
            if node.get("stop_reason_id") not in allowed_stop_reasons:
                raise DelegationEvidenceError(
                    "terminal root execution node needs a known stop reason"
                )
            if any(
                node.get(field) is not None
                for field in [
                    "result_id", "result_status", "result_evidence",
                    "accepted_summary_evidence",
                ]
            ):
                raise DelegationEvidenceError(
                    "root execution node cannot carry worker result evidence"
                )
        elif node.get("result_evidence") is not None or node.get(
            "accepted_summary_evidence"
        ) is not None:
            raise DelegationEvidenceError(
                f"execution node {node_id} has premature result evidence"
            )
        if not terminal and node.get("stop_reason_id") is not None:
            raise DelegationEvidenceError(
                f"non-terminal execution node {node_id} has a stop reason"
            )
        if not terminal and (
            node.get("result_status") is not None
            or node["summary_covers_result_ids"]
            or node["satisfied_acceptance_ids"]
            or node["satisfied_proof_obligation_ids"]
            or node["produced_evidence_ids"]
        ):
            raise DelegationEvidenceError(
                f"non-terminal execution node {node_id} claims result evidence"
            )
    return nodes


def _validate_header_and_budget(
    tree: dict[str, Any], policy: dict[str, Any], *, artifact_root: Path
) -> tuple[datetime, str, int, set[str], dict[str, Any]]:
    _exact(_object(tree, "execution tree"), TREE_FIELDS, "execution tree")
    if tree.get("schema_version") != 3 or tree.get("tree_kind") != (
        "alatyr-delegation-execution-tree"
    ):
        raise DelegationEvidenceError("execution tree identity is invalid")
    for field in [
        "operation_id", "base_revision", "task_profile", "capability_evidence",
        "root_node_id", "analysis_strategy_id",
    ]:
        _string(tree.get(field), f"execution tree.{field}")
    strategy_id = tree["analysis_strategy_id"]
    if strategy_id not in PRIMARY_ANALYSIS_STRATEGIES:
        raise DelegationEvidenceError(
            "execution tree analysis_strategy_id is invalid"
        )
    problem_model_sha256 = tree.get("problem_model_sha256")
    if strategy_id != "direct-local" and problem_model_sha256 is None:
        raise DelegationEvidenceError(
            "non-local execution strategy requires a problem-model digest"
        )
    if problem_model_sha256 is not None:
        _sha256(problem_model_sha256, "execution tree.problem_model_sha256")
    policy_digest = _sha256(
        tree.get("policy_revision"), "execution tree.policy_revision"
    )
    if policy_digest != _json_sha256(policy):
        raise DelegationEvidenceError(
            "execution tree policy revision does not match the resolved policy"
        )
    recorded_at = _timestamp(tree.get("recorded_at"), "execution tree.recorded_at")
    capability_digest = _sha256(
        tree.get("capability_evidence_sha256"),
        "execution tree.capability_evidence_sha256",
    )
    capability_path = _contained_file(
        artifact_root,
        tree["capability_evidence"],
        "execution tree.capability_evidence",
    )
    if hashlib.sha256(capability_path.read_bytes()).hexdigest() != capability_digest:
        raise DelegationEvidenceError(
            "execution tree capability evidence digest does not match content"
        )
    authorization = _object(
        tree.get("current_user_authorization"),
        "execution tree.current_user_authorization",
    )
    _exact(
        authorization,
        {"scope", "allowed_actions", "authorized_phases", "approval_record"},
        "execution tree.current_user_authorization",
    )
    _string(
        authorization.get("scope"),
        "execution tree.current_user_authorization.scope",
    )
    _strings(
        authorization.get("allowed_actions"),
        "execution tree.current_user_authorization.allowed_actions",
    )
    phases = _strings(
        authorization.get("authorized_phases"),
        "execution tree.current_user_authorization.authorized_phases",
    )
    if "inspect" not in phases:
        raise DelegationEvidenceError(
            "delegation execution requires current inspect authorization"
        )
    approval_record = authorization.get("approval_record")
    if approval_record is not None:
        _string(
            approval_record,
            "execution tree.current_user_authorization.approval_record",
        )

    tree_policy = _object(policy.get("tree_policy"), "delegation policy.tree_policy")
    compaction = _object(
        policy.get("context_compaction"), "delegation policy.context_compaction"
    )
    stop_policy = _object(
        policy.get("stop_policy"), "delegation policy.stop_policy"
    )
    allowed_stops = set(
        _strings(
            stop_policy.get("stop_reason_ids"),
            "delegation policy.stop_reason_ids",
        )
    )
    if stop_policy.get("require_stop_reason") is not True:
        raise DelegationEvidenceError("delegation policy must require stop reasons")
    hard_depth = _integer(
        tree_policy.get("hard_max_depth"),
        "delegation policy.hard_max_depth",
        minimum=1,
        maximum=PORTABLE_MAX_DEPTH,
    )
    child_behavior = tree_policy.get("worker_child_behavior")
    if child_behavior not in {"propose-only", "primary-preauthorized-read-only"}:
        raise DelegationEvidenceError(
            "delegation policy worker_child_behavior is unresolved"
        )
    recursive_policy = policy.get("recursive_child_policy")
    if recursive_policy is not None:
        expected_recursive_policy = {
            "require_verified_nested_capability": True,
            "require_primary_branch_envelope": True,
            "allowed_actions": ["inspect"],
            "write_scope": "none",
            "must_narrow_parent_scope": True,
            "escalation": "return-to-primary",
        }
        if recursive_policy != expected_recursive_policy:
            raise DelegationEvidenceError(
                "delegation policy recursive_child_policy is invalid"
            )
    if compaction.get("mode") != "hierarchical-summary" or compaction.get(
        "digest_algorithm"
    ) != "sha256":
        raise DelegationEvidenceError("delegation policy compaction contract is invalid")

    budget = _object(tree.get("aggregate_budget"), "execution tree.aggregate_budget")
    _exact(budget, BUDGET_FIELDS, "execution tree.aggregate_budget")
    policy_maxima = {
        "max_total_delegates": (
            tree_policy.get("max_total_delegates"), PORTABLE_MAX_DELEGATES
        ),
        "max_parallel_delegates": (
            policy.get(
                "max_parallel_delegates",
                tree_policy.get("max_parallel_delegates"),
            ),
            PORTABLE_MAX_DELEGATES,
        ),
        "max_children_per_parent": (
            tree_policy.get("max_children_per_parent"), PORTABLE_MAX_CHILDREN
        ),
        "max_context_words_total": (
            tree_policy.get("max_context_words_total"), PORTABLE_MAX_CONTEXT_WORDS
        ),
        "max_result_words_total": (
            compaction.get("max_result_words_total"), PORTABLE_MAX_RESULT_WORDS
        ),
        "max_primary_summary_words_total": (
            compaction.get("max_primary_summary_words_total"),
            PORTABLE_MAX_PRIMARY_SUMMARY_WORDS,
        ),
        "max_retries_total": (
            tree_policy.get("max_retries_total"), PORTABLE_MAX_RETRIES
        ),
    }
    for field, (policy_value, portable_maximum) in policy_maxima.items():
        minimum = 0 if field == "max_retries_total" else 1
        policy_limit = _integer(
            policy_value,
            f"delegation policy.{field}",
            minimum=minimum,
            maximum=portable_maximum,
        )
        _integer(
            budget.get(field),
            f"execution tree.aggregate_budget.{field}",
            minimum=minimum,
            maximum=policy_limit,
        )
    if budget["max_primary_summary_words_total"] > budget["max_result_words_total"]:
        raise DelegationEvidenceError(
            "primary summary budget exceeds the aggregate result budget"
        )
    return recorded_at, capability_digest, hard_depth, allowed_stops, budget


def _validate_topology(
    tree: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    budget: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    root = nodes.get(tree["root_node_id"])
    if root is None or root.get("depth") != 0:
        raise DelegationEvidenceError("execution tree root is invalid")
    children: dict[str, list[dict[str, Any]]] = {}
    for node in nodes.values():
        if node["depth"] == 0:
            continue
        parent = nodes.get(node.get("parent_node_id"))
        if parent is None or node["depth"] != parent["depth"] + 1:
            raise DelegationEvidenceError(
                f"execution node {node['node_id']} has invalid parent"
            )
        if node.get("parent_packet_id") != parent.get("packet_id"):
            raise DelegationEvidenceError(
                f"execution node {node['node_id']} packet parent is invalid"
            )
        children.setdefault(parent["node_id"], []).append(node)
    for parent_id, child_nodes in children.items():
        if len(child_nodes) > budget["max_children_per_parent"]:
            raise DelegationEvidenceError(
                f"execution node {parent_id} exceeds child budget"
            )

    branch_fields = {
        "branch_envelope", "branch_envelope_sha256",
        "branch_checkpoint", "branch_checkpoint_sha256",
    }
    for node in nodes.values():
        recursive_coordinator = node["depth"] == 1 and bool(
            children.get(node["node_id"])
        )
        populated = {field for field in branch_fields if node.get(field) is not None}
        if recursive_coordinator and populated != branch_fields:
            raise DelegationEvidenceError(
                f"recursive coordinator {node['node_id']} has incomplete branch evidence"
            )
        if not recursive_coordinator and populated:
            raise DelegationEvidenceError(
                f"execution node {node['node_id']} carries inapplicable branch evidence"
            )

    edge_rows = tree.get("edges")
    if not isinstance(edge_rows, list) or len(edge_rows) != len(nodes) - 1:
        raise DelegationEvidenceError("execution tree must contain one edge per worker")
    edge_pairs: set[tuple[str, str]] = set()
    for edge in edge_rows:
        edge = _object(edge, "execution edge")
        _exact(edge, {"parent_node_id", "child_node_id", "edge_kind"}, "execution edge")
        pair = (edge.get("parent_node_id"), edge.get("child_node_id"))
        if pair in edge_pairs or pair[1] not in nodes or pair[0] not in nodes:
            raise DelegationEvidenceError("execution edge is duplicate or unresolved")
        if nodes[pair[1]].get("parent_node_id") != pair[0] or edge.get("edge_kind") not in EDGE_KINDS:
            raise DelegationEvidenceError("execution edge disagrees with topology")
        if nodes[pair[1]]["depth"] == 2 and edge.get("edge_kind") != "primary-envelope-dispatch":
            raise DelegationEvidenceError("depth-2 dispatch requires a branch envelope")
        if nodes[pair[1]]["depth"] == 1 and edge.get("edge_kind") != "primary-approved-dispatch":
            raise DelegationEvidenceError("depth-1 dispatch requires primary approval")
        edge_pairs.add(pair)
    expected_edge_pairs = {
        (node["parent_node_id"], node["node_id"])
        for node in nodes.values()
        if node["depth"] > 0
    }
    if edge_pairs != expected_edge_pairs:
        raise DelegationEvidenceError("execution edges do not cover the node topology")
    return root, children


def _validate_result_artifacts(
    tree: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    children: dict[str, list[dict[str, Any]]],
    *,
    artifact_root: Path,
    allowed_stop_reasons: set[str],
) -> tuple[int, int, dict[str, dict[str, Any]]]:
    result_words = 0
    primary_summary_words = 0
    result_by_id: dict[str, dict[str, Any]] = {}
    result_artifact_paths: set[str] = set()
    for node in nodes.values():
        if node["depth"] == 0:
            continue
        context_ref = validate_artifact(
            node.get("context_evidence"),
            artifact_root=artifact_root,
            label=f"node {node['node_id']} context_evidence",
        )
        if context_ref["word_count"] != node["context_words"]:
            raise DelegationEvidenceError(
                f"node {node['node_id']} context_words does not match its artifact"
            )
        if context_ref["path"] in result_artifact_paths:
            raise DelegationEvidenceError("worker context artifacts must be unique")
        result_artifact_paths.add(context_ref["path"])
    for node in nodes.values():
        if node["depth"] == 0 or node.get("status") not in TERMINAL_STATUSES:
            continue
        result_ref = validate_artifact(
            node.get("result_evidence"),
            artifact_root=artifact_root,
            label=f"node {node['node_id']} result_evidence",
        )
        if result_ref["path"] in result_artifact_paths:
            raise DelegationEvidenceError("worker result artifacts must be unique")
        result_artifact_paths.add(result_ref["path"])
        result_path = _contained_file(
            artifact_root,
            result_ref["path"],
            f"node {node['node_id']} result path",
        )
        result, raw_words, summary_words = validate_worker_result(
            result_path,
            artifact_root=artifact_root,
            node=node,
            expected_base_revision=tree["base_revision"],
            allowed_stop_reasons=allowed_stop_reasons,
        )
        result_words += raw_words
        for field in ["raw_payload", "accepted_summary"]:
            artifact_path = result[field]["path"]
            if artifact_path in result_artifact_paths:
                raise DelegationEvidenceError(
                    "worker result, raw, and summary artifacts must be unique"
                )
            result_artifact_paths.add(artifact_path)
        if node["depth"] == 1:
            primary_summary_words += summary_words
        result_by_id[result["result_id"]] = result
        child_ids = {
            child["result_id"]
            for child in children.get(node["node_id"], [])
            if child.get("result_id")
        }
        if set(node["summary_covers_result_ids"]) != child_ids:
            raise DelegationEvidenceError(
                f"node {node['node_id']} summary does not cover direct child results"
            )
        if not child_ids and result["child_result_sha256"]:
            raise DelegationEvidenceError(
                f"leaf node {node['node_id']} reports child result digests"
            )
    return result_words, primary_summary_words, result_by_id


def validate_execution_tree(
    tree: dict[str, Any],
    policy: dict[str, Any],
    *,
    artifact_root: Path,
) -> dict[str, Any]:
    """Validate a resolved schema-2 execution tree and referenced artifacts."""
    (
        recorded_at,
        capability_evidence_sha256,
        hard_depth,
        allowed_stop_reasons,
        budget,
    ) = _validate_header_and_budget(tree, policy, artifact_root=artifact_root)

    nodes = _validate_nodes(
        tree,
        hard_depth=hard_depth,
        allowed_stop_reasons=allowed_stop_reasons,
    )
    for node in nodes.values():
        if node["depth"] == 0:
            continue
        if node["max_result_words"] > budget["max_result_words_total"]:
            raise DelegationEvidenceError(
                f"execution node {node['node_id']} result limit exceeds aggregate budget"
            )
        if node["max_summary_words"] > budget["max_primary_summary_words_total"]:
            raise DelegationEvidenceError(
                f"execution node {node['node_id']} summary limit exceeds aggregate budget"
            )

    depth_two_present = any(node["depth"] == 2 for node in nodes.values())
    if depth_two_present and policy["tree_policy"]["worker_child_behavior"] != (
        "primary-preauthorized-read-only"
    ):
        raise DelegationEvidenceError(
            "resolved delegation policy does not authorize recursive dispatch"
        )
    packet_contract = policy.get("worker_packet_contract")
    if packet_contract is not None:
        for node in nodes.values():
            if node["depth"] > 0 and (
                node["allowed_actions"] != packet_contract["allowed_actions"]
                or node["write_scope"] != packet_contract["write_scope"]
            ):
                raise DelegationEvidenceError(
                    "execution node exceeds the source worker packet contract"
                )

    root, children = _validate_topology(tree, nodes, budget)

    result_words, primary_summary_words, result_by_id = _validate_result_artifacts(
        tree,
        nodes,
        children,
        artifact_root=artifact_root,
        allowed_stop_reasons=allowed_stop_reasons,
    )
    checkpoint_rejected_ids: set[str] = set()
    for node in nodes.values():
        if node["depth"] == 1 and children.get(node["node_id"]):
            envelope_ref = node.get("branch_envelope")
            envelope_sha = _sha256(node.get("branch_envelope_sha256"), f"node {node['node_id']}.branch_envelope_sha256")
            envelope_path = _contained_file(artifact_root, envelope_ref, f"node {node['node_id']}.branch_envelope")
            branch_children = children[node["node_id"]]
            if node.get("status") not in TERMINAL_STATUSES or any(
                child.get("status") not in TERMINAL_STATUSES
                for child in branch_children
            ):
                raise DelegationEvidenceError(
                    "recursive branch acceptance requires terminal coordinator and child evidence"
                )
            envelope = validate_branch_envelope(
                envelope_path,
                expected_sha256=envelope_sha,
                now=recorded_at,
            )
            if envelope["parent_node_id"] != node["node_id"] or envelope["operation_id"] != tree["operation_id"]:
                raise DelegationEvidenceError("branch envelope identity disagrees with execution tree")
            if envelope["root_packet_id"] != node["packet_id"]:
                raise DelegationEvidenceError("branch envelope root packet is invalid")
            if set(envelope["proof_obligation_ids"]) != set(
                node["proof_obligation_ids"]
            ):
                raise DelegationEvidenceError(
                    "branch envelope proof obligations disagree with coordinator"
                )
            if envelope["base_revision"] != tree["base_revision"]:
                raise DelegationEvidenceError("branch envelope base_revision is stale")
            if envelope["capability_evidence_sha256"] != capability_evidence_sha256:
                raise DelegationEvidenceError(
                    "branch envelope capability evidence is stale"
                )
            if len(branch_children) > envelope["max_children"]:
                raise DelegationEvidenceError("branch envelope child budget exceeded")
            if sum(item["context_words"] for item in branch_children) > envelope["max_context_words"]:
                raise DelegationEvidenceError("branch envelope context budget exceeded")
            if sum(result_by_id[item["result_id"]]["raw_payload"]["word_count"] for item in branch_children) > envelope["max_result_words"]:
                raise DelegationEvidenceError("branch envelope result budget exceeded")
            if result_by_id[node["result_id"]]["accepted_summary"]["word_count"] > envelope["max_summary_words"]:
                raise DelegationEvidenceError("branch envelope summary budget exceeded")
            if sum(item["attempt"] for item in branch_children) > envelope["max_retries"]:
                raise DelegationEvidenceError("branch envelope retry budget exceeded")
            allowed_surfaces = envelope["allowed_surface_refs"]
            observed_validation: set[str] = set()
            for child in branch_children:
                if child["allowed_actions"] != ["inspect"] or child["write_scope"] != "none":
                    raise DelegationEvidenceError("recursive children must be read-only")
                if not child["coverage_key"].startswith(envelope["coverage_prefix"]):
                    raise DelegationEvidenceError("recursive child coverage escapes branch envelope")
                child_scope = child["semantic_scope"]
                parent_scope = envelope["semantic_scope"]
                if child_scope != parent_scope and not child_scope.startswith(parent_scope + "/"):
                    raise DelegationEvidenceError(
                        "recursive child semantic scope escapes branch envelope"
                    )
                if any(
                    not _matches_surface(surface, allowed_surfaces)
                    for surface in child["surface_refs"]
                ):
                    raise DelegationEvidenceError(
                        "recursive child surface escapes branch envelope"
                    )
                child_result = result_by_id[child["result_id"]]
                if any(
                    not any(
                        fnmatchcase(tool_id, allowed_tool)
                        for allowed_tool in envelope["allowed_tools"]
                    )
                    for tool_id in child_result["tools_used"]
                ):
                    raise DelegationEvidenceError(
                        "recursive child reports a tool outside its branch envelope"
                    )
                if child_result["input_context_packet_sha256"] != envelope["context_packet_sha256"]:
                    raise DelegationEvidenceError(
                        "recursive child input context digest disagrees with branch envelope"
                    )
                if not set(child["proof_obligation_ids"]) <= set(
                    envelope["proof_obligation_ids"]
                ):
                    raise DelegationEvidenceError(
                        "recursive child proof obligations escape branch envelope"
                    )
                observed_validation.update(child_result["validation"])
            if not set(envelope["required_validation"]) <= observed_validation:
                raise DelegationEvidenceError(
                    "recursive branch does not report required validation"
                )
            child_result_digests = {
                child["result_evidence"]["sha256"] for child in branch_children
            }
            if set(result_by_id[node["result_id"]]["child_result_sha256"]) != child_result_digests:
                raise DelegationEvidenceError("branch coordinator result omits child result digests")
            checkpoint_sha = _sha256(node.get("branch_checkpoint_sha256"), f"node {node['node_id']}.branch_checkpoint_sha256")
            checkpoint_path = _contained_file(artifact_root, node.get("branch_checkpoint"), f"node {node['node_id']}.branch_checkpoint")
            checkpoint = validate_branch_checkpoint(
                checkpoint_path,
                artifact_root=artifact_root,
                expected_sha256=checkpoint_sha,
                envelope=envelope,
                node=node,
                allowed_stop_reasons=allowed_stop_reasons,
            )
            child_ids = {child["result_id"] for child in branch_children}
            accepted_ids = set(checkpoint["accepted_result_ids"])
            rejected_ids = set(checkpoint["rejected_result_ids"])
            if accepted_ids & rejected_ids or accepted_ids | rejected_ids != child_ids:
                raise DelegationEvidenceError(
                    "branch checkpoint does not partition child results"
                )
            if any(
                child["status"] != "DONE"
                for child in branch_children
                if child["result_id"] in accepted_ids
            ):
                raise DelegationEvidenceError(
                    "branch checkpoint accepts a non-successful child result"
                )
            checkpoint_rejected_ids.update(rejected_ids)
            accepted_digests = {
                child["result_evidence"]["sha256"]
                for child in branch_children
                if child["result_id"] in accepted_ids
            }
            if set(checkpoint["accepted_result_sha256"]) != accepted_digests:
                raise DelegationEvidenceError("branch checkpoint child digests are incomplete")
            accepted_coverages = {
                child["coverage_key"]
                for child in branch_children
                if child["result_id"] in accepted_ids
            }
            if set(checkpoint["completed_coverage_keys"]) != accepted_coverages:
                raise DelegationEvidenceError(
                    "branch checkpoint coverage keys are incomplete"
                )
            accepted_obligations = {
                obligation_id
                for child in branch_children
                if child["result_id"] in accepted_ids
                for obligation_id in child["satisfied_proof_obligation_ids"]
            }
            if set(checkpoint["completed_proof_obligation_ids"]) != (
                accepted_obligations
            ):
                raise DelegationEvidenceError(
                    "branch checkpoint proof-obligation coverage is incomplete"
                )
            if checkpoint["accepted_summary"] != node["accepted_summary_evidence"]:
                raise DelegationEvidenceError(
                    "branch checkpoint summary disagrees with coordinator result"
                )
            if checkpoint["context_packet_sha256"] != envelope["context_packet_sha256"]:
                raise DelegationEvidenceError(
                    "branch checkpoint context digest disagrees with its envelope"
                )
            if checkpoint["stop_reason_id"] != node["stop_reason_id"]:
                raise DelegationEvidenceError(
                    "branch checkpoint stop reason disagrees with its coordinator"
                )
            accepted_evidence = {
                result_id: result_by_id[result_id]["evidence_manifest"]
                for result_id in sorted(accepted_ids)
            }
            accepted_validation = {
                result_id: result_by_id[result_id]["validation"]
                for result_id in sorted(accepted_ids)
            }
            if checkpoint["evidence_manifest_sha256"] != _json_sha256(accepted_evidence):
                raise DelegationEvidenceError(
                    "branch checkpoint evidence manifest digest is invalid"
                )
            if checkpoint["validation_sha256"] != _json_sha256(accepted_validation):
                raise DelegationEvidenceError(
                    "branch checkpoint validation digest is invalid"
                )
            if node["status"] == "DONE" and checkpoint["unresolved_escalations"]:
                raise DelegationEvidenceError(
                    "completed branch checkpoint has unresolved escalations"
                )

    return _validate_budget_and_convergence(
        tree,
        nodes=nodes,
        root=root,
        budget=budget,
        result_words=result_words,
        primary_summary_words=primary_summary_words,
        checkpoint_rejected_ids=checkpoint_rejected_ids,
        allowed_stop_reasons=allowed_stop_reasons,
    )


def _validate_budget_and_convergence(
    tree: dict[str, Any],
    *,
    nodes: dict[str, dict[str, Any]],
    root: dict[str, Any],
    budget: dict[str, Any],
    result_words: int,
    primary_summary_words: int,
    checkpoint_rejected_ids: set[str],
    allowed_stop_reasons: set[str],
) -> dict[str, Any]:
    used = {
        "used_total_delegates": len(nodes) - 1,
        "used_parallel_delegates": max(
            (
                sum(
                    1
                    for node in nodes.values()
                    if node.get("dispatch_group_id") == group
                )
                for group in {
                    node.get("dispatch_group_id")
                    for node in nodes.values()
                    if node.get("dispatch_group_id")
                }
            ),
            default=0,
        ),
        "used_context_words": sum(
            node["context_words"] for node in nodes.values() if node["depth"] > 0
        ),
        "used_result_words": result_words,
        "used_primary_summary_words": primary_summary_words,
        "used_retries": sum(
            node["attempt"] for node in nodes.values() if node["depth"] > 0
        ),
    }
    maximum_fields = {
        "used_total_delegates": "max_total_delegates",
        "used_parallel_delegates": "max_parallel_delegates",
        "used_context_words": "max_context_words_total",
        "used_result_words": "max_result_words_total",
        "used_primary_summary_words": "max_primary_summary_words_total",
        "used_retries": "max_retries_total",
    }
    for field, measured in used.items():
        if budget.get(field) != measured:
            raise DelegationEvidenceError(
                f"aggregate {field} does not match measured evidence"
            )
        maximum_field = maximum_fields[field]
        if measured > budget[maximum_field]:
            raise DelegationEvidenceError(
                f"aggregate {field} exceeds {maximum_field}"
            )

    convergence = _object(tree.get("primary_convergence"), "primary convergence")
    _exact(convergence, CONVERGENCE_FIELDS, "primary convergence")
    status = convergence.get("status")
    if status not in {"pending", "completed", "blocked", "cancelled"}:
        raise DelegationEvidenceError("primary convergence status is invalid")
    required_acceptance = set(
        _strings(
            convergence.get("required_acceptance_ids"),
            "primary convergence.required_acceptance_ids",
        )
    )
    required_evidence = set(
        _strings(
            convergence.get("required_evidence_ids"),
            "primary convergence.required_evidence_ids",
        )
    )
    required_obligations = set(
        _strings(
            convergence.get("required_proof_obligation_ids"),
            "primary convergence.required_proof_obligation_ids",
        )
    )
    satisfied_obligations = set(
        _strings(
            convergence.get("satisfied_proof_obligation_ids"),
            "primary convergence.satisfied_proof_obligation_ids",
        )
    )
    reviewed = set(
        _strings(
            convergence.get("reviewed_result_ids"),
            "primary convergence.reviewed_result_ids",
        )
    )
    indirect = set(
        _strings(
            convergence.get("indirect_result_ids"),
            "primary convergence.indirect_result_ids",
        )
    )
    rejected = set(
        _strings(
            convergence.get("rejected_result_ids"),
            "primary convergence.rejected_result_ids",
        )
    )
    final_stop_reason = convergence.get("final_stop_reason_id")
    if status in {"completed", "blocked", "cancelled"}:
        if final_stop_reason not in allowed_stop_reasons:
            raise DelegationEvidenceError(
                "terminal primary convergence needs a known final stop reason"
            )
    elif final_stop_reason is not None:
        raise DelegationEvidenceError(
            "pending primary convergence cannot have a final stop reason"
        )
    root_statuses = {
        "pending": {"PLANNED", "READY", "RUNNING"},
        "completed": {"DONE"},
        "blocked": {"BLOCKED", "REVIEW_REQUIRED", "FAILED", "REJECTED"},
        "cancelled": {"CANCELLED"},
    }
    if root["status"] not in root_statuses[status]:
        raise DelegationEvidenceError(
            "primary convergence status disagrees with the root execution node"
        )
    if status != "pending" and root["stop_reason_id"] != final_stop_reason:
        raise DelegationEvidenceError(
            "primary convergence stop reason disagrees with the root execution node"
        )
    direct_results = {
        node["result_id"]
        for node in nodes.values()
        if node["depth"] == 1 and node.get("result_id")
    }
    descendant_results = {
        node["result_id"]
        for node in nodes.values()
        if node["depth"] == 2 and node.get("result_id")
    }
    if reviewed != direct_results or indirect != descendant_results:
        raise DelegationEvidenceError(
            "primary convergence direct or indirect result coverage is incomplete"
        )
    if not rejected <= reviewed | indirect:
        raise DelegationEvidenceError(
            "primary convergence rejects an unknown result"
        )
    if not checkpoint_rejected_ids <= rejected:
        raise DelegationEvidenceError(
            "primary convergence accepts a branch-rejected result"
        )
    accepted_result_ids = (reviewed | indirect) - rejected
    if status == "completed" and any(
        node["status"] != "DONE"
        for node in nodes.values()
        if node.get("result_id") in accepted_result_ids
    ):
        raise DelegationEvidenceError(
            "completed convergence accepts an unfinished or unsuccessful worker"
        )
    accepted_nodes = [
        node
        for node in nodes.values()
        if node.get("result_id") in accepted_result_ids and node["status"] == "DONE"
    ]
    acceptance = {
        item for node in accepted_nodes for item in node["satisfied_acceptance_ids"]
    }
    evidence = {
        item for node in accepted_nodes for item in node["produced_evidence_ids"]
    }
    worker_obligations = {
        item
        for node in accepted_nodes
        for item in node["satisfied_proof_obligation_ids"]
    }
    if not satisfied_obligations <= required_obligations:
        raise DelegationEvidenceError(
            "primary convergence satisfies an unrequired proof obligation"
        )
    if not worker_obligations <= satisfied_obligations:
        raise DelegationEvidenceError(
            "primary convergence omits accepted worker proof evidence"
        )
    if status == "completed" and (
        not required_acceptance <= acceptance
        or not required_evidence <= evidence
    ):
        raise DelegationEvidenceError(
            "completed convergence lacks required acceptance or evidence coverage"
        )
    if status == "completed" and required_obligations != satisfied_obligations:
        raise DelegationEvidenceError(
            "completed convergence lacks required proof-obligation coverage"
        )
    return tree
