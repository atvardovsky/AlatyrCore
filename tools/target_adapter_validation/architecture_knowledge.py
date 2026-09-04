"""Validate target-owned architecture knowledge support."""

from __future__ import annotations

from typing import Any
from target_validation_support import ManifestData, dotted
from target_adapter_validation.values import is_resolved_string

from target_adapter_validation.capability import (
    CapabilityValidationContext,
    FunctionCapabilityModule,
)


def validate_architecture_knowledge(
    context: CapabilityValidationContext,
    manifest: ManifestData | None,
) -> None:
    if not context.module_validation_enabled(
        "architecture-knowledge",
        "ARCHITECTURE_MODULE_UNDECLARED",
        "ARCHITECTURE_MODULE_STATE_MISSING",
        "architecture-knowledge",
    ):
        return

    required_paths = [
        ".ai/project/architecture/README.md",
        ".ai/project/architecture/catalog.json",
        ".ai/assistant/context/intents/architecture-request.json",
        ".ai/assistant/flows/architecture-assistance.flow.md",
        ".ai/assistant/templates/architecture-pattern.md",
        ".ai/assistant/templates/architecture-area.md",
        ".ai/assistant/templates/architecture-discussion-result.md",
        ".ai/framework/architecture-knowledge.md",
    ]
    missing_required = False
    for relpath in required_paths:
        if not context.target_path(relpath).is_file():
            missing_required = True
            context.error(
                "ARCHITECTURE_REQUIRED_FILE_MISSING",
                "enabled architecture-knowledge module is missing a contract",
                relpath,
            )
    if missing_required:
        return

    if manifest is not None:
        expected_manifest = {
            ("source_of_truth", "architecture_index"): required_paths[0],
            ("source_of_truth", "architecture_catalog"): required_paths[1],
            ("operations", "architecture_assistance"): required_paths[3],
            (
                "operations",
                "architecture_discussion_result",
            ): required_paths[6],
        }
        for key, expected in expected_manifest.items():
            scalar = manifest.scalars.get(key)
            if scalar is None or scalar.value != expected:
                context.error(
                    "ARCHITECTURE_MANIFEST_PATH",
                    f"{dotted(key)} must be {expected} when architecture knowledge is enabled",
                    ".ai/alatyr.yaml",
                )

    catalog_relpath = required_paths[1]
    catalog = context.load_json_object(
        context.target_path(catalog_relpath), "ARCHITECTURE_CATALOG"
    )
    if catalog is None:
        return
    if catalog.get("schema_version") != 1:
        context.error(
            "ARCHITECTURE_CATALOG_SCHEMA",
            "schema_version should be 1",
            catalog_relpath,
        )
    if catalog.get("catalog_kind") != "target-architecture-knowledge-catalog":
        context.error(
            "ARCHITECTURE_CATALOG_KIND",
            "catalog_kind should be target-architecture-knowledge-catalog",
            catalog_relpath,
        )
    if catalog.get("human_index") != required_paths[0]:
        context.error(
            "ARCHITECTURE_CATALOG_INDEX",
            f"human_index should point to {required_paths[0]}",
            catalog_relpath,
        )

    concrete = is_resolved_string

    def string_list(value: Any, label: str, *, non_empty: bool = True) -> list[str]:
        if not isinstance(value, list) or (non_empty and not value) or not all(
            isinstance(item, str) and item for item in value
        ):
            context.error(
                "ARCHITECTURE_CATALOG_LIST",
                f"{label} must be a {'non-empty ' if non_empty else ''}string list",
                catalog_relpath,
            )
            return []
        return value

    metadata_fields = [
        "project",
        "module_state",
        "architecture_owner",
        "decision_authority",
        "last_reviewed",
        "evidence_revision",
    ]
    for field in metadata_fields:
        value = catalog.get(field)
        if not isinstance(value, str) or not value.strip():
            context.error(
                "ARCHITECTURE_CATALOG_METADATA",
                f"{field} must be a non-empty string",
                catalog_relpath,
            )
    module_state = catalog.get("module_state")
    if concrete(module_state) and module_state not in {
        "enabled",
        "deferred",
        "disabled",
        "not-applicable",
        "blocked",
    }:
        context.error(
            "ARCHITECTURE_MODULE_STATE",
            f"module_state is invalid: {module_state}",
            catalog_relpath,
        )
    if module_state == "enabled":
        for field in [
            "project",
            "architecture_owner",
            "decision_authority",
            "last_reviewed",
            "evidence_revision",
        ]:
            if not concrete(catalog.get(field)):
                context.error(
                    "ARCHITECTURE_ENABLED_METADATA_UNRESOLVED",
                    f"enabled architecture knowledge requires resolved {field}",
                    catalog_relpath,
                )

    canonical_sources = string_list(
        catalog.get("canonical_sources"), "canonical_sources"
    )
    decision_sources = string_list(
        catalog.get("decision_sources"), "decision_sources"
    )
    known_gaps = string_list(
        catalog.get("known_gaps"), "known_gaps", non_empty=False
    )
    if module_state == "enabled":
        for label, values in [
            ("canonical_sources", canonical_sources),
            ("decision_sources", decision_sources),
        ]:
            if not any(concrete(item) for item in values):
                context.error(
                    "ARCHITECTURE_ENABLED_METADATA_UNRESOLVED",
                    f"enabled architecture knowledge requires resolved {label}",
                    catalog_relpath,
                )
        if any(not concrete(item) for item in known_gaps):
            context.error(
                "ARCHITECTURE_KNOWN_GAP_UNRESOLVED",
                "known_gaps must be empty or contain concrete gap records",
                catalog_relpath,
            )

    statuses = {
        "observed",
        "proposed",
        "accepted",
        "preferred",
        "restricted",
        "deprecated",
        "contradicted",
        "unknown",
    }
    pattern_kinds = {
        "style",
        "boundary",
        "integration",
        "data",
        "security",
        "runtime",
        "operational",
        "other",
    }
    accepted_states = {"accepted", "preferred", "restricted", "deprecated"}
    areas = catalog.get("areas")
    if not isinstance(areas, list):
        context.error(
            "ARCHITECTURE_AREAS_SHAPE",
            "areas must be a list",
            catalog_relpath,
        )
        areas = []
    patterns = catalog.get("patterns")
    if not isinstance(patterns, list):
        context.error(
            "ARCHITECTURE_PATTERNS_SHAPE",
            "patterns must be a list",
            catalog_relpath,
        )
        patterns = []

    area_ids = {
        item.get("id")
        for item in areas
        if isinstance(item, dict) and concrete(item.get("id"))
    }
    concrete_area_count = sum(
        1
        for item in areas
        if isinstance(item, dict) and concrete(item.get("id"))
    )
    if len(area_ids) != concrete_area_count:
        context.error(
            "ARCHITECTURE_AREA_ID_DUPLICATE",
            "concrete area IDs must be unique",
            catalog_relpath,
        )

    pattern_ids = {
        item.get("id")
        for item in patterns
        if isinstance(item, dict) and concrete(item.get("id"))
    }
    concrete_pattern_count = sum(
        1
        for item in patterns
        if isinstance(item, dict) and concrete(item.get("id"))
    )
    if len(pattern_ids) != concrete_pattern_count:
        context.error(
            "ARCHITECTURE_PATTERN_ID_DUPLICATE",
            "concrete pattern IDs must be unique",
            catalog_relpath,
        )

    area_fields = {"id", "name", "status", "owner", "detail", "evidence", "pattern_ids"}
    for index, area in enumerate(areas):
        label = f"areas[{index}]"
        if not isinstance(area, dict):
            context.error("ARCHITECTURE_AREA_SHAPE", f"{label} must be an object", catalog_relpath)
            continue
        missing = sorted(area_fields - set(area))
        if missing:
            context.error("ARCHITECTURE_AREA_FIELDS", f"{label} is missing {missing}", catalog_relpath)
        status = area.get("status")
        if concrete(status) and status not in statuses:
            context.error(
                "ARCHITECTURE_ITEM_STATUS",
                f"{label}.status is invalid: {status}",
                catalog_relpath,
            )
        evidence = string_list(area.get("evidence"), f"{label}.evidence")
        refs = string_list(
            area.get("pattern_ids"),
            f"{label}.pattern_ids",
            non_empty=False,
        )
        for ref in refs:
            if concrete(ref) and ref not in pattern_ids:
                context.error(
                    "ARCHITECTURE_PATTERN_REFERENCE",
                    f"{label} references unknown pattern {ref}",
                    catalog_relpath,
                )
        if module_state == "enabled":
            for field in ["id", "name", "status", "owner"]:
                if not concrete(area.get(field)):
                    context.error(
                        "ARCHITECTURE_ITEM_IDENTITY_UNRESOLVED",
                        f"{label}.{field} must be resolved",
                        catalog_relpath,
                    )
            if not any(concrete(item) for item in evidence):
                context.error(
                    "ARCHITECTURE_ITEM_EVIDENCE_UNRESOLVED",
                    f"{label} needs concrete evidence",
                    catalog_relpath,
                )

    pattern_fields = {
        "id", "name", "kind", "status", "scope", "problem",
        "decision_owner", "decision_record", "detail", "evidence",
        "validation", "related_pattern_ids", "last_verified_revision",
    }
    for index, pattern in enumerate(patterns):
        label = f"patterns[{index}]"
        if not isinstance(pattern, dict):
            context.error("ARCHITECTURE_PATTERN_SHAPE", f"{label} must be an object", catalog_relpath)
            continue
        missing = sorted(pattern_fields - set(pattern))
        if missing:
            context.error("ARCHITECTURE_PATTERN_FIELDS", f"{label} is missing {missing}", catalog_relpath)
        status = pattern.get("status")
        if concrete(status) and status not in statuses:
            context.error(
                "ARCHITECTURE_ITEM_STATUS",
                f"{label}.status is invalid: {status}",
                catalog_relpath,
            )
        kind = pattern.get("kind")
        if concrete(kind) and kind not in pattern_kinds:
            context.error(
                "ARCHITECTURE_PATTERN_KIND",
                f"{label}.kind is invalid: {kind}",
                catalog_relpath,
            )
        for field in ["scope", "evidence", "validation"]:
            values = string_list(pattern.get(field), f"{label}.{field}")
            if (
                module_state == "enabled"
                and not any(concrete(item) for item in values)
            ):
                context.error(
                    "ARCHITECTURE_ITEM_FIELD_UNRESOLVED",
                    f"{label}.{field} needs at least one concrete value",
                    catalog_relpath,
                )
        refs = string_list(
            pattern.get("related_pattern_ids"),
            f"{label}.related_pattern_ids",
            non_empty=False,
        )
        for ref in refs:
            if concrete(ref) and ref not in pattern_ids:
                context.error(
                    "ARCHITECTURE_PATTERN_REFERENCE",
                    f"{label} references unknown pattern {ref}",
                    catalog_relpath,
                )
        if module_state == "enabled":
            for field in [
                "id",
                "name",
                "kind",
                "status",
                "problem",
                "decision_owner",
                "last_verified_revision",
            ]:
                if not concrete(pattern.get(field)):
                    context.error(
                        "ARCHITECTURE_ITEM_IDENTITY_UNRESOLVED",
                        f"{label}.{field} must be resolved",
                        catalog_relpath,
                    )
        if status in accepted_states:
            for field in ["decision_owner", "decision_record", "last_verified_revision"]:
                if not concrete(pattern.get(field)):
                    context.error(
                        "ARCHITECTURE_ACCEPTED_EVIDENCE",
                        f"{label} accepted state requires resolved {field}",
                        catalog_relpath,
                    )

    operation_catalog = context.load_json_object(
        context.target_path(".ai/assistant/operation-catalog.json"),
        "OPERATION_CATALOG",
    )
    operations = operation_catalog.get("operations") if isinstance(operation_catalog, dict) else None
    operation = next(
        (
            item for item in operations
            if isinstance(item, dict) and item.get("id") == "architecture-assistance"
        ),
        None,
    ) if isinstance(operations, list) else None
    if not isinstance(operation, dict):
        context.error(
            "ARCHITECTURE_OPERATION_MISSING",
            "enabled architecture knowledge requires architecture-assistance operation",
            ".ai/assistant/operation-catalog.json",
        )
    else:
        if operation.get("required_module") != "architecture-knowledge":
            context.error("ARCHITECTURE_OPERATION_MODULE", "architecture-assistance must require architecture-knowledge", ".ai/assistant/operation-catalog.json")
        if operation.get("flow") != required_paths[3]:
            context.error("ARCHITECTURE_OPERATION_FLOW", f"architecture-assistance must route to {required_paths[3]}", ".ai/assistant/operation-catalog.json")
        if operation.get("allowed_actions") != ["read-only", "docs-only", "full-with-approval"]:
            context.error("ARCHITECTURE_OPERATION_ACTIONS", "architecture-assistance allowed actions are invalid", ".ai/assistant/operation-catalog.json")

    router = context.load_json_object(
        context.target_path(".ai/assistant/context-router.json"), "ROUTER"
    )
    overlays = router.get("intent_overlays") if isinstance(router, dict) else None
    route = overlays.get("architecture-request") if isinstance(overlays, dict) else None
    if not isinstance(route, dict) or route.get("operation_candidates") != ["architecture-assistance"]:
        context.error(
            "ARCHITECTURE_OPERATION_UNROUTED",
            "enabled architecture assistance has no architecture-request intent route",
            ".ai/assistant/context-router.json",
        )

    required_text = {
        required_paths[0]: ["## Status Meanings", "## Architecture Patterns And Items", "Evidence revision:"],
        required_paths[3]: ["## Routing Modes", "no-change baseline", "reuse of an accepted project pattern", "adaptation of an existing pattern", "new pattern", "`docs-only`", "`full-with-approval`"],
        required_paths[4]: ["Pattern ID:", "Problem addressed:", "Rules and invariants:", "Do not use when:", "Last verified revision:"],
        required_paths[5]: ["Area ID:", "Responsibilities:", "Pattern IDs:", "Validation or fitness checks:"],
        required_paths[6]: ["No-change baseline:", "Reuse accepted project pattern:", "Adapt existing project pattern:", "Introduce new pattern:", "Pattern-proliferation result:"],
    }
    for relpath, snippets in required_text.items():
        text = context.read_text(context.target_path(relpath))
        for snippet in snippets:
            if snippet not in text:
                context.error(
                    "ARCHITECTURE_CONTRACT_INCOMPLETE",
                    f"architecture contract is missing {snippet}",
                    relpath,
                )


ARCHITECTURE_KNOWLEDGE_MODULE = FunctionCapabilityModule(
    check_id="check_architecture_knowledge",
    validator=validate_architecture_knowledge,
)
