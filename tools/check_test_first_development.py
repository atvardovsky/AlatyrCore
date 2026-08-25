#!/usr/bin/env python3
"""Validate test-first framework and target-template contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
FRAMEWORK = ROOT / "framework" / "test-first-development.md"
TESTING = ROOT / "framework" / "testing-guidance.md"
POLICY_INDEX = TARGET / ".ai/project/testing/README.md"
POLICY = TARGET / ".ai/project/testing/test-first-policy.json"
INTENT = TARGET / ".ai/assistant/context/intents/test-first-request.json"
CONFIG_FLOW = TARGET / ".ai/assistant/flows/test-first-configuration.flow.md"
CHANGE_FLOW = TARGET / ".ai/assistant/flows/test-first-change.flow.md"
GATE = TARGET / ".ai/assistant/gates/test-first-development.md"
EVIDENCE = TARGET / ".ai/assistant/templates/test-first-evidence.md"
SKILL = TARGET / ".ai/assistant/skills/test-first-development/SKILL.md"
MODULES = TARGET / ".ai/assistant/module-profile.md"
CATALOG = TARGET / ".ai/assistant/operation-catalog.json"
ROUTER = TARGET / ".ai/assistant/context-router.json"
MANIFEST = TARGET / ".ai/alatyr.yaml"
BRIDGES = TARGET / ".ai/assistant/bridge-capability-matrix.md"
SURFACES = ROOT / "conformance/runs/assistant-surfaces.json"
INSTALL = ROOT / "INSTALL.md"
INSTALL_FLOW = ROOT / "installer/assistant-installation.flow.md"
READINESS = ROOT / "installer/readiness-checklist.md"
PLAN = ROOT / "installer/installation-plan-template.md"
LIFECYCLE = ROOT / "framework/lifecycle.md"
RECHECK = TARGET / ".ai/assistant/flows/adapter-recheck.flow.md"
POST_INSTALL = TARGET / ".ai/assistant/templates/post-install-message.md"
POST_UPDATE = TARGET / ".ai/assistant/templates/post-update-message.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(read(path))
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return data


def require(path: Path, snippets: list[str], failures: list[str]) -> None:
    text = " ".join(read(path).split())
    for snippet in snippets:
        if " ".join(snippet.split()) not in text:
            failures.append(f"{path.relative_to(ROOT)} missing {snippet}")


def main() -> int:
    failures: list[str] = []
    required_files = [
        FRAMEWORK, TESTING, POLICY_INDEX, POLICY, INTENT, CONFIG_FLOW,
        CHANGE_FLOW, GATE, EVIDENCE, SKILL, MODULES, CATALOG, ROUTER,
        MANIFEST, BRIDGES,
        INSTALL, INSTALL_FLOW, READINESS, PLAN, LIFECYCLE, RECHECK,
        POST_INSTALL, POST_UPDATE,
    ]
    for path in required_files:
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    require(
        FRAMEWORK,
        [
            "ALATYR-TDD-001", "## Enablement Contract", "## Recommendation Gate",
            "strict-tdd", "regression-first", "characterization-first",
            "contract-first", "test-after-with-reason", "at most one concise recommendation per task",
            "A syntax, import, setup, unavailable-service, or unrelated failure is not valid RED evidence",
        ],
        failures,
    )
    require(
        POLICY_INDEX,
        [
            "Alatyr enable test-first",
            "not a shell command",
            "It is not mandatory unless an enabled accepted target policy",
        ],
        failures,
    )
    require(
        CONFIG_FLOW,
        ["`assess`", "`enable`", "`disable`", "Require target authority", "Do not add dependencies"],
        failures,
    )
    require(
        CHANGE_FLOW,
        ["`required`, `recommended`, `not-indicated`, or `blocked`", "Accept RED only", "same focused contract and command", "test-after-with-reason"],
        failures,
    )
    require(
        GATE,
        ["shown no more than once per task", "Disabled, deferred, or missing module state does not become a blocker", "RED was executed", "GREEN used the same focused contract"],
        failures,
    )
    require(
        SKILL,
        ["Do not activate this placeholder", "Do not accept syntax, setup, infrastructure, or unrelated failure as RED"],
        failures,
    )
    require(
        INSTALL,
        ["ALATYR-TDD-001", "optional test-first owner", ".ai/project/testing/README.md"],
        failures,
    )
    require(
        INSTALL_FLOW,
        ["framework/test-first-development.md", "ALATYR-TDD-001", "test-first-request", "RED/GREEN evidence template"],
        failures,
    )
    require(
        READINESS,
        ["test-first owner", "bounded recommendation behavior", "RED/GREEN/refactor evidence"],
        failures,
    )
    require(
        PLAN,
        ["Test-first-development need", "Recommendation behavior", "Test-first policy state"],
        failures,
    )
    require(
        LIFECYCLE,
        ["When `test-first-development` is enabled", "Preserve target test-first policies", "test-first rule"],
        failures,
    )
    require(
        RECHECK,
        ["Test-first development:", "test-first policy owner", "historical evidence"],
        failures,
    )
    require(
        POST_INSTALL,
        ["Alatyr enable test-first", "Alatyr test first", "non-blocking"],
        failures,
    )
    require(
        POST_UPDATE,
        ["When test-first development is enabled", "RED/GREEN routing"],
        failures,
    )

    try:
        policy = load_json(POLICY)
        intent = load_json(INTENT)
        catalog = load_json(CATALOG)
        router = load_json(ROUTER)
    except (json.JSONDecodeError, ValueError) as exc:
        failures.append(str(exc))
        policy = intent = catalog = router = {}

    if policy.get("schema_version") != 1:
        failures.append("test-first policy schema_version must be 1")
    if policy.get("policy_kind") != "target-test-first-development-policy":
        failures.append("test-first policy_kind is invalid")
    for field in [
        "project", "state", "owner", "decision_authority", "last_reviewed",
        "evidence_revision", "suggestion", "available_modes",
        "activation_triggers", "test_levels", "commands", "isolation",
        "exceptions", "evidence_requirements", "known_gaps",
    ]:
        if field not in policy:
            failures.append(f"test-first policy missing {field}")
    suggestion = policy.get("suggestion")
    if not isinstance(suggestion, dict) or suggestion.get("max_per_task") != 1:
        failures.append("test-first policy must limit suggestions to one per task")
    if not isinstance(suggestion, dict) or suggestion.get("suppress_after_decline") is not True:
        failures.append("test-first policy must suppress repeated declined suggestions")
    if not isinstance(suggestion, dict) or suggestion.get("cost_statement_required") is not True:
        failures.append("test-first policy must require a cost statement")
    if "{" not in read(POLICY):
        failures.append("test-first policy template must remain placeholder-based")

    if intent.get("required_module") != "core-profile":
        failures.append("test-first intent must allow configuration from core-profile")
    expected_candidates = ["test-first-configuration", "test-first-change"]
    if intent.get("operation_candidates") != expected_candidates:
        failures.append("test-first intent operation candidates are invalid")
    overlay = router.get("intent_overlays", {}).get("test-first-request")
    if not isinstance(overlay, dict) or overlay.get("operation_candidates") != expected_candidates:
        failures.append("context router does not expose test-first configuration and execution")

    operations = {
        operation.get("id"): operation
        for operation in catalog.get("operations", [])
        if isinstance(operation, dict)
    }
    configuration = operations.get("test-first-configuration")
    execution = operations.get("test-first-change")
    if not isinstance(configuration, dict) or configuration.get("required_module") != "core-profile":
        failures.append("test-first configuration must remain available before enablement")
    if not isinstance(execution, dict) or execution.get("required_module") != "test-first-development":
        failures.append("test-first execution must require enabled module")
    if not isinstance(configuration, dict) or "Alatyr enable test-first" not in configuration.get("aliases", []):
        failures.append("operation catalog missing enable test-first alias")
    if not isinstance(execution, dict) or "Alatyr test first" not in execution.get("aliases", []):
        failures.append("operation catalog missing test-first execution alias")

    module_text = read(MODULES)
    for path in [
        ".ai/project/testing/README.md",
        ".ai/project/testing/test-first-policy.json",
        ".ai/assistant/context/intents/test-first-request.json",
        ".ai/assistant/flows/test-first-configuration.flow.md",
        ".ai/assistant/flows/test-first-change.flow.md",
        ".ai/assistant/gates/test-first-development.md",
        ".ai/assistant/templates/test-first-evidence.md",
        ".ai/assistant/skills/test-first-development/SKILL.md",
    ]:
        if path not in module_text:
            failures.append(f"module profile missing test-first path {path}")

    manifest_text = read(MANIFEST)
    for snippet in [
        "test_first_development:",
        'policy: ".ai/project/testing/test-first-policy.json"',
        'configuration_flow: ".ai/assistant/flows/test-first-configuration.flow.md"',
        'change_flow: ".ai/assistant/flows/test-first-change.flow.md"',
    ]:
        if snippet not in manifest_text:
            failures.append(f"manifest missing {snippet}")

    surface_count = len(load_json(SURFACES).get("surfaces", []))
    if read(BRIDGES).count("Routes test-first aliases:") != surface_count:
        failures.append(
            "bridge matrix must route test-first aliases on every canonical "
            f"surface ({surface_count})"
        )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("OK: test-first enablement, recommendation, routing, and target templates are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
