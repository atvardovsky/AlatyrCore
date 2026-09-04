#!/usr/bin/env python3
"""Exercise stable contracts of the portable target adapter validator."""

from __future__ import annotations

import hashlib
import json
import shutil
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
    parse_manifest,
    parse_registry_fact_entries,
    result_code,
    scope_entries_cover,
)
from target_adapter_validation.context_catalogs import (
    validate_context_catalog_contract,
)
from target_adapter_validation.assistant_capabilities import (
    CAPABILITY_INDEX_KIND,
    CAPABILITY_INDEX_SCHEMA_VERSION,
    STATE_EVIDENCE_TEXT,
    SURFACE_CAPABILITY_KIND,
    SURFACE_CAPABILITY_SCHEMA_VERSION,
    capability_record_path,
)

ROOT = Path(__file__).resolve().parents[1]
DELEGATION_FIXTURE_PATHS = (
    ".ai/framework/task-decomposition.md",
    ".ai/framework/subagent-delegation.md",
    ".ai/assistant/task-decomposition.json",
    ".ai/assistant/delegation-policy.json",
    ".ai/assistant/context/task-scales/delegated-execution.json",
    ".ai/assistant/flows/subagent-delegation.flow.md",
    ".ai/assistant/prompts/worker-orchestration.md",
    ".ai/assistant/templates/subagent-task-packet.md",
    ".ai/assistant/templates/native-worker-binding.md",
    ".ai/assistant/templates/worker-execution-plan.md",
    ".ai/assistant/templates/worker-result.md",
    ".ai/assistant/workers/role-catalog.json",
    ".ai/assistant/workers/roles/explorer.md",
    ".ai/assistant/workers/roles/implementer.md",
    ".ai/assistant/workers/roles/test-runner.md",
    ".ai/assistant/workers/roles/documentation-worker.md",
    ".ai/assistant/workers/roles/reviewer.md",
    ".ai/assistant/workers/roles/fast-focused-worker.md",
    ".ai/assistant/assistant-capabilities.json",
    ".ai/assistant/bridge-capability-matrix.md",
)


def validator(
    target: Path,
    framework_source: Path | None = None,
    *,
    validation_phase: str = "migration-staging",
) -> Validator:
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
        validation_phase=validation_phase,
    )


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def check_context_cache_regressions(
    target: Path,
    manifest: object,
    record_path: Path,
    record: dict[str, object],
    failures: list[str],
) -> None:
    permissions = record["tool_permissions"]
    assert isinstance(permissions, dict)
    permissions["alatyr_authorization_separate"] = False
    write_json(record_path, record)
    permission_validator = validator(target)
    permission_validator.check_assistant_instruction_capabilities(manifest)
    if "ASSISTANT_PERMISSION_AUTHORIZATION_CONFLICT" not in {
        finding.code for finding in permission_validator.findings
    }:
        failures.append("client permissions must not grant Alatyr authorization")
    permissions["alatyr_authorization_separate"] = True

    caching = record["context_caching"]
    assert isinstance(caching, dict)
    caching["provider_cache_mode"] = "explicit"
    write_json(record_path, record)
    cache_control_validator = validator(target)
    cache_control_validator.check_assistant_instruction_capabilities(manifest)
    if "ASSISTANT_CONTEXT_CACHE_CONTROL" not in {
        finding.code for finding in cache_control_validator.findings
    }:
        failures.append(
            "explicit-only provider caching must require exposed client controls"
        )

    caching["provider_cache_mode"] = "automatic"
    caching["context_window_reduction"] = True
    write_json(record_path, record)
    cache_claim_validator = validator(target)
    cache_claim_validator.check_assistant_instruction_capabilities(manifest)
    if "ASSISTANT_CONTEXT_CACHE_WINDOW_CLAIM" not in {
        finding.code for finding in cache_claim_validator.findings
    }:
        failures.append("context caching must not claim context-window reduction")
    caching["context_window_reduction"] = False

    caching["provider_cache_mode"] = "unsupported"
    write_json(record_path, record)
    cache_state_validator = validator(target)
    cache_state_validator.check_assistant_instruction_capabilities(manifest)
    if "ASSISTANT_CONTEXT_CACHE_STATE_CONFLICT" not in {
        finding.code for finding in cache_state_validator.findings
    }:
        failures.append("supported cache routes must reject unsupported provider mode")
    caching["provider_cache_mode"] = "automatic"
    write_json(record_path, record)


def main() -> int:
    failures: list[str] = []
    parsed_registry = parse_registry_fact_entries(
        "### Fact Type: `business rule`\n\n"
        "Fact type: `business rule`\n"
        "Consistency map node: `fact-business-rule`\n"
    )
    if len(parsed_registry) != 1 or (
        parsed_registry[0].heading_fact_type,
        parsed_registry[0].declared_fact_type,
        parsed_registry[0].map_node_id,
    ) != ("business rule", "business rule", "fact-business-rule"):
        failures.append("registry Fact Type parser lost exact node identity")
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
        catalog_target = target / "context-catalog"
        catalog_target.mkdir()
        scaffold_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/scaffold_target_structure.py"),
                "--target",
                str(catalog_target),
                "--write",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if scaffold_result.returncode != 0:
            failures.append("context-catalog target scaffold failed")
        else:
            catalog_manifest = parse_manifest(catalog_target / ".ai/alatyr.yaml")
            current_catalogs = validator(catalog_target)
            validate_context_catalog_contract(current_catalogs, catalog_manifest)
            if any(
                finding.level == "error" for finding in current_catalogs.findings
            ):
                failures.append("fresh scaffold context catalogs produced errors")
            contour_path = catalog_target / ".ai/assistant/contour.md"
            contour_path.write_text(
                contour_path.read_text(encoding="utf-8") + "\nCatalog drift fixture.\n",
                encoding="utf-8",
            )
            stale_catalogs = validator(catalog_target)
            validate_context_catalog_contract(stale_catalogs, catalog_manifest)
            if "CONTEXT_CATALOG_INVALID" not in {
                finding.code for finding in stale_catalogs.findings
            }:
                failures.append("context catalog content drift was not detected")
            repair_result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/render_installed_context_catalogs.py"),
                    "--target",
                    str(catalog_target),
                    "--write",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            repaired_catalogs = validator(catalog_target)
            validate_context_catalog_contract(repaired_catalogs, catalog_manifest)
            if repair_result.returncode != 0 or any(
                finding.level == "error" for finding in repaired_catalogs.findings
            ):
                failures.append("explicit installed context-catalog repair failed")

        instruction_target = target / "instruction-capabilities"
        (instruction_target / ".ai/assistant/assistant-capabilities").mkdir(
            parents=True
        )
        (instruction_target / "AGENTS.md").write_text(
            "# Test instructions\n", encoding="utf-8"
        )
        (instruction_target / ".ai/alatyr.yaml").parent.mkdir(
            parents=True, exist_ok=True
        )
        (instruction_target / ".ai/alatyr.yaml").write_text(
            "schema_version: 27\nsupported_assistants:\n  - generic\n",
            encoding="utf-8",
        )
        instruction_index = {
            "schema_version": CAPABILITY_INDEX_SCHEMA_VERSION,
            "capability_kind": CAPABILITY_INDEX_KIND,
            "state_evidence": {
                "state_model": STATE_EVIDENCE_TEXT,
                "selected_surface": "generic",
                "selected_surface_evidence": "fixture manifest",
                "capability_records_are_authoritative": True,
                "unknown_means_not_verified": True,
                "stale_or_expired_evidence_requires_recheck": True,
            },
            "surfaces": {
                "generic": capability_record_path("generic")
            },
        }
        write_json(
            instruction_target / ".ai/assistant/assistant-capabilities.json",
            instruction_index,
        )
        evidence = {
            "verified_at": "2026-08-25",
            "client_version": "fixture-1",
            "evidence": "fixture observation",
            "expires_at": "review-trigger: client changed",
            "review_triggers": ["client changed"],
        }
        instruction_record = {
            "schema_version": SURFACE_CAPABILITY_SCHEMA_VERSION,
            "capability_kind": SURFACE_CAPABILITY_KIND,
            "assistant_surface": "generic",
            "surface_state": {
                "overall": "supported",
                "selected_for_target": "yes",
                "evidence_state": "current",
                "advertised_by_surface": "yes",
                "verified_for_target": "yes",
                "limitations": ["fixture-only capability evidence"],
                "review_triggers": ["client changed"],
            },
            "instruction_loading": {
                **evidence,
                "route": "supported",
                "runtime_variant": "fixture",
                "selected_entry_path": "AGENTS.md",
                "competing_sources": [],
                "auto_load_observed": "yes",
                "precedence_evidence": "fixture observation",
                "configuration_state": "fixture default",
            },
            "skills": {
                **evidence,
                "route": "unsupported",
                "discovery_paths": [],
                "selected_source": "none",
                "activation_mode": "disabled",
            },
            "tool_permissions": {
                **evidence,
                "client_permission_mode": "ask",
                "effective_restrictions": "fixture read/write prompt",
                "alatyr_authorization_separate": True,
            },
            "context_caching": {
                **evidence,
                "route": "supported",
                "provider": "fixture-provider",
                "model": "fixture-model",
                "provider_cache_mode": "automatic",
                "client_control_exposure": "unsupported",
                "client_telemetry_exposure": "supported",
                "retention": "fixture-session",
                "minimum_cacheable_tokens": "1",
                "stable_prefix_ordering": True,
                "context_window_reduction": False,
                "fallback": "bounded-context-routing",
            },
            "diagram_discussion": {},
            "subagent_delegation": {},
        }
        instruction_path = (
            instruction_target
            / ".ai/assistant/assistant-capabilities/generic.json"
        )
        write_json(instruction_path, instruction_record)
        instruction_validator = validator(instruction_target)
        instruction_manifest = parse_manifest(
            instruction_target / ".ai/alatyr.yaml"
        )
        instruction_validator.check_assistant_instruction_capabilities(
            instruction_manifest
        )
        instruction_errors = {
            finding.code
            for finding in instruction_validator.findings
            if finding.level == "error"
        }
        if instruction_errors:
            failures.append(
                "valid assistant instruction capability produced errors: "
                + ", ".join(sorted(instruction_errors))
            )

        invalid_index = dict(instruction_index)
        invalid_index["surfaces"] = {
            "generic": ".ai/assistant/assistant-capabilities/wrong.json"
        }
        write_json(
            instruction_target / ".ai/assistant/assistant-capabilities.json",
            invalid_index,
        )
        invalid_index_validator = validator(instruction_target)
        invalid_index_validator.check_assistant_instruction_capabilities(
            instruction_manifest
        )
        if "ASSISTANT_CAPABILITY_INDEX_ENTRY" not in {
            finding.code for finding in invalid_index_validator.findings
        }:
            failures.append("assistant capability index path drift must be rejected")
        write_json(
            instruction_target / ".ai/assistant/assistant-capabilities.json",
            instruction_index,
        )

        instruction_record["instruction_loading"]["auto_load_observed"] = "no"
        write_json(instruction_path, instruction_record)
        unproven_validator = validator(instruction_target)
        unproven_validator.check_assistant_instruction_capabilities(
            instruction_manifest
        )
        if "ASSISTANT_AUTO_LOAD_UNPROVEN" not in {
            finding.code for finding in unproven_validator.findings
        }:
            failures.append("supported assistant route must require observed auto-load")

        instruction_record["instruction_loading"]["auto_load_observed"] = "yes"
        instruction_record["tool_permissions"]["alatyr_authorization_separate"] = True
        check_context_cache_regressions(
            instruction_target,
            instruction_manifest,
            instruction_path,
            instruction_record,
            failures,
        )

        inactive_bridge_target = target / "inactive-assistant-bridge"
        (inactive_bridge_target / ".ai/assistant/assistant-capabilities").mkdir(
            parents=True
        )
        (inactive_bridge_target / "AGENTS.md").write_text(
            "# Active instructions\n", encoding="utf-8"
        )
        (inactive_bridge_target / "AI_ASSISTANTS.md").write_text(
            "Neutral example: size={24}\n", encoding="utf-8"
        )
        (inactive_bridge_target / "CLAUDE.md").write_text(
            "Legacy example: size={24}\n", encoding="utf-8"
        )
        inactive_manifest_path = inactive_bridge_target / ".ai/alatyr.yaml"
        inactive_manifest_path.write_text(
            "supported_assistants:\n  - codex\n", encoding="utf-8"
        )
        write_json(
            inactive_bridge_target / ".ai/assistant/assistant-capabilities.json",
            {
                "schema_version": CAPABILITY_INDEX_SCHEMA_VERSION,
                "capability_kind": CAPABILITY_INDEX_KIND,
                "state_evidence": {
                    "state_model": STATE_EVIDENCE_TEXT,
                    "selected_surface": "codex",
                    "selected_surface_evidence": "fixture manifest",
                    "capability_records_are_authoritative": True,
                    "unknown_means_not_verified": True,
                    "stale_or_expired_evidence_requires_recheck": True,
                },
                "surfaces": {
                    "codex": capability_record_path("codex"),
                    "claude": capability_record_path("claude"),
                },
                "bridge_paths": {
                    "codex": ["AGENTS.md", "AI_ASSISTANTS.md"],
                    "claude": ["CLAUDE.md"],
                },
            },
        )
        write_json(
            inactive_bridge_target
            / ".ai/assistant/assistant-capabilities/codex.json",
            {
                "surface_state": {
                    "overall": "supported",
                    "selected_for_target": "yes",
                    "evidence_state": "current",
                    "advertised_by_surface": "yes",
                    "verified_for_target": "yes",
                },
                "instruction_loading": {"route": "supported"},
            },
        )
        write_json(
            inactive_bridge_target
            / ".ai/assistant/assistant-capabilities/claude.json",
            {
                "surface_state": {
                    "overall": "unsupported",
                    "selected_for_target": "no",
                    "evidence_state": "current",
                    "advertised_by_surface": "yes",
                    "verified_for_target": "yes",
                },
                "instruction_loading": {"route": "unsupported"},
            },
        )
        inactive_manifest = parse_manifest(inactive_manifest_path)
        inactive_bridge_validator = validator(
            inactive_bridge_target, validation_phase="acceptance"
        )
        inactive_bridge_validator.check_placeholders(
            inactive_manifest, "core", set()
        )
        if any(
            finding.code == "PLACEHOLDER_UNRESOLVED"
            and finding.path == "CLAUDE.md:1"
            for finding in inactive_bridge_validator.findings
        ):
            failures.append(
                "explicitly unsupported unselected assistant bridges must not be "
                "scanned as active adapter surfaces"
            )
        if not any(
            finding.code == "PLACEHOLDER_UNRESOLVED"
            and finding.path == "AI_ASSISTANTS.md:1"
            for finding in inactive_bridge_validator.findings
        ):
            failures.append(
                "neutral assistant entry points must remain active regardless of "
                "surface capability routes"
            )

        capability_index_path = (
            inactive_bridge_target / ".ai/assistant/assistant-capabilities.json"
        )
        partial_index = json.loads(capability_index_path.read_text(encoding="utf-8"))
        partial_index["bridge_paths"]["unrepresented"] = ["CLAUDE.md"]
        write_json(capability_index_path, partial_index)
        partial_index_validator = validator(
            inactive_bridge_target, validation_phase="acceptance"
        )
        partial_index_validator.check_placeholders(
            inactive_manifest, "core", set()
        )
        if not any(
            finding.code == "PLACEHOLDER_UNRESOLVED"
            and finding.path == "CLAUDE.md:1"
            for finding in partial_index_validator.findings
        ):
            failures.append(
                "partially represented bridge ownership must remain active fail-safe"
            )
        partial_index["bridge_paths"].pop("unrepresented")
        write_json(capability_index_path, partial_index)

        inactive_manifest_path.write_text(
            "supported_assistants:\n  - claude\n", encoding="utf-8"
        )
        selected_inactive_manifest = parse_manifest(inactive_manifest_path)
        selected_inactive_validator = validator(
            inactive_bridge_target, validation_phase="acceptance"
        )
        selected_inactive_validator.check_placeholders(
            selected_inactive_manifest, "core", set()
        )
        if not any(
            finding.code == "PLACEHOLDER_UNRESOLVED"
            and finding.path == "CLAUDE.md:1"
            for finding in selected_inactive_validator.findings
        ):
            failures.append(
                "a manifest-selected assistant bridge must remain active even when "
                "its capability route is inconsistent"
            )

        policy_source = (
            ROOT
            / "templates"
            / "target"
            / ".ai"
            / "assistant"
            / "policies"
            / "action-authorization.json"
        )
        authorization_policy = json.loads(policy_source.read_text(encoding="utf-8"))
        write_json(
            target / ".ai/assistant/policies/action-authorization.json",
            authorization_policy,
        )
        authorization_surfaces = {
            "AGENTS.md": (
                "ALATYR-AUTHORIZATION-001\n"
                "Implementation does not imply commit; commit does not imply push\n"
            ),
            ".ai/assistant/gates/core.md": (
                "Issue/backlog returns\n"
                "Do not infer commit from implementation, publish from commit\n"
            ),
            ".ai/assistant/gates/final-evidence.md": (
                "`current_user_authorization`\n"
                "latest commit/publish/live confirmation\n"
            ),
            ".ai/assistant/contour.md": (
                ".ai/assistant/policies/action-authorization.json\n"
                "current-scope action authorization\n"
            ),
            ".ai/assistant/module-profile.md": (
                "current-scope-action-authorization\n"
                ".ai/assistant/policies/action-authorization.json\n"
            ),
            ".ai/assistant/maturity-profile.md": (
                ".ai/assistant/policies/action-authorization.json\n"
                "Prior authorization\n"
            ),
            ".ai/assistant/templates/installation-note.md": (
                ".ai/assistant/policies/action-authorization.json\n"
                "previous task's authorization expires\n"
            ),
            ".ai/assistant/templates/operation-request.md": (
                "Current logical scope:\n"
                "Current user authorization:\n"
                "Authorization source/message:\n"
                "Prior authorization invalidated:\n"
            ),
        }
        for relpath, content in authorization_surfaces.items():
            surface = target / relpath
            surface.parent.mkdir(parents=True, exist_ok=True)
            surface.write_text(content, encoding="utf-8")
        authorization = validator(target)
        authorization.check_action_authorization_contract()
        if any(
            finding.code.startswith("AUTHORIZATION_")
            for finding in authorization.findings
        ):
            failures.append("valid action authorization contract should pass")

        authorization_policy["scope"]["prior_authorization_reusable"] = True
        write_json(
            target / ".ai/assistant/policies/action-authorization.json",
            authorization_policy,
        )
        reusable = validator(target)
        reusable.check_action_authorization_contract()
        if "AUTHORIZATION_SCOPE_REUSE" not in {
            finding.code for finding in reusable.findings
        }:
            failures.append("reusable prior authorization must be rejected")
        authorization_policy["scope"]["prior_authorization_reusable"] = False
        write_json(
            target / ".ai/assistant/policies/action-authorization.json",
            authorization_policy,
        )

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

        schema_seven_descriptor = (
            target
            / ".ai"
            / "assistant"
            / "context"
            / "profiles"
            / "docs-local.json"
        )
        write_json(
            schema_seven_descriptor,
            {
                "schema_version": 1,
                "descriptor_kind": "target-context-profile",
                "profile": "docs-local",
            },
        )
        schema_seven = validator(target)
        schema_seven_profiles = schema_seven.router_profiles(
            {
                "schema_version": 7,
                "profile_index": {
                    "docs-local": {
                        "descriptor": (
                            ".ai/assistant/context/profiles/docs-local.json"
                        )
                    }
                },
            }
        )
        if set(schema_seven_profiles) != {"docs-local"}:
            failures.append(
                "schema-7 router must load descriptor-backed canonical profiles"
            )

        consistency_descriptor = (
            target
            / ".ai"
            / "assistant"
            / "context"
            / "consistency-routing.json"
        )
        write_json(
            consistency_descriptor,
            {
                "schema_version": 1,
                "descriptor_kind": "target-consistency-routing",
                "required_context": [".ai/project/consistency-map.json"],
            },
        )
        write_json(
            router_path,
            {
                "schema_version": 1,
                "router_kind": "target-context-router",
                "human_reference": ".ai/assistant/context-profiles.md",
                "routing_order": ["docs-local"],
                "profiles": {},
                "consistency_routing": {
                    "descriptor": ".ai/assistant/context/consistency-routing.json"
                },
            },
        )
        consistency_router = validator(target)
        consistency_router.check_router({"consistency-map"})
        consistency_router_codes = {
            finding.code for finding in consistency_router.findings
        }
        for required in [
            "ROUTER_CONSISTENCY_CONTEXT",
            "ROUTER_CONSISTENCY_CONDITIONAL",
        ]:
            if required not in consistency_router_codes:
                failures.append(
                    f"broken consistency routing missing finding {required}"
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

        consistency_cost_descriptor = (
            target / ".ai" / "assistant" / "context" / "cost-consistency.json"
        )
        write_json(
            consistency_cost_descriptor,
            {
                "required_context": [
                    ".ai/project/source-of-truth-registry.md",
                    ".ai/project/consistency-map.json",
                ]
            },
        )
        (target / ".ai" / "project").mkdir(parents=True, exist_ok=True)
        (target / ".ai" / "project" / "source-of-truth-registry.md").write_text(
            "one two three four five\n", encoding="utf-8"
        )
        (target / ".ai" / "project" / "consistency-map.json").write_text(
            "one two three four five\n", encoding="utf-8"
        )
        composition_validator = validator(target)
        composition_validator.check_installed_context_costs(
            {
                "preloaded_context": [],
                "bootstrap_context": [],
                "profile_index": {},
                "consistency_routing": {
                    "descriptor": ".ai/assistant/context/cost-consistency.json"
                },
            },
            {
                "code-local": {
                    "required_context": [".ai/framework/large-context.md"]
                }
            },
            {
                "bootstrap": {"max_files": 4, "max_words": 100},
                "profile_default": {
                    "max_files": 8,
                    "max_total_words": 10,
                    "max_portable_words": 100,
                    "reserved_target_words": 100,
                },
            },
        )
        if "ROUTER_CONSISTENCY_COMPOSITION_COST" not in {
            finding.code for finding in composition_validator.findings
        }:
            failures.append(
                "profile plus consistency routing over-budget must be rejected"
            )

        pack_target = target / "pack-target"
        framework_target = pack_target / ".ai" / "framework"
        framework_target.mkdir(parents=True)
        manifest_path = pack_target / ".ai" / "alatyr.yaml"
        manifest_path.write_text("framework:\n  pack: core\n", encoding="utf-8")
        for name, content in projected_framework_contents("core").items():
            destination = framework_target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
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
        original_inventory = inventory_path.read_bytes()
        inventory = json.loads(original_inventory.decode("utf-8"))
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
        inventory_path.write_bytes(original_inventory)

        registry_path = framework_target / "rule-registry.json"
        original_registry = registry_path.read_bytes()
        registry = json.loads(original_registry.decode("utf-8"))
        registry["rules"] = registry["rules"][1:]
        write_json(registry_path, registry)
        tampered_registry_validator = validator(pack_target, ROOT)
        tampered_registry_validator.check_framework_baseline()
        if "FRAMEWORK_PACK_REGISTRY_DRIFT" not in {
            finding.code for finding in tampered_registry_validator.findings
        }:
            failures.append("selective pack must detect projected registry tampering")
        registry_path.write_bytes(original_registry)

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

        delegation_target = target / "delegation-target"
        delegation_manifest_path = delegation_target / ".ai" / "alatyr.yaml"
        delegation_manifest_path.parent.mkdir(parents=True)
        delegation_manifest_path.write_text(
            "schema_version: 11\nmodules:\n  enabled:\n    - subagent-delegation\n",
            encoding="utf-8",
        )
        delegation_paths = list(DELEGATION_FIXTURE_PATHS)
        capability_index = json.loads(
            (
                ROOT
                / "templates/target/.ai/assistant/assistant-capabilities.json"
            ).read_text(encoding="utf-8")
        )
        delegation_paths.extend(capability_index["surfaces"].values())
        for relpath in delegation_paths:
            source = (
                ROOT / "framework" / Path(relpath).name
                if relpath.startswith(".ai/framework/")
                else ROOT / "templates/target" / relpath
            )
            destination = delegation_target / relpath
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
        write_json(
            delegation_target / ".ai/assistant/ai-infrastructure-router.json",
            {"items": [{"id": "fixture.dispatcher"}]},
        )
        generic_capability_path = (
            delegation_target
            / ".ai/assistant/assistant-capabilities/generic.json"
        )
        generic_capability = json.loads(
            generic_capability_path.read_text(encoding="utf-8")
        )
        generic_delegation = generic_capability["subagent_delegation"]
        generic_delegation.update(
            {
                "route": "supported",
                "dispatch_backend": "external",
                "external_dispatcher": "fixture.dispatcher",
                "native_subagents": "unsupported",
            }
        )
        write_json(generic_capability_path, generic_capability)

        external_delegation = validator(delegation_target)
        external_manifest = external_delegation.check_manifest()
        external_delegation.findings.clear()
        external_delegation.check_subagent_delegation(external_manifest)
        external_errors = {
            finding.code
            for finding in external_delegation.findings
            if finding.level == "error" and finding.code.startswith("DELEGATION_")
        }
        if external_errors:
            failures.append(
                "valid external delegation backend produced errors: "
                + ", ".join(sorted(external_errors))
            )

        generic_delegation["external_dispatcher"] = "missing.dispatcher"
        write_json(generic_capability_path, generic_capability)
        missing_dispatcher = validator(delegation_target)
        missing_dispatcher.check_subagent_delegation(external_manifest)
        if "DELEGATION_EXTERNAL_DISPATCHER" not in {
            finding.code for finding in missing_dispatcher.findings
        }:
            failures.append("external delegation must reject an unknown dispatcher")

        generic_delegation.update(
            {
                "dispatch_backend": "native",
                "external_dispatcher": "none",
                "native_subagents": "unsupported",
            }
        )
        write_json(generic_capability_path, generic_capability)
        unsupported_native = validator(delegation_target)
        unsupported_native.check_subagent_delegation(external_manifest)
        if "DELEGATION_NATIVE_BACKEND_UNSUPPORTED" not in {
            finding.code for finding in unsupported_native.findings
        }:
            failures.append(
                "native delegation must require native worker capability evidence"
            )

        generic_delegation.update(
            {
                "route": "supported",
                "native_subagents": "supported",
                "explicit_delegation": "supported",
                "project_worker_definitions": "supported",
                "worker_definition_format": "fixture-markdown",
                "worker_definition_paths": [".ai/native-workers/explorer.md"],
            }
        )
        native_worker_path = delegation_target / ".ai/native-workers/explorer.md"
        native_worker_path.parent.mkdir(parents=True, exist_ok=True)
        native_worker_path.write_text("native worker without routing\n", encoding="utf-8")
        write_json(generic_capability_path, generic_capability)
        non_thin_worker = validator(delegation_target)
        non_thin_worker.check_subagent_delegation(external_manifest)
        if "DELEGATION_WORKER_DEFINITION_NOT_THIN" not in {
            finding.code for finding in non_thin_worker.findings
        }:
            failures.append(
                "native worker definitions must route to canonical contracts"
            )

        generic_delegation["worker_definition_paths"] = ["../outside-worker.md"]
        write_json(generic_capability_path, generic_capability)
        unsafe_worker_path = validator(delegation_target)
        unsafe_worker_path.check_subagent_delegation(external_manifest)
        if "DELEGATION_WORKER_DEFINITION_PATH" not in {
            finding.code for finding in unsafe_worker_path.findings
        }:
            failures.append(
                "native worker definitions must reject unsafe target paths"
            )

        generic_delegation.update(
            {
                "dispatch_backend": "external",
                "external_dispatcher": "fixture.dispatcher",
                "project_worker_definitions": "unsupported",
                "worker_definition_format": "none",
                "worker_definition_paths": [],
                "role_bindings": [
                    {
                        "role_id": "missing-role",
                        "selection_mode": "inherit",
                        "model": "inherit",
                        "reasoning": "client-default",
                        "availability": "supported",
                        "evidence": "fixture",
                        "expires_at": "manual review",
                    }
                ],
            }
        )
        write_json(generic_capability_path, generic_capability)
        unknown_role = validator(delegation_target)
        unknown_role.check_subagent_delegation(external_manifest)
        if "DELEGATION_ROLE_BINDING_UNKNOWN" not in {
            finding.code for finding in unknown_role.findings
        }:
            failures.append("surface bindings must reject unknown worker roles")

        migration_descriptor_path = (
            target / ".ai" / "assistant" / "context" / "migration-routing.json"
        )
        write_json(
            migration_descriptor_path,
            {
                "schema_version": 1,
                "descriptor_kind": "target-migration-routing",
            },
        )
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
                "schema_version": CAPABILITY_INDEX_SCHEMA_VERSION,
                "capability_kind": CAPABILITY_INDEX_KIND,
                "state_evidence": {
                    "state_model": STATE_EVIDENCE_TEXT,
                    "selected_surface": "generic",
                    "selected_surface_evidence": "fixture",
                    "capability_records_are_authoritative": True,
                    "unknown_means_not_verified": True,
                    "stale_or_expired_evidence_requires_recheck": True,
                },
                "surfaces": {
                    "generic": capability_record_path("generic")
                },
            },
        )
        write_json(
            target / ".ai" / "assistant" / "assistant-capabilities" / "generic.json",
            {
                "schema_version": 1,
                "capability_kind": SURFACE_CAPABILITY_KIND,
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
            "# Module Profile\n\n"
            "Module: `dependency-knowledge`\nState: `enabled`\n",
            encoding="utf-8",
        )
        dependency_knowledge = validator(target)
        dependency_knowledge.check_dependency_knowledge(None)
        if "DEPENDENCY_KNOWLEDGE_REQUIRED_FILE_MISSING" not in {
            finding.code for finding in dependency_knowledge.findings
        }:
            failures.append(
                "enabled dependency knowledge must report missing contracts"
            )

        dependency_paths = [
            ".ai/framework/dependency-knowledge.md",
            ".ai/project/dependencies/README.md",
            ".ai/project/dependencies/policy.json",
            ".ai/project/dependencies/catalog.json",
            ".ai/project/dependencies/knowledge-lock.json",
            ".ai/project/dependencies/deviations.json",
            ".ai/project/dependencies/snapshots/README.md",
            ".ai/assistant/context/intents/dependency-knowledge-request.json",
            ".ai/assistant/flows/dependency-knowledge-sync.flow.md",
            ".ai/assistant/gates/dependency-knowledge.md",
            ".ai/assistant/templates/dependency-knowledge-sync-report.md",
            ".ai/assistant/operation-catalog.json",
            ".ai/assistant/context-router.json",
        ]
        for relpath in dependency_paths:
            source = (
                ROOT / "framework/dependency-knowledge.md"
                if relpath.startswith(".ai/framework/")
                else ROOT / "templates/target" / relpath
            )
            destination = target / relpath
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
        (target / "package.json").write_text("{}\n", encoding="utf-8")
        (target / "package-lock.json").write_text("{}\n", encoding="utf-8")
        dependency_policy_path = target / ".ai/project/dependencies/policy.json"
        dependency_policy = json.loads(
            dependency_policy_path.read_text(encoding="utf-8")
        )
        dependency_policy.update({"state": "enabled", "owner": "fixture-owner"})
        dependency_policy["package_sources"] = [
            {
                "ecosystem": "fixture",
                "manifest": "package.json",
                "lockfile": "package-lock.json",
                "metadata_locator_kind": "native-package-metadata-key",
                "metadata_locator": "fixture.alatyr",
            }
        ]
        dependency_policy["limits"] = {
            key: 10
            for key in [
                "max_manifest_bytes",
                "max_export_bytes",
                "max_exports_per_package",
                "max_graph_depth",
                "max_graph_instances",
            ]
        }
        write_json(dependency_policy_path, dependency_policy)
        instance_id = "fixture:example/library@1.0.0#root"
        export_id = "fixture:example/library.public-contract"
        fingerprint = "a" * 64
        export_digest = "b" * 64
        manifest_digest = "c" * 64
        catalog_data = {
            "schema_version": 1,
            "catalog_kind": "target-dependency-knowledge-catalog",
            "owner": "fixture-owner",
            "package_lock_fingerprint": fingerprint,
            "packages": [
                {
                    "instance_id": instance_id,
                    "ecosystem": "fixture",
                    "name": "example/library",
                    "version": "1.0.0",
                    "export_status": "available",
                    "trust": "reviewed",
                    "freshness": "current",
                    "exports": [
                        {
                            "id": export_id,
                            "type": "public-contract",
                            "summary": "fixture public contract",
                            "content_digest": export_digest,
                            "authority": "upstream-canonical",
                            "stability": "stable",
                            "applicability": {
                                "state": "active",
                                "conditions": [],
                            },
                            "evidence": ["exports/contracts.json"],
                        }
                    ],
                }
            ],
        }
        lock_data = {
            "schema_version": 1,
            "lock_kind": "target-dependency-knowledge-lock",
            "knowledge_api": 1,
            "package_lock_fingerprint": fingerprint,
            "instances": [
                {
                    "instance_id": instance_id,
                    "ecosystem": "fixture",
                    "name": "example/library",
                    "version": "1.0.0",
                    "source": "fixture-source",
                    "integrity": "fixture-integrity",
                    "revision": "fixture-revision",
                    "modifications": [],
                    "manifest": {
                        "path": "alatyr-dependency.json",
                        "content_digest": manifest_digest,
                    },
                    "exports": [
                        {
                            "id": export_id,
                            "path": "exports/contracts.json",
                            "content_digest": export_digest,
                        }
                    ],
                    "graph": {
                        "dependency_set": "runtime",
                        "direct": True,
                        "public_instance_ids": [],
                    },
                }
            ],
        }
        write_json(target / ".ai/project/dependencies/catalog.json", catalog_data)
        write_json(target / ".ai/project/dependencies/knowledge-lock.json", lock_data)
        write_json(
            target / ".ai/project/dependencies/deviations.json",
            {
                "schema_version": 1,
                "deviation_kind": "target-dependency-knowledge-deviations",
                "owner": "fixture-owner",
                "deviations": [],
            },
        )
        valid_dependency = validator(target)
        valid_dependency.check_dependency_knowledge(None)
        valid_dependency_errors = [
            finding.code
            for finding in valid_dependency.findings
            if finding.level == "error"
            and finding.code.startswith("DEPENDENCY_KNOWLEDGE_")
        ]
        if valid_dependency_errors:
            failures.append(
                "resolved dependency knowledge projection produced errors: "
                + ", ".join(valid_dependency_errors)
            )
        dependency_policy["package_sources"][0]["metadata_locator_kind"] = "adapter"
        write_json(dependency_policy_path, dependency_policy)
        invalid_locator = validator(target)
        invalid_locator.check_dependency_knowledge(None)
        if "DEPENDENCY_KNOWLEDGE_SOURCE_LOCATOR" not in {
            finding.code for finding in invalid_locator.findings
        }:
            failures.append(
                "dependency knowledge must reject non-native metadata locators"
            )
        dependency_policy["package_sources"][0]["metadata_locator_kind"] = (
            "native-package-metadata-key"
        )
        write_json(dependency_policy_path, dependency_policy)
        lock_data["instances"][0]["graph"]["public_instance_ids"] = [
            "fixture:missing@1.0.0#transitive"
        ]
        write_json(target / ".ai/project/dependencies/knowledge-lock.json", lock_data)
        dangling_dependency = validator(target)
        dangling_dependency.check_dependency_knowledge(None)
        if "DEPENDENCY_KNOWLEDGE_GRAPH_REFERENCE" not in {
            finding.code for finding in dangling_dependency.findings
        }:
            failures.append(
                "dependency knowledge must reject dangling graph references"
            )

        module_profile_path.write_text(
            "# Module Profile\n\nModule: `workspace-modes`\nState: `enabled`\n",
            encoding="utf-8",
        )
        missing_modes = validator(target)
        missing_modes.check_workspace_modes(None)
        if "WORKSPACE_MODE_REQUIRED_FILE_MISSING" not in {
            finding.code for finding in missing_modes.findings
        }:
            failures.append("enabled workspace modes must report missing contracts")

        workspace_mode_paths = [
            ".ai/framework/workspace-modes.md",
            ".ai/project/workspace-modes/README.md",
            ".ai/project/workspace-modes/catalog.json",
            ".ai/project/workspace-modes/root/README.md",
            ".ai/project/workspace-modes/root/context.json",
            ".ai/project/workspace-modes/modes/_template/README.md",
            ".ai/project/workspace-modes/modes/_template/mode.json",
            ".ai/assistant/context/intents/workspace-mode-request.json",
            ".ai/assistant/flows/workspace-mode.flow.md",
            ".ai/assistant/gates/workspace-mode.md",
            ".ai/assistant/templates/workspace-mode-suggestion.md",
            ".ai/assistant/templates/workspace-mode-preflight.md",
            ".ai/assistant/operation-catalog.json",
            ".ai/assistant/context-router.json",
        ]
        for relpath in workspace_mode_paths:
            source = (
                ROOT / "framework/workspace-modes.md"
                if relpath.startswith(".ai/framework/")
                else ROOT / "templates/target" / relpath
            )
            destination = target / relpath
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
        (target / "README.md").write_text("# Fixture\n", encoding="utf-8")
        mode_id = "application-development"
        mode_path = (
            target
            / ".ai/project/workspace-modes/modes"
            / mode_id
            / "mode.json"
        )
        mode_path.parent.mkdir(parents=True, exist_ok=True)
        (mode_path.parent / "README.md").write_text(
            "# Application development\n", encoding="utf-8"
        )
        mode_data = {
            "schema_version": 1,
            "descriptor_kind": "target-workspace-mode",
            "id": mode_id,
            "title": "Application development",
            "state": "accepted",
            "mode_kind": "application-development",
            "purpose": "Develop the application owned by the selected workspace.",
            "owner": "fixture-owner",
            "decision_authority": "fixture-owner",
            "last_reviewed": "2026-08-21",
            "evidence_revision": "fixture-revision",
            "workspace_scope": {
                "root": ".",
                "include": ["."],
                "exclude": [],
            },
            "use_when": ["the selected task changes the application"],
            "do_not_use_when": ["the selected task contributes upstream"],
            "relationships": [
                {
                    "subject": "fixture-workspace",
                    "relationship": "workspace-root",
                    "adapter_role": "active",
                    "ownership": "target",
                    "evidence": ["README.md"],
                }
            ],
            "context": {
                "root_context": "skip",
                "required_context": ["README.md"],
                "conditional_context": [],
            },
            "source_of_truth_ids": [],
            "validation_entry_point_ids": [],
            "constraints": {
                "narrows_allowed_actions": [],
                "grants_write_scope": False,
                "grants_approval": False,
                "grants_permissions": False,
                "grants_authority": False,
                "grants_tools": False,
                "activates_nested_adapters": False,
                "bypasses_gates": False,
            },
            "known_gaps": [],
        }
        write_json(mode_path, mode_data)
        write_json(
            target / ".ai/project/workspace-modes/catalog.json",
            {
                "schema_version": 1,
                "catalog_kind": "target-workspace-mode-catalog",
                "state": "enabled",
                "owner": "fixture-owner",
                "decision_authority": "fixture-owner",
                "workspace": {
                    "id": "fixture-workspace",
                    "kind": "application",
                    "root": ".",
                    "adapter_role": "active",
                    "evidence": ["README.md"],
                },
                "selection": {
                    "default_mode_id": mode_id,
                    "automatic_selection": "accepted-unambiguous-only",
                    "ambiguity_behavior": "ask-user",
                    "no_match_behavior": "root-read-only",
                    "persistence": "per-task",
                    "local_preference_allowed": False,
                    "show_preflight_before_changes": True,
                },
                "suggestions": {
                    "after_installation": True,
                    "after_framework_update": True,
                    "after_workspace_change": True,
                    "automatic_acceptance": False,
                },
                "root_context": ".ai/project/workspace-modes/root/context.json",
                "modes": [
                    {
                        "id": mode_id,
                        "title": "Application development",
                        "state": "accepted",
                        "mode_kind": "application-development",
                        "path": f".ai/project/workspace-modes/modes/{mode_id}/mode.json",
                        "summary": "Develop the selected application.",
                        "evidence_revision": "fixture-revision",
                    }
                ],
            },
        )
        write_json(
            target / ".ai/project/workspace-modes/root/context.json",
            {
                "schema_version": 1,
                "descriptor_kind": "target-workspace-root-context",
                "state": "disabled",
                "owner": "fixture-owner",
                "required_context": [],
                "conditional_context": [],
                "known_gaps": [],
            },
        )
        valid_modes = validator(target)
        valid_modes.check_workspace_modes(None)
        valid_mode_errors = [
            finding.code
            for finding in valid_modes.findings
            if finding.level == "error" and finding.code.startswith("WORKSPACE_MODE_")
        ]
        if valid_mode_errors:
            failures.append(
                "resolved workspace modes produced errors: "
                + ", ".join(valid_mode_errors)
            )
        proposed_catalog = json.loads(
            (target / ".ai/project/workspace-modes/catalog.json").read_text(
                encoding="utf-8"
            )
        )
        proposed_catalog["selection"]["default_mode_id"] = None
        proposed_catalog["modes"][0]["state"] = "proposed"
        mode_data["state"] = "proposed"
        write_json(target / ".ai/project/workspace-modes/catalog.json", proposed_catalog)
        write_json(mode_path, mode_data)
        proposed_modes = validator(target)
        proposed_modes.check_workspace_modes(None)
        proposed_mode_errors = [
            finding.code
            for finding in proposed_modes.findings
            if finding.level == "error" and finding.code.startswith("WORKSPACE_MODE_")
        ]
        if proposed_mode_errors:
            failures.append(
                "proposal-only workspace modes produced errors: "
                + ", ".join(proposed_mode_errors)
            )

        def workspace_mode_codes() -> set[str]:
            checked = validator(target)
            checked.check_workspace_modes(None)
            return {
                finding.code
                for finding in checked.findings
                if finding.level == "error" and finding.code.startswith("WORKSPACE_MODE_")
            }

        proposed_catalog["selection"]["default_mode_id"] = mode_id
        write_json(target / ".ai/project/workspace-modes/catalog.json", proposed_catalog)
        if "WORKSPACE_MODE_DEFAULT" not in workspace_mode_codes():
            failures.append("workspace modes must reject a proposed default mode")

        proposed_catalog["selection"]["default_mode_id"] = mode_id
        proposed_catalog["modes"][0]["state"] = "accepted"
        mode_data["state"] = "accepted"
        write_json(target / ".ai/project/workspace-modes/catalog.json", proposed_catalog)
        write_json(mode_path, mode_data)

        mode_data["workspace_scope"]["root"] = "missing-workspace"
        write_json(mode_path, mode_data)
        if "WORKSPACE_MODE_SCOPE" not in workspace_mode_codes():
            failures.append("accepted workspace modes must reject missing workspace roots")
        mode_data["workspace_scope"]["root"] = "."

        mode_data["context"]["root_context"] = "required"
        write_json(mode_path, mode_data)
        if "WORKSPACE_MODE_CONTEXT" not in workspace_mode_codes():
            failures.append("accepted workspace modes must reject disabled required root context")
        mode_data["context"]["root_context"] = "skip"

        mode_data["constraints"]["grants_approval"] = True
        write_json(mode_path, mode_data)
        if "WORKSPACE_MODE_GRANT" not in workspace_mode_codes():
            failures.append("workspace modes must reject permission-granting constraints")
        mode_data["constraints"]["grants_approval"] = False

        proposed_catalog["modes"][0]["state"] = "proposed"
        write_json(target / ".ai/project/workspace-modes/catalog.json", proposed_catalog)
        write_json(mode_path, mode_data)
        if "WORKSPACE_MODE_DESCRIPTOR_DRIFT" not in workspace_mode_codes():
            failures.append("workspace modes must reject catalog and descriptor state drift")
        proposed_catalog["modes"][0]["state"] = "accepted"
        write_json(target / ".ai/project/workspace-modes/catalog.json", proposed_catalog)

        mode_data["relationships"].append(
            {
                "subject": "fixture-workspace",
                "relationship": "workspace-root",
                "adapter_role": "active",
                "ownership": "target",
                "evidence": ["README.md"],
            }
        )
        write_json(mode_path, mode_data)
        if "WORKSPACE_MODE_ACTIVE_ROOT" not in workspace_mode_codes():
            failures.append("accepted workspace modes must reject multiple active roots")
        mode_data["relationships"].pop()

        mode_data["relationships"].append(
            {
                "subject": "fixture-dependency",
                "relationship": "dependency",
                "adapter_role": "active",
                "ownership": "upstream",
                "evidence": ["README.md"],
            }
        )
        write_json(mode_path, mode_data)
        invalid_modes = validator(target)
        invalid_modes.check_workspace_modes(None)
        if "WORKSPACE_MODE_NESTED_ADAPTER" not in {
            finding.code for finding in invalid_modes.findings
        }:
            failures.append("workspace modes must reject active dependency adapters")
        write_json(router_path, {"intent_overlays": {}})

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

        registry_path = target / ".ai" / "project" / "source-of-truth-registry.md"
        registry_path.write_text(
            "# Registry\n\n"
            "### Fact Type: `business rule`\n\n"
            "Fact type: `business rule`\n"
            "Consistency map node: `fact-business-rule`\n\n"
            "### Fact Type: `data model`\n\n"
            "Fact type: `data model`\n"
            "Consistency map node: `fact-data-model`\n",
            encoding="utf-8",
        )
        write_json(
            map_path,
            {
                "schema_version": 2,
                "map_kind": "target-consistency-map",
                "human_registry": ".ai/project/source-of-truth-registry.md",
                "registry_sync_policy": {
                    "coverage": "every-live-registry-fact-type",
                    "node_reference": "registry-consistency-map-node-id",
                    "fact_type_match": "exact",
                    "extra_nodes": "allowed-for-derived-contract-area-system-and-adapter-surfaces",
                },
                "levels": ["fact", "contract", "area", "system", "adapter"],
                "relationship_types": [
                    "implements",
                    "verifies",
                    "documents",
                    "visualizes",
                    "generates",
                    "constrains",
                    "depends-on",
                    "routes",
                ],
                "impact_policy": {
                    "transitive_expand_when": ["dependent contract changes"],
                    "required_evidence": ["selected relationships"],
                },
                "nodes": [
                    {
                        "id": "fact-business-rule",
                        "fact_type": "business Rule",
                        "level": "fact",
                        "project_area": "core",
                        "canonical_owner": "docs/business.md",
                        "relationships": [
                            {
                                "id": "documents-business-rule",
                                "type": "documents",
                                "target": "docs/reference.md",
                                "target_level": "contract",
                                "direction": "outbound",
                                "required_when": ["business rule changes"],
                                "validation": ["manual review"],
                            }
                        ],
                    }
                ],
            },
        )
        registry_map_sync = validator(target)
        registry_map_sync.check_consistency_map()
        registry_map_codes = {
            finding.code for finding in registry_map_sync.findings
        }
        for required in [
            "CONSISTENCY_REGISTRY_NODE_FACT_TYPE_DRIFT",
            "CONSISTENCY_REGISTRY_NODE_MISSING",
        ]:
            if required not in registry_map_codes:
                failures.append(
                    f"registry/map semantic drift missing finding {required}"
                )

        capabilities_path = target / ".ai" / "framework" / "capabilities.json"
        write_json(
            capabilities_path,
            {
                "schema_version": 1,
                "capability_kind": "alatyr-optional-module-catalog",
                "modules": {
                    "consistency-map": {
                        "target_files": [
                            ".ai/assistant/flows/consistency-review.flow.md"
                        ]
                    }
                },
            },
        )
        stale_flow = (
            target
            / ".ai"
            / "assistant"
            / "flows"
            / "consistency-review.flow.md"
        )
        stale_flow.parent.mkdir(parents=True, exist_ok=True)
        stale_flow.write_text(
            "The consistency-map module is deferred.\n", encoding="utf-8"
        )
        stale_module = validator(target)
        stale_module.check_enabled_module_status_claims({"consistency-map"})
        if "ENABLED_MODULE_STALE_STATUS" not in {
            finding.code for finding in stale_module.findings
        }:
            failures.append("enabled module stale status claim was not rejected")
        stale_flow.write_text(
            "If the consistency-map module is deferred, stop and report it.\n",
            encoding="utf-8",
        )
        conditional_module = validator(target)
        conditional_module.check_enabled_module_status_claims({"consistency-map"})
        if "ENABLED_MODULE_STALE_STATUS" in {
            finding.code for finding in conditional_module.findings
        }:
            failures.append("conditional module-state guidance was treated as stale")

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

        historical_target = target / "historical-approval-selection"
        historical_path = (
            historical_target
            / ".ai"
            / "assistant"
            / "approvals"
            / "historical.json"
        )
        historical_data = dict(approval_data)
        historical_data["scope"] = dict(approval_data["scope"])
        historical_data["scope"]["allowed_files_or_surfaces"] = [
            "../external-project/**"
        ]
        historical_data["use_result"] = {
            "patch_changed_after_approval": "yes: historical correction",
            "implementation_within_scope": "yes",
        }
        write_json(historical_path, historical_data)

        ordinary_health = validator(
            historical_target, validation_phase="acceptance"
        )
        ordinary_health.check_approval_scope()
        ordinary_findings = {
            finding.code: finding.level for finding in ordinary_health.findings
        }
        for expected_archive_warning in {
            "APPROVAL_RECORD_SCOPE_INVALID",
            "APPROVAL_PATCH_CHANGED",
        }:
            if ordinary_findings.get(expected_archive_warning) != "warning":
                failures.append(
                    "ordinary health must audit historical approval archives without "
                    f"promoting {expected_archive_warning} to current-scope enforcement"
                )
        if "APPROVAL_SCOPE_MISMATCH" in ordinary_findings:
            failures.append(
                "ordinary current-health validation must not apply historical approval "
                "scope to the current diff"
            )
        if ordinary_findings.get("APPROVAL_ARCHIVE_CHECKED") != "info":
            failures.append("ordinary health must report historical approval archive audit")

        malformed_history = historical_path.with_name("malformed.json")
        malformed_history.write_text("{invalid\n", encoding="utf-8")
        malformed_health = validator(
            historical_target, validation_phase="acceptance"
        )
        malformed_health.check_approval_scope()
        if not any(
            finding.code == "APPROVAL_RECORD_INVALID_JSON"
            and finding.level == "warning"
            and finding.path.endswith("malformed.json")
            for finding in malformed_health.findings
        ):
            failures.append("ordinary health must detect malformed archived approvals")

        explicit_history = Validator(
            historical_target,
            framework_source=None,
            diff_ref=None,
            approval_records=[historical_path],
            enforce_approval_scope=False,
            change_packages=[],
            enforce_change_package=False,
            migration_diff=None,
            allow_placeholders=False,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
            validation_phase="acceptance",
        )
        explicit_history.check_approval_scope()
        explicit_codes = {finding.code for finding in explicit_history.findings}
        for required in {
            "APPROVAL_RECORD_SCOPE_INVALID",
            "APPROVAL_PATCH_CHANGED",
        }:
            if required not in explicit_codes:
                failures.append(
                    f"explicitly selected historical approval must retain {required}"
                )

        payload = findings_payload(
            [],
            target=target,
            strict_warnings=False,
            installation_state="accepted",
        )
        evidence = payload.get("evidence", {})
        if payload.get("schema_version") != 3:
            failures.append("validator JSON schema must expose evidence schema 3")
        if evidence.get("basis") != "current-state-structural":
            failures.append("validator JSON must classify current-state evidence")
        if evidence.get("historical_actions_verified") is not False:
            failures.append("validator JSON must not imply historical actions were verified")

        staging_payload = findings_payload(
            [
                Finding(
                    "warning",
                    "PLACEHOLDER_STAGING_UNRESOLVED",
                    "staged placeholder",
                    ".ai/project/debug/README.md:1",
                )
            ],
            target=target,
            strict_warnings=False,
            validation_phase="migration-staging",
            installation_state="staged",
        )
        if staging_payload.get("status") != "staged":
            failures.append("migration staging must not report passed status")
        if staging_payload.get("adapter_health", {}).get("state") != "unverified":
            failures.append("migration staging must report unverified adapter health")
        if staging_payload.get("placeholder_validation", {}).get("acceptance_eligible") is not False:
            failures.append("migration staging must never be acceptance eligible")
        if staging_payload.get("placeholder_validation", {}).get("unresolved_active") != 1:
            failures.append("migration staging must count unresolved active placeholders")

        active_target = target / "active-surface"
        active_readme = active_target / ".ai/project/debug/README.md"
        active_readme.parent.mkdir(parents=True, exist_ok=True)
        active_readme.write_text("Owner: `{DEBUG_EVIDENCE_OWNER}`\n", encoding="utf-8")
        strict_placeholders = validator(active_target, validation_phase="acceptance")
        strict_placeholders.capability_modules = {
            "debug-mode": {"target_files": [".ai/project/debug/README.md"]}
        }
        strict_placeholders.check_placeholders(
            None, "core", {"debug-mode"}
        )
        if "PLACEHOLDER_UNRESOLVED" not in {
            finding.code for finding in strict_placeholders.findings
        }:
            failures.append("acceptance must reject placeholders on enabled live surfaces")

        staged_placeholders = validator(
            active_target, validation_phase="migration-staging"
        )
        staged_placeholders.capability_modules = strict_placeholders.capability_modules
        staged_placeholders.check_placeholders(None, "core", {"debug-mode"})
        if "PLACEHOLDER_STAGING_UNRESOLVED" not in {
            finding.code for finding in staged_placeholders.findings
        }:
            failures.append("migration staging must inventory live placeholders")
        if any(
            finding.code == "PLACEHOLDER_UNRESOLVED"
            for finding in staged_placeholders.findings
        ):
            failures.append("migration staging must classify rather than accept/reject placeholders")

        profile_target = target / "module-profile-sync"
        profile_path = profile_target / ".ai/assistant/module-profile.md"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text("# Module Profile\n", encoding="utf-8")
        profile_manifest_path = profile_target / ".ai/alatyr.yaml"
        profile_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        profile_manifest_path.write_text(
            "modules:\n  enabled:\n    - debug-mode\n", encoding="utf-8"
        )
        profile_manifest = parse_manifest(profile_manifest_path)
        profile_validator = validator(profile_target)
        profile_validator.capability_modules = {"debug-mode": {}}
        profile_validator.check_module_profile_sync(profile_manifest)
        if "MODULE_PROFILE_ENABLED_MISSING" not in {
            finding.code for finding in profile_validator.findings
        }:
            failures.append("manifest-enabled modules must require a matching profile block")

        projection_target = target / "policy-projection"
        projection_readme = projection_target / ".ai/project/debug/README.md"
        projection_readme.parent.mkdir(parents=True, exist_ok=True)
        projection_readme.write_text("Owner: human-owner\n", encoding="utf-8")
        projection_validator = validator(projection_target)
        projection_validator.check_policy_readme_projection(
            index={"owner": "machine-owner"},
            readme_relpath=".ai/project/debug/README.md",
            fields={"Owner": "owner"},
            code_prefix="DEBUG_MODE_POLICY",
        )
        if "DEBUG_MODE_POLICY_DRIFT" not in {
            finding.code for finding in projection_validator.findings
        }:
            failures.append("machine and human policy metadata drift must be rejected")

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
            installation_state="accepted",
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
            installation_state="accepted",
        )
        if extension_health.get("adapter_health", {}).get("repair_operations") != [
            "extension-management"
        ]:
            failures.append("extension findings must route to extension-management")
        if extension_health.get("exit_code") != 0:
            failures.append("ordinary advisory warnings must remain non-blocking by default")

        contract_target = target / "versioned-record-contracts"
        shutil.copytree(ROOT / "templates" / "target", contract_target)
        engineering_template_path = contract_target / ".ai/assistant/templates/engineering-evidence-record.json"
        engineering_template = json.loads(engineering_template_path.read_text(encoding="utf-8"))
        engineering_template["schema_version"] = 1
        engineering_template["repository_binding"].pop("binding_state")
        engineering_template["repository_binding"].pop("prior_bindings")
        write_json(engineering_template_path, engineering_template)
        debug_template_path = contract_target / ".ai/assistant/templates/debug-session-record.json"
        debug_template = json.loads(debug_template_path.read_text(encoding="utf-8"))
        debug_template["schema_version"] = 1
        debug_template["final_result"]["repository_binding"].pop("binding_state")
        debug_template["final_result"]["repository_binding"].pop("prior_bindings")
        debug_template.pop("continuation")
        debug_template["final_result"].pop("claim_validation")
        debug_template["final_result"].pop("engineering_evidence_decision")
        write_json(debug_template_path, debug_template)
        stale_templates = validator(contract_target)
        manifest = parse_manifest(contract_target / ".ai/alatyr.yaml")
        stale_templates.check_engineering_evidence(manifest)
        stale_templates.check_debug_mode(manifest)
        stale_template_codes = {finding.code for finding in stale_templates.findings}
        for required in {
            "ENGINEERING_EVIDENCE_TEMPLATE_VERSION",
            "ENGINEERING_EVIDENCE_TEMPLATE_BINDING",
            "DEBUG_MODE_TEMPLATE_VERSION",
            "DEBUG_MODE_TEMPLATE_BINDING",
            "DEBUG_MODE_TEMPLATE_EVIDENCE_DECISION",
            "DEBUG_MODE_TEMPLATE_CONTINUATION",
        }:
            if required not in stale_template_codes:
                failures.append(f"installed validator did not detect stale authoring contract {required}")

        manifest_path = contract_target / ".ai/alatyr.yaml"
        manifest_text = manifest_path.read_text(encoding="utf-8")
        manifest_text = manifest_text.replace(
            "engineering_evidence:\n  contract_version: 3",
            "engineering_evidence:\n  contract_version: 1",
        ).replace(
            "debug_mode:\n  contract_version: 6",
            "debug_mode:\n  contract_version: 1",
        )
        manifest_path.write_text(manifest_text, encoding="utf-8")
        stale_contracts = validator(contract_target)
        stale_manifest = parse_manifest(manifest_path)
        stale_contracts.check_engineering_evidence(stale_manifest)
        stale_contracts.check_debug_mode(stale_manifest)
        stale_contract_codes = {finding.code for finding in stale_contracts.findings}
        for required in {
            "ENGINEERING_EVIDENCE_CONTRACT_VERSION",
            "DEBUG_MODE_CONTRACT_VERSION",
        }:
            if required not in stale_contract_codes:
                failures.append(f"installed validator did not detect stale manifest contract {required}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("OK: checked target adapter validator routing, scope, and evidence contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
