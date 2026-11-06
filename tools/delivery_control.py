"""Conditional request delivery preflight; declared history is not execution proof."""

from __future__ import annotations

from request_values import fields, request_path, strings, text

MAX_HISTORY_BYTES = 65536
MAX_ATTEMPTS = 32
MAX_SECONDS = 86400
RESULTS = frozenset({"passed", "failed", "interrupted", "expected-red"})


def integer(value: object, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} requires an integer in {minimum}..{maximum}")
    return value


def parse_control(value: object, outcome_ids: set[str]) -> dict:
    control = fields(value, {"pilot_outcome_ids", "validation_history", "max_expensive_runs",
                             "max_validation_seconds"}, "delivery_control")
    pilots = strings(control["pilot_outcome_ids"], "pilot_outcome_ids", minimum=1)
    if not set(pilots) <= outcome_ids:
        raise ValueError("pilot_outcome_ids must select original requested outcomes")
    request_path(control["validation_history"])
    integer(control["max_expensive_runs"], "max_expensive_runs", 1, MAX_ATTEMPTS)
    integer(control["max_validation_seconds"], "max_validation_seconds", 1, MAX_SECONDS)
    return control


def parse_validation(value: object) -> dict:
    run = fields(value, {"command_id", "scope", "estimated_seconds", "diagnosis_proof_id",
                         "independent_review_proof_id"}, "validation")
    text(run["command_id"], "validation.command_id")
    if not isinstance(run["scope"], str) or run["scope"] not in {"focused", "broad"}:
        raise ValueError("validation.scope must be focused or broad")
    integer(run["estimated_seconds"], "validation.estimated_seconds", 1, MAX_SECONDS)
    for key in ("diagnosis_proof_id", "independent_review_proof_id"):
        if run[key] is not None:
            text(run[key], "validation." + key)
    return run


def parse_history(raw: bytes, brief: dict) -> dict:
    from inspect_session_context import json_object
    if len(raw) > MAX_HISTORY_BYTES:
        raise ValueError("validation history exceeds 64 KiB")
    try:
        document = json_object(raw, "validation history")
    except RecursionError as exc:
        raise ValueError("validation history nesting exceeds parser limits") from exc
    history = fields(document,
                     {"schema_version", "request_id", "task_id", "attempts"}, "validation history")
    if type(history["schema_version"]) is not int or history["schema_version"] != 1:
        raise ValueError("validation history requires schema 1")
    for key in ("request_id", "task_id"):
        if history[key] != brief[key]:
            raise ValueError("validation history has a different " + key)
    attempts = history["attempts"]
    if not isinstance(attempts, list) or len(attempts) > MAX_ATTEMPTS:
        raise ValueError("validation history exceeds 32 attempts; reassess instead of truncating")
    seen = set()
    for row in attempts:
        fields(row, {"evidence_ref", "result", "scope", "duration_seconds", "expected_red_proof_id"}, "validation attempt")
        text(row["evidence_ref"], "attempt.evidence_ref")
        if row["evidence_ref"] in seen:
            raise ValueError("validation attempts cannot repeat evidence references")
        seen.add(row["evidence_ref"])
        if not isinstance(row["result"], str) or row["result"] not in RESULTS:
            raise ValueError("validation attempt requires an exact result")
        if not isinstance(row["scope"], str) or row["scope"] not in {"focused", "broad"}:
            raise ValueError("validation attempt requires a focused or broad scope")
        integer(row["duration_seconds"], "attempt.duration_seconds", 0, MAX_SECONDS)
        if row["expected_red_proof_id"] is not None:
            text(row["expected_red_proof_id"], "attempt.expected_red_proof_id")
        if row["result"] != "expected-red" and row["expected_red_proof_id"] is not None:
            raise ValueError("only expected-red attempts may select an expected RED proof")
    return history


def delivery_failures(brief: dict, action: dict, model: dict, history: dict) -> list[str]:
    control = brief["delivery_control"]
    proofs = {row["id"]: row for row in model["proof_obligations"]}
    def passed(key: object) -> bool:
        proof = proofs.get(key) if isinstance(key, str) else None
        return proof is not None and proof["required"] is True and proof["status"] == "passed"
    failures = []
    pilot_proofs = {key for row in brief["outcomes"] if row["id"] in control["pilot_outcome_ids"]
                    for key in row["proof_obligation_ids"]}
    expands = (action["kind"] == "work" and action["phase"] != "inspect"
               and not set(action["outcome_ids"]) <= set(control["pilot_outcome_ids"]))
    run = action.get("validation")
    if (expands or run is not None and run["scope"] == "broad") and not all(passed(key) for key in pilot_proofs):
        failures.append("representative outcome proofs must pass before expanding implementation or broad validation")
    attempts = history["attempts"]
    for row in attempts:
        if row["result"] == "expected-red":
            proof = proofs.get(row["expected_red_proof_id"])
            if not passed(row["expected_red_proof_id"]) or row["evidence_ref"] not in proof.get("evidence_refs", []):
                failures.append("expected RED requires a passed required proof linked to the retained attempt")
    if action["kind"] == "complete" and attempts and attempts[-1]["result"] != "passed":
        failures.append("latest validation attempt is not passed; do not report complete")
    if run is None:
        return failures
    if len(attempts) >= MAX_ATTEMPTS:
        failures.append("validation history is full; reassess without dropping earlier attempts")
    broad_runs = sum(row["scope"] == "broad" for row in attempts)
    if broad_runs + (run["scope"] == "broad") > control["max_expensive_runs"]:
        failures.append("planned broad validation exceeds max_expensive_runs")
    elapsed = sum(row["duration_seconds"] for row in attempts)
    if elapsed + run["estimated_seconds"] > control["max_validation_seconds"]:
        failures.append(f"planned validation exceeds max_validation_seconds: {elapsed} + {run['estimated_seconds']} > {control['max_validation_seconds']}")
    # Count cumulatively, including test-author/environment failures, not just the last retry.
    unexpected = sum(row["result"] in {"failed", "interrupted"} for row in attempts)
    last_failure = next((row for row in reversed(attempts) if row["result"] in {"failed", "interrupted"}), None)
    def addresses_failure(key: object) -> bool:
        return (passed(key) and key not in pilot_proofs and last_failure is not None
                and last_failure["evidence_ref"] in proofs[key].get("evidence_refs", []))
    if unexpected and not addresses_failure(run["diagnosis_proof_id"]):
        failures.append("unexpected validation failure requires a passed required diagnosis proof linked to the latest failure before retry")
    if unexpected >= 2:
        review = run["independent_review_proof_id"]
        if not addresses_failure(review) or review == run["diagnosis_proof_id"]:
            failures.append("repeated validation failure requires a distinct passed required independent-review proof")
    if unexpected >= 3 and run["scope"] == "broad":
        diagnostic = attempts[-1]
        linked = all(addresses_failure(key) and diagnostic["evidence_ref"] in proofs[key].get("evidence_refs", [])
                     for key in (run["diagnosis_proof_id"], run["independent_review_proof_id"]))
        if diagnostic["scope"] != "focused" or diagnostic["result"] != "passed" or not linked:
            failures.append("three unexpected failures stop broad validation until a later passed focused diagnostic is linked by diagnosis and independent review")
    return failures
