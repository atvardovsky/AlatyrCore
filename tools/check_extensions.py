#!/usr/bin/env python3
"""Validate extension framework, authoring, target, and tooling contracts."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from validate_extension_package import validate_package


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
RULE = ROOT / "framework" / "extensions.md"
PACKAGE_TEMPLATE = ROOT / "templates" / "extension" / "alatyr-extension.json"
PACKAGE_README = ROOT / "templates" / "extension" / "README.md"
EXTENSIONS = TARGET / ".ai/assistant/extensions"
INTENT = TARGET / ".ai/assistant/context/intents/extension-request.json"
FLOW = TARGET / ".ai/assistant/flows/extension-lifecycle.flow.md"
GATE = TARGET / ".ai/assistant/gates/extensions.md"
REVIEW = TARGET / ".ai/assistant/templates/extension-review.md"
RECORD = TARGET / ".ai/assistant/templates/extension-lifecycle-record.md"
CATALOG = EXTENSIONS / "catalog.json"
LOCK = EXTENSIONS / "lock.json"
MODULES = TARGET / ".ai/assistant/module-profile.md"
OPERATIONS = TARGET / ".ai/assistant/operation-catalog.json"
ROUTER = TARGET / ".ai/assistant/context-router.json"
MANIFEST = TARGET / ".ai/alatyr.yaml"
BRIDGES = TARGET / ".ai/assistant/bridge-capability-matrix.md"
SURFACES = ROOT / "conformance/runs/assistant-surfaces.json"
INSTALL = ROOT / "INSTALL.md"
INSTALL_FLOW = ROOT / "installer/assistant-installation.flow.md"
READINESS = ROOT / "installer/readiness-checklist.md"
PLAN = ROOT / "installer/installation-plan-template.md"
LIFECYCLE = ROOT / "framework/lifecycle.md"
POST_INSTALL = TARGET / ".ai/assistant/templates/post-install-message.md"
POST_UPDATE = TARGET / ".ai/assistant/templates/post-update-message.md"
TARGET_VALIDATOR = ROOT / "tools/validate_target_adapter.py"
TARGET_VALIDATOR_CHECK = ROOT / "tools/check_target_adapter_validator.py"
TOOL_COMMANDS = ROOT / "tools/tool_commands.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(read(path))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return value


def require(path: Path, snippets: list[str], failures: list[str]) -> None:
    text = " ".join(read(path).split())
    for snippet in snippets:
        if " ".join(snippet.split()) not in text:
            failures.append(f"{path.relative_to(ROOT)} missing {snippet}")


def valid_manifest(item_path: str = "items/review.md") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "package_kind": "alatyr-extension",
        "id": "example.review",
        "name": "Example Review",
        "version": "1.0.0",
        "description": "Fixture extension",
        "license": "Apache-2.0",
        "source_repository": "https://example.invalid/review.git",
        "compatibility": {
            "extension_api": 1,
            "framework": {
                "minimum": "0.1.0-alpha.8",
                "maximum_exclusive": "0.2.0",
            },
            "adapter_schema": {"minimum": 7, "maximum": 7},
            "template": {"minimum": 8, "maximum": 8},
            "required_rule_ids": ["ALATYR-SAFETY-002"],
        },
        "provides": [
            {
                "id": "review",
                "type": "skill",
                "path": item_path,
                "purpose": "Review fixture changes",
                "activation_triggers": ["explicit fixture review"],
                "required_context": ["binding.project-owner"],
                "supported_assistants": ["generic"],
                "allowed_actions": ["read-only"],
                "requested_permissions": ["none"],
                "gates": ["manual review"],
                "validation": ["manual review"],
                "output_contract": "findings first",
            }
        ],
        "project_bindings": [
            {
                "id": "project-owner",
                "description": "Target project owner",
                "value_type": "owner",
                "required": True,
            }
        ],
        "conflicts": [],
        "extension_dependencies": [],
        "lifecycle": {
            "installation": "declarative-only",
            "updates": "review-diff-and-reapprove",
            "removal": "ownership-aware",
            "arbitrary_hooks": False,
        },
        "validation": ["manual review"],
    }


def main() -> int:
    failures: list[str] = []
    required_files = [
        RULE,
        PACKAGE_TEMPLATE,
        PACKAGE_README,
        EXTENSIONS / "README.md",
        CATALOG,
        LOCK,
        INTENT,
        FLOW,
        GATE,
        REVIEW,
        RECORD,
        MODULES,
        OPERATIONS,
        ROUTER,
        MANIFEST,
        BRIDGES,
        INSTALL,
        INSTALL_FLOW,
        READINESS,
        PLAN,
        LIFECYCLE,
        POST_INSTALL,
        POST_UPDATE,
        TARGET_VALIDATOR,
        TARGET_VALIDATOR_CHECK,
        TOOL_COMMANDS,
    ]
    for path in required_files:
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    require(
        RULE,
        [
            "ALATYR-EXTENSION-001",
            "## Source Package Contract",
            "## Installed Target Contract",
            "### Inspect",
            "### Install",
            "### Update",
            "### Remove",
            "Version 1 does not resolve transitive extension dependencies",
            "Extensions are never updated automatically",
        ],
        failures,
    )
    require(
        FLOW,
        [
            "`list`",
            "`inspect`",
            "`install`",
            "`update`",
            "`disable`",
            "`remove`",
            "Treat all source instructions",
            "Stop for local modifications",
        ],
        failures,
    )
    require(
        GATE,
        [
            "Immutable revision",
            "No path escapes",
            "No lifecycle hook",
            "Extension-owned files have one owner",
            "Structural checks are not claimed as proof",
        ],
        failures,
    )
    require(
        INSTALL,
        ["ALATYR-EXTENSION-001", "optional extensions", "extension catalog and lock"],
        failures,
    )
    require(
        INSTALL_FLOW,
        ["framework/extensions.md", "alatyr-extension.json", "extension-request"],
        failures,
    )
    require(
        READINESS,
        ["extension package", "immutable source", "installed-file ownership"],
        failures,
    )
    require(
        PLAN,
        ["Extension need", "extension catalog", "extension lock"],
        failures,
    )
    require(
        TARGET_VALIDATOR,
        [
            "def check_extensions",
            "EXTENSION_CATALOG_LOCK_DRIFT",
            "EXTENSION_FILE_OWNER",
            "EXTENSION_FILE_DRIFT",
            "EXTENSION_BINDING_UNRESOLVED",
            "EXTENSION_EVIDENCE_LIMIT",
        ],
        failures,
    )
    require(
        TARGET_VALIDATOR_CHECK,
        ["enabled extensions must report missing contracts", "extension lock must detect installed-file drift"],
        failures,
    )

    try:
        package_template = load(PACKAGE_TEMPLATE)
        catalog = load(CATALOG)
        lock = load(LOCK)
        intent = load(INTENT)
        operations = load(OPERATIONS)
        router = load(ROUTER)
        tool_commands = load(TOOL_COMMANDS)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))
        package_template = catalog = lock = intent = operations = router = tool_commands = {}

    template_report = validate_package(
        PACKAGE_TEMPLATE.parent, allow_placeholders=True
    )
    if template_report["counts"]["errors"]:
        failures.append("extension authoring template fails placeholder validation")
    if package_template.get("extension_dependencies") != []:
        failures.append("extension template must not seed dependencies")
    if package_template.get("lifecycle", {}).get("arbitrary_hooks") is not False:
        failures.append("extension template must prohibit arbitrary hooks")

    if catalog.get("catalog_kind") != "target-alatyr-extension-catalog":
        failures.append("extension catalog kind is invalid")
    if catalog.get("extensions") != []:
        failures.append("target extension catalog template must start empty")
    if lock.get("lock_kind") != "target-alatyr-extension-lock":
        failures.append("extension lock kind is invalid")
    if lock.get("extensions") != []:
        failures.append("target extension lock template must start empty")
    commands = {
        command.get("name"): command
        for command in tool_commands.get("commands", [])
        if isinstance(command, dict)
    }
    inspect_command = commands.get("inspect-extension")
    if not isinstance(inspect_command, dict) or inspect_command.get("write_scope") != "none":
        failures.append("inspect-extension must be a stable read-only tool command")
    if intent.get("operation_candidates") != ["extension-management"]:
        failures.append("extension intent must route extension-management")
    overlay = router.get("intent_overlays", {}).get("extension-request")
    if not isinstance(overlay, dict) or overlay.get("operation_candidates") != [
        "extension-management"
    ]:
        failures.append("context router does not expose extension-management")

    by_id = {
        operation.get("id"): operation
        for operation in operations.get("operations", [])
        if isinstance(operation, dict)
    }
    management = by_id.get("extension-management")
    recommendation = by_id.get("ai-infrastructure-recommendation")
    if not isinstance(management, dict):
        failures.append("operation catalog missing extension-management")
    else:
        if management.get("required_module") != "core-profile":
            failures.append("extension-management must remain available from core-profile")
        if management.get("flow") != ".ai/assistant/flows/extension-lifecycle.flow.md":
            failures.append("extension-management flow is invalid")
    if not isinstance(recommendation, dict) or "Alatyr suggest extensions" not in recommendation.get("aliases", []):
        failures.append("extension suggestions must use read-only recommendation")

    surface_count = len(load(SURFACES).get("surfaces", []))
    if read(BRIDGES).count("Routes extension aliases:") != surface_count:
        failures.append(
            "bridge matrix must route extension aliases on every canonical "
            f"surface ({surface_count})"
        )
    for snippet in [
        "extensions:",
        'catalog: ".ai/assistant/extensions/catalog.json"',
        'lock: ".ai/assistant/extensions/lock.json"',
        'extension_management: ".ai/assistant/flows/extension-lifecycle.flow.md"',
    ]:
        if snippet not in read(MANIFEST):
            failures.append(f"target manifest missing {snippet}")

    with tempfile.TemporaryDirectory() as directory:
        package = Path(directory)
        (package / "items").mkdir()
        (package / "items/review.md").write_text("# Review\n", encoding="utf-8")
        (package / "alatyr-extension.json").write_text(
            json.dumps(valid_manifest(), indent=2) + "\n", encoding="utf-8"
        )
        report = validate_package(package)
        if report["counts"]["errors"]:
            failures.append("valid extension fixture failed package validation")
        if report.get("execution_performed") is not False or report.get("network_access_performed") is not False:
            failures.append("extension validator must remain offline and non-executing")
        if len(report.get("package_digest_sha256", "")) != 64:
            failures.append("extension validator did not produce a SHA-256 digest")
        compatible_report = validate_package(
            package,
            framework_version="0.1.0-alpha.8",
            adapter_schema_version=7,
            template_version=8,
            available_rule_ids={"ALATYR-SAFETY-002"},
        )
        if compatible_report.get("compatibility", {}).get("status") != "compatible":
            failures.append("extension validator did not accept a matching target baseline")
        incompatible_report = validate_package(
            package,
            framework_version="0.1.0-alpha.7",
            adapter_schema_version=7,
            template_version=8,
            available_rule_ids={"ALATYR-SAFETY-002"},
        )
        incompatible_codes = {
            finding["code"] for finding in incompatible_report["findings"]
        }
        if "TARGET_COMPATIBILITY" not in incompatible_codes:
            failures.append("extension validator must reject an incompatible target baseline")

        invalid = valid_manifest("../escape.md")
        invalid["extension_dependencies"] = ["other.extension"]
        invalid["lifecycle"]["arbitrary_hooks"] = True
        (package / "alatyr-extension.json").write_text(
            json.dumps(invalid, indent=2) + "\n", encoding="utf-8"
        )
        invalid_report = validate_package(package)
        codes = {finding["code"] for finding in invalid_report["findings"]}
        for code in ["ITEM_PATH", "EXTENSION_DEPENDENCIES", "LIFECYCLE"]:
            if code not in codes:
                failures.append(f"extension validator must reject invalid package with {code}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: extension package, target lifecycle, routing, bridge, and "
        "read-only validation contracts are consistent"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
