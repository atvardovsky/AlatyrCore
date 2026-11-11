"""Evidence-linked analysis inside the existing bounded problem model.

These records describe observations and review work, not private reasoning or
permission to execute. Files are verified by the caller's contained read view.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import PurePath
from typing import Any, Callable

from target_validation_support import is_target_relative_path


MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
MAX_EVIDENCE_BYTES = 16 * 1024 * 1024


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def probe_binding(model: dict, probe: dict) -> str:
    """Bind the question and predictions, not a self-referential result."""
    hypotheses = {row["id"]: row["statement"] for row in model["hypotheses"]}
    unknowns = {row["id"]: row["statement"] for row in model["unknowns"]}
    obligations = {row["id"]: row["statement"] for row in model["proof_obligations"]}
    return digest({"model_id": model["model_id"], "operation_id": model["operation_id"],
                   "repository_binding": model["repository_binding"], "task_binding": model["task_binding"],
                   "hypotheses": {row["hypothesis_id"]: hypotheses.get(row["hypothesis_id"]) for row in probe["predictions"]},
                   "unknowns": {key: unknowns.get(key) for key in probe["unknown_ids"]},
                   "obligation": obligations.get(probe["obligation_id"]),
                   "probe": {key: value for key, value in probe.items() if key != "result"}})


def evidence_failures(model: dict, *, completion: bool = False) -> list[str]:
    """Cross-reference schema-validated evidence without executing a probe."""
    block = model.get("analysis_evidence")
    if block is None:
        return ["hypothesis-driven analysis requires operational analysis_evidence"] if model["primary_strategy_id"] == "hypothesis-driven" and model["schema_version"] >= 7 else []
    failures: list[str] = []
    selected = block.get("selected_context", [])
    if len({row["path"] for row in selected}) != len(selected):
        failures.append("selected context requires unique exact artifact paths")
    hypotheses = {row["id"]: row for row in model["hypotheses"]}
    obligations = {row["id"]: row for row in model["proof_obligations"]}
    unknowns = {row["id"] for row in model["unknowns"]}
    assumptions = {row["id"]: row for row in model["assumptions"]}
    counterexamples = {row["id"]: row for row in model["counterexamples"]}
    outcomes: dict[str, set[str]] = {key: set() for key in hypotheses}
    seen: set[str] = set()
    predicted: set[str] = set()
    if model["primary_strategy_id"] == "hypothesis-driven" and not block["probes"]:
        failures.append("hypothesis-driven analysis requires at least one operational probe")
    for probe in block["probes"]:
        identity = probe["obligation_id"]
        if identity in seen or identity not in obligations:
            failures.append(f"probe obligation {identity!r} must be unique and known")
        seen.add(identity)
        if not set(probe["unknown_ids"]) <= unknowns:
            failures.append(f"probe {identity} references unknown uncertainty IDs")
        predictions = [row["hypothesis_id"] for row in probe["predictions"]]
        predicted.update(predictions)
        if len(predictions) != len(set(predictions)) or not set(predictions) <= hypotheses.keys():
            failures.append(f"probe {identity} predictions must reference unique known hypotheses")
        for prediction in probe["predictions"]:
            if prediction["supports"] == prediction["refutes"]:
                failures.append(f"probe {identity} must distinguish supporting and refuting observations")
        for path in probe["input_paths"]:
            if not is_target_relative_path(path) or "\\" in path:
                failures.append(f"probe {identity} has unsafe input path: {path}")
        result = probe["result"]
        if result is None:
            if identity in obligations and obligations[identity]["status"] == "passed":
                failures.append(f"unrun probe {identity} cannot pass its proof obligation")
            continue
        if result["probe_sha256"] != probe_binding(model, probe):
            failures.append(f"probe {identity} result is stale for its task/question binding")
        if set(result["input_sha256"]) != set(probe["input_paths"]):
            failures.append(f"probe {identity} requires exact input digest coverage")
        verdicts = [row["hypothesis_id"] for row in result["outcomes"]]
        if len(verdicts) != len(set(verdicts)) or set(verdicts) != set(predictions):
            failures.append(f"probe {identity} requires exactly one outcome per prediction")
        for row in result["outcomes"]:
            if row["hypothesis_id"] in outcomes:
                outcomes[row["hypothesis_id"]].add(row["verdict"])
        if identity in obligations and obligations[identity]["status"] == "passed":
            paths = {row["path"] for row in result["artifacts"]}
            if not paths.intersection(obligations[identity]["evidence_refs"]):
                failures.append(f"passed probe {identity} must cite a measured result artifact")
    for identity, hypothesis in hypotheses.items():
        verdicts = outcomes[identity] - {"inconclusive"}
        if hypothesis["status"] in {"supported", "rejected"}:
            expected = "supports" if hypothesis["status"] == "supported" else "refutes"
            if verdicts != {expected}:
                failures.append(f"hypothesis {identity} conclusion requires consistent recorded {expected} evidence")
            paths = {artifact["path"] for probe in block["probes"] if probe["result"] is not None
                     and any(row["hypothesis_id"] == identity and row["verdict"] == expected for row in probe["result"]["outcomes"])
                     for artifact in probe["result"]["artifacts"]}
            if not paths.intersection(hypothesis["evidence_refs"]):
                failures.append(f"hypothesis {identity} must cite its result artifact")
        if completion and len(verdicts) > 1:
            failures.append(f"hypothesis {identity} has unresolved contradictory observations")
    if model["primary_strategy_id"] == "hypothesis-driven":
        if not hypotheses or not hypotheses.keys() <= predicted:
            failures.append("hypothesis-driven analysis requires predictions covering every hypothesis")
        if completion and not any(row["status"] == "supported" for row in hypotheses.values()):
            failures.append("hypothesis-driven completion requires an evidence-supported explanation")
    updates = block["updates"]
    bound_paths = {path for path, _ in artifact_bindings(model)}
    if len({row["id"] for row in updates}) != len(updates):
        failures.append("analysis evidence update IDs must be unique")
    for update in updates:
        if not set(update["evidence_refs"]) & bound_paths:
            failures.append(f"evidence update {update['id']} must cite a digest-bound observation artifact")
        if not (update["hypothesis_ids"] or update["invalidated_assumption_ids"] or update["reopened_obligation_ids"]):
            failures.append(f"evidence update {update['id']} needs a named revision effect")
        if not set(update["hypothesis_ids"]) <= hypotheses.keys() or not set(update["reopened_obligation_ids"]) <= obligations.keys():
            failures.append(f"evidence update {update['id']} has unknown hypothesis/obligation IDs")
        if not set(update["invalidated_assumption_ids"]) <= assumptions.keys():
            failures.append(f"evidence update {update['id']} has unknown assumption IDs")
        elif any(assumptions[key]["status"] != "invalidated" for key in update["invalidated_assumption_ids"]):
            failures.append(f"evidence update {update['id']} must retain invalidated assumptions")
        if update["state"] == "pending":
            if update["resolution_evidence_refs"]:
                failures.append(f"pending evidence update {update['id']} cannot claim resolution")
            if any(obligations[key]["status"] in {"passed", "waived"} for key in update["reopened_obligation_ids"] if key in obligations):
                failures.append(f"pending evidence update {update['id']} must keep reopened duties unresolved")
            if completion:
                failures.append(f"pending evidence update {update['id']} blocks completion")
        elif not set(update["resolution_evidence_refs"]) - set(update["evidence_refs"]):
            failures.append(f"resolved evidence update {update['id']} requires new resolution evidence")
        if not set(update["resolution_evidence_refs"]) <= bound_paths:
            failures.append(f"evidence update {update['id']} has unbound resolution evidence")
    challenges = block["review_challenges"]
    if len({row["id"] for row in challenges}) != len(challenges):
        failures.append("analysis review challenge IDs must be unique")
    for challenge in challenges:
        if not set(challenge["counterexample_ids"]) <= counterexamples.keys() or not set(challenge["proof_obligation_ids"]) <= obligations.keys():
            failures.append(f"challenge {challenge['id']} has unknown counterexample/obligation IDs")
        if model.get("original_case") is not None and challenge["original_source_ref"] != model["original_case"]["source_ref"]:
            failures.append(f"challenge {challenge['id']} must preserve the original case source")
        if challenge["status"] == "passed":
            if challenge["normative_source_ref"] not in bound_paths:
                failures.append(f"challenge {challenge['id']} must bind its normative source to a measured artifact")
            if challenge["original_source_ref"].casefold() in {"unknown", "unresolved", "pending", "none"} or "{" in challenge["original_source_ref"]:
                failures.append(f"challenge {challenge['id']} requires a resolved original source")
            if any(obligations[key]["status"] != "passed" for key in challenge["proof_obligation_ids"] if key in obligations):
                failures.append(f"challenge {challenge['id']} requires passed counterexample obligations")
            paths = {row["path"] for row in challenge["artifacts"]}
            for key in challenge["counterexample_ids"]:
                if key in counterexamples and not paths.intersection(counterexamples[key]["evidence_refs"]):
                    failures.append(f"challenge {challenge['id']} must bind counterexample {key} to a result artifact")
        if completion and challenge["status"] != "passed":
            failures.append(f"challenge {challenge['id']} remains unresolved")
    if any(row["status"] == "passed" for row in model["review_results"]) and (not challenges or any(row["status"] != "passed" for row in challenges)):
        failures.append("passed adversarial review requires passed evidence-linked challenges")
    if "outcome_checks" in block:
        from outcome_evidence import outcome_failures
        failures.extend(outcome_failures(model, completion=completion))
    return failures


def artifact_bindings(model: dict) -> list[tuple[str, str]]:
    block = model.get("analysis_evidence", {})
    result = [(row["path"], row["sha256"]) for row in block.get("selected_context", [])]
    applicability = block.get("package_applicability")
    if applicability is not None:
        result.extend((applicability[key]["path"], applicability[key]["sha256"])
                      for key in ("router", "ordinary_result", "profile") if applicability.get(key) is not None)
    for probe in block.get("probes", []):
        if probe["result"] is not None:
            result.extend(probe["result"]["input_sha256"].items())
            result.extend((row["path"], row["sha256"]) for row in probe["result"]["artifacts"])
    for challenge in block.get("review_challenges", []):
        result.extend((row["path"], row["sha256"]) for row in challenge["artifacts"])
    for update in block.get("updates", []):
        result.extend((row["path"], row["sha256"]) for row in update["artifacts"])
    if "outcome_checks" in block:
        from outcome_evidence import artifact_bindings as outcome_bindings
        result.extend(outcome_bindings(model))
    return result


def active_retention_failures(model: dict, is_ignored: Callable[[str], bool | None]) -> list[str]:
    """A schema-validated active witness must carry retainable dependencies."""
    return [f"active handoff depends on ignored or unverified analysis artifact: {path}"
            for path in sorted({path for path, _ in artifact_bindings(model)})
            if is_ignored(path) is not False]


def artifact_obligations(model: dict, path: str, identities: dict[str, str]) -> set[str] | None:
    """Declared impact only; an unscoped/shared context input affects the task."""
    block = model.get("analysis_evidence", {})
    identity = PurePath(identities.get(path, path))
    def matches(value: str) -> bool:
        return PurePath(identities.get(value, value)) == identity
    if any(matches(row["path"]) for row in block.get("selected_context", [])):
        return None
    affected = {row["id"] for row in model["proof_obligations"] if any(matches(ref) for ref in row["evidence_refs"])}
    for probe in block.get("probes", []):
        result = probe["result"]
        if result and (any(matches(ref) for ref in result["input_sha256"]) or any(matches(row["path"]) for row in result["artifacts"])):
            affected.add(probe["obligation_id"])
    for challenge in block.get("review_challenges", []):
        if any(matches(row["path"]) for row in challenge["artifacts"]):
            affected.update(challenge["proof_obligation_ids"])
    for update in block.get("updates", []):
        if any(matches(row["path"]) for row in update["artifacts"]):
            return None
    for case in block.get("outcome_checks", []):
        observation = case["observation"]
        if (matches(case["oracle"]["path"]) or observation and
                (any(matches(ref) for ref in observation["input_sha256"]) or any(matches(row["path"]) for row in observation["artifacts"]))):
            affected.update(case["proof_obligation_ids"])
    return affected or None


def evidence_readiness(model: dict, issues: list[dict], identities: dict[str, str] | None = None) -> dict:
    identities = identities or {}
    affected = set()
    global_review = len(issues) > 8
    for issue in issues if not global_review else []:
        scope = artifact_obligations(model, issue["path"], identities) if issue["path"] is not None else None
        if scope is None:
            global_review = True
        else:
            affected.update(scope)
    return {"state": "stale-or-unavailable" if issues else "current-content-not-execution-proof",
            "affected_obligation_ids": sorted(affected), "global_review_required": global_review,
            "diagnostics": [{**issue, "identity": identities.get(issue["path"], issue["path"])} for issue in issues[:8]],
            "failure_count": len(issues),
            "authority": "none", "authorization_granted": False, "acceptance_granted": False}


def verify_artifacts(model: dict, read: Callable[[str, int], bytes], *, historical_outcomes: bool = False,
                     issues: list[dict] | None = None) -> list[str]:
    """Cap accepted payload and each read allocation; readers may probe one byte."""
    failures = []
    def fail(message: str, path: str | None = None) -> None:
        failures.append(message)
        if issues is not None:
            issues.append({"path": path, "message": message})
    measured: dict[str, str] = {}
    total = 0
    bindings = artifact_bindings(model)
    if historical_outcomes:
        from outcome_evidence import retained_bindings
        bindings = retained_bindings(model)
    for path, expected in bindings:
        if not is_target_relative_path(path) or "\\" in path:
            fail(f"analysis evidence has unsafe artifact path: {path}")
            continue
        if path not in measured:
            limit = min(MAX_ARTIFACT_BYTES, MAX_EVIDENCE_BYTES - total)
            try:
                raw = read(path, limit)
            except (OSError, ValueError) as exc:
                fail(f"analysis evidence artifact {path}: {exc}")
                break
            if len(raw) > limit:
                fail("analysis evidence exceeds artifact verification byte budget")
                break
            total += len(raw)
            measured[path] = hashlib.sha256(raw).hexdigest()
            if "outcome_checks" in model.get("analysis_evidence", {}):
                from outcome_evidence import supersession_artifact_failures
                for failure in supersession_artifact_failures(model, path, raw):
                    fail(failure)
        if measured[path] != expected:
            fail(f"analysis evidence artifact digest changed: {path}", path)
    return failures


def revision_failures(previous: dict, current: dict) -> list[str]:
    """Publication may revise conclusions, not silently drop captured duties."""
    old = previous.get("analysis_evidence")
    new = current.get("analysis_evidence")
    if old is None:
        return []
    if new is None:
        return ["captured analysis evidence cannot be removed; use an explicit successor task"]
    failures = []
    if "outcome_checks" in old:
        from outcome_evidence import revision_failures as outcome_revisions
        failures.extend(outcome_revisions(previous, current))
    current_probes = {row["obligation_id"]: row for row in new["probes"]}
    revised_hypotheses: set[str] = set()
    for probe in old["probes"]:
        replacement = current_probes.get(probe["obligation_id"])
        immutable = ("unknown_ids", "method", "action_kind", "input_paths", "predictions")
        if replacement is None or any(replacement[key] != probe[key] for key in immutable):
            failures.append(f"captured probe {probe['obligation_id']} and its question cannot be removed or rewritten")
        elif replacement["result"] != probe["result"]:
            revised_hypotheses.update(row["hypothesis_id"] for row in probe["predictions"])
    for collection, immutable in (("updates", ("reason", "evidence_refs", "hypothesis_ids", "invalidated_assumption_ids", "reopened_obligation_ids")),
                                  ("review_challenges", ("original_source_ref", "normative_source_ref", "counterexample_ids", "proof_obligation_ids"))):
        current_rows = {row["id"]: row for row in new[collection]}
        for row in old[collection]:
            if row["id"] not in current_rows or any(current_rows[row["id"]][key] != row[key] for key in immutable):
                failures.append(f"captured {collection} {row['id']} and its duties cannot be removed or rewritten")
    changed = {row["id"] for row in previous["hypotheses"] if row not in current["hypotheses"]}
    changed.update(revised_hypotheses)
    additions = [row for row in new["updates"] if row not in old["updates"]]
    covered = {key for row in additions for key in row["hypothesis_ids"]}
    if not changed <= covered:
        failures.append("changed hypothesis conclusions require an evidence update in the same strategy")
    return failures


def active_evidence(model: dict) -> dict:
    block = model["analysis_evidence"]
    summary = {}
    if "outcome_checks" in block:
        from outcome_evidence import active_checks
        summary["outcome_checks"] = active_checks(model)
    return {**({"selected_context": block["selected_context"]} if "selected_context" in block else {}),
            **summary,
            "probes": [{"obligation_id": row["obligation_id"], "unknown_ids": row["unknown_ids"],
                        "method": row["method"], "action_kind": row["action_kind"],
                        "estimated_tool_calls": row["estimated_tool_calls"],
                        "predictions": row["predictions"], "result": row["result"]} for row in block["probes"]],
            "pending_updates": [row for row in block["updates"] if row["state"] == "pending"],
            "review_challenges": block["review_challenges"],
            "rejected_hypotheses": [row for row in model["hypotheses"] if row["status"] == "rejected"]}


def next_action_advice(model: dict, model_sha256: str, *, readiness: dict | None = None) -> dict:
    from task_readiness import execution_readiness
    if readiness is None:
        readiness = execution_readiness(model)
    ready = set(readiness.get("ready", []))
    blocked = set(readiness.get("blocked", []))
    prerequisites = readiness.get("unsettled_prerequisites", {row["obligation_id"]: row["requires"] for row in readiness.get("waiting", [])})
    obligations = {row["id"]: row for row in model["proof_obligations"]}
    candidates, retained = [], []
    for probe in model["analysis_evidence"]["probes"]:
        identity = probe["obligation_id"]
        obligation = obligations[identity]
        if obligation["status"] in {"passed", "waived"}:
            continue
        eligibility = ("dependency-unconfigured" if readiness["state"] == "not-configured" else
                       "dependency-invalid" if readiness["state"] != "declared-readiness" else
                       "ready" if identity in ready else "blocked" if identity in blocked else "waiting")
        row = {"obligation_id": identity, "required": obligation["required"],
               "status": obligation["status"], "eligibility": eligibility,
               "dependency_ready": None if eligibility == "dependency-unconfigured" else identity in ready,
               "unsettled_prerequisites": prerequisites.get(identity, []), "unknown_ids": probe["unknown_ids"],
               "action_kind": probe["action_kind"], "prediction_count": len(probe["predictions"]),
               "selection_review_required": True,
               "retry_review_required": probe["result"] is not None,
               "previous_result_sha256": digest(probe["result"]) if probe["result"] is not None else None,
               "estimated_tool_calls": probe["estimated_tool_calls"],
               "reason": "discriminate a named uncertainty; recorded estimates are not measured savings"}
        (candidates if eligibility == "ready" else retained).append(row)
    risk_order = {"read-only": 0, "local-check": 1, "protected-action": 2, "unknown": 3}
    def order(row: dict) -> tuple:
        return (not row["required"], risk_order[row["action_kind"]], row["retry_review_required"],
                row["estimated_tool_calls"] is None, row["estimated_tool_calls"] or 0,
                row["obligation_id"])
    candidates.sort(key=order)
    retained.sort(key=order)
    return {"model_sha256": model_sha256, "task_binding": model["task_binding"], "authority": "none",
            "authorization_granted": False, "evidence_verified": False,
            "dependency_state": readiness["state"], "candidates": candidates, "retained_candidates": retained,
            "unresolved_required": [row["id"] for row in model["proof_obligations"] if row["required"] and row["status"] not in {"passed", "waived"}],
            "unresolved_reviews": sorted(set(model["required_review_ids"]) - {row["id"] for row in model["review_results"] if row["status"] == "passed"}),
            "pending_revision_ids": [row["id"] for row in model["analysis_evidence"]["updates"] if row["state"] == "pending"],
            "escalation": "reassess-systemic-repair" if model["incident"]["corrective_iteration"] >= 2 else "none",
            "selection_policy": "Review which possible observation changes the decision. Hypothesis count is descriptive, not information gain. Within equal duty/risk prefer unrun probes before reviewed retries; cost remains an estimate.",
            "limitation": "Local advice, not a scheduler or proven optimum. Unknown cost remains unknown. Resolve authorization, owners, conflicts and required reviews before action."}
