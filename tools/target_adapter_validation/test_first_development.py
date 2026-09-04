"""Validate target-owned test first development support."""

from __future__ import annotations

from typing import Any
from target_validation_support import ManifestData, dotted, is_placeholder, is_unresolved_value

from target_adapter_validation.capability import (
    CapabilityValidationContext,
    FunctionCapabilityModule,
)


def validate_test_first_development(
    context: CapabilityValidationContext,
    manifest: ManifestData | None,
) -> None:
    if not context.module_validation_enabled(
        "test-first-development",
        "TDD_MODULE_UNDECLARED",
        "TDD_MODULE_STATE_MISSING",
        "test-first-development",
    ):
        return

    required_paths = [
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
    missing = False
    for relpath in required_paths:
        if not context.target_path(relpath).is_file():
            missing = True
            context.error(
                "TDD_REQUIRED_FILE_MISSING",
                "enabled test-first-development module is missing a contract",
                relpath,
            )
    if missing:
        return

    if manifest is not None:
        expected_manifest = {
            ("source_of_truth", "testing_index"): required_paths[0],
            ("source_of_truth", "test_first_policy"): required_paths[1],
            ("operations", "test_first_configuration"): required_paths[3],
            ("operations", "test_first_change"): required_paths[4],
            ("operations", "test_first_evidence"): required_paths[6],
            ("test_first_development", "policy"): required_paths[1],
            ("test_first_development", "intent"): required_paths[2],
            ("test_first_development", "configuration_flow"): required_paths[3],
            ("test_first_development", "change_flow"): required_paths[4],
            ("test_first_development", "gate"): required_paths[5],
            ("test_first_development", "evidence"): required_paths[6],
            ("test_first_development", "skill"): required_paths[7],
        }
        for key, expected in expected_manifest.items():
            scalar = manifest.scalars.get(key)
            if scalar is None or scalar.value != expected:
                context.error(
                    "TDD_MANIFEST_PATH",
                    f"{dotted(key)} must be {expected} when test-first development is enabled",
                    ".ai/alatyr.yaml",
                )

    policy_relpath = required_paths[1]
    policy = context.load_json_object(
        context.target_path(policy_relpath), "TDD_POLICY"
    )
    if policy is None:
        return

    def resolved(value: Any) -> bool:
        return (
            isinstance(value, str)
            and bool(value.strip())
            and not is_placeholder(value)
            and not is_unresolved_value(value)
        )

    if policy.get("schema_version") != 1:
        context.error("TDD_POLICY_SCHEMA", "schema_version should be 1", policy_relpath)
    if policy.get("policy_kind") != "target-test-first-development-policy":
        context.error("TDD_POLICY_KIND", "policy_kind is invalid", policy_relpath)
    if str(policy.get("state", "")).casefold() not in {"enabled", "required"}:
        context.error(
            "TDD_POLICY_NOT_ENABLED",
            "enabled module requires enabled or required target policy state",
            policy_relpath,
        )
    for field in ["project", "owner", "decision_authority", "last_reviewed", "evidence_revision"]:
        if not resolved(policy.get(field)):
            context.error(
                "TDD_POLICY_METADATA_UNRESOLVED",
                f"enabled test-first policy requires resolved {field}",
                policy_relpath,
            )

    suggestion = policy.get("suggestion")
    if not isinstance(suggestion, dict):
        context.error("TDD_SUGGESTION_SHAPE", "suggestion must be an object", policy_relpath)
    else:
        if suggestion.get("mode") not in {"off", "advisory"}:
            context.error("TDD_SUGGESTION_MODE", "suggestion.mode must be off or advisory", policy_relpath)
        if suggestion.get("minimum_result") not in {"recommended", "required"}:
            context.error("TDD_SUGGESTION_RESULT", "suggestion.minimum_result is invalid", policy_relpath)
        if suggestion.get("max_per_task") != 1 or suggestion.get("suppress_after_decline") is not True:
            context.error("TDD_SUGGESTION_BOUNDS", "suggestions must be limited to once per task and suppressed after decline", policy_relpath)
        if suggestion.get("cost_statement_required") is not True:
            context.error("TDD_SUGGESTION_COST", "suggestions must state expected cost", policy_relpath)

    valid_modes = {
        "strict-tdd", "regression-first", "characterization-first",
        "contract-first", "test-after-with-reason",
    }
    modes = policy.get("available_modes")
    if not isinstance(modes, list) or not modes or not all(mode in valid_modes for mode in modes):
        context.error("TDD_MODES_INVALID", "available_modes must contain accepted test-first modes", policy_relpath)

    triggers = policy.get("activation_triggers")
    if not isinstance(triggers, list) or not triggers:
        context.error("TDD_TRIGGERS_EMPTY", "enabled policy requires activation triggers", policy_relpath)
    else:
        trigger_ids: set[str] = set()
        for index, trigger in enumerate(triggers):
            if not isinstance(trigger, dict):
                context.error("TDD_TRIGGER_SHAPE", f"activation_triggers[{index}] must be an object", policy_relpath)
                continue
            for field in ["id", "state", "mode"]:
                if not resolved(trigger.get(field)):
                    context.error("TDD_TRIGGER_UNRESOLVED", f"activation_triggers[{index}].{field} must be resolved", policy_relpath)
            trigger_id = trigger.get("id")
            if resolved(trigger_id):
                if trigger_id in trigger_ids:
                    context.error(
                        "TDD_TRIGGER_DUPLICATE",
                        f"activation_triggers contains duplicate id {trigger_id}",
                        policy_relpath,
                    )
                trigger_ids.add(trigger_id)
            if trigger.get("state") not in {"required", "recommended", "disabled"}:
                context.error("TDD_TRIGGER_STATE", f"activation_triggers[{index}].state is invalid", policy_relpath)
            if trigger.get("mode") not in valid_modes:
                context.error("TDD_TRIGGER_MODE", f"activation_triggers[{index}].mode is invalid", policy_relpath)
            elif isinstance(modes, list) and trigger.get("mode") not in modes:
                context.error(
                    "TDD_TRIGGER_MODE_UNAVAILABLE",
                    f"activation_triggers[{index}].mode is not in available_modes",
                    policy_relpath,
                )
            for field in ["changed_fact_classes", "conditions", "test_level_ids"]:
                value = trigger.get(field)
                if not isinstance(value, list) or not value or not all(resolved(item) for item in value):
                    context.error("TDD_TRIGGER_LIST", f"activation_triggers[{index}].{field} needs resolved values", policy_relpath)
            exceptions = trigger.get("exceptions")
            if not isinstance(exceptions, list) or not all(
                resolved(item) for item in exceptions
            ):
                context.error(
                    "TDD_TRIGGER_EXCEPTIONS",
                    f"activation_triggers[{index}].exceptions must contain resolved IDs",
                    policy_relpath,
                )

    for field in ["test_levels", "commands", "evidence_requirements"]:
        value = policy.get(field)
        if not isinstance(value, list) or not value:
            context.error("TDD_POLICY_LIST_EMPTY", f"{field} must be non-empty", policy_relpath)
    exceptions = policy.get("exceptions")
    if not isinstance(exceptions, list):
        context.error("TDD_EXCEPTIONS_SHAPE", "exceptions must be a list", policy_relpath)
    evidence_requirements = policy.get("evidence_requirements")
    if isinstance(evidence_requirements, list) and not all(
        resolved(item) for item in evidence_requirements
    ):
        context.error(
            "TDD_EVIDENCE_REQUIREMENTS",
            "evidence_requirements must contain resolved values",
            policy_relpath,
        )
    known_gaps = policy.get("known_gaps")
    if not isinstance(known_gaps, list) or not all(
        resolved(item) for item in known_gaps
    ):
        context.error(
            "TDD_KNOWN_GAPS",
            "known_gaps must be a list of resolved values",
            policy_relpath,
        )

    def indexed_records(field: str) -> tuple[dict[str, dict[str, Any]], bool]:
        records = policy.get(field)
        indexed: dict[str, dict[str, Any]] = {}
        valid = isinstance(records, list)
        if not isinstance(records, list):
            return indexed, False
        for index, record in enumerate(records):
            if not isinstance(record, dict) or not resolved(record.get("id")):
                context.error(
                    "TDD_RECORD_ID",
                    f"{field}[{index}] requires a resolved id",
                    policy_relpath,
                )
                valid = False
                continue
            record_id = record["id"]
            if record_id in indexed:
                context.error(
                    "TDD_RECORD_DUPLICATE",
                    f"{field} contains duplicate id {record_id}",
                    policy_relpath,
                )
                valid = False
            indexed[record_id] = record
        return indexed, valid

    test_levels, _ = indexed_records("test_levels")
    commands, _ = indexed_records("commands")
    exception_records, _ = indexed_records("exceptions")

    for level_id, level in test_levels.items():
        for field in ["purpose", "feedback_time"]:
            if not resolved(level.get(field)):
                context.error(
                    "TDD_TEST_LEVEL_UNRESOLVED",
                    f"test level {level_id} requires resolved {field}",
                    policy_relpath,
                )
        for field in ["paths", "command_ids", "fixtures_and_helpers"]:
            values = level.get(field)
            if not isinstance(values, list) or not values or not all(
                resolved(item) for item in values
            ):
                context.error(
                    "TDD_TEST_LEVEL_LIST",
                    f"test level {level_id}.{field} requires resolved values",
                    policy_relpath,
                )
        for command_id in level.get("command_ids", []):
            if command_id not in commands:
                context.error(
                    "TDD_COMMAND_REFERENCE",
                    f"test level {level_id} references unknown command {command_id}",
                    policy_relpath,
                )

    for command_id, command in commands.items():
        for field in ["command", "scope", "live_external_actions"]:
            if not resolved(command.get(field)):
                context.error(
                    "TDD_COMMAND_UNRESOLVED",
                    f"command {command_id} requires resolved {field}",
                    policy_relpath,
                )
        if command.get("live_external_actions") not in {
            "forbidden", "allowed-with-approval", "not-applicable",
        }:
            context.error(
                "TDD_COMMAND_EXTERNAL_ACTIONS",
                f"command {command_id}.live_external_actions is invalid",
                policy_relpath,
            )

    for exception_id, exception in exception_records.items():
        for field in ["condition", "approval", "alternative_validation"]:
            if not resolved(exception.get(field)):
                context.error(
                    "TDD_EXCEPTION_UNRESOLVED",
                    f"exception {exception_id} requires resolved {field}",
                    policy_relpath,
                )
        if exception.get("required_reason") is not True:
            context.error(
                "TDD_EXCEPTION_REASON",
                f"exception {exception_id} must require a reason",
                policy_relpath,
            )

    for index, trigger in enumerate(triggers if isinstance(triggers, list) else []):
        if not isinstance(trigger, dict):
            continue
        for level_id in trigger.get("test_level_ids", []):
            if level_id not in test_levels:
                context.error(
                    "TDD_TEST_LEVEL_REFERENCE",
                    f"activation_triggers[{index}] references unknown test level {level_id}",
                    policy_relpath,
                )
        for exception_id in trigger.get("exceptions", []):
            if exception_id not in exception_records:
                context.error(
                    "TDD_EXCEPTION_REFERENCE",
                    f"activation_triggers[{index}] references unknown exception {exception_id}",
                    policy_relpath,
                )
    isolation = policy.get("isolation")
    if not isinstance(isolation, dict):
        context.error("TDD_ISOLATION_SHAPE", "isolation must be an object", policy_relpath)
    else:
        for field in ["clock", "randomness", "database", "queue", "filesystem", "network", "secrets"]:
            if not resolved(isolation.get(field)):
                context.error("TDD_ISOLATION_UNRESOLVED", f"isolation.{field} must be resolved", policy_relpath)

    catalog = context.load_json_object(
        context.target_path(".ai/assistant/operation-catalog.json"), "OPERATION_CATALOG"
    )
    operations = catalog.get("operations") if isinstance(catalog, dict) else None
    by_id = {
        item.get("id"): item
        for item in operations or []
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    configuration = by_id.get("test-first-configuration")
    execution = by_id.get("test-first-change")
    if not isinstance(configuration, dict) or configuration.get("required_module") != "core-profile":
        context.error("TDD_CONFIGURATION_UNROUTED", "test-first configuration must remain available through core-profile", ".ai/assistant/operation-catalog.json")
    if not isinstance(execution, dict) or execution.get("required_module") != "test-first-development":
        context.error("TDD_EXECUTION_UNROUTED", "test-first execution must require the enabled module", ".ai/assistant/operation-catalog.json")

    router = context.load_json_object(
        context.target_path(".ai/assistant/context-router.json"), "ROUTER"
    )
    overlays = router.get("intent_overlays") if isinstance(router, dict) else None
    route = overlays.get("test-first-request") if isinstance(overlays, dict) else None
    if not isinstance(route, dict) or route.get("operation_candidates") != [
        "test-first-configuration", "test-first-change"
    ]:
        context.error("TDD_INTENT_UNROUTED", "test-first intent must route configuration and execution", ".ai/assistant/context-router.json")

    context.info(
        "TDD_EVIDENCE_LIMIT",
        "test-first structural checks do not prove command execution, expected RED causality, assertion semantics, or changed-contract correctness",
    )


TEST_FIRST_DEVELOPMENT_MODULE = FunctionCapabilityModule(
    check_id="check_test_first_development",
    validator=validate_test_first_development,
)
