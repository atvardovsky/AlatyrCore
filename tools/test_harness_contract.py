"""Opt-in material harness identity and honest test-case accounting."""

from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
from typing import Any

from path_spec import logical_path
from repair_qualification import pointer_value
from target_validation_support import is_target_relative_path

MAX_INPUTS = 256
MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 8 * MAX_FILE_BYTES
COUNT_KEYS = {"discovered", "executed", "passed", "failed", "skipped", "not_run"}


def input_paths(execution: dict) -> list[str]:
    values = execution.get("harness_inputs")
    if not isinstance(values, list) or not 1 <= len(values) <= 64 or any(not isinstance(path, str) for path in values):
        raise ValueError("harness_inputs requires 1..64 unique exact material paths")
    if len(set(values)) != len(values):
        raise ValueError("harness_inputs contains duplicate paths")
    paths = sorted(set(values) | set(execution["configuration_paths"]))
    if len(paths) > MAX_INPUTS:
        raise ValueError("material harness/configuration union exceeds 256 files")
    for path in paths:
        logical_path(path)
        path.encode("utf-8")
        if not is_target_relative_path(path) or "\\" in path or path != PurePosixPath(path).as_posix():
            raise ValueError("harness inputs must be exact contained target-relative paths")
    return paths


def harness_digest(view: Any, record: dict, execution: dict, policy_path: str) -> str:
    """Re-read bound material bytes, not an unverified record hash assertion."""
    policy = view.read_bytes_result(view.target / policy_path, max_bytes=512 * 1024)
    if policy.value is None or policy.digest != record["policy_sha256"]:
        raise ValueError("harness identity requires the current canonical policy hash")
    pairs, total = [], 0
    for path in input_paths(execution):
        read = view.read_bytes_result(view.target / path, max_bytes=min(MAX_FILE_BYTES, MAX_TOTAL_BYTES - total))
        if read.value is None or read.digest != record["input_sha256"].get(path):
            raise ValueError("harness material input is missing, oversized, escaped or stale: " + path)
        total += len(read.value)
        pairs.append([path, read.digest])
    payload = ["alatyr-harness-inputs-v1", record["policy_sha256"], record["command_id"], pairs]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()


def accounting_failures(value: Any, record: dict) -> list[str]:
    if not isinstance(value, dict) or set(value) != {"behavioral", "supporting"}:
        return ["case accounting requires exactly behavioral and supporting partitions"]
    for name, counts in value.items():
        if (not isinstance(counts, dict) or not COUNT_KEYS - {"not_run"} <= set(counts)
                or set(counts) - COUNT_KEYS or any(type(n) is not int or n < 0 for n in counts.values())):
            return [name + " accounting requires nonnegative integer counters"]
        if (counts["executed"] != counts["passed"] + counts["failed"]
                or counts["discovered"] != counts["executed"] + counts["skipped"] + counts.get("not_run", 0)):
            return [name + " accounting does not conserve its cases"]
    if any(sum(counts.get(key, 0) for counts in value.values()) != record["counts"].get(key, 0) for key in COUNT_KEYS):
        return ["behavioral/supporting accounting differs from aggregate evidence counts"]
    if record["claim"] in {"focused", "suite", "full"} and value["behavioral"]["executed"] == 0:
        return ["behavioral completion cannot be established by supporting/setup/no-op cases alone"]
    return []


def observation_failures(view: Any, record: dict, execution: dict, artifact: Any, policy_path: str) -> list[str]:
    failures = []
    try:
        if "harness_inputs" in execution:
            binding = record["harness_identity"]
            expected = harness_digest(view, record, execution, policy_path)
            observed = pointer_value(artifact, binding["observations_pointer"])
            if observed != expected or binding["sha256"] != expected:
                failures.append("observed harness identity differs from current material inputs")
        if execution.get("behavioral_accounting") == "required":
            binding = record["case_accounting"]
            failures.extend(accounting_failures(pointer_value(artifact, binding["observations_pointer"]), record))
    except (KeyError, ValueError, UnicodeError, RecursionError) as exc:
        failures.append("harness/accounting evidence: " + str(exc))
    return failures
