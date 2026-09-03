#!/usr/bin/env python3
"""Validate compact source and installation context routing."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from render_framework_file_inventory import build_inventory
from check_all import ALLOWED_PROFILES, load_manifest
from context_catalog import ContextCatalogError, load_codebook, validate_context_catalog
from task_classification_contract import (
    AMBIGUITY_READ_ONLY_MARKER,
    DEFAULT_TASK_CLASS,
    SOURCE_REQUIRED_EXPANSION_TRIGGERS,
    SOURCE_SMALL_TASK_FOCUSED_CHECKS_MARKER,
    TASK_CLASSES,
    TASK_CLASSIFICATION_SCHEMA_VERSION,
    missing_required_values,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROUTER = ROOT / "tools" / "source_context_router.json"
INSTALL_ROUTER = ROOT / "installer" / "context-router.json"
INVENTORY = ROOT / "framework" / "file-inventory.json"
SOURCE_AGENTS = ROOT / "AGENTS.md"
SOURCE_ASSISTANTS = ROOT / "AI_ASSISTANTS.md"
SOURCE_WORKER_STRATEGY = ROOT / "docs" / "source-worker-strategy.md"
SOURCE_WORKER_POLICY = ROOT / "tools" / "source_worker_policy.json"
EXPECTED_SOURCE_PROFILES = {
    "docs-local",
    "framework-rule",
    "installer-template",
    "source-tooling",
    "release-versioning",
    "ai-infrastructure-bridge",
    "repository-audit",
}
EXPECTED_INSTALL_STAGES = [
    "discovery",
    "scope-selection",
    "plan-and-approval",
    "adaptation",
    "validation",
    "handoff",
]
EXPECTED_PRIMARY_OWNED_ACTIONS = {
    "architecture-decisions",
    "conflict-resolution",
    "current-scope-authorization",
    "final-synthesis",
    "final-validation",
    "logical-integrity-review",
    "modify",
    "commit",
    "publish",
    "live-external",
}
EXPECTED_DECISION_FIELDS = {
    "evaluation_status",
    "runtime_capability_status",
    "selected_workstream_ids",
    "decision",
    "reason",
}
EXPECTED_SKIP_REASONS = {
    "capability-unavailable",
    "capability-unverified",
    "insufficient-independent-work",
    "dependency-ordering",
    "overlapping-scope",
    "coordination-cost-exceeds-benefit",
    "client-policy-prohibits",
    "user-restricted",
}
EXPECTED_CAPABILITY_FIELDS = {
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
    "freshness",
    "evidence",
}
EXPECTED_PACKET_FIELDS = {
    "workstream_id",
    "role_id",
    "objective",
    "bounded_context",
    "conditional_context",
    "non_goals",
    "allowed_actions",
    "write_scope",
    "expected_evidence",
}


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return data


def concrete_paths(value: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in {"required_context", "preloaded_context", "bootstrap_context"}:
                if isinstance(nested, list):
                    paths.extend(item for item in nested if isinstance(item, str))
            paths.extend(concrete_paths(nested))
    elif isinstance(value, list):
        for nested in value:
            paths.extend(concrete_paths(nested))
    return paths


def word_count(paths: list[str]) -> int:
    total = 0
    for relpath in dict.fromkeys(paths):
        path = ROOT / relpath
        if path.is_file():
            total += len(re.findall(r"\S+", path.read_text(encoding="utf-8")))
    return total


def validate_router_paths(router: dict[str, Any], label: str) -> list[str]:
    failures: list[str] = []
    for relpath in concrete_paths(router):
        if "{" in relpath or relpath in {
            "edited file",
            "directly linked neighbor",
        }:
            continue
        if not (ROOT / relpath).is_file():
            failures.append(f"{label} references missing required path {relpath}")
    return failures


def require_text(path: Path, values: list[str], failures: list[str]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        failures.append(str(exc))
        return
    for value in values:
        if value not in text:
            failures.append(f"{path.relative_to(ROOT)} missing {value}")


def validate_source_worker_policy(
    source: dict[str, Any],
    failures: list[str],
) -> None:
    """Validate source-only decomposition without binding it to an AI provider."""
    profiles = source.get("profiles")
    audit = profiles.get("repository-audit", {}) if isinstance(profiles, dict) else {}
    decomposition = audit.get("decomposition") if isinstance(audit, dict) else None
    candidates: list[str] = []
    if not isinstance(decomposition, dict):
        failures.append("repository-audit has no worker-policy decomposition route")
    else:
        if decomposition.get("required") is not True:
            failures.append("repository-audit must require a decomposition assessment")
        if decomposition.get("worker_policy") != "tools/source_worker_policy.json":
            failures.append("repository-audit references the wrong source worker policy")
        raw_candidates = decomposition.get("candidate_workstreams")
        if (
            not isinstance(raw_candidates, list)
            or len(raw_candidates) < 2
            or not all(isinstance(item, str) and item for item in raw_candidates)
            or len(raw_candidates) != len(set(raw_candidates))
        ):
            failures.append(
                "repository-audit must declare at least two unique candidate workstreams"
            )
        else:
            candidates = raw_candidates

    try:
        policy = load_object(SOURCE_WORKER_POLICY)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(f"source worker policy is missing or invalid: {exc}")
        return

    if (
        policy.get("schema_version") != 1
        or policy.get("policy_kind") != "alatyr-source-worker-policy"
    ):
        failures.append("source worker policy schema or kind is invalid")
    if policy.get("scope") != "source-repository":
        failures.append("source worker policy must be scoped to the source repository")
    if policy.get("provider_neutral") is not True:
        failures.append("source worker policy must declare provider-neutral routing")
    if policy.get("runtime_capability_owner") != "active-assistant":
        failures.append(
            "source worker runtime capability must be verified by the active assistant"
        )
    if policy.get("fallback_executor") != "primary-assistant":
        failures.append("source worker fallback must remain the primary assistant")
    authorization_boundary = policy.get("authorization_boundary")
    if (
        not isinstance(authorization_boundary, str)
        or "current user request" not in authorization_boundary
        or "do not grant" not in authorization_boundary
    ):
        failures.append("source worker policy has no current-scope authorization boundary")

    forbidden_bindings = {
        "provider",
        "provider_id",
        "model",
        "model_id",
        "dispatch_backend",
        "executable",
    }
    present_bindings: set[str] = set()

    def collect_forbidden_keys(value: Any) -> None:
        if isinstance(value, dict):
            present_bindings.update(forbidden_bindings.intersection(value))
            for nested in value.values():
                collect_forbidden_keys(nested)
        elif isinstance(value, list):
            for nested in value:
                collect_forbidden_keys(nested)

    collect_forbidden_keys(policy)
    if present_bindings:
        failures.append(
            "source worker policy must not hard-code provider runtime bindings: "
            f"{sorted(present_bindings)}"
        )

    decision_evidence = policy.get("decision_evidence")
    if not isinstance(decision_evidence, dict):
        failures.append("source worker policy has no decision-evidence contract")
    else:
        required_fields = decision_evidence.get("required_fields")
        if not isinstance(required_fields, list) or not EXPECTED_DECISION_FIELDS <= set(
            required_fields
        ):
            failures.append("source worker decision evidence is incomplete")
        skip_reasons = decision_evidence.get("skip_reason_ids")
        if not isinstance(skip_reasons, list) or not EXPECTED_SKIP_REASONS <= set(
            skip_reasons
        ):
            failures.append("source worker skip-reason contract is incomplete")
        if not isinstance(decision_evidence.get("skip_reason_requirement"), str):
            failures.append("source worker policy does not require concrete skip evidence")
        decisions = decision_evidence.get("preflight_decisions")
        if not isinstance(decisions, list) or not {
            "runtime-verification-required",
            "delegation-recommended",
            "kept-local",
            "primary-assistant",
        } <= set(decisions):
            failures.append("source worker preflight decision vocabulary is incomplete")
        completion = decision_evidence.get("completion_decisions")
        if not isinstance(completion, list) or not {"delegated", "kept-local"} <= set(
            completion
        ):
            failures.append("source worker completion decision vocabulary is incomplete")

    capability = policy.get("runtime_capability_contract")
    if not isinstance(capability, dict):
        failures.append("source worker policy has no runtime capability contract")
    else:
        capability_fields = capability.get("required_fields")
        if not isinstance(capability_fields, list) or not EXPECTED_CAPABILITY_FIELDS <= set(
            capability_fields
        ):
            failures.append("source worker runtime capability contract is incomplete")
        if capability.get("minimum_parallelism") != 2:
            failures.append("source worker audit capability must require two workers")
        if capability.get("write_isolation") != "read-only":
            failures.append("source worker capability must require read-only isolation")
        if capability.get("result_delivery") is not True:
            failures.append("source worker capability must require result delivery")
        if capability.get("freshness") != "current-session":
            failures.append("source worker capability evidence must be current-session")

    packet_contract = policy.get("worker_packet_contract")
    if not isinstance(packet_contract, dict):
        failures.append("source worker policy has no worker packet contract")
    else:
        packet_fields = packet_contract.get("required_fields")
        if not isinstance(packet_fields, list) or not EXPECTED_PACKET_FIELDS <= set(
            packet_fields
        ):
            failures.append("source worker packet contract is incomplete")
        if packet_contract.get("allowed_actions") != ["inspect"]:
            failures.append("source worker packets must be inspect-only")
        if packet_contract.get("write_scope") != "none":
            failures.append("source worker packets must have no write scope")
        if packet_contract.get("role_id") != "read-only-auditor":
            failures.append("source worker packets must use the read-only audit role")

    workstreams = policy.get("workstreams")
    if not isinstance(workstreams, dict) or len(workstreams) < 2:
        failures.append("source worker policy must define at least two bounded workstreams")
        workstreams = {}
    else:
        for workstream_id, workstream in workstreams.items():
            if not isinstance(workstream_id, str) or not workstream_id:
                failures.append("source worker policy contains an invalid workstream ID")
                continue
            if not isinstance(workstream, dict):
                failures.append(
                    f"source worker workstream {workstream_id} must be an object"
                )
                continue
            if workstream.get("mode") != "read-only":
                failures.append(
                    f"source worker workstream {workstream_id} must stay read-only"
                )
            if workstream.get("independent") is not True:
                failures.append(
                    f"source worker workstream {workstream_id} must be independently reviewable"
                )
            required_context = workstream.get("required_context")
            if not isinstance(required_context, list) or not required_context or not all(
                isinstance(item, str) and item for item in required_context
            ):
                failures.append(
                    f"source worker workstream {workstream_id} has no bounded required context"
                )
            else:
                missing_context = [
                    relpath
                    for relpath in required_context
                    if not (ROOT / relpath).is_file()
                ]
                if missing_context:
                    failures.append(
                        f"source worker workstream {workstream_id} references missing "
                        f"context: {missing_context}"
                    )
            for field in ["objective", "expected_evidence"]:
                if not isinstance(workstream.get(field), str) or not workstream[field]:
                    failures.append(
                        f"source worker workstream {workstream_id} has no {field}"
                    )
            non_goals = workstream.get("non_goals")
            if not isinstance(non_goals, list) or not non_goals:
                failures.append(
                    f"source worker workstream {workstream_id} has no non-goals"
                )

    primary_owned = policy.get("primary_owned_actions")
    if not isinstance(primary_owned, list):
        failures.append("source worker policy has no primary-owned action list")
    else:
        missing = sorted(EXPECTED_PRIMARY_OWNED_ACTIONS - set(primary_owned))
        if missing:
            failures.append(
                "source worker policy does not keep required actions primary-owned: "
                f"{missing}"
            )

    if candidates:
        unknown = sorted(set(candidates) - set(workstreams))
        if unknown:
            failures.append(
                "repository-audit references unknown source worker workstreams: "
                f"{unknown}"
            )


def main() -> int:
    failures: list[str] = []
    try:
        source = load_object(SOURCE_ROUTER)
        installer = load_object(INSTALL_ROUTER)
        inventory = load_object(INVENTORY)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if source.get("schema_version") != 1 or source.get("router_kind") != "alatyr-source-context-router":
        failures.append("source context router schema or kind is invalid")
    profiles = source.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != EXPECTED_SOURCE_PROFILES:
        failures.append("source context router profile set is incomplete")
    else:
        manifest = load_manifest()
        manifest_by_id = {check["id"]: check for check in manifest}
        manifest_ids = set(manifest_by_id)
        for profile_id, profile in profiles.items():
            checks = profile.get("checks")
            if not isinstance(checks, list) or not checks:
                failures.append(f"source profile {profile_id} has no check IDs")
                continue
            unknown = sorted(set(checks) - manifest_ids)
            if unknown:
                failures.append(
                    f"source profile {profile_id} references unknown check IDs: {unknown}"
                )
                continue
            check_profile = profile.get("check_profile")
            additional_profiles = profile.get("additional_check_profiles", [])
            if check_profile not in ALLOWED_PROFILES:
                failures.append(
                    f"source profile {profile_id} has no valid check profile: {check_profile}"
                )
                continue
            if (
                not isinstance(additional_profiles, list)
                or not all(isinstance(item, str) for item in additional_profiles)
                or not set(additional_profiles) <= ALLOWED_PROFILES
            ):
                failures.append(
                    f"source profile {profile_id} has invalid additional check profiles"
                )
                continue
            validation_profiles = {check_profile, *additional_profiles}
            uncovered = sorted(
                check_id
                for check_id in checks
                if not validation_profiles.intersection(
                    manifest_by_id[check_id]["profiles"]
                )
            )
            if uncovered:
                failures.append(
                    f"source profile {profile_id} validation profiles do not cover "
                    f"declared checks: {uncovered}"
                )
        audit = profiles.get("repository-audit", {})
        if audit.get("check_profile") != "full":
            failures.append("repository-audit must route through the full check profile")
        source_tooling = profiles.get("source-tooling", {})
        if "by trigger_paths" not in source_tooling.get("check_selection", ""):
            failures.append("source-tooling must document trigger_paths selection")
    classification = source.get("task_classification")
    if not isinstance(classification, dict):
        failures.append("source context router has no task_classification")
    else:
        if classification.get("schema_version") != TASK_CLASSIFICATION_SCHEMA_VERSION:
            failures.append("source task classification schema is invalid")
        if classification.get("classification_order") != TASK_CLASSES:
            failures.append("source task classification order is invalid")
        if classification.get("default_class") != DEFAULT_TASK_CLASS:
            failures.append("source task classification default is invalid")
        if AMBIGUITY_READ_ONLY_MARKER not in str(
            classification.get("ambiguity_behavior", "")
        ):
            failures.append("source task classification ambiguity must stay read-only")
        small_use = classification.get("small_task_use_when")
        if not isinstance(small_use, list) or not all(
            isinstance(item, str) and item for item in small_use
        ):
            failures.append("source task classification has no small-task triggers")
        elif not any(
            SOURCE_SMALL_TASK_FOCUSED_CHECKS_MARKER in item for item in small_use
        ):
            failures.append("source small-task triggers must require focused source checks")
        expansion = classification.get("expansion_triggers")
        if not isinstance(expansion, list) or not all(
            isinstance(item, str) and item for item in expansion
        ):
            failures.append("source task classification has no expansion triggers")
        else:
            for required in missing_required_values(
                expansion, SOURCE_REQUIRED_EXPANSION_TRIGGERS
            ):
                failures.append(
                    f"source task classification missing expansion trigger {required}"
                )
    overlays = source.get("conditional_overlays")
    worker_overlay = overlays.get("source-worker-strategy") if isinstance(overlays, dict) else None
    if not isinstance(worker_overlay, dict):
        failures.append("source router has no source-worker-strategy overlay")
    else:
        if worker_overlay.get("required_context") != ["docs/source-worker-strategy.md"]:
            failures.append("source worker overlay context is invalid")
        if worker_overlay.get("canonical_rule") != "ALATYR-DELEGATION-001":
            failures.append("source worker overlay canonical rule is invalid")
        if worker_overlay.get("fallback") != "continue with the primary assistant":
            failures.append("source worker overlay fallback is invalid")
    validate_source_worker_policy(source, failures)
    source_bootstrap = [
        *source.get("preloaded_context", []),
        *source.get("bootstrap_context", []),
    ]
    source_limit = source.get("budgets", {}).get("bootstrap_max_words")
    source_words = word_count(source_bootstrap)
    source_headroom = source.get("budgets", {}).get("minimum_headroom_words")
    if not isinstance(source_limit, int) or source_words > source_limit:
        failures.append("source bootstrap exceeds its word budget")
    if (
        not isinstance(source_headroom, int)
        or source_headroom < 100
        or not isinstance(source_limit, int)
        or source_limit - source_words < source_headroom
    ):
        failures.append("source bootstrap does not preserve 100 words of headroom")
    recursive = source.get("recursive_context")
    if not isinstance(recursive, dict) or recursive != {
        "schema_version": 1,
        "framework_index": "framework/context-index.json",
        "max_depth": 8,
        "selection": "follow only entries matched by the selected profile, rule owner, path, contract, dependency, risk, conflict, or failed check",
    }:
        failures.append("source recursive context contract is invalid")
    semantic = source.get("semantic_codebook")
    expected_preload = [
        "alatyr:current-scope-authorization@1",
        "alatyr:canonical-owner@1",
        "alatyr:protected-change@1",
        "alatyr:logical-integrity@1",
        "alatyr:bounded-context-expansion@1",
    ]
    if (
        not isinstance(semantic, dict)
        or semantic.get("schema_version") != 1
        or semantic.get("index") != "framework/semantics/index.json"
        or semantic.get("preload_terms") != expected_preload
    ):
        failures.append("source semantic codebook routing contract is invalid")
    try:
        validate_context_catalog(
            ROOT / "framework/context-index.json", catalog_root=ROOT / "framework"
        )
        resolved_terms = load_codebook(
            ROOT / "framework/semantics/index.json",
            root=ROOT / "framework/semantics",
        )
        if set(resolved_terms) != set(expected_preload):
            failures.append("source semantic preload differs from the codebook")
    except ContextCatalogError as exc:
        failures.append(f"source context catalog or codebook is invalid: {exc}")

    if installer.get("schema_version") != 1 or installer.get("router_kind") != "alatyr-installation-context-router":
        failures.append("installation context router schema or kind is invalid")
    if installer.get("routing_order") != EXPECTED_INSTALL_STAGES:
        failures.append("installation context router stage order is invalid")
    stages = installer.get("stages")
    if not isinstance(stages, dict) or list(stages) != EXPECTED_INSTALL_STAGES:
        failures.append("installation context router stages are incomplete")
    install_bootstrap = [
        *installer.get("preloaded_context", []),
        *installer.get("bootstrap_context", []),
    ]
    install_limit = installer.get("budgets", {}).get("bootstrap_max_words")
    if not isinstance(install_limit, int) or word_count(install_bootstrap) > install_limit:
        failures.append("installation bootstrap exceeds its word budget")

    failures.extend(validate_router_paths(source, "source router"))
    failures.extend(validate_router_paths(installer, "installation router"))

    if inventory != build_inventory():
        failures.append("framework/file-inventory.json is stale")

    entry_points = {
        "AGENTS.md": "tools/source_context_router.json",
        "README.md": "installer/context-router.json",
        "INSTALL.md": "installer/context-router.json",
        "AI_ASSISTANTS.md": "installer/context-router.json",
        "installer/assistant-installation.flow.md": "installer/context-router.json",
    }
    for relpath, required in entry_points.items():
        if required not in (ROOT / relpath).read_text(encoding="utf-8"):
            failures.append(f"{relpath} does not route through {required}")

    require_text(
        SOURCE_AGENTS,
        [
            "framework/context-index.json",
            "framework/semantics/index.json",
            "classify task scale before expansion",
            "## Source-Contour Worker Routing",
            "docs/source-worker-strategy.md",
            "Host and target repositories keep their own active adapter policy",
            "ALATYR-DELEGATION-001",
        ],
        failures,
    )
    require_text(
        SOURCE_ASSISTANTS,
        [
            "framework/context-index.json",
            "framework/semantics/index.json",
            "classify task scale before expansion",
            "docs/source-worker-strategy.md",
            "Host and target",
            "active adapter policy",
        ],
        failures,
    )
    require_text(
        SOURCE_WORKER_STRATEGY,
        [
            "Scope: AlatyrCore source repository only.",
            "Canonical portable rule: `ALATYR-DELEGATION-001`",
            "## Activation",
            "## Model Routing",
            "## Responsibility",
        ],
        failures,
    )

    forbidden = [
        "Read every framework file before copying",
        "Read each framework file before copying",
    ]
    for relpath in ["README.md", "INSTALL.md", "AI_ASSISTANTS.md"]:
        text = (ROOT / relpath).read_text(encoding="utf-8")
        for phrase in forbidden:
            if phrase in text:
                failures.append(f"{relpath} retains broad bootstrap phrase: {phrase}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: checked source and installation routing; "
        f"source_words={source_words} "
        f"installation_words={word_count(install_bootstrap)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
