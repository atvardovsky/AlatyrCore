"""Validate the required target support-surface state."""

from __future__ import annotations

from typing import Any

from support_state import (
    STATE_PATH,
    SupportStateError,
    build_support_state,
    state_differences,
    state_is_current,
    validate_policy,
)
from target_adapter_validation.capability import CapabilityValidationContext
from target_validation_support import is_placeholder


def validate_support_state(
    context: CapabilityValidationContext,
    manifest: Any,
) -> None:
    del manifest
    policy_relpath = ".ai/project/support-policy.json"
    policy = context.load_json_object(
        context.target_path(policy_relpath), "SUPPORT_POLICY"
    )
    state = context.load_json_object(
        context.target_path(STATE_PATH), "SUPPORT_STATE"
    )
    if policy is None or state is None:
        return
    try:
        validate_policy(policy)
    except SupportStateError as exc:
        context.error("SUPPORT_POLICY_INVALID", str(exc), policy_relpath)
        return
    if state.get("schema_version") != 1 or state.get("state_kind") != "target-support-state":
        context.error(
            "SUPPORT_STATE_CONTRACT",
            "support state must use target-support-state schema version 1",
            STATE_PATH,
        )
        return
    placeholder_state = any(
        is_placeholder(state.get(field))
        for field in ["policy_digest", "source_revision", "root_digest"]
    )
    if placeholder_state:
        report = context.warn if context.allow_placeholders else context.error
        report(
            "SUPPORT_STATE_UNRESOLVED",
            "support state must be generated from the installed target before acceptance",
            STATE_PATH,
        )
        return
    target = context.target_path(".ai").parent
    try:
        current = build_support_state(target, policy)
    except SupportStateError as exc:
        context.error("SUPPORT_STATE_BUILD", str(exc), policy_relpath)
        return
    if not state_is_current(state, current):
        differences = state_differences(state, current)
        details = ", ".join(
            f"{item.change}:{item.path}" for item in differences[:12]
        )
        report = context.warn if context.allow_placeholders else context.error
        report(
            "SUPPORT_STATE_STALE",
            "generated support state differs from current managed surfaces"
            + (f": {details}" if details else ""),
            STATE_PATH,
        )
        return
    context.info(
        "SUPPORT_STATE_CURRENT",
        f"support state covers {len(current['files'])} managed files across "
        f"{len(current['groups'])} groups",
        STATE_PATH,
    )


__all__ = ["validate_support_state"]
