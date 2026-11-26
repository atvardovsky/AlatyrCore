"""Opt-in material harness identity and honest test-case accounting."""

from __future__ import annotations

import hashlib
import json
import re
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


def runtime_build_failures(view: Any, value: dict, record: dict, execution: dict, expected: str) -> list[str]:
    from test_selection import read_selection_json

    try:
        if set(value) != {"kind", "harness_sha256", "build", "observed_build_id", "resources"} or value["kind"] != "alatyr-runtime-harness-v1":
            raise ValueError("unsupported runtime harness observation")
        if value["harness_sha256"] != expected or execution.get("source_stability") != "required":
            raise ValueError("runtime evidence needs the current harness digest and adopted source stability")
        resources = record["resources"]
        if value["resources"] != resources or not {"service", "port"} <= {r["kind"] for r in resources if r["access"] != "read"}:
            raise ValueError("observed runtime resources must match declared writable service and port claims")
        binding = value["build"]
        if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
            raise ValueError("runtime build binding must contain a path and digest")
        path, digest = logical_path(binding["path"]), binding["sha256"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("runtime build receipt requires an exact SHA-256")
        material = set(input_paths(execution))
        result_path = record["result_artifact"]["path"]
        if path in material or path == result_path:
            raise ValueError("build receipt must be distinct from source inputs and the test result")
        if (view.target / path).resolve() != view.target / path:
            raise ValueError("build receipt must not traverse a symlink")
        receipt = read_selection_json(view, path, digest)
        if (not isinstance(receipt, dict)
                or set(receipt) != {"record_kind", "repository_revision", "build_id", "inputs", "artifact"}
                or receipt["record_kind"] != "target-qualified-build"
                or receipt["repository_revision"] != record["repository_revision"]):
            raise ValueError("build receipt has no exact matching execution revision")
        identity = receipt["build_id"]
        if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", identity) or value["observed_build_id"] != identity:
            raise ValueError("served build identity differs from the qualified build")
        artifact = receipt["artifact"]
        if not isinstance(artifact, dict) or set(artifact) != {"path", "sha256"}:
            raise ValueError("build artifact needs a digest-bound material manifest")
        artifact_path = logical_path(artifact["path"])
        if (artifact_path in material | {path, result_path}
                or receipt["inputs"] != {p: record["input_sha256"].get(p) for p in material}):
            raise ValueError("build receipt must bind its distinct artifact manifest and all material harness inputs")
        candidate = view.target / artifact_path
        if candidate.resolve() != candidate:
            raise ValueError("build artifact manifest must not traverse a symlink")
        read = view.read_bytes_result(candidate, max_bytes=MAX_FILE_BYTES)
        if read.value is None or read.digest != artifact["sha256"]:
            raise ValueError("qualified build artifact manifest is missing, oversized or changed")
    except (KeyError, TypeError, ValueError, OSError, UnicodeError, RuntimeError) as exc:
        return [str(exc)]
    return []


def observation_failures(view: Any, record: dict, execution: dict, artifact: Any, policy_path: str) -> list[str]:
    failures = []
    try:
        executed = record["counts"]["executed"] > 0
        if "harness_inputs" in execution and (executed or "harness_identity" in record):
            binding = record["harness_identity"]
            expected = harness_digest(view, record, execution, policy_path)
            observed = pointer_value(artifact, binding["observations_pointer"])
            if binding["sha256"] != expected:
                failures.append("observed harness identity differs from current material inputs")
            elif isinstance(observed, dict):
                failures.extend(runtime_build_failures(view, observed, record, execution, expected))
            elif observed != expected:
                failures.append("observed harness identity differs from current material inputs")
        if execution.get("behavioral_accounting") == "required" and (executed or "case_accounting" in record):
            binding = record["case_accounting"]
            failures.extend(accounting_failures(pointer_value(artifact, binding["observations_pointer"]), record))
    except (KeyError, ValueError, UnicodeError, RecursionError) as exc:
        failures.append("harness/accounting evidence: " + str(exc))
    return failures
