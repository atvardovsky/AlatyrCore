"""Validate the optional blueprint-driven change capability."""

from __future__ import annotations

from typing import Any

from target_adapter_validation.capability import (
    CapabilityValidationContext,
    FunctionCapabilityModule,
)


CATALOG_RELPATH = ".ai/assistant/operation-catalog.json"
EXPECTED_OPERATIONS = {
    "create-project-blueprint": ".ai/assistant/flows/project-blueprint-creation.flow.md",
    "product-change": ".ai/assistant/flows/blueprint-driven-change.flow.md",
}
REQUIRED_PATHS = (
    ".ai/framework/blueprint-driven-change.md",
    *EXPECTED_OPERATIONS.values(),
)


def validate_blueprint_change(
    context: CapabilityValidationContext,
    manifest: Any,
) -> None:
    del manifest
    if not context.module_validation_enabled(
        "blueprint-change",
        "BLUEPRINT_CHANGE_MODULE_UNDECLARED",
        "BLUEPRINT_CHANGE_MODULE_STATE_MISSING",
        "blueprint-change",
    ):
        return

    for relpath in REQUIRED_PATHS:
        if not context.is_target_file(relpath):
            context.error(
                "BLUEPRINT_CHANGE_REQUIRED_FILE_MISSING",
                "enabled blueprint-change capability is missing a required contract",
                relpath,
            )

    catalog = context.load_json_object(
        context.target_path(CATALOG_RELPATH), "BLUEPRINT_CHANGE_OPERATION_CATALOG"
    )
    operations = catalog.get("operations") if catalog else None
    if not isinstance(operations, list):
        context.error(
            "BLUEPRINT_CHANGE_OPERATION_CATALOG",
            "enabled blueprint-change capability requires the operation catalog",
            CATALOG_RELPATH,
        )
        return

    by_id = {
        operation.get("id"): operation
        for operation in operations
        if isinstance(operation, dict) and isinstance(operation.get("id"), str)
    }
    for operation_id, expected_flow in EXPECTED_OPERATIONS.items():
        operation = by_id.get(operation_id)
        if operation is None:
            context.error(
                "BLUEPRINT_CHANGE_OPERATION_MISSING",
                f"enabled blueprint-change capability is missing operation {operation_id}",
                CATALOG_RELPATH,
            )
            continue
        if operation.get("required_module") != "blueprint-change":
            context.error(
                "BLUEPRINT_CHANGE_OPERATION_MODULE",
                f"operation {operation_id} must require blueprint-change",
                CATALOG_RELPATH,
            )
        if operation.get("flow") != expected_flow:
            context.error(
                "BLUEPRINT_CHANGE_OPERATION_FLOW",
                f"operation {operation_id} must route to {expected_flow}",
                CATALOG_RELPATH,
            )


BLUEPRINT_CHANGE_MODULE = FunctionCapabilityModule(
    "check_blueprint_change", validate_blueprint_change
)
