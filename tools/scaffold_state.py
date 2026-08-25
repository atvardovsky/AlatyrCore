"""Conservative installation-state transitions for scaffold projections."""

from __future__ import annotations

from typing import Any


INITIAL_INSTALLATION_STATE = "scaffolded"
INSTALLATION_STATES = frozenset({"scaffolded", "staged", "accepted", "degraded"})
TRANSITION_REASONS = {
    (None, "scaffolded"): "initial-scaffold",
    (None, "staged"): "legacy-migration-baseline",
    ("scaffolded", "staged"): "adaptation-started",
    ("staged", "accepted"): "strict-acceptance",
    ("accepted", "staged"): "controlled-update",
    ("accepted", "degraded"): "blocking-drift",
    ("degraded", "staged"): "repair-started",
}


def installation_transition_allowed(
    current: str,
    next_state: str,
    *,
    strict_acceptance: bool = False,
    controlled_update: bool = False,
    blocking_drift: bool = False,
) -> bool:
    """Return whether current evidence permits an installation-state change."""

    if current not in INSTALLATION_STATES or next_state not in INSTALLATION_STATES:
        return False
    if current == next_state:
        return True
    if current == "scaffolded":
        return next_state == "staged"
    if current == "staged":
        return next_state == "accepted" and strict_acceptance
    if current == "accepted":
        return (next_state == "staged" and controlled_update) or (
            next_state == "degraded" and blocking_drift
        )
    if current == "degraded":
        return next_state == "staged"
    return False


def validate_installation_state_record(
    record: Any,
    *,
    manifest_state: str | None = None,
) -> list[str]:
    """Validate ordered transition evidence against the lifecycle state graph."""

    failures: list[str] = []
    if not isinstance(record, dict):
        return ["installation-state record must be an object"]
    if record.get("schema_version") != 1:
        failures.append("installation-state schema_version must be 1")
    if record.get("record_kind") != "alatyr-installation-state":
        failures.append("installation-state record_kind is invalid")
    current_state = record.get("current_state")
    if current_state not in INSTALLATION_STATES:
        failures.append("installation-state current_state is invalid")
    if manifest_state is not None and current_state != manifest_state:
        failures.append("installation-state current_state differs from manifest state")

    transitions = record.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        failures.append("installation-state transitions must be a non-empty list")
        return failures

    previous_next: str | None = None
    for index, transition in enumerate(transitions, start=1):
        label = f"installation-state transition {index}"
        if not isinstance(transition, dict):
            failures.append(f"{label} must be an object")
            continue
        if transition.get("sequence") != index:
            failures.append(f"{label} sequence must be {index}")
        previous = transition.get("previous_state")
        next_state = transition.get("next_state")
        if index == 1:
            if previous is not None:
                failures.append(f"{label} must start with previous_state null")
        elif previous != previous_next:
            failures.append(f"{label} previous_state breaks transition continuity")

        expected_reason = TRANSITION_REASONS.get((previous, next_state))
        if expected_reason is None:
            failures.append(f"{label} transition {previous!r} -> {next_state!r} is invalid")
        elif transition.get("reason") != expected_reason:
            failures.append(f"{label} reason must be {expected_reason}")

        for field in [
            "operation_id",
            "repository_revision",
            "current_user_authorization",
            "recorded_at",
        ]:
            if not isinstance(transition.get(field), str) or not transition[field]:
                failures.append(f"{label} {field} must be non-empty")
        approval = transition.get("approval_evidence")
        if approval is not None and (not isinstance(approval, str) or not approval):
            failures.append(f"{label} approval_evidence must be non-empty or null")
        validation = transition.get("validation")
        if not isinstance(validation, dict):
            failures.append(f"{label} validation must be an object")
        else:
            status = validation.get("status")
            if status not in {"not-run", "passed", "failed", "unavailable"}:
                failures.append(f"{label} validation status is invalid")
            if not isinstance(validation.get("evidence"), str) or not validation["evidence"]:
                failures.append(f"{label} validation evidence must be non-empty")
            if next_state == "accepted" and status != "passed":
                failures.append(f"{label} acceptance requires passed strict validation")

        previous_next = next_state if next_state in INSTALLATION_STATES else None

    if previous_next != current_state:
        failures.append("installation-state final transition differs from current_state")
    return failures
