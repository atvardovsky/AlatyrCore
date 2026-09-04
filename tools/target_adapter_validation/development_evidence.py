"""Validate target-owned development evidence support."""

from __future__ import annotations

from target_validation_support import ManifestData, is_unresolved_value

from target_adapter_validation.capability import (
    CapabilityValidationContext,
    FunctionCapabilityModule,
)


def validate_development_evidence(
    context: CapabilityValidationContext,
    manifest: ManifestData | None,
) -> None:
    key = ("source_of_truth", "development_evidence")
    scalar = manifest.scalars.get(key) if manifest else None
    relpath = scalar.value if scalar else ".ai/project/development-evidence.json"
    path = context.target_path(relpath)
    if not path.is_file():
        context.warn(
            "DEVELOPMENT_EVIDENCE_MISSING",
            "target has no compact development evidence index; recurring request "
            "and process-pattern recommendations remain conversation-local",
            relpath,
        )
        return

    data = context.load_json_object(path, "DEVELOPMENT_EVIDENCE")
    if data is None:
        return
    if data.get("schema_version") != 1:
        context.error(
            "DEVELOPMENT_EVIDENCE_SCHEMA",
            "schema_version should be 1",
            relpath,
        )
    if data.get("register_kind") != "target-development-evidence":
        context.error(
            "DEVELOPMENT_EVIDENCE_KIND",
            "register_kind should be target-development-evidence",
            relpath,
        )

    for field in ["project", "owner", "retention_policy", "last_reviewed"]:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            context.error(
                "DEVELOPMENT_EVIDENCE_METADATA",
                f"{field} must be a non-empty string",
                relpath,
            )
        elif is_unresolved_value(value):
            report = context.warn if context.allow_placeholders else context.error
            report(
                "DEVELOPMENT_EVIDENCE_METADATA_UNRESOLVED",
                f"{field} is unresolved",
                relpath,
            )

    content_policy = data.get("content_policy")
    if not isinstance(content_policy, str) or not all(
        term in content_policy.lower()
        for term in ["raw chat", "secrets", "credentials", "personal data"]
    ):
        context.error(
            "DEVELOPMENT_EVIDENCE_CONTENT_POLICY",
            "content_policy must exclude raw chat, secrets, credentials, and personal data",
            relpath,
        )

    patterns = data.get("patterns")
    if not isinstance(patterns, list):
        context.error(
            "DEVELOPMENT_EVIDENCE_PATTERNS",
            "patterns must be a list",
            relpath,
        )
        return

    required_strings = [
        "id",
        "category",
        "project_area",
        "source_owner",
        "normalized_problem",
        "first_observed",
        "last_observed",
        "evidence_quality",
        "status",
    ]
    list_fields = ["evidence_refs", "outcome_signals", "existing_ai_item_ids"]
    evidence_qualities = {
        "measured",
        "observed",
        "anecdotal",
        "conflicting",
        "unresolved",
    }
    statuses = {"active", "resolved", "deferred", "unresolved"}
    pattern_ids: set[str] = set()
    for index, pattern in enumerate(patterns):
        label = f"patterns[{index}]"
        if not isinstance(pattern, dict):
            context.error(
                "DEVELOPMENT_EVIDENCE_PATTERN_SHAPE",
                f"{label} must be an object",
                relpath,
            )
            continue
        for field in required_strings:
            value = pattern.get(field)
            if not isinstance(value, str) or not value.strip():
                context.error(
                    "DEVELOPMENT_EVIDENCE_PATTERN_FIELD",
                    f"{label}.{field} must be a non-empty string",
                    relpath,
                )
        pattern_id = pattern.get("id")
        if isinstance(pattern_id, str) and pattern_id:
            if pattern_id in pattern_ids:
                context.error(
                    "DEVELOPMENT_EVIDENCE_PATTERN_DUPLICATE",
                    f"duplicate pattern id {pattern_id}",
                    relpath,
                )
            pattern_ids.add(pattern_id)
        occurrence_count = pattern.get("occurrence_count")
        if not isinstance(occurrence_count, int) or occurrence_count < 1:
            context.error(
                "DEVELOPMENT_EVIDENCE_OCCURRENCE_COUNT",
                f"{label}.occurrence_count must be a positive integer",
                relpath,
            )
        for field in list_fields:
            values = pattern.get(field)
            if not isinstance(values, list) or not all(
                isinstance(value, str) and value for value in values
            ):
                context.error(
                    "DEVELOPMENT_EVIDENCE_PATTERN_LIST",
                    f"{label}.{field} must be a string list",
                    relpath,
                )
        if not pattern.get("evidence_refs"):
            context.error(
                "DEVELOPMENT_EVIDENCE_REFERENCE_MISSING",
                f"{label}.evidence_refs must identify at least one occurrence",
                relpath,
            )
        if pattern.get("evidence_quality") not in evidence_qualities:
            context.error(
                "DEVELOPMENT_EVIDENCE_QUALITY",
                f"{label}.evidence_quality is invalid",
                relpath,
            )
        if pattern.get("status") not in statuses:
            context.error(
                "DEVELOPMENT_EVIDENCE_STATUS",
                f"{label}.status is invalid",
                relpath,
            )


DEVELOPMENT_EVIDENCE_MODULE = FunctionCapabilityModule(
    check_id="check_development_evidence",
    validator=validate_development_evidence,
)
