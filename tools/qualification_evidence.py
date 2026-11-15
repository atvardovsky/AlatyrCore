"""Bounded coverage review; retained runs never become fresh acceptance."""

from __future__ import annotations

from cli_inputs import json_object
from delivery_receipts import artifact, parse_receipt, read_bound, sha256
from request_values import fields, integer, request_path, text


def case_ids(value, label):
    if not isinstance(value, list) or not 1 <= len(value) <= 256:
        raise ValueError(label + " requires 1..256 case IDs")
    result = [text(item, label, 256) for item in value]
    if len(set(result)) != len(result):
        raise ValueError(label + " contains duplicate case IDs")
    return result


def review_qualification(context, target, value):
    manifest = fields(value, {"schema_version", "required_case_ids", "current_input_sha256", "runs"}, "qualification review")
    integer(manifest["schema_version"], "qualification schema_version", 1, 1)
    required = set(case_ids(manifest["required_case_ids"], "required cases"))
    current = manifest["current_input_sha256"]
    if not isinstance(current, dict) or not 1 <= len(current) <= 32:
        raise ValueError("qualification review requires 1..32 exact current inputs")
    bindings = {}
    for path, digest in current.items():
        request_path(path); sha256(digest, "current input")
        read_bound(context, target, {"path": path, "sha256": digest}, bindings, limit=4 * 1024 * 1024)
    runs = manifest["runs"]
    if not isinstance(runs, list) or not 1 <= len(runs) <= 32:
        raise ValueError("qualification review requires 1..32 selected runs")
    seen, seen_receipts, historical, failed_runs = set(), set(), set(), []
    statuses, historical_failures = {}, set()
    for raw in runs:
        row = fields(raw, {"id", "receipt", "disposition", "equivalence_review"}, "qualification run")
        identity = text(row["id"], "qualification run ID")
        if identity in seen:
            raise ValueError("qualification run IDs must be unique")
        seen.add(identity)
        ref = artifact(row["receipt"], "qualification receipt")
        if ref["sha256"] in seen_receipts:
            raise ValueError("qualification cannot count a receipt twice")
        seen_receipts.add(ref["sha256"])
        receipt = parse_receipt(read_bound(context, target, ref, bindings))
        result = json_object(read_bound(context, target, artifact(receipt["result_artifact"], "case result"), bindings), "case result")
        fields(result, {"cases"}, "normalized case result")
        cases = result["cases"]
        if not isinstance(cases, list) or not 1 <= len(cases) <= 256:
            raise ValueError("normalized case result requires 1..256 cases")
        local = {}
        for item in cases:
            fields(item, {"id", "status"}, "normalized case")
            key = text(item["id"], "case ID", 256)
            state = item["status"]
            if key in local or key not in required:
                raise ValueError("normalized case is duplicated or outside the selected case set")
            if not isinstance(state, str) or state not in {"passed", "failed", "skipped", "blocked", "not-run"}:
                raise ValueError("normalized case status is unsupported")
            local[key] = state
        if receipt["result"] == "passed" and any(state != "passed" for state in local.values()):
            raise ValueError("passed receipt contradicts its normalized case outcomes")
        if receipt["result"] != "passed":
            failed_runs.append(identity)
        disposition = row["disposition"]
        if not isinstance(disposition, str) or disposition not in {"current", "retained"}:
            raise ValueError("qualification disposition must be current or retained")
        if disposition == "current":
            if row["equivalence_review"] is not None or any(receipt["input_sha256"].get(p) != h for p, h in current.items()):
                raise ValueError("current run has stale input bindings or an inapplicable equivalence review")
            for key, state in local.items():
                statuses.setdefault(key, set()).add(state)
        else:
            review_ref = artifact(row["equivalence_review"], "retained qualification review")
            review = json_object(read_bound(context, target, review_ref, bindings), "retained qualification review")
            fields(review, {"schema_version", "receipt_sha256", "current_input_sha256", "case_ids", "owner_ref", "reason"}, "retained qualification review")
            integer(review["schema_version"], "retained qualification schema", 1, 1)
            if review["receipt_sha256"] != ref["sha256"] or review["current_input_sha256"] != current:
                raise ValueError("retained qualification review does not bind the receipt and current inputs")
            text(review["owner_ref"], "equivalence owner"); text(review["reason"], "equivalence reason")
            selected = set(case_ids(review["case_ids"], "retained case IDs"))
            if not selected <= {key for key, state in local.items() if state == "passed"}:
                raise ValueError("retained review cannot promote failed, missing or unexecuted cases")
            historical.update(selected)
            historical_failures.update(key for key, state in local.items() if state != "passed")
    passed = {key for key, observed in statuses.items() if observed == {"passed"}}
    contradictory = sorted(key for key, observed in statuses.items() if len(observed) > 1)
    return {"status": "current-evidence-reviewed" if passed == required and not failed_runs else "target-review-required",
            "current_passed_case_ids": sorted(passed), "retained_reviewed_case_ids": sorted(historical),
            "uncovered_case_ids": sorted(required - passed - historical),
            "fresh_missing_case_ids": sorted(required - passed), "contradictory_case_ids": contradictory,
            "failed_or_interrupted_run_ids": failed_runs, "historical_nonpassed_case_ids": sorted(historical_failures),
            "authorization_granted": False, "acceptance_granted": False,
            "limitation": "Target-normalized outcomes and declared input coverage only; retained cases are historical, not a fresh full matrix, native-run authentication or a waiver of required acceptance."}
