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
from source_check_manifest import valid_manifest_path
from task_classification_contract import (
    AMBIGUITY_READ_ONLY_MARKER,
    DEFAULT_TASK_CLASS,
    SOURCE_REQUIRED_EXPANSION_TRIGGERS,
    SOURCE_SMALL_TASK_FOCUSED_CHECKS_MARKER,
    TASK_CLASSES,
    TASK_CLASSIFICATION_SCHEMA_VERSION,
    missing_required_values,
)
from source_worker_contract import (
    SourceWorkerContractError,
    load_source_worker_policy,
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
EXPECTED_SMALL_TASK_PROFILES = {"docs-local", "source-tooling"}
REQUIRED_SMALL_TASK_BOUNDARIES = {
    "AGENTS.md",
    "AI_ASSISTANTS.md",
    "INSTALL.md",
    "CHANGELOG.md",
    "VERSION",
    "ADAPTER_SCHEMA_VERSION",
    "TEMPLATE_VERSION",
    "framework/**",
    "installer/**",
    "templates/**",
    "tools/check_manifest.json",
    "tools/source_context_router.json",
    "tools/source_worker_policy.json",
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


def validate_small_task_eligibility(
    classification: dict[str, Any],
    failures: list[str],
) -> None:
    contract = classification.get("small_task_eligibility")
    if not isinstance(contract, dict):
        failures.append("source task classification has no small-task eligibility contract")
        return
    if contract.get("default_enabled") is not False:
        failures.append("source small-task eligibility must be disabled by default")
    maximum = contract.get("maximum_changed_paths")
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum != 1:
        failures.append("source small-task eligibility must allow exactly one changed path")
    profiles = contract.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != EXPECTED_SMALL_TASK_PROFILES:
        failures.append("source small-task eligibility profile set is invalid")
    else:
        for profile_id, profile in profiles.items():
            patterns = (
                profile.get("allowed_path_patterns")
                if isinstance(profile, dict)
                else None
            )
            if (
                not isinstance(patterns, list)
                or not patterns
                or len(patterns) != len(set(patterns))
                or not all(
                    isinstance(item, str) and valid_manifest_path(item)
                    for item in patterns
                )
            ):
                failures.append(
                    f"source small-task profile {profile_id} has invalid path patterns"
                )
    boundaries = contract.get("boundary_path_patterns")
    if (
        not isinstance(boundaries, list)
        or len(boundaries) != len(set(boundaries))
        or not all(
            isinstance(item, str) and valid_manifest_path(item)
            for item in boundaries
        )
    ):
        failures.append("source small-task boundary path patterns are invalid")
    elif not REQUIRED_SMALL_TASK_BOUNDARIES <= set(boundaries):
        failures.append("source small-task boundary path patterns are incomplete")
    for field in [
        "requires_no_unmatched_paths",
        "requires_no_full_fallback",
        "requires_focused_check_coverage",
    ]:
        if contract.get(field) is not True:
            failures.append(f"source small-task eligibility must require {field}")


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
        policy = load_source_worker_policy(SOURCE_WORKER_POLICY, root=ROOT)
    except SourceWorkerContractError as exc:
        failures.append(f"source worker policy is missing or invalid: {exc}")
        return
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

    if candidates:
        unknown = sorted(set(candidates) - set(policy["workstreams"]))
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
        validate_small_task_eligibility(classification, failures)
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

    if installer.get("schema_version") != 2 or installer.get("router_kind") != "alatyr-installation-context-router":
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
