"""Exact test-request conservation over target-produced observations."""

from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
from typing import Any

from repair_qualification import pointer_value
from path_spec import logical_path
from target_validation_support import is_target_relative_path, is_unresolved_value

MAX_FILES = 256
MAX_CASES = 4096
MAX_BYTES = 512 * 1024
STATUSES = {"discovered", "passed", "failed", "skipped", "not-run"}


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 1024 or is_unresolved_value(value):
        raise ValueError(label + " must be resolved bounded text")
    return value


def _files(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_FILES:
        raise ValueError(f"{label} requires at most {MAX_FILES} files")
    result = [_text(item, label) for item in value]
    for path in result:
        logical_path(path, pattern=True)
    if len(set(result)) != len(result) or any(not is_target_relative_path(path) or "\\" in path or path != PurePosixPath(path).as_posix() for path in result):
        raise ValueError(label + " contains duplicate or unsafe paths")
    return result


def _cases(value: Any, *, observations: bool) -> dict[tuple[str, str], str]:
    if not isinstance(value, list) or len(value) > MAX_CASES:
        raise ValueError(f"cases requires at most {MAX_CASES} exact case identities")
    result = {}
    fields = {"file", "id", "status"} if observations else {"file", "id"}
    for row in value:
        if not isinstance(row, dict) or set(row) != fields:
            raise ValueError("case requires exact file/id and observed status fields")
        file, identity = _text(row["file"], "case file"), _text(row["id"], "case ID")
        logical_path(file, pattern=True)
        if not is_target_relative_path(file) or "\\" in file or file != PurePosixPath(file).as_posix() or (file, identity) in result:
            raise ValueError("case identity is duplicated or its file is unsafe")
        status = row["status"] if observations else "requested"
        if observations and (not isinstance(status, str) or status not in STATUSES):
            raise ValueError("case status must be a supported observed string")
        result[(file, identity)] = status
    return result


def selection_report(request: Any, observations: Any, *, command_id: str,
                     phase: str = "discovery", require_success: bool = False,
                     record: dict | None = None, existing_files: set[str] | None = None) -> dict:
    result = {"state": "blocked", "failures": [], "missing_files": [], "missing_cases": [],
              "authorization_granted": False, "execution_performed": False}
    failures = result["failures"]
    try:
        if not isinstance(phase, str) or phase not in {"discovery", "execution"}:
            raise ValueError("selection phase must be discovery or execution")
        for value, kind, fields in ((request, "target-test-selection-request", {"files", "cases"}),
                                    (observations, "target-test-selection-observation", {"discovered_files", "executed_files", "cases"})):
            if not isinstance(value, dict) or set(value) != {"schema_version", "record_kind", "command_id", *fields}:
                raise ValueError("selection artifact has missing or unknown fields")
            if type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["record_kind"] != kind:
                raise ValueError("selection artifact kind/version is invalid")
            if value["command_id"] != command_id or not isinstance(value["command_id"], str):
                raise ValueError("selection artifact differs from the canonical command ID")
        requested = set(_files(request["files"], "requested files"))
        discovered = set(_files(observations["discovered_files"], "discovered files"))
        executed = set(_files(observations["executed_files"], "executed files"))
        wanted = _cases(request["cases"], observations=False)
        cases = _cases(observations["cases"], observations=True)
        if not requested:
            raise ValueError("selection request must name at least one test file")
        if any(file not in requested for file, _ in wanted) or any(file not in discovered for file, _ in cases):
            raise ValueError("case files must belong to their requested/discovered inventories")
        if not executed <= discovered or any(file not in executed for (file, _), status in cases.items() if status in {"passed", "failed"}):
            raise ValueError("executed cases/files are absent from the observed inventory")
        result["missing_files"] = sorted(requested - discovered)
        result["missing_cases"] = [{"file": file, "id": identity} for file, identity in sorted(wanted.keys() - cases.keys())]
        if result["missing_files"] or result["missing_cases"]:
            failures.append("requested test files or exact case IDs were not discovered")
        if existing_files is not None and not discovered <= existing_files:
            failures.append("observed discovery contains missing, non-file or escaped target paths")
        if phase == "execution" and record is not None:
            if requested != set(record["files"]["selected"]) or executed != set(record["files"]["executed"]):
                failures.append("request/observations differ from the selected and executed evidence files")
            counts = {"discovered": len(cases), "executed": sum(status in {"passed", "failed"} for status in cases.values()),
                      "passed": sum(status == "passed" for status in cases.values()), "failed": sum(status == "failed" for status in cases.values()),
                      "skipped": sum(status == "skipped" for status in cases.values()), "not_run": sum(status in {"not-run", "discovered"} for status in cases.values())}
            if any(record["counts"].get(key, 0) != value for key, value in counts.items()):
                failures.append("observed case identities do not conserve the evidence counts")
        if require_success:
            narrowed = {file for file, _ in wanted}
            expected = set(wanted) | {key for key in cases if key[0] in requested - narrowed}
            represented = {file for file, _ in cases}
            if not requested <= executed or not requested <= represented or not expected or any(cases.get(key) != "passed" for key in expected):
                failures.append("requested test scope has not completely passed")
    except ValueError as exc:
        failures.append(str(exc))
    result["state"] = "selection-consistent" if not failures else "blocked"
    result["limitation"] = "Exact target-produced identities, not runner-syntax parsing, harness authenticity, domain fidelity or execution permission. Missing selectors must not be omitted while normalizing the request."
    return result


def _unique(pairs: list[tuple[str, Any]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("selection JSON contains duplicate members")
        value[key] = item
    return value


def _constant(value: str) -> None:
    raise ValueError("selection JSON contains a non-finite constant: " + value)


def read_selection_json(view: Any, path: str, digest: str | None = None) -> Any:
    if not isinstance(path, str) or not is_target_relative_path(path):
        raise ValueError("selection artifact must have a contained target-relative path")
    result = view.read_bytes_result(view.target / path, max_bytes=MAX_BYTES)
    if result.value is None or (digest is not None and hashlib.sha256(result.value).hexdigest() != digest):
        raise ValueError("selection artifact is missing, escaped, oversized or stale")
    return json.loads(result.value, object_pairs_hook=_unique, parse_constant=_constant)


def observed_selection(view: Any, request: Any, observations: Any, *, command_id: str,
                       phase: str = "discovery", record: dict | None = None) -> dict:
    initial = selection_report(request, observations, command_id=command_id)
    if initial["failures"]:
        return initial
    discovered = observations["discovered_files"]
    existing = {path for path in discovered if view.status(view.target / path).is_file}
    return selection_report(request, observations, command_id=command_id, phase=phase,
                            require_success=record is not None and record["claim"] in {"focused", "suite", "full"},
                            record=record, existing_files=existing)


def selected_execution_failures(view: Any, record: dict, *, artifact: Any) -> list[str]:
    binding = record.get("selection_evidence")
    if binding is None:
        return ["required selection evidence is missing"]
    try:
        request_ref = binding["request"]
        request = read_selection_json(view, request_ref["path"], request_ref["sha256"])
        observations = pointer_value(artifact, binding["observations_pointer"])
        return observed_selection(view, request, observations, command_id=record["command_id"], phase="execution", record=record)["failures"]
    except (ValueError, UnicodeError, RecursionError) as exc:
        return [str(exc)]
