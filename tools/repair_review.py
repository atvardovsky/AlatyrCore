"""Bounded repair-review invariants; observed runs retain canonical ownership."""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone

from jsonschema import Draft202012Validator
from target_validation_support import is_target_relative_path, is_unresolved_value, is_placeholder

BOUNDARIES = frozenset({"entrypoint", "producers-consumers", "persistence", "process-topology", "resources", "positive-preconditions"})


def shape_failures(value: Any, definition: str, schema: dict[str, Any]) -> list[str]:
    selected = {"$ref": f"#/$defs/{definition}", "$defs": schema["$defs"]}
    failures = [f"{list(error.absolute_path)}: {error.message}" for error in Draft202012Validator(selected).iter_errors(value)]
    if isinstance(value, dict) and type(value.get("schema_version")) is not int:
        failures.append("repair schema_version must be an integer")
    return failures


def resolved(value: str) -> bool:
    return not is_unresolved_value(value) and not is_placeholder(value)


def policy_failures(review: Any, policy: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    failures = shape_failures(review, "repair_policy", schema)
    if failures:
        return failures
    commands = {command["id"]: command for command in policy["commands"]}
    if review["state"] == "enabled" and not review["acceptance_command_ids"]:
        failures.append("enabled repair review requires target-owned acceptance command IDs")
    if review["state"] != "enabled" and review["records"]:
        failures.append("disabled or deferred repair review cannot select records")
    for command_id in review["acceptance_command_ids"]:
        command = commands.get(command_id)
        if command is None or command["execution"]["proof_boundary"] != "end-to-end" or command["execution"]["suite_scope"] != "full" or command["execution"]["kind"] != "automated-test":
            failures.append(f"repair acceptance command {command_id!r} requires a full automated end-to-end boundary")
    for key in ("task_id", "path"):
        values = [entry[key] for entry in review["records"]]
        if len(set(values)) != len(values) or any(not resolved(value) for value in values):
            failures.append(f"repair record {key} values must be unique and resolved")
    if any(not is_target_relative_path(entry["path"]) for entry in review["records"]):
        failures.append("repair evidence paths must remain target-relative and contained")
    return failures


def run_window(run: dict[str, Any]) -> tuple[datetime, datetime] | None:
    value = run.get("run_window")
    if not isinstance(value, dict) or set(value) != {"started_at", "finished_at"}:
        return None
    try:
        if not all(isinstance(item, str) and len(item) <= 64 for item in value.values()):
            return None
        start, end = (datetime.fromisoformat(value[key].replace("Z", "+00:00")) for key in ("started_at", "finished_at"))
        if start.tzinfo is None or end.tzinfo is None or end < start:
            return None
        return start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def controlled_contrast(before: dict[str, Any], after: dict[str, Any], metadata_paths: set[str]) -> bool:
    if before["command_id"] != after["command_id"] or before["filter"] != after["filter"]:
        return True
    paths = set(before["input_sha256"]) | set(after["input_sha256"])
    return any(not path.casefold().startswith(".ai/") and path.casefold() not in metadata_paths and before["input_sha256"].get(path) != after["input_sha256"].get(path) for path in paths)


def evidence_failures(record: Any, review: dict[str, Any], runs: dict[str, Any], schema: dict[str, Any], *, completion: bool, current_refs: set[str] | None = None) -> list[str]:
    failures = shape_failures(record, "repair_evidence", schema)
    if failures:
        return failures
    ids = [item["id"] for item in record["hypotheses"]]
    if len(set(ids)) != len(ids):
        failures.append("repair hypotheses must have unique IDs")
    for item in record["hypotheses"]:
        if any(not resolved(item[key]) for key in ("id", "falsifier")):
            failures.append("hypotheses require resolved canonical IDs and falsifiers")
    boundaries = record["fixture_boundaries"]
    if {item["id"] for item in boundaries} != BOUNDARIES or len(boundaries) != len(BOUNDARIES):
        failures.append("repair review requires each fixture boundary exactly once")
    for item in boundaries:
        refs = item["evidence_refs"]
        if not resolved(item["reason"]) or any(ref not in runs for ref in refs):
            failures.append(f"fixture boundary {item['id']} has unresolved reason or run reference")
        if item["state"] != "unknown" and not refs:
            failures.append(f"fixture boundary {item['id']} requires review evidence, including non-applicability")
    current_refs = set(runs) if current_refs is None else current_refs
    acceptance_ids = set(review["acceptance_command_ids"])
    required_refs = {ref for ref, run in runs.items() if ref in current_refs and run["command_id"] in acceptance_ids and run["filter"] is None}
    attempts = record["attempts"]
    metadata_paths = {ref.casefold() for ref in runs}
    metadata_paths.update(item["path"].casefold() for item in review["records"])
    metadata_paths.update(run["result_artifact"]["path"].casefold() for run in runs.values() if isinstance(run.get("result_artifact"), dict))
    metadata_paths.update(attempt["historical_policy"]["path"].casefold() for attempt in attempts if attempt["historical_policy"] is not None)
    if not required_refs <= {attempt["run_ref"] for attempt in attempts if attempt["purpose"] == "acceptance"}:
        failures.append("repair review cannot omit selected current acceptance runs, including failures")
    seen, diagnostics, pending, latest = set(), {}, {}, {}
    previous_start = None
    last_acceptance_end = {}
    for attempt in record["attempts"]:
        ref = attempt["run_ref"]
        run = runs.get(ref)
        if ref in seen or run is None or attempt["hypothesis_id"] not in ids:
            failures.append("attempts require unique selected runs and a declared hypothesis")
            continue
        seen.add(ref)
        window = run_window(run)
        if window is None:
            failures.append(f"run {ref} requires a valid timezone-bound ordered run_window")
            continue
        if previous_start is not None and window[0] < previous_start:
            failures.append("repair attempts must retain observed run chronology")
        previous_start = window[0]
        if not resolved(attempt["expected_effect"]) or not resolved(attempt["observed_effect"]):
            failures.append("attempts require resolved expected and observed incident-level effects")
        command_id = run["command_id"]
        reassessment = attempt["reassessment_ref"]
        whole_flow = run["filter"] is None and run["proof_boundary"] == "end-to-end"
        if whole_flow and attempt["purpose"] != "acceptance":
            failures.append("historical or current whole-flow runs retain acceptance significance despite diagnostic labels")
        if attempt["purpose"] == "acceptance" or whole_flow:
            if run["filter"] is not None or command_id not in acceptance_ids:
                failures.append("acceptance attempts must use configured unfiltered whole-flow commands")
            if command_id in last_acceptance_end and window[0] < last_acceptance_end[command_id]:
                failures.append("overlapping acceptance runs for one command have ambiguous terminal order")
            last_acceptance_end[command_id] = window[1]
            failed_ref = pending.get(command_id)
            if failed_ref is not None:
                diagnostic = diagnostics.get(reassessment)
                if diagnostic is None or diagnostic["failure_ref"] != failed_ref or run_window(runs[reassessment])[1] > window[0]:
                    failures.append("repeated acceptance requires a completed discriminating diagnostic tied to its failed run")
                else:
                    pending.pop(command_id)
            elif reassessment is not None and reassessment not in diagnostics:
                failures.append("reassessment must reference an earlier diagnostic run")
            if ref in current_refs:
                latest[command_id] = run
            if run["state"] == "failed":
                pending[command_id] = ref
        else:
            artifact = run.get("result_artifact")
            if run["state"] not in {"passed", "failed"} or run["counts"]["executed"] == 0 or artifact is None or run["proof_boundary"] in {"static-metadata", "manual"}:
                failures.append("diagnostic evidence requires an observed non-static executed run")
            else:
                failed_ref = attempt["failure_ref"]
                if failed_ref is not None:
                    failed = runs.get(failed_ref)
                    old_window = run_window(failed) if isinstance(failed, dict) else None
                    failed_artifact = failed.get("result_artifact") if isinstance(failed, dict) else None
                    if failed_ref not in seen or failed is None or failed["state"] != "failed" or old_window is None or old_window[1] > window[0] or not isinstance(failed_artifact, dict) or not controlled_contrast(failed, run, metadata_paths) or artifact["sha256"] == failed_artifact["sha256"]:
                        failures.append("reassessment requires a completed failure and a real input/selection contrast, not output or timestamp churn")
                    else:
                        diagnostics[ref] = attempt
                else:
                    diagnostics[ref] = attempt
        if (run["state"] == "failed" and attempt["failure_class"] == "none") or (run["state"] == "passed" and attempt["failure_class"] != "none"):
            failures.append("failure classification must agree with the observed run state")
    if record["claim"] == "incident-fixed" or completion:
        diagnosis = record["diagnosis"]
        if diagnosis is None or diagnosis["run_ref"] not in diagnostics or not any(attempt["purpose"] == "diagnostic" and attempt["hypothesis_id"] == diagnosis["hypothesis_id"] and attempt["run_ref"] == diagnosis["run_ref"] and attempt["failure_class"] not in {"test-author", "unverified"} for attempt in record["attempts"]):
            failures.append("incident completion requires a supported diagnosis bound to a discriminating run")
        if record["claim"] != "incident-fixed" or not resolved(record["original_case_ref"]):
            failures.append("incident completion requires original-case evidence and incident-fixed claim")
        if any(item["state"] == "unknown" for item in boundaries):
            failures.append("unknown fixture fidelity cannot establish incident acceptance")
        if pending:
            failures.append("an unresolved failed acceptance attempt prevents incident completion")
        for command_id in review["acceptance_command_ids"]:
            run = latest.get(command_id)
            if run is None or run["state"] != "passed" or run["claim"] != "full" or run["proof_boundary"] != "end-to-end":
                failures.append(f"incident completion requires full observed acceptance for {command_id}")
    return failures
