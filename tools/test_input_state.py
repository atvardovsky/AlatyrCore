"""Bounded before/after source observations; not a runner or filesystem lock."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any

from path_spec import logical_path, select_paths
from target_validation_support import is_target_relative_path
from test_harness_contract import input_paths, MAX_INPUTS, MAX_FILE_BYTES, MAX_TOTAL_BYTES

DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def valid_observed_map(mapping: Any, paths) -> bool:
    return (isinstance(mapping, dict) and set(mapping) == set(paths)
            and all(isinstance(value, str) and DIGEST.fullmatch(value) for value in mapping.values()))


def selected_inputs(execution: dict, files: list[str]) -> list[str]:
    if (not isinstance(files, list) or len(files) > MAX_INPUTS
            or any(not isinstance(path, str) for path in files)
            or len(files) != len(set(files))):
        raise ValueError("input stability requires bounded unique selected test files")
    for path in files:
        logical_path(path)
        path.encode("utf-8")
        if not is_target_relative_path(path) or "\\" in path or path != PurePosixPath(path).as_posix():
            raise ValueError("selected test inputs must be exact contained target-relative paths")
    if set(select_paths(files, execution["suite_patterns"])) != set(files):
        raise ValueError("selected test inputs are outside canonical suite patterns")
    paths = sorted(set(input_paths(execution)) | set(files))
    if len(paths) > MAX_INPUTS:
        raise ValueError("input-stability scope exceeds 256 exact files")
    return paths


def capture_inputs(view: Any, execution: dict, files: list[str]) -> dict[str, str]:
    result, total = {}, 0
    for path in selected_inputs(execution, files):
        read = view.read_bytes_result(view.target / path, max_bytes=min(MAX_FILE_BYTES, MAX_TOTAL_BYTES - total))
        if read.value is None:
            raise ValueError("input-stability source is missing, escaped or oversized: " + path)
        total += len(read.value)
        result[path] = read.digest
    return result


def stability_failures(view: Any, record: dict, execution: dict, observation: Any) -> list[str]:
    if not isinstance(observation, dict) or set(observation) != {"before", "after"}:
        return ["input stability requires exactly observed before and after maps"]
    try:
        current = capture_inputs(view, execution, record["files"]["selected"])
    except (ValueError, UnicodeError) as exc:
        return [str(exc)]
    for name in ("before", "after"):
        mapping = observation[name]
        if not valid_observed_map(mapping, current):
            return [f"input stability {name} must bind every selected material input to a SHA-256"]
    changed = sorted(path for path in current
                     if observation["before"][path] != observation["after"][path]
                     or observation["after"][path] != current[path]
                     or record["input_sha256"].get(path) != current[path])
    return ["input stability changed or stale: " + ", ".join(changed)] if changed else []


def state_report(view: Any, policy: dict, command: dict, files: list[str], before: Any = None) -> dict:
    execution = command["execution"]
    if execution.get("source_stability") != "required":
        raise ValueError("source stability requires explicit canonical command adoption")
    selected_inputs(execution, files)
    selected = sorted(files)
    inputs = capture_inputs(view, execution, selected)
    digest = view.content_digest(view.target / policy["execution_contract"]["canonical_policy"])
    report = {"schema_version": 1, "record_kind": "target-test-input-state",
              "command_id": command["id"], "policy_sha256": digest,
              "files": selected, "inputs": inputs, "state": "captured", "observation": None,
              "execution_performed": False, "authorization_granted": False, "acceptance_granted": False}
    if before is not None:
        if (not isinstance(before, dict) or set(before) != set(report)
                or type(before.get("schema_version")) is not int or before["schema_version"] != 1
                or before.get("record_kind") != report["record_kind"] or before.get("state") != "captured"
                or before.get("command_id") != command["id"] or before.get("policy_sha256") != digest
                or before.get("files") != selected or before.get("observation") is not None
                or any(before.get(key) is not False for key in ("execution_performed", "authorization_granted", "acceptance_granted"))):
            raise ValueError("before snapshot must be an unchanged command/policy/selection-bound capture")
        if not valid_observed_map(before.get("inputs"), inputs):
            raise ValueError("before snapshot must bind every selected material input to a SHA-256")
        report["observation"] = {"before": before.get("inputs"), "after": inputs}
        failures = stability_failures(view, {"files": {"selected": selected}, "input_sha256": inputs}, execution, report["observation"])
        report["state"] = "changed" if failures else "unchanged"
        report["failures"] = failures
    return report
