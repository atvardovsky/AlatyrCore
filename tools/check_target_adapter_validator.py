#!/usr/bin/env python3
"""Exercise stable contracts of the portable target adapter validator."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from framework_packaging import FRAMEWORK_ROOT, projected_framework_contents
from validate_target_adapter import (
    AdapterValidatorConfig,
    Finding,
    Validator,
    approval_enforcement_enabled,
    extract_list_field,
    findings_payload,
    git_changed_files,
    result_code,
    scope_entries_cover,
)

ROOT = Path(__file__).resolve().parents[1]


def validator(target: Path, framework_source: Path | None = None) -> Validator:
    return Validator(
        target,
        framework_source=framework_source,
        diff_ref=None,
        approval_records=[],
        enforce_approval_scope=False,
        change_packages=[],
        enforce_change_package=False,
        migration_diff=None,
        allow_placeholders=True,
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
    )


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    if not approval_enforcement_enabled(
        diff_ref="HEAD",
        approval_records=[Path("approval.json")],
        explicitly_enforced=False,
    ):
        failures.append("explicit approval plus diff must enable scope enforcement")
    if approval_enforcement_enabled(
        diff_ref="HEAD",
        approval_records=[],
        explicitly_enforced=False,
    ):
        failures.append("diff inspection without selected approval must remain advisory")
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory)
        router_path = target / ".ai" / "assistant" / "context-router.json"
        profiles_path = target / ".ai" / "assistant" / "context-profiles.md"
        profiles_path.parent.mkdir(parents=True, exist_ok=True)
        profiles_path.write_text("# Profiles\n", encoding="utf-8")
        write_json(
            router_path,
            {
                "schema_version": 1,
                "router_kind": "target-context-router",
                "human_reference": ".ai/assistant/context-profiles.md",
                "routing_order": ["docs-local"],
                "profiles": {},
            },
        )
        legacy = validator(target)
        legacy.check_router()
        legacy_codes = {finding.code for finding in legacy.findings}
        if "ROUTER_SCHEMA_LEGACY" not in legacy_codes:
            failures.append("schema-1 router must produce a migration warning")
        for forbidden in [
            "ROUTER_PRELOADED",
            "ROUTER_BOOTSTRAP",
            "ROUTER_BUDGETS_MISSING",
            "ROUTER_RECEIPT_MISSING",
        ]:
            if forbidden in legacy_codes:
                failures.append(
                    f"schema-1 router must not receive schema-2 finding {forbidden}"
                )

        large_context_path = target / ".ai" / "framework" / "large-context.md"
        large_context_path.parent.mkdir(parents=True, exist_ok=True)
        large_context_path.write_text("one two three four five\n", encoding="utf-8")
        budget_validator = validator(target)
        budget_validator.check_installed_context_costs(
            {"preloaded_context": [], "bootstrap_context": [], "profile_index": {}},
            {
                "docs-local": {
                    "required_context": [".ai/framework/large-context.md"]
                }
            },
            {
                "bootstrap": {"max_files": 4, "max_words": 100},
                "profile_default": {
                    "max_files": 4,
                    "max_total_words": 100,
                    "max_portable_words": 1,
                },
            },
        )
        if "ROUTER_PROFILE_COST" not in {
            finding.code for finding in budget_validator.findings
        }:
            failures.append("portable context over-budget must produce ROUTER_PROFILE_COST")

        pack_target = target / "pack-target"
        framework_target = pack_target / ".ai" / "framework"
        framework_target.mkdir(parents=True)
        manifest_path = pack_target / ".ai" / "alatyr.yaml"
        manifest_path.write_text("framework:\n  pack: core\n", encoding="utf-8")
        for name, content in projected_framework_contents("core").items():
            destination = framework_target / name
            if content is None:
                destination.write_bytes((FRAMEWORK_ROOT / name).read_bytes())
            else:
                destination.write_bytes(content.encode("utf-8"))
        pack_validator = validator(pack_target, ROOT)
        pack_validator.check_framework_baseline()
        pack_drift = [
            finding
            for finding in pack_validator.findings
            if finding.code.startswith("FRAMEWORK_")
        ]
        if pack_drift:
            failures.append(
                "fresh selective framework pack must match its projected baseline: "
                + ", ".join(finding.code for finding in pack_drift)
            )

        inventory_path = framework_target / "file-inventory.json"
        original_inventory = inventory_path.read_text(encoding="utf-8")
        inventory = json.loads(original_inventory)
        inventory["files"][0]["sha256"] = "0" * 64
        write_json(inventory_path, inventory)
        tampered_inventory_validator = validator(pack_target, ROOT)
        tampered_inventory_validator.check_framework_baseline()
        tampered_inventory_codes = {
            finding.code for finding in tampered_inventory_validator.findings
        }
        if "FRAMEWORK_PACK_INVENTORY_DIGEST_DRIFT" not in tampered_inventory_codes:
            failures.append("selective pack must detect a self-declared digest change")
        if "FRAMEWORK_PACK_INVENTORY_CONTENT_DRIFT" not in tampered_inventory_codes:
            failures.append("selective pack must detect projected inventory tampering")
        if result_code(
            tampered_inventory_validator.findings, strict_warnings=False
        ) != 1:
            failures.append("framework integrity drift must fail without strict warnings")
        drift_payload = findings_payload(
            tampered_inventory_validator.findings,
            target=pack_target,
            strict_warnings=False,
        )
        if drift_payload.get("adapter_health", {}).get("state") != "blocked":
            failures.append("framework integrity drift must block adapter health")
        if drift_payload.get("counts", {}).get("blocking_warnings", 0) < 1:
            failures.append("validator JSON must count blocking warnings")
        inventory_path.write_text(original_inventory, encoding="utf-8")

        registry_path = framework_target / "rule-registry.json"
        original_registry = registry_path.read_text(encoding="utf-8")
        registry = json.loads(original_registry)
        registry["rules"] = registry["rules"][1:]
        write_json(registry_path, registry)
        tampered_registry_validator = validator(pack_target, ROOT)
        tampered_registry_validator.check_framework_baseline()
        if "FRAMEWORK_PACK_REGISTRY_DRIFT" not in {
            finding.code for finding in tampered_registry_validator.findings
        }:
            failures.append("selective pack must detect projected registry tampering")
        registry_path.write_text(original_registry, encoding="utf-8")

        capability_target = target / "capability-target"
        capability_framework = capability_target / ".ai" / "framework"
        capability_framework.mkdir(parents=True)
        (capability_framework / "capabilities.json").write_bytes(
            (ROOT / "framework" / "capabilities.json").read_bytes()
        )
        capability_manifest = capability_target / ".ai" / "alatyr.yaml"
        capability_manifest.write_text(
            "framework:\n  pack: complete\nmodules:\n  enabled:\n    - extensions\n",
            encoding="utf-8",
        )
        capability_check = validator(capability_target)
        parsed_capability_manifest = capability_check.check_manifest()
        capability_check.check_capability_closure(parsed_capability_manifest)
        capability_codes = {finding.code for finding in capability_check.findings}
        if "CAPABILITY_DEPENDENCY_MISSING" not in capability_codes:
            failures.append("enabled module dependency closure must be enforced")
        if "CAPABILITY_TARGET_FILE_MISSING" not in capability_codes:
            failures.append("enabled module target-file closure must be enforced")

        write_json(
            router_path,
            {
                "schema_version": 2,
                "router_kind": "target-context-router",
                "human_reference": ".ai/assistant/context-profiles.md",
                "preloaded_context": ["AGENTS.md"],
                "bootstrap_context": [
                    ".ai/alatyr.yaml",
                    ".ai/README.md",
                    ".ai/assistant/context-router.json",
                ],
                "context_budgets": {},
                "context_receipt": {},
                "routing_order": ["docs-local"],
                "profiles": {},
            },
        )
        migration = validator(target)
        migration.check_router()
        migration_codes = {finding.code for finding in migration.findings}
        if "ROUTER_MIGRATION_MISSING" not in migration_codes:
            failures.append("schema-2 router must require migration-first routing")

        catalog_path = target / ".ai" / "assistant" / "operation-catalog.json"
        write_json(
            catalog_path,
            {
                "schema_version": 1,
                "catalog_kind": "target-operation-catalog",
                "fallback_operation": "help",
                "compact_help": ".ai/assistant/help.md",
                "human_reference": ".ai/assistant/help-reference.md",
                "routing_flow": ".ai/assistant/flows/operation-routing.flow.md",
                "health_flow": ".ai/assistant/flows/adapter-health.flow.md",
                "pre_change_preview": ".ai/assistant/templates/pre-change-preview.md",
                "module_profile": ".ai/assistant/module-profile.md",
                "operations": [
                    {
                        "id": operation_id,
                        "title": operation_id,
                        "summary": "fixture operation",
                        "use_when": ["fixture"],
                        "context_profiles": ["docs-local"],
                        "required_module": "core-profile",
                        "flow": ".ai/assistant/flows/operation-routing.flow.md",
                        "minimum_inputs": ["fixture"],
                        "allowed_actions": ["read-only"],
                        "preview": "never",
                        "aliases": [alias],
                        "final_evidence": ["fixture evidence"],
                    }
                    for operation_id, alias in [
                        ("help", "Alatyr"),
                        ("adapter-health", "Alatyr status"),
                    ]
                ],
            },
        )
        write_json(
            router_path,
            {
                "schema_version": 2,
                "router_kind": "target-context-router",
                "human_reference": ".ai/assistant/context-profiles.md",
                "bootstrap_context": [
                    ".ai/alatyr.yaml",
                    ".ai/README.md",
                    ".ai/assistant/context-router.json",
                ],
                "operation_routing": {
                    "catalog": ".ai/assistant/operation-catalog.json",
                    "health_operation": "adapter-health",
                },
                "profiles": {
                    "docs-local": {
                        "operation_candidates": ["unknown-operation"]
                    }
                },
            },
        )
        catalog_validator = validator(target)
        catalog_validator.check_operation_catalog()
        catalog_codes = {finding.code for finding in catalog_validator.findings}
        if "OPERATION_CANDIDATE_UNKNOWN" not in catalog_codes:
            failures.append("operation catalog must reject unknown profile candidates")

        module_profile_path = target / ".ai" / "assistant" / "module-profile.md"
        module_profile_path.write_text(
            "# Module Profile\n\nModule: `diagrams`\nState: `enabled`\n",
            encoding="utf-8",
        )
        diagrams = validator(target)
        diagrams.check_discussion_diagrams(None)
        diagram_codes = {finding.code for finding in diagrams.findings}
        for required in [
            "DIAGRAM_REQUIRED_FILE_MISSING",
            "DIAGRAM_OPERATION_MISSING",
            "DIAGRAM_OPERATION_UNROUTED",
            "DIAGRAM_BRIDGE_CAPABILITY_MISSING",
        ]:
            if required not in diagram_codes:
                failures.append(f"broken diagram module missing finding {required}")

        diagram_flow = (
            target / ".ai" / "assistant" / "flows" / "diagram-discussion.flow.md"
        )
        diagram_flow.parent.mkdir(parents=True, exist_ok=True)
        diagram_flow.write_text(
            "`read-only` current assistant surface record portable ASCII view "
            "hard maximum of 100 columns stable diagram ID "
            "Classify data sensitivity\n",
            encoding="utf-8",
        )
        diagram_presentation = (
            target / ".ai" / "assistant" / "templates" / "diagram-presentation.md"
        )
        diagram_presentation.parent.mkdir(parents=True, exist_ok=True)
        diagram_presentation.write_text(
            "Presentation mode:\nPortable ASCII presentation:\n"
            "ASCII readability check:\nDiagram ID:\n"
            "Data classification:\nExternal renderer or network action:\n"
            "is not project source of truth\n",
            encoding="utf-8",
        )
        ascii_presentation = (
            target / ".ai" / "assistant" / "templates" / "ascii-diagram.md"
        )
        ascii_presentation.write_text(
            "Hard maximum width: `100`\n"
            "printable 7-bit ASCII plus line feeds\n"
            "Longest line at most 100 columns\n",
            encoding="utf-8",
        )
        matrix_path = target / ".ai" / "assistant" / "bridge-capability-matrix.md"
        matrix_path.write_text(
            "### Assistant Surface: `generic`\n\n"
            "Diagram capability record: "
            "`.ai/assistant/assistant-capabilities/generic.json`\n",
            encoding="utf-8",
        )
        write_json(
            target / ".ai" / "assistant" / "assistant-capabilities.json",
            {
                "schema_version": 2,
                "capability_kind": "target-assistant-capability-index",
                "surfaces": {
                    "generic": ".ai/assistant/assistant-capabilities/generic.json"
                },
            },
        )
        write_json(
            target / ".ai" / "assistant" / "assistant-capabilities" / "generic.json",
            {
                "schema_version": 1,
                "capability_kind": "target-assistant-surface-capabilities",
                "assistant_surface": "generic",
                "diagram_discussion": {
                    "route": "maybe",
                    "native_inline_syntaxes": ["unknown"],
                    "artifact_presentation": "maybe",
                    "readable_fallback": "text",
                    "verified_at": "unknown",
                    "expires_at": "unknown",
                    "review_triggers": [],
                    "client_version": "unknown",
                    "evidence": "manual review",
                },
            },
        )
        capability_validator = validator(target)
        capability_validator.check_discussion_diagrams(None)
        capability_codes = {
            finding.code for finding in capability_validator.findings
        }
        for required in [
            "DIAGRAM_CAPABILITY_ROUTE",
            "DIAGRAM_CAPABILITY_ARTIFACT",
            "DIAGRAM_CAPABILITY_FRESHNESS",
            "DIAGRAM_CAPABILITY_CLIENT_VERSION",
            "DIAGRAM_CAPABILITY_ASCII_FALLBACK",
        ]:
            if required not in capability_codes:
                failures.append(
                    f"invalid diagram capability missing finding {required}"
                )

        module_profile_path.write_text(
            "# Module Profile\n\n"
            "Module: `architecture-knowledge`\nState: `enabled`\n",
            encoding="utf-8",
        )
        architecture = validator(target)
        architecture.check_architecture_knowledge(None)
        if "ARCHITECTURE_REQUIRED_FILE_MISSING" not in {
            finding.code for finding in architecture.findings
        }:
            failures.append(
                "enabled architecture knowledge must report missing contracts"
            )

        module_profile_path.write_text(
            "# Module Profile\n\n"
            "Module: `code-documentation`\nState: `enabled`\n",
            encoding="utf-8",
        )
        code_documentation = validator(target)
        code_documentation.check_code_documentation(None)
        if "CODEDOC_REQUIRED_FILE_MISSING" not in {
            finding.code for finding in code_documentation.findings
        }:
            failures.append(
                "enabled code documentation must report missing contracts"
            )

        module_profile_path.write_text(
            "# Module Profile\n\n"
            "Module: `project-vocabulary`\nState: `enabled`\n",
            encoding="utf-8",
        )
        project_vocabulary = validator(target)
        project_vocabulary.check_project_vocabulary(None)
        if "VOCABULARY_REQUIRED_FILE_MISSING" not in {
            finding.code for finding in project_vocabulary.findings
        }:
            failures.append(
                "enabled project vocabulary must report missing contracts"
            )

        module_profile_path.write_text(
            "# Module Profile\n\n"
            "Module: `test-first-development`\nState: `enabled`\n",
            encoding="utf-8",
        )
        test_first = validator(target)
        test_first.check_test_first_development(None)
        if "TDD_REQUIRED_FILE_MISSING" not in {
            finding.code for finding in test_first.findings
        }:
            failures.append(
                "enabled test-first development must report missing contracts"
            )

        test_first_paths = [
            ".ai/project/testing/README.md",
            ".ai/project/testing/test-first-policy.json",
            ".ai/assistant/context/intents/test-first-request.json",
            ".ai/assistant/flows/test-first-configuration.flow.md",
            ".ai/assistant/flows/test-first-change.flow.md",
            ".ai/assistant/gates/test-first-development.md",
            ".ai/assistant/templates/test-first-evidence.md",
            ".ai/assistant/skills/test-first-development/SKILL.md",
            ".ai/framework/test-first-development.md",
        ]
        for relpath in test_first_paths:
            path = target / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("test-first contract fixture\n", encoding="utf-8")
        write_json(
            target / ".ai/project/testing/test-first-policy.json",
            {
                "schema_version": 1,
                "policy_kind": "target-test-first-development-policy",
                "project": "fixture",
                "state": "enabled",
                "owner": "test-owner",
                "decision_authority": "test-authority",
                "last_reviewed": "2026-08-12",
                "evidence_revision": "fixture-revision",
                "suggestion": {
                    "mode": "advisory",
                    "minimum_result": "recommended",
                    "max_per_task": 1,
                    "suppress_after_decline": True,
                    "cost_statement_required": True,
                },
                "available_modes": ["regression-first"],
                "activation_triggers": [
                    {
                        "id": "defect",
                        "state": "recommended",
                        "changed_fact_classes": ["behavior"],
                        "conditions": ["reproducible defect"],
                        "mode": "regression-first",
                        "test_level_ids": ["missing-level"],
                        "exceptions": ["missing-exception"],
                    }
                ],
                "test_levels": [
                    {
                        "id": "unit",
                        "purpose": "observable behavior",
                        "paths": ["tests"],
                        "command_ids": ["missing-command"],
                        "feedback_time": "fast",
                        "fixtures_and_helpers": ["fixture builder"],
                    }
                ],
                "commands": [
                    {
                        "id": "unit-test",
                        "command": "fixture test command",
                        "scope": "unit",
                        "live_external_actions": "forbidden",
                    }
                ],
                "isolation": {
                    "clock": "fake",
                    "randomness": "seeded",
                    "database": "isolated",
                    "queue": "fake",
                    "filesystem": "temporary",
                    "network": "forbidden",
                    "secrets": "not available",
                },
                "exceptions": [],
                "evidence_requirements": ["RED and GREEN"],
                "known_gaps": [],
            },
        )
        bad_references = validator(target)
        bad_references.check_test_first_development(None)
        bad_reference_codes = {
            finding.code for finding in bad_references.findings
        }
        for required in [
            "TDD_COMMAND_REFERENCE",
            "TDD_TEST_LEVEL_REFERENCE",
            "TDD_EXCEPTION_REFERENCE",
        ]:
            if required not in bad_reference_codes:
                failures.append(
                    f"test-first policy must reject invalid references with {required}"
                )

        valid_policy_path = target / ".ai/project/testing/test-first-policy.json"
        valid_policy = json.loads(valid_policy_path.read_text(encoding="utf-8"))
        valid_policy["activation_triggers"][0]["test_level_ids"] = ["unit"]
        valid_policy["activation_triggers"][0]["exceptions"] = []
        valid_policy["test_levels"][0]["command_ids"] = ["unit-test"]
        write_json(valid_policy_path, valid_policy)
        write_json(
            catalog_path,
            {
                "operations": [
                    {
                        "id": "test-first-configuration",
                        "required_module": "core-profile",
                    },
                    {
                        "id": "test-first-change",
                        "required_module": "test-first-development",
                    },
                ]
            },
        )
        write_json(
            router_path,
            {
                "intent_overlays": {
                    "test-first-request": {
                        "operation_candidates": [
                            "test-first-configuration",
                            "test-first-change",
                        ]
                    }
                }
            },
        )
        enabled_policy = validator(target)
        enabled_policy.check_test_first_development(None)
        enabled_errors = [
            finding.code
            for finding in enabled_policy.findings
            if finding.level == "error" and finding.code.startswith("TDD_")
        ]
        if enabled_errors:
            failures.append(
                "resolved enabled test-first policy produced errors: "
                + ", ".join(enabled_errors)
            )

        module_profile_path.write_text(
            "# Module Profile\n\nModule: `extensions`\nState: `enabled`\n",
            encoding="utf-8",
        )
        missing_extensions = validator(target)
        missing_extensions.check_extensions(None)
        if "EXTENSION_REQUIRED_FILE_MISSING" not in {
            finding.code for finding in missing_extensions.findings
        }:
            failures.append("enabled extensions must report missing contracts")

        extension_contract_paths = [
            ".ai/assistant/extensions/README.md",
            ".ai/assistant/extensions/catalog.json",
            ".ai/assistant/extensions/lock.json",
            ".ai/assistant/context/intents/extension-request.json",
            ".ai/assistant/flows/extension-lifecycle.flow.md",
            ".ai/assistant/gates/extensions.md",
            ".ai/assistant/templates/extension-review.md",
            ".ai/assistant/templates/extension-lifecycle-record.md",
            ".ai/framework/extensions.md",
        ]
        for relpath in extension_contract_paths:
            path = target / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("extension contract fixture\n", encoding="utf-8")

        extension_id = "example.review"
        extension_root = target / ".ai/assistant/extensions" / extension_id
        extension_root.mkdir(parents=True, exist_ok=True)
        manifest_path = extension_root / "manifest.json"
        bindings_path = extension_root / "bindings.json"
        item_path = extension_root / "items" / "review.md"
        adaptation_path = extension_root / "adaptation-record.md"
        approval_path = target / ".ai/assistant/approvals/extension.json"
        rule_registry_path = target / ".ai/framework/rule-registry.json"
        write_json(
            manifest_path,
            {
                "schema_version": 1,
                "package_kind": "alatyr-extension",
                "id": extension_id,
                "version": "1.0.0",
                "provides": [{"id": "review", "type": "skill", "path": "items/review.md"}],
            },
        )
        write_json(
            bindings_path,
            {
                "schema_version": 1,
                "binding_kind": "target-alatyr-extension-bindings",
                "extension_id": extension_id,
                "bindings": [
                    {
                        "id": "project-owner",
                        "value": "fixture-owner",
                        "owner": "fixture-owner",
                        "source": ".ai/project/contour.md",
                    }
                ],
            },
        )
        item_path.parent.mkdir(parents=True, exist_ok=True)
        item_path.write_text("normalized review item\n", encoding="utf-8")
        adaptation_path.write_text("review and approval evidence\n", encoding="utf-8")
        write_json(approval_path, {"approval_id": "extension-fixture"})
        write_json(rule_registry_path, {"schema_version": 1, "rules": []})

        def extension_hash(path: Path) -> str:
            return hashlib.sha256(path.read_bytes()).hexdigest()

        installed_files = [
            {
                "path": path.relative_to(target).as_posix(),
                "sha256": extension_hash(path),
                "owner": extension_id,
            }
            for path in [manifest_path, bindings_path, item_path, adaptation_path]
        ]
        catalog_entry = {
            "id": extension_id,
            "version": "1.0.0",
            "state": "active",
            "owner": "fixture-owner",
            "lock_id": "extension-fixture-lock",
            "manifest": manifest_path.relative_to(target).as_posix(),
            "bindings": bindings_path.relative_to(target).as_posix(),
            "item_ids": ["review"],
            "supported_assistants": ["generic"],
            "last_reviewed": "2026-08-12",
            "evidence_revision": "fixture-revision",
            "known_gaps": [],
        }
        lock_entry = {
            "id": extension_id,
            "lock_id": "extension-fixture-lock",
            "version": "1.0.0",
            "state": "active",
            "source_type": "git-url",
            "source": "https://example.invalid/review.git",
            "source_revision": "0123456789abcdef0123456789abcdef01234567",
            "package_digest_sha256": "a" * 64,
            "license_status": "accepted",
            "compatibility": {"result": "compatible"},
            "manifest": manifest_path.relative_to(target).as_posix(),
            "bindings": bindings_path.relative_to(target).as_posix(),
            "adaptation_record": adaptation_path.relative_to(target).as_posix(),
            "installed_files": installed_files,
            "integration_surfaces": [".ai/assistant/operation-catalog.json"],
            "approval_record": approval_path.relative_to(target).as_posix(),
            "validation": ["fixture structural validation passed"],
            "installed_at": "2026-08-12T00:00:00Z",
        }
        write_json(
            target / ".ai/assistant/extensions/catalog.json",
            {
                "schema_version": 1,
                "catalog_kind": "target-alatyr-extension-catalog",
                "extension_api": 1,
                "owner": "fixture-owner",
                "last_reviewed": "2026-08-12",
                "extensions": [catalog_entry],
            },
        )
        write_json(
            target / ".ai/assistant/extensions/lock.json",
            {
                "schema_version": 1,
                "lock_kind": "target-alatyr-extension-lock",
                "extension_api": 1,
                "target_baseline": {
                    "framework_version": "0.1.0-alpha.8",
                    "adapter_schema_version": 7,
                    "template_version": 8,
                    "rule_registry": ".ai/framework/rule-registry.json",
                },
                "extensions": [lock_entry],
            },
        )
        write_json(
            catalog_path,
            {
                "operations": [
                    {"id": "extension-management", "required_module": "core-profile"}
                ]
            },
        )
        installed_extension = validator(target)
        installed_extension.check_extensions(None)
        extension_errors = [
            finding.code
            for finding in installed_extension.findings
            if finding.level == "error" and finding.code.startswith("EXTENSION_")
        ]
        if extension_errors:
            failures.append(
                "resolved installed extension produced errors: "
                + ", ".join(extension_errors)
            )
        item_path.write_text("locally modified review item\n", encoding="utf-8")
        drifted_extension = validator(target)
        drifted_extension.check_extensions(None)
        if "EXTENSION_FILE_DRIFT" not in {
            finding.code for finding in drifted_extension.findings
        }:
            failures.append("extension lock must detect installed-file drift")

        module_profile_path.write_text(
            "# Module Profile\n\n"
            "Module: `architecture-knowledge`\nState: `enabled`\n",
            encoding="utf-8",
        )

        architecture_text_files = {
            ".ai/project/architecture/README.md": (
                "## Status Meanings\n## Architecture Patterns And Items\n"
                "Evidence revision:\n"
            ),
            ".ai/assistant/context/intents/architecture-request.json": "{}\n",
            ".ai/assistant/flows/architecture-assistance.flow.md": (
                "## Routing Modes\nno-change baseline\n"
                "reuse of an accepted project pattern\n"
                "adaptation of an existing pattern\nnew pattern\n"
                "`docs-only`\n`full-with-approval`\n"
            ),
            ".ai/assistant/templates/architecture-pattern.md": (
                "Pattern ID:\nProblem addressed:\nRules and invariants:\n"
                "Do not use when:\nLast verified revision:\n"
            ),
            ".ai/assistant/templates/architecture-area.md": (
                "Area ID:\nResponsibilities:\nPattern IDs:\n"
                "Validation or fitness checks:\n"
            ),
            ".ai/assistant/templates/architecture-discussion-result.md": (
                "No-change baseline:\nReuse accepted project pattern:\n"
                "Adapt existing project pattern:\nIntroduce new pattern:\n"
                "Pattern-proliferation result:\n"
            ),
            ".ai/framework/architecture-knowledge.md": (
                "# Architecture Knowledge\n"
            ),
        }
        for relpath, content in architecture_text_files.items():
            path = target / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        write_json(
            target / ".ai" / "project" / "architecture" / "catalog.json",
            {
                "schema_version": 1,
                "catalog_kind": "target-architecture-knowledge-catalog",
                "project": "fixture",
                "module_state": "enabled",
                "human_index": ".ai/project/architecture/README.md",
                "architecture_owner": "architecture-team",
                "decision_authority": "architecture-board",
                "canonical_sources": ["docs/architecture.md"],
                "decision_sources": ["docs/decisions"],
                "last_reviewed": "2026-08-03",
                "evidence_revision": "fixture-revision",
                "areas": [
                    {
                        "id": "area-core",
                        "name": "Core",
                        "status": "accepted",
                        "owner": "core-team",
                        "detail": "docs/core.md",
                        "evidence": ["src/core"],
                        "pattern_ids": ["missing-pattern"],
                    },
                    {
                        "id": "area-core",
                        "name": "Duplicate",
                        "status": "observed",
                        "owner": "core-team",
                        "detail": "docs/core.md",
                        "evidence": ["src/core"],
                        "pattern_ids": [],
                    },
                ],
                "patterns": [
                    {
                        "id": "pattern-layered",
                        "name": "Layered",
                        "kind": "invalid-kind",
                        "status": "accepted",
                        "scope": ["area-core"],
                        "problem": "dependency direction",
                        "decision_owner": "architecture-board",
                        "decision_record": "{UNRESOLVED_DECISION_RECORD}",
                        "detail": "docs/patterns/layered.md",
                        "evidence": ["src/core"],
                        "validation": ["architecture check"],
                        "related_pattern_ids": ["missing-pattern"],
                        "last_verified_revision": "fixture-revision",
                    }
                ],
                "known_gaps": [],
            },
        )
        invalid_architecture = validator(target)
        invalid_architecture.check_architecture_knowledge(None)
        invalid_architecture_codes = {
            finding.code for finding in invalid_architecture.findings
        }
        for required in [
            "ARCHITECTURE_AREA_ID_DUPLICATE",
            "ARCHITECTURE_PATTERN_KIND",
            "ARCHITECTURE_PATTERN_REFERENCE",
            "ARCHITECTURE_ACCEPTED_EVIDENCE",
            "ARCHITECTURE_OPERATION_MISSING",
            "ARCHITECTURE_OPERATION_UNROUTED",
        ]:
            if required not in invalid_architecture_codes:
                failures.append(
                    f"invalid architecture catalog missing finding {required}"
                )

        routing_path = (
            target / ".ai" / "assistant" / "flows" / "operation-routing.flow.md"
        )
        routing_path.parent.mkdir(parents=True, exist_ok=True)
        routing_path.write_text(
            "Load bootstrap context only. Do not load all `.ai/framework` files.\n",
            encoding="utf-8",
        )
        bounded_routing = validator(target)
        bounded_routing.check_bootstrap_references()
        if "ROUTING_LOADS_BROAD_CONTEXT" in {
            finding.code for finding in bounded_routing.findings
        }:
            failures.append("negative broad-load guidance must not fail routing checks")
        routing_path.write_text(
            "Load bootstrap context only. Load all `.ai/framework` files.\n",
            encoding="utf-8",
        )
        broad_routing = validator(target)
        broad_routing.check_bootstrap_references()
        if "ROUTING_LOADS_BROAD_CONTEXT" not in {
            finding.code for finding in broad_routing.findings
        }:
            failures.append("positive broad-load guidance must fail routing checks")

        framework_tool_reference = target / ".ai" / "framework" / "migration-diff.md"
        framework_tool_reference.parent.mkdir(parents=True, exist_ok=True)
        framework_tool_reference.write_text(
            "The source may provide `tools/validate_target_adapter.py`.\n",
            encoding="utf-8",
        )
        checker_claims = validator(target)
        checker_claims.check_checker_claims([], [])
        if "STALE_CHECKER_REFERENCE" in {
            finding.code for finding in checker_claims.findings
        }:
            failures.append(
                "portable source-tool guidance must not become a target-local checker claim"
            )

        map_path = target / ".ai" / "project" / "consistency-map.json"
        write_json(
            map_path,
            {
                "schema_version": 1,
                "map_kind": "target-consistency-map",
                "levels": ["fact"],
                "relationship_types": ["implements"],
                "nodes": [],
            },
        )
        consistency = validator(target)
        consistency.check_consistency_map()
        consistency_codes = {finding.code for finding in consistency.findings}
        for required in [
            "CONSISTENCY_MAP_LEVELS",
            "CONSISTENCY_MAP_RELATIONSHIPS",
            "CONSISTENCY_MAP_NODES",
        ]:
            if required not in consistency_codes:
                failures.append(f"broken consistency map missing finding {required}")

        ai_router_path = target / ".ai" / "assistant" / "ai-infrastructure-router.json"
        write_json(
            ai_router_path,
            {
                "schema_version": 1,
                "router_kind": "target-ai-infrastructure-router",
                "item_types": ["skill"],
                "routing_order": ["inventory"],
                "routes": {},
                "items": [],
            },
        )
        ai_router = validator(target)
        ai_router.check_ai_infrastructure_router()
        ai_codes = {finding.code for finding in ai_router.findings}
        for required in ["AI_ROUTER_ROUTES", "AI_ROUTER_ITEM_TYPES", "AI_ROUTER_ITEMS"]:
            if required not in ai_codes:
                failures.append(f"broken AI router missing finding {required}")

        development_evidence_path = (
            target / ".ai" / "project" / "development-evidence.json"
        )
        write_json(
            development_evidence_path,
            {
                "schema_version": 1,
                "register_kind": "target-development-evidence",
                "project": "fixture",
                "owner": "fixture-owner",
                "retention_policy": "keep bounded references",
                "last_reviewed": "2026-07-17",
                "content_policy": (
                    "no raw chat, secrets, credentials, or personal data"
                ),
                "patterns": [
                    {
                        "id": "pattern-1",
                        "category": "review-rework",
                        "project_area": "api",
                        "source_owner": "api-contract",
                        "normalized_problem": "companion contract updates are missed",
                        "occurrence_count": 0,
                        "first_observed": "operation-1",
                        "last_observed": "operation-1",
                        "evidence_quality": "invented",
                        "evidence_refs": [],
                        "outcome_signals": ["rework"],
                        "existing_ai_item_ids": [],
                        "status": "unknown",
                    }
                ],
            },
        )
        development_evidence = validator(target)
        development_evidence.check_development_evidence(None)
        development_codes = {
            finding.code for finding in development_evidence.findings
        }
        for required in [
            "DEVELOPMENT_EVIDENCE_OCCURRENCE_COUNT",
            "DEVELOPMENT_EVIDENCE_REFERENCE_MISSING",
            "DEVELOPMENT_EVIDENCE_QUALITY",
            "DEVELOPMENT_EVIDENCE_STATUS",
        ]:
            if required not in development_codes:
                failures.append(
                    f"broken development evidence missing finding {required}"
                )

        team_model = target / ".ai" / "project" / "team-operating-model.md"
        team_model.write_text(
            (
                "# Team Operating Model\n\n"
                "### Actor `actor-owner`\n\n"
                "### Priority `normal`\n"
            ),
            encoding="utf-8",
        )
        write_json(
            target / ".ai" / "project" / "team-policy.json",
            {
                "schema_version": 1,
                "policy_kind": "target-team-policy",
                "policy_revision": "policy-1",
                "identity": {
                    "local_identity_path": ".ai/local/team-identity.json",
                    "git_identity_is_authoritative": False,
                },
                "actors": [
                    {
                        "id": "actor-owner",
                        "display_name": "Owner",
                        "aliases": [],
                        "status": "active",
                        "teams": [],
                        "roles": ["owner"],
                        "responsibilities": [],
                        "decision_authority": [],
                        "review_scopes": [],
                        "priority_scopes": ["normal"],
                        "external_identity_refs": [],
                    }
                ],
                "priorities": [
                    {"id": "normal", "assigner_actor_ids": ["actor-owner"]}
                ],
                "review_policy": {
                    "implementer_reviewer_separation": "required"
                },
                "state_transitions": [],
            },
        )
        write_json(
            target / ".ai" / "assistant" / "team" / "active-work-index.json",
            {
                "schema_version": 1,
                "index_kind": "target-team-active-work-index",
                "source_registry": ".ai/assistant/team/work-registry.json",
                "entries": [],
            },
        )
        write_json(
            target / ".ai" / "assistant" / "team" / "backend-contract.json",
            {
                "schema_version": 1,
                "contract_kind": "target-team-backend-contract",
                "backend_id": "repository",
                "backend_mode": "repository",
                "provider": "repository",
                "canonical_task_source": "registry",
                "projection_direction": "manual",
                "consistency_model": "manual",
                "write_strategy": "compare-and-swap",
                "capabilities": ["read-tasks"],
                "idempotency_policy": "task revision",
                "conflict_policy": "stop",
                "permission_policy": "adapter-only",
                "authentication_policy": "target",
                "validation": "fixture",
            },
        )
        team_overlay_path = (
            target / ".ai" / "assistant" / "team" / "context-overlay.json"
        )
        write_json(
            team_overlay_path,
            {
                "schema_version": 1,
                "overlay_kind": "target-team-context-overlay",
                "overlay_id": "team-active",
                "operation_candidates": ["team-status"],
                "required_context": [
                    ".ai/framework/team-collaboration.md",
                    ".ai/project/team-operating-model.md",
                    ".ai/assistant/team/work-registry.json",
                    ".ai/assistant/gates/team-collaboration.md",
                ],
            },
        )
        write_json(
            router_path,
            {
                "task_scale_overlays": {
                    "team-active": {
                        "use_when": ["team request"],
                        "descriptor": ".ai/assistant/team/context-overlay.json",
                    }
                }
            },
        )
        team_registry_path = (
            target / ".ai" / "assistant" / "team" / "work-registry.json"
        )
        write_json(
            team_registry_path,
            {
                "schema_version": 1,
                "registry_kind": "target-team-work-registry",
                "project": "fixture",
                "module_state": "enabled",
                "coordination_backend": "repository",
                "canonical_task_source": "registry",
                "synchronization_direction": "manual",
                "operating_model": ".ai/project/team-operating-model.md",
                "updated_at": "2026-07-23",
                "evidence_revision": "unavailable",
                "storage_policy": "repository",
                "retention_policy": "target policy",
                "privacy_policy": "no sensitive content",
                "tasks": [
                    {
                        "id": "task-1",
                        "goal": "fixture goal",
                        "non_goals": [],
                        "priority": "normal",
                        "priority_rationale": "fixture",
                        "priority_decided_by": "actor-owner",
                        "status": "merge-ready",
                        "owner_actor_id": "actor-missing",
                        "reviewer_actor_ids": [],
                        "parent_request": "fixture",
                        "coordination_backend_ref": "task-1",
                        "branch_or_worktree": "fixture",
                        "base_revision": "unavailable",
                        "evidence_revision": "unavailable",
                        "allowed_actions": ["code-and-tests"],
                        "context_profiles": ["code-local"],
                        "project_areas": ["fixture"],
                        "changed_fact_ids": ["fact-1"],
                        "canonical_owner_refs": ["owner-1"],
                        "expected_surfaces": ["src"],
                        "dependencies": [],
                        "blockers": [],
                        "related_task_ids": [],
                        "overlap": {
                            "state": "conflicting",
                            "checked_at": "2026-07-23",
                            "checked_revision": "unavailable",
                            "fact_ids": ["fact-1"],
                            "contract_or_dependency_refs": [],
                            "file_or_surface_refs": [],
                            "resolution": "none",
                        },
                        "claim": {
                            "mode": "advisory",
                            "actor_id": "none",
                            "claimed_at": "none",
                            "expires_at": "none",
                            "base_revision": "none",
                            "state": "unclaimed",
                        },
                        "approval_records": [],
                        "review_state": "approved",
                        "review_evidence_refs": [],
                        "validation_state": "failed",
                        "latest_checkpoint": "none",
                        "handoff_state": "none",
                        "decision_records": [],
                        "residual_risks": [],
                        "next_action": "repair",
                        "updated_at": "2026-07-23",
                    }
                ],
            },
        )
        team = validator(target)
        team.check_team_collaboration(None)
        team_codes = {finding.code for finding in team.findings}
        for required in [
            "TEAM_ACTOR_UNKNOWN",
            "TEAM_ACTIVE_OVERLAP_BLOCKED",
            "TEAM_MERGE_READY_VALIDATION",
            "TEAM_MERGE_READY_REVIEW_EVIDENCE",
            "TEAM_MERGE_READY_OVERLAP",
            "TEAM_MERGE_READY_REVIEWERS",
            "TEAM_MERGE_READY_REVISION",
        ]:
            if required not in team_codes:
                failures.append(f"broken team registry missing finding {required}")

        approval = """Allowed files or surfaces:

- `.ai/assistant/help.md`

Excluded files or surfaces:

- `.ai/assistant/private/*`
"""
        allowed = extract_list_field(approval, "Allowed files or surfaces:")
        excluded = extract_list_field(approval, "Excluded files or surfaces:")
        if not scope_entries_cover(".ai/assistant/help.md", allowed):
            failures.append("exact approval scope should cover its named file")
        if scope_entries_cover(".ai/assistant/help.md.backup", allowed):
            failures.append("approval scope must not match path substrings")
        if not scope_entries_cover(".ai/assistant/private/item.md", excluded):
            failures.append("approval scope glob should cover nested target files")

        git_target = target / "approval-diff"
        git_target.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=git_target, check=True)
        subprocess.run(
            ["git", "config", "user.email", "alatyr@example.invalid"],
            cwd=git_target,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Alatyr Check"],
            cwd=git_target,
            check=True,
        )
        source = git_target / "src"
        source.mkdir()
        (source / "allowed.txt").write_text("before\n", encoding="utf-8")
        (source / "outside.txt").write_text("before\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=git_target, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "fixture"],
            cwd=git_target,
            check=True,
        )
        (source / "allowed.txt").write_text("after\n", encoding="utf-8")
        (source / "outside.txt").write_text("after\n", encoding="utf-8")
        (source / "untracked.txt").write_text("new\n", encoding="utf-8")
        approval_path = (
            git_target
            / ".ai"
            / "assistant"
            / "approvals"
            / "approval.json"
        )
        approval_data = {
            "schema_version": 1,
            "record_kind": "alatyr-approval-record",
            "evidence_classification": "historical-record",
            "approval_id": "approval-test",
            "operation": {"id": "operation-test", "type": "code-change"},
            "plan": {"version": "1", "sha256": "none", "file": "none"},
            "diff": {
                "base": "HEAD",
                "patch_sha256": "none",
                "repository_revision_at_approval": "HEAD",
            },
            "scope": {
                "allowed_protected_changes": ["test change"],
                "allowed_files_or_surfaces": [
                    "src/allowed.txt",
                    ".ai/assistant/approvals/approval.json",
                ],
                "excluded_files_or_surfaces": [],
                "excluded_actions": ["live actions"],
                "allowed_actions_mode": "code-and-tests",
                "invalidation_rule": "any scope change invalidates approval",
            },
            "approval": {
                "approved_by": "tester",
                "approved_at": "2026-07-14",
            },
            "use_result": {},
        }
        write_json(approval_path, approval_data)
        changed = git_changed_files(git_target, "HEAD")
        expected_changed = {
            ".ai/assistant/approvals/approval.json",
            "src/allowed.txt",
            "src/outside.txt",
            "src/untracked.txt",
        }
        if changed is None or set(changed) != expected_changed:
            failures.append(
                "approval diff collection must include tracked and untracked paths"
            )

        strict = Validator(
            git_target,
            framework_source=None,
            diff_ref="HEAD",
            approval_records=[approval_path],
            enforce_approval_scope=True,
            change_packages=[],
            enforce_change_package=False,
            migration_diff=None,
            allow_placeholders=True,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
        )
        strict.check_approval_scope()
        mismatch_messages = [
            finding.message
            for finding in strict.findings
            if finding.code == "APPROVAL_SCOPE_MISMATCH" and finding.level == "error"
        ]
        if not any("src/outside.txt" in message for message in mismatch_messages):
            failures.append("strict approval scope must reject tracked out-of-scope files")
        if not any("src/untracked.txt" in message for message in mismatch_messages):
            failures.append("strict approval scope must reject untracked out-of-scope files")

        approval_data["scope"]["allowed_files_or_surfaces"] = [
            "src/*",
            ".ai/assistant/approvals/approval.json",
        ]
        write_json(approval_path, approval_data)
        covered = Validator(
            git_target,
            framework_source=None,
            diff_ref="HEAD",
            approval_records=[approval_path],
            enforce_approval_scope=True,
            change_packages=[],
            enforce_change_package=False,
            migration_diff=None,
            allow_placeholders=True,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
        )
        covered.check_approval_scope()
        if any(
            finding.level == "error" and finding.code.startswith("APPROVAL_")
            for finding in covered.findings
        ):
            failures.append("covered strict approval scope should pass")

        payload = findings_payload([], target=target, strict_warnings=False)
        evidence = payload.get("evidence", {})
        if payload.get("schema_version") != 2:
            failures.append("validator JSON schema must expose evidence schema 2")
        if evidence.get("basis") != "current-state-structural":
            failures.append("validator JSON must classify current-state evidence")
        if evidence.get("historical_actions_verified") is not False:
            failures.append("validator JSON must not imply historical actions were verified")

        health_payload = findings_payload(
            [
                Finding(
                    "warning",
                    "OPERATION_CATALOG_MISSING",
                    "catalog missing",
                    ".ai/assistant/operation-catalog.json",
                )
            ],
            target=target,
            strict_warnings=False,
        )
        if health_payload.get("adapter_health", {}).get("state") != "attention":
            failures.append("validator warning must produce attention health state")
        if health_payload.get("adapter_health", {}).get("repair_operations") != [
            "recheck-after-installation"
        ]:
            failures.append("validator health must return prioritized repair routes")
        health_finding = health_payload.get("findings", [{}])[0]
        if health_finding.get("automatic_repair") is not False:
            failures.append("validator findings must not imply automatic repair")
        extension_health = findings_payload(
            [
                Finding(
                    "warning",
                    "EXTENSION_FILE_DRIFT",
                    "extension item changed",
                    ".ai/assistant/extensions/example/items/review.md",
                )
            ],
            target=target,
            strict_warnings=False,
        )
        if extension_health.get("adapter_health", {}).get("repair_operations") != [
            "extension-management"
        ]:
            failures.append("extension findings must route to extension-management")
        if extension_health.get("exit_code") != 0:
            failures.append("ordinary advisory warnings must remain non-blocking by default")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("OK: checked target adapter validator routing, scope, and evidence contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
