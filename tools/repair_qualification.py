"""Opt-in observations and comparable measurements, never causal inference."""

from __future__ import annotations

import math
import re
from fractions import Fraction
from statistics import median
from typing import Any

from path_spec import logical_path
from target_validation_support import is_unresolved_value, is_placeholder

MISSING = object()


def finite_number(value: Any) -> bool:
    return type(value) in (int, float) and -1e100 <= value <= 1e100 and math.isfinite(value)


def scalar(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip()) and not is_unresolved_value(value) and not is_placeholder(value)
    return type(value) is bool or finite_number(value)


def same_value(left: Any, right: Any) -> bool:
    if not scalar(left) or not scalar(right):
        return False
    if type(left) is bool or type(right) is bool:
        return type(left) is type(right) and left == right
    return left == right


def pointer_value(document: Any, pointer: str) -> Any:
    if not isinstance(pointer, str) or not pointer.startswith("/") or len(pointer) > 512 or re.search(r"~(?![01])", pointer):
        return MISSING
    value = document
    for raw in pointer.split("/")[1:]:
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            value = value.get(key, MISSING)
        elif isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]{0,8}", key):
            index = int(key)
            value = value[index] if index < len(value) else MISSING
        else:
            return MISSING
    return value


def policy_qualification_failures(qualification: dict, commands: dict, acceptance_ids: set[str]) -> list[str]:
    failures = []
    assertions = qualification["assertions"]
    ids = [item["id"] for item in assertions]
    if len(ids) != len(set(ids)):
        failures.append("qualification assertion IDs must be unique")
    if not any(item["stage"] == "diagnosis" and item["control_pointer"] is not None for item in assertions):
        failures.append("qualification requires a diagnosis assertion with an observed control contrast")
    if not any(item["stage"] == "acceptance" for item in assertions):
        failures.append("qualification requires an original-flow acceptance assertion")
    for item in assertions:
        if not scalar(item["expected"]):
            failures.append(f"qualification {item['id']} expected value must be a resolved finite scalar")
        if item["control_pointer"] == item["artifact_pointer"]:
            failures.append(f"qualification {item['id']} control and observation pointers must differ")
        for command_id in item["command_ids"]:
            command = commands.get(command_id)
            if command is None or command["execution"]["kind"] != "automated-test" or command["execution"]["proof_boundary"] in {"manual", "static-metadata"}:
                failures.append(f"qualification {item['id']} requires known behavioral automated command IDs")
        if item["stage"] == "acceptance" and not set(item["command_ids"]) <= acceptance_ids:
            failures.append(f"qualification {item['id']} acceptance assertions must select configured whole-flow commands")
    for command_id in acceptance_ids:
        if not any(item["stage"] == "acceptance" and command_id in item["command_ids"] for item in assertions):
            failures.append(f"qualification requires an acceptance assertion for {command_id}")
    metrics = qualification["performance"]
    if len({item["id"] for item in metrics}) != len(metrics):
        failures.append("performance metric IDs must be unique")
    for item in metrics:
        if type(item["min_samples"]) is not int or any(not finite_number(item[key]) for key in ("max_regression_percent", "max_spread_percent")):
            failures.append(f"performance {item['id']} budgets require finite numbers and integer sample counts")
        if not scalar(item["unit"]):
            failures.append(f"performance {item['id']} unit must be resolved")
    for value in [*ids, *(item["id"] for item in metrics)]:
        if not scalar(value):
            failures.append("qualification and performance IDs must be resolved")
    return failures


def qualification_failures(record: dict, review: dict, runs: dict, artifacts: dict,
                           *, completion: bool, current_refs: set[str]) -> list[str]:
    assertions = {item["id"]: item for item in review["qualification"]["assertions"]}
    attempts = {item["run_ref"]: item for item in record["attempts"]}
    failures, seen, valid = [], set(), set()
    for observation in record["observations"]:
        key = observation["assertion_id"], observation["run_ref"]
        if key in seen:
            failures.append("qualification observations must be unique per assertion/run")
        seen.add(key)
        assertion, run, attempt = assertions.get(key[0]), runs.get(key[1]), attempts.get(key[1])
        if assertion is None or run is None or attempt is None or key[1] not in current_refs:
            failures.append("qualification observations require known assertions and current selected attempts")
            continue
        purpose = "diagnostic" if assertion["stage"] == "diagnosis" else "acceptance"
        if attempt["purpose"] != purpose or run["command_id"] not in assertion["command_ids"]:
            failures.append(f"qualification {key[0]} is bound to the wrong run purpose or command")
            continue
        actual = pointer_value(artifacts.get(key[1]), assertion["artifact_pointer"])
        if not same_value(actual, assertion["expected"]):
            failures.append(f"qualification {key[0]} observation is missing, unresolved, or differs from its policy expectation")
            continue
        if assertion["control_pointer"] is not None:
            control = pointer_value(artifacts.get(key[1]), assertion["control_pointer"])
            if not scalar(control) or same_value(control, actual):
                failures.append(f"qualification {key[0]} lacks an observed discriminating control contrast")
                continue
        valid.add(key)
    boundaries = {item["id"]: item for item in record["fixture_boundaries"]}
    for assertion_id, ref in valid:
        boundary = boundaries.get(assertions[assertion_id]["boundary"])
        if boundary is None or boundary["state"] != "verified" or ref not in boundary["evidence_refs"]:
            failures.append(f"qualification {assertion_id} must retain its actual run in the verified fixture boundary")
    qualified = record["repair_stage"] in {"qualified-repair", "acceptance"}
    if qualified and any(item["state"] == "unknown" for item in record["fixture_boundaries"]):
        failures.append("qualified repair requires reviewed fixture boundaries; unknown is not verified")
    if completion or record["claim"] == "incident-fixed":
        if record["repair_stage"] != "acceptance":
            failures.append("incident completion requires acceptance stage, not qualification alone")
    diagnosis = record["diagnosis"]
    required_diagnostics = {item["reassessment_ref"] for item in record["attempts"] if item["reassessment_ref"] is not None}
    if qualified:
        if diagnosis is None:
            failures.append("qualified repair requires a selected diagnostic hypothesis/run")
        else:
            required_diagnostics.add(diagnosis["run_ref"])
            attempt = attempts.get(diagnosis["run_ref"])
            if diagnosis["hypothesis_id"] not in {item["id"] for item in record["hypotheses"]} or attempt is None or attempt["purpose"] != "diagnostic" or attempt["hypothesis_id"] != diagnosis["hypothesis_id"] or attempt["failure_class"] in {"test-author", "unverified"}:
                failures.append("qualified repair diagnosis must match its declared diagnostic hypothesis and failure disposition")
    for ref in required_diagnostics:
        run = runs.get(ref)
        applicable = [item for item in assertions.values() if item["stage"] == "diagnosis" and run is not None and run["command_id"] in item["command_ids"]]
        if not any(item["control_pointer"] is not None for item in applicable):
            failures.append(f"diagnostic {ref} requires a policy-selected observed control contrast")
        for item in applicable:
            if (item["id"], ref) not in valid:
                failures.append(f"diagnostic {ref} lacks qualified observation {item['id']}")
    # Each selected acceptance run must retain scenario evidence, including failures.
    for ref, attempt in attempts.items():
        if attempt["purpose"] == "acceptance" and ref in current_refs:
            for item in assertions.values():
                if item["stage"] == "acceptance" and runs.get(ref) is not None and runs[ref]["command_id"] in item["command_ids"] and (item["id"], ref) not in valid:
                    failures.append(f"acceptance {ref} lacks qualified observation {item['id']}")
    return failures


def comparison_failures(record: dict, review: dict, runs: dict, artifacts: dict,
                        *, current_refs: set[str]) -> list[str]:
    metrics = {item["id"]: item for item in review["qualification"]["performance"]}
    failures, seen = [], set()
    for comparison in record["performance_comparisons"]:
        metric_id = comparison["metric_id"]
        if metric_id not in metrics or metric_id in seen:
            failures.append("performance comparisons require unique configured metric IDs")
            continue
        seen.add(metric_id)
        metric = metrics[metric_id]
        baseline_ref, candidate_ref = comparison["baseline"]["run"]["path"], comparison["candidate_run_ref"]
        baseline, candidate = runs.get(baseline_ref), runs.get(candidate_ref)
        if baseline_ref == candidate_ref or baseline is None or candidate is None or candidate_ref not in current_refs:
            failures.append(f"performance {metric_id} requires a bound baseline and distinct current candidate")
            continue
        from repair_review import run_window
        windows = run_window(baseline), run_window(candidate)
        if any(window is None for window in windows) or windows[0] == windows[1] or windows[0][1] > windows[1][0]:
            failures.append(f"performance {metric_id} requires distinct ordered baseline/candidate execution windows")
        try:
            source = logical_path(baseline["result_artifact"]["path"])
            target = logical_path(candidate["result_artifact"]["path"])
            if source == target:
                failures.append(f"performance {metric_id} baseline must retain its own result artifact, not alias the candidate")
        except (KeyError, TypeError, ValueError):
            failures.append(f"performance {metric_id} requires separate canonical result artifact paths")
        if candidate_ref not in {item["run_ref"] for item in record["attempts"]}:
            failures.append(f"performance {metric_id} candidate must be a selected repair attempt")
        if any(run["state"] != "passed" or run["counts"]["executed"] == 0 or run["proof_boundary"] in {"manual", "static-metadata"} for run in (baseline, candidate)):
            failures.append(f"performance {metric_id} requires executed behavioral measurements")
        documents = artifacts.get(baseline_ref), artifacts.get(candidate_ref)
        for pointer in metric["comparability_pointers"]:
            left, right = (pointer_value(document, pointer) for document in documents)
            if not same_value(left, right):
                failures.append(f"performance {metric_id} has missing or incompatible measurement conditions at {pointer}")
        values = []
        for document in documents:
            value = pointer_value(document, metric["artifact_pointer"])
            samples = value.get("samples") if isinstance(value, dict) else None
            if not isinstance(value, dict) or value.get("unit") != metric["unit"] or not isinstance(samples, list) or not metric["min_samples"] <= len(samples) <= 256 or any(not finite_number(sample) or sample < 0 for sample in samples):
                failures.append(f"performance {metric_id} requires comparable units and bounded finite sample arrays")
                break
            measured = [Fraction(str(sample)) for sample in samples]
            middle = median(measured)
            spread = max(measured) - min(measured)
            if spread > middle * Fraction(str(metric["max_spread_percent"])) / 100:
                failures.append(f"performance {metric_id} sample spread exceeds the target policy")
            values.append(middle)
        if len(values) == 2:
            baseline_value, candidate_value = values
            delta = candidate_value - baseline_value if metric["direction"] == "lower-is-better" else baseline_value - candidate_value
            if delta > baseline_value * Fraction(str(metric["max_regression_percent"])) / 100:
                failures.append(f"performance {metric_id} exceeds the configured median regression budget")
    if record["repair_stage"] in {"qualified-repair", "acceptance"} and set(metrics) != seen:
        failures.append("qualified repair requires every policy-selected performance comparison")
    return failures
