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


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROUTER = ROOT / "tools" / "source_context_router.json"
INSTALL_ROUTER = ROOT / "installer" / "context-router.json"
INVENTORY = ROOT / "framework" / "file-inventory.json"
SOURCE_AGENTS = ROOT / "AGENTS.md"
SOURCE_ASSISTANTS = ROOT / "AI_ASSISTANTS.md"
SOURCE_WORKER_STRATEGY = ROOT / "docs" / "source-worker-strategy.md"
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
        manifest_ids = {check["id"] for check in load_manifest()}
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
            check_profile = profile.get("check_profile")
            if check_profile is not None and check_profile not in ALLOWED_PROFILES:
                failures.append(
                    f"source profile {profile_id} has invalid check profile {check_profile}"
                )
        audit = profiles.get("repository-audit", {})
        if audit.get("check_profile") != "full":
            failures.append("repository-audit must route through the full check profile")
        source_tooling = profiles.get("source-tooling", {})
        if "by trigger_paths" not in source_tooling.get("check_selection", ""):
            failures.append("source-tooling must document trigger_paths selection")
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
    source_bootstrap = [
        *source.get("preloaded_context", []),
        *source.get("bootstrap_context", []),
    ]
    source_limit = source.get("budgets", {}).get("bootstrap_max_words")
    if not isinstance(source_limit, int) or word_count(source_bootstrap) > source_limit:
        failures.append("source bootstrap exceeds its word budget")

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
        f"source_words={word_count(source_bootstrap)} "
        f"installation_words={word_count(install_bootstrap)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
