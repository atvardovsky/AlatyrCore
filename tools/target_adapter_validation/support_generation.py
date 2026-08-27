"""Validate the optional support-generation capability."""

from __future__ import annotations

from typing import Any

from support_generation import (
    INDEX_PATH,
    REGISTRY_PATH,
    SupportGenerationError,
    build_generation_index,
    load_index,
    load_registry,
)
from target_adapter_validation.capability import CapabilityValidationContext


def _has_placeholder(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_placeholder(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_placeholder(item) for item in value)
    return isinstance(value, str) and "{" in value and "}" in value


class SupportGenerationModule:
    check_id = "check_support_generation"

    def validate(self, context: CapabilityValidationContext, manifest: Any) -> None:
        del manifest
        target = context.target_path(".ai").parent
        registry_data = context.load_json_object(
            context.target_path(REGISTRY_PATH), "SUPPORT_GENERATION_REGISTRY"
        )
        index_data = context.load_json_object(
            context.target_path(INDEX_PATH), "SUPPORT_GENERATION_INDEX"
        )
        if registry_data is None or index_data is None:
            return
        if _has_placeholder(registry_data) or _has_placeholder(index_data):
            report = context.warn if context.allow_placeholders else context.error
            report(
                "SUPPORT_GENERATION_UNRESOLVED",
                "enabled support-generation contracts must be target-adapted and recorded",
                REGISTRY_PATH,
            )
            return
        try:
            load_registry(target)
            current = build_generation_index(target)
            recorded = load_index(target)
        except SupportGenerationError as exc:
            context.error("SUPPORT_GENERATION_INVALID", str(exc), REGISTRY_PATH)
            return
        if recorded != current:
            context.error(
                "SUPPORT_GENERATION_INDEX_STALE",
                "generated support-generation index differs from current inputs or outputs",
                INDEX_PATH,
            )
            return
        context.info(
            "SUPPORT_GENERATION_CURRENT",
            f"support-generation index covers {len(current['artifacts'])} artifacts",
            INDEX_PATH,
        )


SUPPORT_GENERATION_MODULE = SupportGenerationModule()
