"""Validate retained target-discovery evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema

from target_adapter_validation.capability import CapabilityValidationContext
from target_adapter_validation.source_contracts import load_source_json_object
from target_validation_support import is_placeholder, is_target_relative_path


REPORT_PATH = ".ai/assistant/discovery-report.json"
REPORT_SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "alatyr-target-discovery-report.schema.json"
)


def _has_placeholder(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_placeholder(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_placeholder(item) for item in value)
    return isinstance(value, str) and is_placeholder(value)


def _resolved_authority(value: str) -> bool:
    return value.casefold() not in {"unknown", "unresolved", "missing", "unavailable"}


def validate_target_discovery(
    context: CapabilityValidationContext,
    manifest: Any,
) -> None:
    report = context.load_json_object(
        context.target_path(REPORT_PATH), "TARGET_DISCOVERY_REPORT"
    )
    if report is None:
        return
    try:
        schema = load_source_json_object(REPORT_SCHEMA)
        errors = sorted(
            jsonschema.Draft7Validator(
                schema,
                format_checker=(
                    None
                    if context.allow_placeholders
                    else jsonschema.FormatChecker()
                ),
            ).iter_errors(report),
            key=lambda error: list(error.absolute_path),
        )
    except (OSError, ValueError, jsonschema.SchemaError) as exc:
        context.error(
            "TARGET_DISCOVERY_SOURCE_SCHEMA",
            f"cannot load target-discovery schema: {exc}",
            REPORT_PATH,
        )
        return
    for error in errors:
        location = ".".join(str(item) for item in error.absolute_path) or "root"
        context.error(
            "TARGET_DISCOVERY_SCHEMA",
            f"target discovery report {location}: {error.message}",
            REPORT_PATH,
        )
    if errors:
        return
    if manifest is not None:
        configured = manifest.scalars.get(("installation", "discovery_report"))
        if configured is None or configured.value != REPORT_PATH:
            context.error(
                "TARGET_DISCOVERY_MANIFEST_PATH",
                f"installation.discovery_report must reference {REPORT_PATH}",
                ".ai/alatyr.yaml",
            )
        profile = manifest.scalars.get(("installation", "support_profile"))
        report_profile = report["scope"]["support_profile"]
        if profile is not None and profile.value != report_profile:
            context.error(
                "TARGET_DISCOVERY_PROFILE_DRIFT",
                "discovery support profile differs from the installed support profile",
                REPORT_PATH,
            )
    if _has_placeholder(report):
        result = context.warn if context.allow_placeholders else context.error
        result(
            "TARGET_DISCOVERY_UNRESOLVED",
            "target discovery report still contains unresolved authoring placeholders",
            REPORT_PATH,
        )
        return
    findings = report["findings"]
    finding_ids: set[str] = set()
    material = 0
    unresolved_material = 0
    categories_with_findings: set[str] = set()
    for finding in findings:
        finding_id = finding["id"]
        if finding_id in finding_ids:
            context.error(
                "TARGET_DISCOVERY_FINDING_DUPLICATE",
                f"target discovery finding id is repeated: {finding_id}",
                REPORT_PATH,
            )
        finding_ids.add(finding_id)
        categories_with_findings.add(finding["category"])
        if finding["material"]:
            material += 1
            if finding["disposition"] == "unresolved":
                unresolved_material += 1
                context.error(
                    "TARGET_DISCOVERY_MATERIAL_UNRESOLVED",
                    f"material discovery finding remains unresolved: {finding_id}",
                    REPORT_PATH,
                )
        if finding["evidence_state"] == "accepted" and finding[
            "decision_authority"
        ].casefold() in {"unknown", "unresolved", "missing", "unavailable"}:
            context.error(
                "TARGET_DISCOVERY_AUTHORITY_MISSING",
                f"accepted discovery finding has no decision authority: {finding_id}",
                REPORT_PATH,
            )
        if (
            finding["material"]
            and finding["disposition"]
            in {"projected", "rejected", "deferred", "not-applicable"}
            and not _resolved_authority(finding["decision_authority"])
        ):
            context.error(
                "TARGET_DISCOVERY_DISPOSITION_AUTHORITY_MISSING",
                f"material discovery disposition has no decision authority: {finding_id}",
                REPORT_PATH,
            )
        source_count = finding["source_count"]
        listed_sources = len(finding["sources"])
        truncated = finding["sources_truncated"]
        if source_count < listed_sources or (
            truncated and source_count <= listed_sources
        ) or (not truncated and source_count != listed_sources):
            context.error(
                "TARGET_DISCOVERY_SOURCE_COUNT_DRIFT",
                f"discovery source count and truncation state disagree: {finding_id}",
                REPORT_PATH,
            )
        for source in finding["sources"]:
            if not is_target_relative_path(source["path"]):
                context.error(
                    "TARGET_DISCOVERY_SOURCE_PATH",
                    f"discovery source must be target-relative: {source['path']}",
                    REPORT_PATH,
                )
        for projection in finding["projections"]:
            if not is_target_relative_path(projection):
                context.error(
                    "TARGET_DISCOVERY_PROJECTION_PATH",
                    f"discovery projection must be target-relative: {projection}",
                    REPORT_PATH,
                )
    selected_categories = set(report["scope"]["categories"])
    missing_categories = sorted(selected_categories - categories_with_findings)
    if missing_categories:
        context.error(
            "TARGET_DISCOVERY_CATEGORY_UNCLASSIFIED",
            "selected discovery categories have no findings: "
            + ", ".join(missing_categories),
            REPORT_PATH,
        )
    expected_summary = {
        "selected_categories": len(selected_categories),
        "classified_findings": len(findings),
        "material_findings": material,
        "unresolved_material_findings": unresolved_material,
    }
    for field, expected in expected_summary.items():
        if report["summary"].get(field) != expected:
            context.error(
                "TARGET_DISCOVERY_SUMMARY_DRIFT",
                f"summary.{field} must equal {expected}",
                REPORT_PATH,
            )
