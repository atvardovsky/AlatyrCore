"""Optional request-bound work selection; not intent inference or authorization."""

from __future__ import annotations

from request_values import strings
from task_readiness import execution_readiness


def parse_focus_control(value: object) -> None:
    if value is not None and (not isinstance(value, str) or value != "dependency-readiness"):
        raise ValueError("focus_control must be null or dependency-readiness")


def parse_focus_action(action: dict) -> None:
    if "brief_sha256" in action:
        value = action["brief_sha256"]
        if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("action.brief_sha256 requires a lowercase SHA-256 digest")
    if "obligation_ids" in action:
        strings(action["obligation_ids"], "action.obligation_ids", minimum=1)


def focus_failures(brief: dict, action: dict, model: dict, brief_sha256: str) -> list[str]:
    """Parsed inputs only; reuse declared readiness and walk prerequisite edges."""
    adopted = brief.get("focus_control") == "dependency-readiness"
    failures = []
    if adopted and "brief_sha256" not in action:
        failures.append("adopted focus_control requires action.brief_sha256 from the original dispatch/review")
    if "brief_sha256" in action and action["brief_sha256"] != brief_sha256:
        failures.append("action brief digest is stale; reconcile the newest request without retagging old work")
    if not adopted:
        if "obligation_ids" in action:
            failures.append("obligation selection requires an adopted focus_control")
        return failures
    readiness = execution_readiness(model)
    if readiness["state"] != "declared-readiness":
        return failures + ["focus_control requires valid explicit execution_dependencies: "
                           + "; ".join(readiness["failures"])]
    if action["kind"] == "work" and "obligation_ids" not in action:
        failures.append("adopted focus_control requires work action.obligation_ids")
    selected = set(action.get("obligation_ids", []))
    outcomes = {row["id"]: row for row in brief["outcomes"]}
    allowed = {key for identity in action["outcome_ids"] if identity in outcomes
               for key in outcomes[identity]["proof_obligation_ids"]}
    dependencies = {row["obligation_id"]: row["requires"] for row in model["execution_dependencies"]}
    pending = list(allowed)
    while pending:
        for key in dependencies.get(pending.pop(), []):
            if key not in allowed:
                allowed.add(key)
                pending.append(key)
    if not selected <= allowed:
        failures.append("action obligations are outside the selected outcomes and their prerequisite closure")
    if action["kind"] == "work" and action["phase"] in {"modify", "live-external"}:
        if not selected <= set(readiness["ready"]):
            failures.append("modifying/live work requires ready obligations; inspect blocked or waiting work before mutation")
    return failures
