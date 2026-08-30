"""Shared assistant-capability contract constants and helpers."""

from __future__ import annotations

from typing import Any

from target_validation_support import is_placeholder, is_unresolved_value


CAPABILITY_INDEX_SCHEMA_VERSION = 3
SURFACE_CAPABILITY_SCHEMA_VERSION = 3

CAPABILITY_INDEX_KIND = "target-assistant-capability-index"
SURFACE_CAPABILITY_KIND = "target-assistant-surface-capabilities"

STATE_EVIDENCE_TEXT = (
    "supported|limited|unsupported|unknown plus selected and freshness evidence"
)
INDEX_STATE_EVIDENCE_STRING_FIELDS = {
    "state_model",
    "selected_surface",
    "selected_surface_evidence",
}
INDEX_STATE_EVIDENCE_TRUE_FIELDS = {
    "capability_records_are_authoritative",
    "unknown_means_not_verified",
    "stale_or_expired_evidence_requires_recheck",
}

SURFACE_STATE_FIELDS = {
    "overall",
    "selected_for_target",
    "evidence_state",
    "advertised_by_surface",
    "verified_for_target",
    "limitations",
    "review_triggers",
}
SURFACE_STATE_SCALAR_FIELDS = {
    "overall",
    "selected_for_target",
    "evidence_state",
    "advertised_by_surface",
    "verified_for_target",
}
OVERALL_STATES = {"supported", "limited", "unsupported", "unknown"}
YES_NO_UNKNOWN = {"yes", "no", "unknown"}
EVIDENCE_STATES = {"current", "stale", "expired", "unverified", "unknown"}


def is_concrete_capability_value(value: Any) -> bool:
    """Whether a capability value is a resolved target claim."""

    return (
        isinstance(value, str)
        and bool(value.strip())
        and not is_placeholder(value)
        and not is_unresolved_value(value)
        and "_OR_" not in value
    )


def capability_record_path(surface_id: str) -> str:
    return f".ai/assistant/assistant-capabilities/{surface_id}.json"


def expected_index_state_evidence(
    *,
    selected_surface: str = "{TARGET_SELECTED_ASSISTANT_SURFACE_OR_GENERIC}",
    selected_surface_evidence: str = "{TARGET_SELECTED_SURFACE_EVIDENCE_OR_UNKNOWN}",
) -> dict[str, Any]:
    return {
        "state_model": STATE_EVIDENCE_TEXT,
        "selected_surface": selected_surface,
        "selected_surface_evidence": selected_surface_evidence,
        "capability_records_are_authoritative": True,
        "unknown_means_not_verified": True,
        "stale_or_expired_evidence_requires_recheck": True,
    }
