"""Validate normalized context and semantic-guidance evidence."""

from __future__ import annotations

import hashlib
import json
import re
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
SEMANTIC_EXACT_SOURCES = {"host-telemetry"}
SEMANTIC_GUIDANCE_SCHEMA_VERSION = 1
BUNDLE_DIGEST_SCHEMA_VERSION = 1
BUNDLE_DIGEST_ALGORITHM = "sha256"
SEMANTIC_IDENTITY_FIELDS = {
    "guidance_id",
    "canonical_owner",
    "owner_digest",
    "authority",
    "freshness",
    "applicability",
}
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


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


def semantic_guidance_bundle_digest(
    identities: list[dict[str, str]],
) -> dict[str, Any]:
    """Return the digest for an ordered semantic-guidance identity bundle."""
    payload = json.dumps(
        identities,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "schema_version": BUNDLE_DIGEST_SCHEMA_VERSION,
        "algorithm": BUNDLE_DIGEST_ALGORITHM,
        "value": hashlib.sha256(payload).hexdigest(),
    }


def _validate_semantic_identities(
    value: Any,
    label: str,
    failures: list[str],
    *,
    require_owner_digest: bool,
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        failures.append(f"{label} must be a list")
        return []

    identities: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            failures.append(f"{item_label} must be an object")
            continue
        if set(item) != SEMANTIC_IDENTITY_FIELDS:
            failures.append(
                f"{item_label} must contain exactly {sorted(SEMANTIC_IDENTITY_FIELDS)}"
            )
            continue
        if any(not isinstance(item[field], str) or not item[field] for field in item):
            failures.append(f"{item_label} fields must be non-empty strings")
            continue
        guidance_id = item["guidance_id"]
        if guidance_id in seen_ids:
            failures.append(f"{label} contains duplicate guidance_id {guidance_id}")
        seen_ids.add(guidance_id)
        if not _safe_paths([item["canonical_owner"]]):
            failures.append(f"{item_label}.canonical_owner must be a safe relative path")
        owner_digest = item["owner_digest"]
        if owner_digest != "unknown" and not SHA256_PATTERN.fullmatch(owner_digest):
            failures.append(f"{item_label}.owner_digest must be sha256:<64 lowercase hex>")
        if require_owner_digest and owner_digest == "unknown":
            failures.append(f"{item_label}.owner_digest must be resolved")
        identities.append(item)
    return identities


def _validate_bundle_digest(
    value: Any,
    identities: list[dict[str, str]],
    label: str,
    failures: list[str],
    *,
    allow_unavailable: bool,
) -> None:
    if not isinstance(value, dict):
        failures.append(f"{label} must be an object")
        return
    if set(value) != {"schema_version", "algorithm", "value"}:
        failures.append(
            f"{label} must contain exactly algorithm, schema_version, and value"
        )
        return
    if value.get("schema_version") != BUNDLE_DIGEST_SCHEMA_VERSION:
        failures.append(
            f"{label}.schema_version must be {BUNDLE_DIGEST_SCHEMA_VERSION}"
        )
    if value.get("algorithm") != BUNDLE_DIGEST_ALGORITHM:
        failures.append(f"{label}.algorithm must be {BUNDLE_DIGEST_ALGORITHM}")
    digest_value = value.get("value")
    if allow_unavailable:
        if digest_value != "unavailable":
            failures.append(f"{label}.value must be unavailable")
        return
    if digest_value == "unavailable":
        failures.append(f"{label}.value must be recorded")
        return
    if not isinstance(digest_value, str) or not re.fullmatch(r"[0-9a-f]{64}", digest_value):
        failures.append(f"{label}.value must be 64 lowercase hex or unavailable")
        return
    expected = semantic_guidance_bundle_digest(identities)["value"]
    if digest_value != expected:
        failures.append(f"{label}.value does not match the ordered identities")


def _validate_semantic_guidance(
    value: Any,
    measurement_state: Any,
    label: str,
    failures: list[str],
) -> None:
    if not isinstance(value, dict):
        failures.append(f"{label} must be an object")
        return
    if set(value) != {"schema_version", "planned", "resolved", "observed"}:
        failures.append(
            f"{label} must contain exactly schema_version, planned, resolved, and observed"
        )
        return
    if value.get("schema_version") != SEMANTIC_GUIDANCE_SCHEMA_VERSION:
        failures.append(
            f"{label}.schema_version must be {SEMANTIC_GUIDANCE_SCHEMA_VERSION}"
        )

    for stage_name in ["planned", "resolved"]:
        stage = value.get(stage_name)
        stage_label = f"{label}.{stage_name}"
        if not isinstance(stage, dict):
            failures.append(f"{stage_label} must be an object")
            continue
        if set(stage) != {"status", "identities", "bundle_digest"}:
            failures.append(
                f"{stage_label} must contain exactly status, identities, and bundle_digest"
            )
            continue
        status = stage.get("status")
        if status not in {"recorded", "unavailable"}:
            failures.append(f"{stage_label}.status is invalid")
        identities = _validate_semantic_identities(
            stage.get("identities"),
            f"{stage_label}.identities",
            failures,
            require_owner_digest=stage_name == "resolved" and status == "recorded",
        )
        unavailable = status == "unavailable"
        if unavailable and identities:
            failures.append(f"{stage_label}.identities must be empty when unavailable")
        _validate_bundle_digest(
            stage.get("bundle_digest"),
            identities,
            f"{stage_label}.bundle_digest",
            failures,
            allow_unavailable=unavailable,
        )
        if stage_name == "planned" and status != "recorded":
            failures.append(f"{stage_label} must be recorded")
        if (
            stage_name == "resolved"
            and measurement_state in {"resolved", "observed"}
            and status != "recorded"
        ):
            failures.append(f"{stage_label} must be recorded for {measurement_state} state")

    observed = value.get("observed")
    observed_label = f"{label}.observed"
    if not isinstance(observed, dict):
        failures.append(f"{observed_label} must be an object")
        return
    expected_observed_fields = {
        "evidence_level",
        "source",
        "identities",
        "bundle_digest",
        "evidence",
    }
    if set(observed) != expected_observed_fields:
        failures.append(
            f"{observed_label} must contain exactly {sorted(expected_observed_fields)}"
        )
        return
    level = observed.get("evidence_level")
    source = observed.get("source")
    if level not in OBSERVED_LEVELS:
        failures.append(f"{observed_label}.evidence_level is invalid")
    if source not in OBSERVED_SOURCES:
        failures.append(f"{observed_label}.source is invalid")
    evidence = observed.get("evidence")
    if not isinstance(evidence, str) or not evidence:
        failures.append(f"{observed_label}.evidence must be recorded")
    identities = _validate_semantic_identities(
        observed.get("identities"),
        f"{observed_label}.identities",
        failures,
        require_owner_digest=level in {"exact", "partial"},
    )
    unavailable = level == "unavailable"
    if unavailable:
        if source != "unavailable":
            failures.append(f"{observed_label} unavailable evidence needs unavailable source")
        if identities:
            failures.append(f"{observed_label}.identities must be empty when unavailable")
    elif measurement_state != "observed":
        failures.append(f"{observed_label} evidence requires observed state")
    if level == "exact" and source not in SEMANTIC_EXACT_SOURCES:
        failures.append(
            f"{observed_label} exact identity evidence needs host delivery telemetry"
        )
    _validate_bundle_digest(
        observed.get("bundle_digest"),
        identities,
        f"{observed_label}.bundle_digest",
        failures,
        allow_unavailable=unavailable,
    )


def validate_context_receipt(
    receipt: Any,
    label: str = "context_receipt",
    *,
    require_semantic_guidance: bool = False,
) -> list[str]:
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

    semantic_guidance = receipt.get("semantic_guidance")
    if semantic_guidance is None:
        if require_semantic_guidance:
            failures.append(f"{label}.semantic_guidance must be recorded")
    else:
        _validate_semantic_guidance(
            semantic_guidance,
            state,
            f"{label}.semantic_guidance",
            failures,
        )
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
