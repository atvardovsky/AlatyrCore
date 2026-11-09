"""Optional bounded delivery observations; reassessment never grants authority."""

from __future__ import annotations

import time

from delivery_receipts import artifact, read_bound, receipt_failures, timestamp
from request_values import fields, integer, request_path, strings, text

PHASES = frozenset({"investigation", "implementation", "validation", "coordination",
                    "infrastructure-wait", "approval-wait"})


def parse_review_control(value: object) -> dict:
    control = fields(value, {"max_task_seconds", "max_no_progress_seconds", "max_observation_age_seconds"},
                     "execution_review")
    integer(control["max_task_seconds"], "max_task_seconds", 1, 604800)
    integer(control["max_no_progress_seconds"], "max_no_progress_seconds", 1, 86400)
    integer(control["max_observation_age_seconds"], "max_observation_age_seconds", 1, 3600)
    return control


def parse_history_extension(history: dict) -> None:
    progress = fields(history["progress"], {"started_at", "observed_at", "last_progress_at", "phase",
                      "evidence", "obligation_ids"}, "progress")
    start, observed, last = (timestamp(progress[key], "progress." + key)
                             for key in ("started_at", "observed_at", "last_progress_at"))
    if not start <= last <= observed:
        raise ValueError("progress timestamps require started_at <= last_progress_at <= observed_at")
    if not isinstance(progress["phase"], str) or progress["phase"] not in PHASES:
        raise ValueError("progress.phase requires an exact delivery phase")
    artifact(progress["evidence"], "progress.evidence")
    strings(progress["obligation_ids"], "progress.obligation_ids", minimum=1)
    if history["previous"] is not None:
        artifact(history["previous"], "history.previous")
    elif history["attempts"]:
        raise ValueError("nonempty schema-2 history requires its preceding snapshot")
    for row in history["attempts"]:
        if "receipt" in row:
            text(row["command_id"], "attempt.command_id")
            request_path(row["evidence_ref"])
            artifact(row["receipt"], "attempt.receipt")


def previous_failures(context, target, brief: dict, history: dict, inputs: dict, history_parser,
                      history_anchor: dict | None = None, history_sha256: str | None = None,
                      anchor_request_id: str | None = None) -> tuple[list[str], int]:
    previous = history["previous"]
    anchored = history_anchor is None or (
        history_anchor["path"] == brief["delivery_control"]["validation_history"] and (
            history_sha256 == history_anchor["sha256"] or
            previous is not None and previous["sha256"] == history_anchor["sha256"]))
    if not anchored:
        return ["delivery history must retain the last bound snapshot as its preceding history; no budget reset"], 0
    if previous is None:
        return [], len(history["attempts"]) if history_anchor else 0
    if previous["path"] == brief["delivery_control"]["validation_history"]:
        return ["preceding history must be an immutable separate snapshot"], 0
    legacy_brief = {**brief, "delivery_control": {**brief["delivery_control"], "execution_review": None}}
    if history_anchor is not None and previous["sha256"] == history_anchor["sha256"] and anchor_request_id is not None:
        legacy_brief["request_id"] = anchor_request_id
    raw_prior = read_bound(context, target, previous, inputs)
    if history_anchor is not None and history_sha256 == history_anchor["sha256"]:
        from inspect_session_context import json_object
        historical_request = json_object(raw_prior, "preceding history").get("request_id")
        text(historical_request, "preceding request_id")
        legacy_brief["request_id"] = historical_request
    prior = history_parser(raw_prior, legacy_brief)
    old = prior["attempts"]
    failures = []
    if history["attempts"][:len(old)] != old:
        failures.append("delivery history must preserve every preceding attempt unchanged and in order")
    if any("receipt" not in row for row in history["attempts"][len(old):]):
        failures.append("new attempts require receipts; only exact preceding legacy rows may remain unreceipted")
    if prior["schema_version"] == 2:
        before, after = prior["progress"], history["progress"]
        if before["started_at"] != after["started_at"]:
            failures.append("delivery history cannot reset task started_at")
        for key in ("observed_at", "last_progress_at"):
            if timestamp(after[key], key) < timestamp(before[key], key):
                failures.append("delivery history cannot move " + key + " backwards")
        if (timestamp(after["last_progress_at"], "last_progress_at") > timestamp(before["last_progress_at"], "last_progress_at")
                and after["evidence"]["sha256"] == before["evidence"]["sha256"]):
            failures.append("advancing last_progress_at requires new bound progress evidence, not a renewed timestamp")
    preserved = (len(history["attempts"]) if history_anchor and history_sha256 == history_anchor["sha256"]
                 else len(old) if history_anchor and previous["sha256"] == history_anchor["sha256"] else 0)
    return failures, preserved if not failures else 0


def execution_review(context, target, brief: dict, action: dict, model: dict, history: dict,
                     inputs: dict, *, history_parser, history_anchor: dict | None = None,
                     history_sha256: str | None = None, anchor_request_id: str | None = None,
                     now: float | None = None) -> tuple[dict, list[str]]:
    """Read only adopted evidence; historical input hashes do not become current proof."""
    failures = []
    try:
        continuity, preserved = previous_failures(context, target, brief, history, inputs, history_parser,
                                                  history_anchor, history_sha256, anchor_request_id)
        failures.extend(continuity)
        failures.extend(receipt_failures(context, target, brief, history, inputs, preserved_count=preserved))
        read_bound(context, target, history["progress"]["evidence"], inputs)
    except (OSError, ValueError) as exc:
        failures.append(str(exc))
    progress = history["progress"]
    known = {row["id"] for row in model["proof_obligations"]}
    if not set(progress["obligation_ids"]) <= known:
        failures.append("progress must name existing proof obligations")
    current = time.time() if now is None else now
    start = timestamp(progress["started_at"], "started_at")
    observed = timestamp(progress["observed_at"], "observed_at")
    last = timestamp(progress["last_progress_at"], "last_progress_at")
    control = brief["delivery_control"].get("execution_review")
    reasons = []
    if observed > current:
        reasons.append("progress observation is in the future")
    if control is not None:
        for measured, limit, label in ((current-start, control["max_task_seconds"], "task elapsed time"),
                                      (current-last, control["max_no_progress_seconds"], "time since declared progress"),
                                      (current-observed, control["max_observation_age_seconds"], "progress observation age")):
            if measured > limit:
                reasons.append(f"{label} {measured:.3f}s exceeds {limit}s; reassess before further state changes or validation")
    review = {"state": "reassessment-required" if failures or reasons else "within-declared-bounds",
              "phase": progress["phase"], "elapsed_seconds": max(0, current-start),
              "since_declared_progress_seconds": max(0, current-last), "reasons": failures + reasons,
              "timing_evidence": "declared-timestamps-not-executor-active-time",
              "history_continuity": "last-bound-snapshot" if history_anchor else "unanchored-review",
              "legacy_attempts": sum("receipt" not in row for row in history["attempts"]),
              "authorization_granted": False, "acceptance_granted": False}
    # Inspection/replanning remains possible; elapsed time can never manufacture completion.
    blocking = action["phase"] != "inspect" or action["kind"] == "complete" or "validation" in action
    return review, failures + reasons if blocking else []
