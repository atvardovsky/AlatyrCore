"""Bounded selected-task orientation, derived only from validated existing state."""

from __future__ import annotations

import hashlib

from analysis_strategy_contract import canonical_utf8_size, structured_word_count
from analysis_evidence import probe_binding


MAX_FOCUS_BYTES = 8192
MAX_FOCUS_WORDS = 800


def build_execution_focus(model: dict, task: dict, binding: dict,
                          readiness: dict, advice: dict | None) -> dict:
    """No I/O, execution, authority, new state, or inferred task dependencies."""
    block = model.get("analysis_evidence", {})
    signals = []
    pending = [row["id"] for row in block.get("updates", []) if row["state"] == "pending"]
    if pending:
        signals.append({"reason": "evidence-revision-pending", "ids": pending})
    conflicts = [row["id"] for row in model["invariants"] if row["status"] in {"violated", "unresolved"}]
    if conflicts:
        signals.append({"reason": "invariant-conflict", "ids": conflicts})
    if model["unresolved_decisions"]:
        signals.append({"reason": "project-decision-unresolved", "ids": model["unresolved_decisions"]})
    gate = model["incident"]["latest_failed_gate"]
    if gate["state"] == "open":
        signals.append({"reason": "required-gate-open", "ids": [gate["id"]]})
    original = model.get("original_case")
    original_status = original["status"] if original is not None else "not-recorded"
    if original_status in {"unverified", "still-failing"}:
        signals.append({"reason": "original-case-unresolved", "ids": [original["source_ref"]]})
    if model["incident"]["corrective_iteration"] >= 2:
        signals.append({"reason": "systemic-reassessment", "ids": [model["incident"]["family_id"]]})
    inconclusive = [row["obligation_id"] for row in block.get("probes", [])
                    if row["result"] is not None and row["result"]["outcomes"]
                    and all(item["verdict"] == "inconclusive" for item in row["result"]["outcomes"])]
    if inconclusive:
        signals.append({"reason": "probe-inconclusive", "ids": inconclusive})
    stale = advice is not None and advice.get("state") == "blocked-by-stale-evidence"
    runtime_blocked = readiness["state"] == "blocked-by-runtime-evidence"
    if runtime_blocked:
        signals.append({"reason": "runtime-evidence-unresolved", "ids": []})
    if stale:
        signals.append({"reason": "input-artifacts-changed", "ids": []})
    candidates = advice.get("candidates", []) if advice is not None and not stale and not runtime_blocked else []
    retries = [row["obligation_id"] for row in candidates if row["retry_review_required"]]
    if retries:
        signals.append({"reason": "recorded-probe-needs-retry-review", "ids": retries})
    next_action = None
    if candidates and task["state"] == "active":
        candidate = candidates[0]
        identity = candidate["obligation_id"]
        proof = next(row for row in model["proof_obligations"] if row["id"] == identity)
        probe = next(row for row in block["probes"] if row["obligation_id"] == identity)
        next_action = {"obligation_id": identity, "method": probe["method"],
                       "unknown_ids": probe["unknown_ids"], "action_kind": probe["action_kind"],
                       "probe_sha256": probe_binding(model, probe),
                       "selection_review_required": candidate["selection_review_required"],
                       "previous_result_sha256": candidate["previous_result_sha256"],
                       "retry_review_required": candidate["retry_review_required"],
                       "completion_condition": proof["statement"], "reanchor_required": bool(signals)}
    focus = {
        "schema_version": 1, "view_kind": "alatyr-execution-focus", "task_id": task["task_id"],
        "model": binding, "task_state": task["state"], "objective": model["objective"],
        "active_projection_locator": model["active_projection"] if task["state"] == "active" else None,
        "projection_content_verified": False,
        "state": "historical-disposition" if task["state"] == "closed" else
                 "blocked-by-runtime-evidence" if runtime_blocked else
                 "blocked-by-stale-evidence" if stale else "reanchor-required" if signals else
                 "declared-frontier" if candidates else "orientation-only",
        "scope": {"source": "bound-model-and-active-projection", "non_goals": model["non_goals"],
                  "invariant_ids": [row["id"] for row in model["invariants"]],
                  "canonical_owners": task["canonical_owners"]},
        "original_case_status": original_status,
        "unresolved_required_ids": [row["id"] for row in model["proof_obligations"]
                                    if row["required"] and row["status"] not in {"passed", "waived"}],
        "unresolved_review_ids": sorted(set(model["required_review_ids"]) -
            {row["id"] for row in model["review_results"] if row["status"] == "passed"}),
        "dependency_state": readiness["state"], "eligible_obligation_ids": [row["obligation_id"] for row in candidates],
        "reanchor_signals": signals, "next_action": next_action,
        "intent_currentness": "primary-verification-required", "execution_interception": "not-performed",
        "authority": "none", "authorization_granted": False, "acceptance_granted": False,
        "limitation": "Recorded orientation, not runtime proof or permission. Recheck current intent, owners and authorization before action. Signals require review, not automatic global blocking; independent work remains visible.",
    }
    if canonical_utf8_size(focus) > MAX_FOCUS_BYTES or structured_word_count(focus) > MAX_FOCUS_WORDS:
        fallback = {"schema_version": 1, "view_kind": "alatyr-execution-focus", "task_id": task["task_id"],
                "model": binding, "state": "reference-required", "next_action": None,
                "active_projection_locator": focus["active_projection_locator"],
                "projection_content_verified": False,
                "unresolved_required_count": len(focus["unresolved_required_ids"]),
                "recovery": "Read the bound active projection and named model sections; no duties were truncated into an actionable view.",
                "authority": "none", "authorization_granted": False, "acceptance_granted": False}
        if canonical_utf8_size(fallback) > MAX_FOCUS_BYTES or structured_word_count(fallback) > MAX_FOCUS_WORDS:
            return {"schema_version": 1, "view_kind": "alatyr-execution-focus", "state": "reference-required",
                    "model_sha256": binding["sha256"],
                    "task_id_sha256": hashlib.sha256(task["task_id"].encode("utf-8")).hexdigest(),
                    "recovery": "Read .ai/assistant/active-tasks.json using the selected current-task ID; verify the bound projection before action.",
                    "unresolved_required_count": len(focus["unresolved_required_ids"]),
                    "next_action": None, "authority": "none", "authorization_granted": False,
                    "acceptance_granted": False}
        return fallback
    return focus
