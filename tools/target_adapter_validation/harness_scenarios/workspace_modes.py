"""Target-validator scenarios for workspace modes."""

from __future__ import annotations

from .common import (
    ROOT,
    json,
    validator,
    write_json,
)


def run(target: Path, failures: list[str]) -> None:
    router_path = target / ".ai" / "assistant" / "context-router.json"
    module_profile_path = target / ".ai" / "assistant" / "module-profile.md"
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
