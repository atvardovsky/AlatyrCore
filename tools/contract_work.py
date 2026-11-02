"""Conditional contract bindings on existing proof obligations, not a task engine."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PureWindowsPath
from typing import Any, Callable

from behavior_acceptance import resolved
from target_validation_support import is_target_relative_path

DELEGABLE_LEVELS = frozenset({"L1", "L2", "L3", "L4"})
PREFERENCES = frozenset({"auto", "allow", "forbid", "require-supported"})
MAX_ARTIFACT_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 8 * MAX_ARTIFACT_BYTES
MAX_ARTIFACTS = 32


def _file_path(path: str) -> bool:
    return (resolved(path) and is_target_relative_path(path) and not PureWindowsPath(path).drive
            and not any(character in path for character in ("\\", "#", ":"))
            and all(part not in ("", ".") for part in path.split("/")))


def work_failures(model: dict[str, Any], *, completion: bool = False,
                  policy: dict[str, Any] | None = None,
                  policy_checked: bool = False) -> list[str]:
    """Called after canonical model-schema validation; no filesystem discovery."""
    work = model.get("contract_work")
    if work is None:
        return (["contract-sensitive-multipart work requires contract_work"]
                if "contract-sensitive-multipart" in model.get("risk_classes", []) else [])
    failures: list[str] = []
    if "contract-sensitive-multipart" not in model.get("risk_classes", []):
        failures.append("contract_work requires explicit contract-sensitive-multipart classification")
    obligations = {row["id"]: row for row in model["proof_obligations"]}
    preferences = [work["delegation_preference"]]
    if policy is not None:
        preference = policy.get("default_preference")
        if not isinstance(preference, str) or preference not in PREFERENCES:
            failures.append("contract_work requires a resolved target delegation preference")
        else:
            preferences.append(preference)
    forbid = "forbid" in preferences
    required = "require-supported" in preferences
    seen_parts: set[str] = set()
    delegation_records: set[tuple[str, str, str | None]] = set()
    assigned: set[str] = set()
    groups = [("integration", work["integration_obligation_ids"]),
              ("end-to-end", work["end_to_end_obligation_ids"])]
    for part in work["parts"]:
        name = part["id"]
        if not resolved(name) or name in seen_parts:
            failures.append(f"contract_work part identity is unresolved or duplicate: {name!r}")
        seen_parts.add(name)
        if not resolved(part["reason"]):
            failures.append(f"contract_work part {name!r} requires a concrete executor/blocker reason")
        groups.extend([(f"{name} positive", part["positive_obligation_ids"]),
                       (f"{name} negative", part["negative_obligation_ids"])])
        executor = part["executor"]
        eligible = part["implementation_level"] in DELEGABLE_LEVELS
        if executor == "worker" and (forbid or not eligible):
            failures.append(f"contract_work part {name!r} cannot delegate under this preference/level")
        if policy_checked and executor == "worker" and (policy is None or policy.get("state") not in ("enabled", "suggest-only")):
            failures.append(f"contract_work part {name!r} needs an enabled target delegation policy")
        if required and eligible and executor == "primary":
            failures.append(f"contract_work part {name!r} requires a worker; cost or capability cannot silently waive it")
        if required and forbid and eligible and executor != "blocked":
            failures.append(f"contract_work part {name!r} must block on conflicting delegation preferences")
        result = part["delegation_evidence"]
        if executor != "worker" and result is not None:
            failures.append(f"contract_work part {name!r} cannot claim delegation evidence for {executor}")
        if completion and (executor == "blocked" or executor == "worker" and result is None):
            failures.append(f"contract_work part {name!r} is blocked or lacks delegation evidence")
        if result is not None:
            delegation_records.add((result["kind"], result["path"], result["capability_path"]))
            for path in (result["path"], result["capability_path"]):
                if path is not None and not _file_path(path):
                    failures.append(f"contract_work delegation requires an exact contained path: {path!r}")
            if result["kind"] == "single-read-only-receipt" and result["capability_path"] is None:
                failures.append(f"contract_work part {name!r} receipt requires a capability path")
            if result["kind"] == "execution-tree" and result["capability_path"] is not None:
                failures.append(f"contract_work part {name!r} tree owns its capability binding")
        if executor == "blocked":
            for identity in part["positive_obligation_ids"] + part["negative_obligation_ids"]:
                if identity in obligations and obligations[identity]["status"] in ("passed", "waived"):
                    failures.append(f"blocked contract_work part {name!r} cannot discharge {identity!r}")
    if len(delegation_records) > 1:
        failures.append("contract_work requires one operation-wide delegation record; separate records cannot reset cumulative budgets")
    for label, identities in groups:
        for identity in identities:
            if identity not in obligations or not obligations[identity]["required"]:
                failures.append(f"contract_work {label} references unknown or non-required obligation {identity!r}")
            if identity in assigned:
                failures.append(f"contract_work {label} reuses obligation {identity!r}; component and wider acceptance stay separate")
            assigned.add(identity)
    artifacts: dict[str, str] = {}
    for part in work["parts"]:
        for binding in part["contract_refs"]:
            path = binding["path"]
            if not _file_path(path):
                failures.append(f"contract_work artifact requires a contained exact file path: {path!r}")
            if path in artifacts and artifacts[path] != binding["sha256"]:
                failures.append(f"contract_work has conflicting artifact bindings: {path}")
            artifacts[path] = binding["sha256"]
    if len(artifacts) > MAX_ARTIFACTS:
        failures.append(f"contract_work exceeds {MAX_ARTIFACTS} unique artifacts; decompose the work")
    return failures


def verify_work_artifacts(model: dict[str, Any], read: Callable[[str, int], bytes]) -> list[str]:
    """Verify selected current bindings once each, with bounded cumulative I/O."""
    work = model.get("contract_work")
    if work is None:
        return []
    bindings: dict[str, str] = {}
    for part in work["parts"]:
        for binding in part["contract_refs"]:
            bindings[binding["path"]] = binding["sha256"]
    if len(bindings) > MAX_ARTIFACTS:
        return [f"contract_work exceeds {MAX_ARTIFACTS} unique artifacts"]
    failures: list[str] = []
    consumed = 0
    for path, expected in bindings.items():
        measured = False
        try:
            remaining = MAX_TOTAL_BYTES - consumed
            if remaining < 0:
                raise ValueError("aggregate artifact byte budget exceeded")
            raw = read(path, min(MAX_ARTIFACT_BYTES, remaining))
            if not isinstance(raw, bytes) or len(raw) > min(MAX_ARTIFACT_BYTES, remaining):
                raise ValueError("artifact exceeds byte budget or is not bytes")
            consumed += len(raw)
            measured = True
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError("SHA-256 differs from the bound contract/result")
        except (OSError, ValueError) as exc:
            failures.append(f"contract_work artifact {path!r}: {exc}")
            if not measured:
                # A failed reader may already have spent its allowance.
                break
    return failures


def verify_work_delegation(model: dict[str, Any], *, model_sha256: str, policy: dict[str, Any] | None,
                           target: Path, read: Callable[[Path, int], bytes], completion: bool) -> list[str]:
    """Reuse the existing evidence tier, binding each worker to this exact model."""
    from delegation_evidence import (artifact_reader, load_json_object,
                                     validate_execution_tree, validate_single_read_only_receipt)
    failures: list[str] = []
    validated: dict[tuple[str, str, str | None], dict[str, Any]] = {}
    for part in model.get("contract_work", {}).get("parts", []):
        ref = part["delegation_evidence"]
        if ref is None or part["executor"] != "worker":
            continue
        try:
            key = (ref["kind"], ref["path"], ref["capability_path"])
            if key not in validated:
                with artifact_reader(read):
                    record = load_json_object(target / ref["path"], "contract-work delegation")
                    if not isinstance(policy, dict):
                        raise ValueError("delegation requires a resolved target policy")
                    if ref["kind"] == "execution-tree":
                        validate_execution_tree(record, policy, artifact_root=target)
                    else:
                        capability = load_json_object(target / ref["capability_path"], "delegation capability")
                        validate_single_read_only_receipt(record, policy, capability, artifact_root=target)
                for field, expected in (("operation_id", model["operation_id"]),
                                        ("base_revision", model["repository_binding"]["base_revision"]),
                                        ("analysis_strategy_id", model["primary_strategy_id"]),
                                        ("problem_model_sha256", model_sha256)):
                    if record.get(field) != expected:
                        raise ValueError(f"delegation {field} does not match this model")
                validated[key] = record
            record = validated[key]
            assigned = set(part["positive_obligation_ids"] + part["negative_obligation_ids"])
            contracts = {binding["path"] for binding in part["contract_refs"]}
            if ref["kind"] == "execution-tree":
                nodes = [node for node in record["nodes"] if node["node_id"] == ref["node_id"] and node["depth"] > 0]
                if len(nodes) != 1:
                    raise ValueError("delegation must select one non-primary node")
                node = nodes[0]
                covered = set(node["satisfied_proof_obligation_ids"])
                declared = set(node["proof_obligation_ids"])
                owners = node["canonical_owner_refs"]
                succeeded = node["status"] == "DONE" and record["primary_convergence"]["status"] == "completed"
                if node["implementation_level"] != part["implementation_level"]:
                    raise ValueError("delegation implementation level differs from this part")
            else:
                if record["packet"]["node_id"] != ref["node_id"]:
                    raise ValueError("delegation receipt node differs from this part")
                if part["implementation_level"] != "L1":
                    raise ValueError("inspect-only receipts cannot establish implementation work")
                declared = set(record["packet"]["proof_obligation_ids"])
                owners = record["packet"]["canonical_owner_refs"]
                covered = set(record["result"]["satisfied_proof_obligation_ids"])
                succeeded = record["result"]["status"] == "succeeded" and record["primary_convergence"]["status"] == "accepted"
            if not contracts <= {owner.split("#", 1)[0] for owner in owners}:
                raise ValueError("delegation omits this part's canonical contract owners")
            if not assigned <= declared or completion and (not succeeded or not assigned <= covered):
                raise ValueError("delegation does not cover this part's required obligations")
        except (OSError, ValueError, TypeError, RecursionError) as exc:
            failures.append(f"contract_work part {part['id']!r} delegation: {exc}")
    return failures
