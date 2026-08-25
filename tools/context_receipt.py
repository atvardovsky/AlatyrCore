"""Validate normalized planned, resolved, and observed context evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any


MEASUREMENT_STATES = {"planned", "resolved", "observed"}
OBSERVED_LEVELS = {"exact", "partial", "unavailable"}
OBSERVED_SOURCES = {
    "host-telemetry",
    "provider-usage",
    "assistant-reported",
    "manual",
    "unavailable",
}
EXACT_SOURCES = {"host-telemetry", "provider-usage"}


def _count_or_unknown(value: Any) -> bool:
    return value == "unknown" or (
        isinstance(value, int) and not isinstance(value, bool) and value >= 0
    )


def _safe_paths(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    for item in value:
        if not isinstance(item, str) or not item:
            return False
        path = Path(item)
        if path.is_absolute() or ".." in path.parts:
            return False
    return True


def validate_context_receipt(receipt: Any, label: str = "context_receipt") -> list[str]:
    failures: list[str] = []
    if not isinstance(receipt, dict):
        return [f"{label} must be an object"]
    if receipt.get("schema_version") != 1:
        failures.append(f"{label}.schema_version must be 1")
    if receipt.get("receipt_kind") != "alatyr-context-receipt":
        failures.append(f"{label}.receipt_kind is invalid")
    state = receipt.get("measurement_state")
    if state not in MEASUREMENT_STATES:
        failures.append(f"{label}.measurement_state is invalid")

    planned = receipt.get("planned")
    if not isinstance(planned, dict):
        failures.append(f"{label}.planned must be an object")
    else:
        if not _safe_paths(planned.get("paths")):
            failures.append(f"{label}.planned.paths must contain safe relative paths")
        if not _count_or_unknown(planned.get("approximate_words")):
            failures.append(f"{label}.planned.approximate_words is invalid")

    resolved = receipt.get("resolved")
    if not isinstance(resolved, dict):
        failures.append(f"{label}.resolved must be an object")
    else:
        if resolved.get("status") not in {"recorded", "unavailable"}:
            failures.append(f"{label}.resolved.status is invalid")
        if not _safe_paths(resolved.get("paths")):
            failures.append(f"{label}.resolved.paths must contain safe relative paths")
        if not _count_or_unknown(resolved.get("approximate_words")):
            failures.append(f"{label}.resolved.approximate_words is invalid")
        if state in {"resolved", "observed"} and resolved.get("status") != "recorded":
            failures.append(f"{label}.resolved must be recorded for {state} state")

    observed = receipt.get("observed")
    if not isinstance(observed, dict):
        failures.append(f"{label}.observed must be an object")
    else:
        level = observed.get("evidence_level")
        source = observed.get("source")
        if level not in OBSERVED_LEVELS:
            failures.append(f"{label}.observed.evidence_level is invalid")
        if source not in OBSERVED_SOURCES:
            failures.append(f"{label}.observed.source is invalid")
        for field in ["files_loaded", "input_tokens", "output_tokens"]:
            if not _count_or_unknown(observed.get(field)):
                failures.append(f"{label}.observed.{field} is invalid")
        evidence = observed.get("evidence")
        if not isinstance(evidence, str) or not evidence:
            failures.append(f"{label}.observed.evidence must be recorded")
        if state != "observed" and level != "unavailable":
            failures.append(f"{label}.observed evidence requires observed state")
        if level == "unavailable" and source != "unavailable":
            failures.append(f"{label}.observed unavailable evidence needs unavailable source")
        if level == "exact":
            if state != "observed" or source not in EXACT_SOURCES:
                failures.append(f"{label}.observed exact evidence needs host or provider telemetry")
            for field in ["input_tokens", "output_tokens"]:
                if not isinstance(observed.get(field), int):
                    failures.append(f"{label}.observed exact evidence needs numeric {field}")
    return failures


def supports_observed_context_claim(receipt: Any) -> bool:
    if validate_context_receipt(receipt):
        return False
    observed = receipt["observed"]
    return (
        receipt["measurement_state"] == "observed"
        and observed["evidence_level"] == "exact"
        and observed["source"] in EXACT_SOURCES
        and isinstance(observed["files_loaded"], int)
        and isinstance(observed["input_tokens"], int)
        and isinstance(observed["output_tokens"], int)
    )
