"""Optional request-bound work selection; not intent inference or authorization."""

from __future__ import annotations

from pathlib import PurePath

from request_values import strings
from task_readiness import execution_readiness


def prerequisite_closure(model: dict, identities: set[str]) -> set[str]:
    dependencies = {row["obligation_id"]: row["requires"] for row in model.get("execution_dependencies", [])}
    closure = set(identities)
    pending = list(closure)
    while pending:
        for key in dependencies.get(pending.pop(), []):
            if key not in closure:
                closure.add(key)
                pending.append(key)
    return closure


def request_progress(brief: dict, model: dict, health: dict) -> dict:
    """Cover the whole captured request, never just the action's selected slice."""
    proofs = {row["id"]: row for row in model["proof_obligations"]}
    readiness = execution_readiness(model)
    ready_ids = set(readiness["ready"])
    affected = set(health.get("affected_obligation_ids", []))
    rows = []
    for outcome in brief["outcomes"]:
        roots = set(outcome["proof_obligation_ids"])
        closure = prerequisite_closure(model, roots)
        stale = health.get("global_review_required", False) or bool(closure & affected)
        unresolved = sorted(key for key in roots if key not in proofs or proofs[key]["status"] != "passed")
        ready = closure & ready_ids
        if health.get("global_review_required", False):
            ready = set()
        elif affected:
            ready = {key for key in ready if not prerequisite_closure(model, {key}) & affected}
        rows.append({"id": outcome["id"], "state": "evidence-review-required" if stale else
                     "unverified" if unresolved else "declared-proofs-passed-not-acceptance",
                     "unresolved_proof_ids": unresolved,
                     "ready_obligation_ids": sorted(ready)})
    remaining = [row["id"] for row in rows if row["state"] != "declared-proofs-passed-not-acceptance"]
    return {"state": "partial" if remaining else "declared-proofs-passed-not-acceptance",
            "outcomes": rows, "remaining_outcome_ids": remaining,
            "ready_outcome_ids": [row["id"] for row in rows if row["ready_obligation_ids"]],
            "capture_scope": "declared-request-only", "source_coverage": "primary-review-required",
            "completion_established": False, "authorization_granted": False, "acceptance_granted": False}


def evidence_action_review(brief: dict, action: dict, model: dict, health: dict) -> tuple[dict, list[str]]:
    selected = {row["id"]: row for row in brief["outcomes"]}
    roots = {key for identity in action["outcome_ids"] if identity in selected
             for key in selected[identity]["proof_obligation_ids"]}
    if brief.get("focus_control") == "dependency-readiness" and "obligation_ids" in action:
        roots = set(action["obligation_ids"])
    relevant = health.get("global_review_required", False) or bool(
        prerequisite_closure(model, roots) & set(health.get("affected_obligation_ids", [])))
    relevant = relevant or any(issue.get("identity", issue["path"]) is not None and any(
        PurePath(issue.get("identity", issue["path"])) == PurePath(path)
        or PurePath(path) in PurePath(issue.get("identity", issue["path"])).parents
        for path in action["paths"])
        for issue in health.get("diagnostics", []))
    stale = health.get("state") == "stale-or-unavailable"
    if stale and not relevant and execution_readiness(model)["state"] != "declared-readiness":
        relevant = True  # An absent dependency map cannot prove an independent branch.
    blocking = stale and relevant and action["kind"] == "work" and action["phase"] != "inspect"
    review = {**health, "action_state": "review-required" if blocking else
              "read-only-recovery" if stale and relevant else "not-relied-upon" if stale else health["state"],
              "checkpoint_required": blocking}
    return review, (["selected action relies on stale or unavailable evidence; reconcile affected inputs before mutation"]
                    if blocking else [])


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
    if (brief.get("terminal_control") is not None and action["kind"] == "work"
            and action["phase"] in {"commit", "publish", "live-external"} and "brief_sha256" not in action):
        failures.append("terminal-controlled mutations require the original action brief_sha256")
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
    allowed = prerequisite_closure(model, allowed)
    if not selected <= allowed:
        failures.append("action obligations are outside the selected outcomes and their prerequisite closure")
    if action["kind"] == "work" and action["phase"] in {"modify", "live-external"}:
        if not selected <= set(readiness["ready"]):
            failures.append("modifying/live work requires ready obligations; inspect blocked or waiting work before mutation")
    return failures
