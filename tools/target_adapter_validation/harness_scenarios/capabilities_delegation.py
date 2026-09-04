"""Target-validator scenarios for capabilities delegation."""

from __future__ import annotations

from .common import (
    DELEGATION_FIXTURE_PATHS,
    Path,
    ROOT,
    json,
    validator,
    write_json,
)


def run(target: Path, failures: list[str]) -> None:
    router_path = target / ".ai" / "assistant" / "context-router.json"
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
