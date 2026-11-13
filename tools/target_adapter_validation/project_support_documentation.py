"""Validate baseline project orientation and source-of-truth authority state."""

from __future__ import annotations

import datetime as dt
from typing import Any

from target_adapter_validation.capability import CapabilityValidationContext
from target_validation_support import is_placeholder, is_unresolved_value
from registry_facts import parse_registry_fact_entries


REGISTRY_PATH = ".ai/project/source-of-truth-registry.md"
CONTOUR_PATH = ".ai/project/contour.md"
APPLICABILITY_STATES = {"applicable", "not-applicable", "unknown"}
AUTHORITY_STATES = {
    "observed",
    "proposed",
    "accepted",
    "contradicted",
    "missing",
    "not-applicable",
}
GAP_SEVERITIES = {"none", "non-blocking", "blocking"}
REQUIRED_FIELDS = (
    "Fact type",
    "Applicability state",
    "Authority state",
    "Decision source",
    "Evidence revision",
    "Last reviewed",
    "Gap severity",
)
ROUTING_FIELDS = (
    "Consistency level",
    "Project area",
    "Consistency map node",
    "Relationship coverage",
)


def _resolved(value: str | None) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and not is_placeholder(value)
        and not is_unresolved_value(value)
    )


def _valid_date(value: str | None) -> bool:
    if not _resolved(value):
        return False
    try:
        dt.date.fromisoformat(value or "")
    except ValueError:
        return False
    return True


def validate_project_support_documentation(
    context: CapabilityValidationContext,
    manifest: Any,
) -> None:
    del manifest
    contour = context.read_text(context.target_path(CONTOUR_PATH))
    for heading in [
        "## Project Orientation",
        "Purpose:",
        "Primary users or stakeholders:",
        "Main architectural areas and owners:",
        "Primary runtime or business workflows:",
        "Validation entry points:",
        "Known contradictions, missing facts, or accepted limitations:",
        "## Maintenance",
        "Project Contour Sync Decision",
    ]:
        if heading not in contour:
            context.error(
                "PROJECT_ORIENTATION_INCOMPLETE",
                f"project contour is missing {heading}",
                CONTOUR_PATH,
            )
    registry = context.read_text(context.target_path(REGISTRY_PATH))
    entries = parse_registry_fact_entries(registry)
    if not entries:
        context.error(
            "SOURCE_REGISTRY_EMPTY",
            "source-of-truth registry contains no Fact Type entries",
            REGISTRY_PATH,
        )
        return
    seen_fact_types: set[str] = set()
    for entry in entries:
        fact_type = entry.heading_fact_type
        path = f"{REGISTRY_PATH}:{entry.line}"
        if fact_type in seen_fact_types:
            context.error(
                "SOURCE_REGISTRY_FACT_TYPE_DUPLICATE",
                f"Fact Type {fact_type!r} is declared more than once",
                path,
            )
        seen_fact_types.add(fact_type)
        fields = entry.fields
        owner_values = entry.canonical_owner_values
        for name in entry.conflicts:
            context.error("SOURCE_REGISTRY_DECLARATION_CONFLICT",
                          f"Fact Type {fact_type!r} repeats or contradicts {name}", path)
        missing = [
            field
            for field in (*REQUIRED_FIELDS, *ROUTING_FIELDS)
            if fields[field] is None
        ]
        if not owner_values:
            missing.append("owner")
        if missing:
            context.error(
                "SOURCE_REGISTRY_EVIDENCE_FIELDS",
                f"Fact Type {fact_type!r} is missing fields: {', '.join(missing)}",
                path,
            )
            continue
        if fields["Fact type"] != fact_type:
            context.error(
                "SOURCE_REGISTRY_FACT_TYPE_DRIFT",
                "Fact type field must match its heading exactly",
                path,
            )
        applicability = fields["Applicability state"]
        authority = fields["Authority state"]
        gap = fields["Gap severity"]
        if _resolved(applicability) and applicability not in APPLICABILITY_STATES:
            context.error(
                "SOURCE_REGISTRY_APPLICABILITY",
                f"Fact Type {fact_type!r} has invalid applicability state {applicability!r}",
                path,
            )
        if _resolved(authority) and authority not in AUTHORITY_STATES:
            context.error(
                "SOURCE_REGISTRY_AUTHORITY",
                f"Fact Type {fact_type!r} has invalid authority state {authority!r}",
                path,
            )
        if _resolved(gap) and gap not in GAP_SEVERITIES:
            context.error(
                "SOURCE_REGISTRY_GAP_SEVERITY",
                f"Fact Type {fact_type!r} has invalid gap severity {gap!r}",
                path,
            )
        if context.allow_placeholders and any(
            value is not None and is_placeholder(value) for value in fields.values()
        ):
            continue
        if applicability == "unknown":
            context.error(
                "SOURCE_REGISTRY_APPLICABILITY_UNRESOLVED",
                f"Fact Type {fact_type!r} remains of unknown applicability",
                path,
            )
        elif applicability in {"applicable", "not-applicable"}:
            for field in ["Decision source", "Evidence revision"]:
                if not _resolved(fields[field]):
                    context.error(
                        "SOURCE_REGISTRY_EVIDENCE_UNRESOLVED",
                        f"{applicability} Fact Type {fact_type!r} has unresolved {field}",
                        path,
                    )
            if not _valid_date(fields["Last reviewed"]):
                context.error(
                    "SOURCE_REGISTRY_REVIEW_DATE",
                    f"{applicability} Fact Type {fact_type!r} needs an ISO review date",
                    path,
                )

        if applicability == "applicable":
            if authority != "accepted":
                context.error(
                    "SOURCE_REGISTRY_AUTHORITY_UNACCEPTED",
                    f"applicable Fact Type {fact_type!r} requires accepted authority, not {authority!r}",
                    path,
                )
            if not any(_resolved(value) for value in owner_values):
                context.error(
                    "SOURCE_REGISTRY_EVIDENCE_UNRESOLVED",
                    f"applicable Fact Type {fact_type!r} has no resolved owner",
                    path,
                )
            if gap == "blocking":
                context.error(
                    "SOURCE_REGISTRY_BLOCKING_GAP",
                    f"applicable Fact Type {fact_type!r} retains a blocking gap",
                    path,
                )
        elif applicability == "not-applicable" and authority != "not-applicable":
            context.error(
                "SOURCE_REGISTRY_NOT_APPLICABLE_AUTHORITY",
                f"non-applicable Fact Type {fact_type!r} must record not-applicable authority",
                path,
            )
