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
            recorded = load_index(target)
            current = build_generation_index(target, recorded_index=recorded)
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
        missing_inputs = [
            item["id"]
            for item in current["artifacts"]
            if item.get("missing_inputs")
        ]
        if missing_inputs:
            context.error(
                "SUPPORT_GENERATION_INPUTS_MISSING",
                "required support-generation inputs have no effective matches: "
                + ", ".join(missing_inputs),
                INDEX_PATH,
            )
            return
        missing_reviews = [
            item["id"]
            for item in current["artifacts"]
            if item["mode"] != "deterministic-derived"
            and not item.get("review_evidence")
        ]
        if missing_reviews:
            context.error(
                "SUPPORT_GENERATION_REVIEW_EVIDENCE_MISSING",
                "non-deterministic support artifacts need explicit owner/manual review evidence: "
                + ", ".join(missing_reviews),
                INDEX_PATH,
            )
            return
        context.info(
            "SUPPORT_GENERATION_CURRENT",
            f"support-generation index covers {len(current['artifacts'])} artifacts",
            INDEX_PATH,
        )


SUPPORT_GENERATION_MODULE = SupportGenerationModule()
