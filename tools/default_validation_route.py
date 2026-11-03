"""Verify an explicitly selected default-route run without executing commands."""

from __future__ import annotations

import hashlib
from typing import Any

from repair_review import run_window
from target_validation_support import is_target_relative_path
from test_execution_contract import TestExecutionContract

CONTRACT = ".ai/assistant/validation-contract.json"
POLICY = ".ai/project/testing/test-first-policy.json"
MANIFEST = ".ai/alatyr.yaml"
LIMIT = 128 * 1024


def validate_default_route(sink: Any, declaration: dict, manifest: Any) -> None:
    """Reuse canonical execution evidence; only the selected task is examined."""
    selected = getattr(sink, "current_task_id", None)
    if selected is None:
        sink.info("DEFAULT_ROUTE_NOT_SELECTED", "default-route execution is not verified without an explicit current task", CONTRACT)
        return
    failures: list[str] = []

    def load(path: str) -> dict | None:
        if not is_target_relative_path(path) or "\\" in path or not sink.is_target_file(path):
            failures.append("default-route evidence requires contained existing files")
            return None
        raw = sink.context.read_bytes_result(sink.target_path(path), max_bytes=LIMIT)
        if raw.value is None:
            failures.append("default-route evidence exceeds its read bound or is unavailable")
            return None
        return sink.load_json_object(sink.target_path(path), "DEFAULT_ROUTE_EVIDENCE")

    run = load(declaration["execution_record"])
    policy = load(POLICY)
    if run is None or policy is None:
        failures.append("default-route execution record or canonical execution policy is unavailable")
    else:
        try:
            contract = TestExecutionContract()
        except (OSError, ValueError) as exc:
            sink.error("DEFAULT_ROUTE_EVIDENCE", "canonical execution schema is unavailable: " + str(exc), CONTRACT)
            return
        failures.extend(contract.policy_failures(policy))
        failures.extend(contract.shape(run, "evidence"))
        if not failures:
            command = next((row for row in policy["commands"] if row["id"] == declaration["command_id"]), None)
            if command is None:
                failures.append("default-route command is absent from the canonical execution policy")
            else:
                failures.extend(contract.evidence_failures(run, command, policy["execution_contract"]))
                if command.get("argv") != declaration["argv"]:
                    failures.append("default-route argv differs from its canonical execution command")
                if run["state"] != "passed" or run["authorization"] != "authorized" or run["availability"] != "available":
                    failures.append("default-route run is not an authorized successful execution")
                if run["command_id"] != declaration["command_id"] or run["policy_sha256"] != sink.context.content_digest(sink.target_path(POLICY)):
                    failures.append("default-route run command or policy binding differs")
                required = set(declaration["input_paths"]) | {CONTRACT, POLICY, MANIFEST} | set(command["execution"]["configuration_paths"])
                artifact = run["result_artifact"]
                if len(run["input_sha256"]) > 128 or not required <= run["input_sha256"].keys():
                    failures.append("default-route run lacks its declared current input inventory")
                elif artifact is None or declaration["execution_record"] in run["input_sha256"] or artifact["path"] in run["input_sha256"]:
                    failures.append("default-route input inventory is missing a result or contains an evidence hash cycle")
                else:
                    for path, digest in run["input_sha256"].items():
                        if not is_target_relative_path(path) or "\\" in path:
                            failures.append("default-route input path is unsafe")
                            continue
                        raw = sink.context.read_bytes_result(sink.target_path(path), max_bytes=LIMIT)
                        if digest is None:
                            # Only a genuinely absent input can bind a missing configuration.
                            matches = not sink.is_target_file(path) and sink.context.status(sink.target_path(path)).state.value == "missing"
                        else:
                            matches = raw.value is not None and hashlib.sha256(raw.value).hexdigest() == digest
                        if not matches:
                            failures.append("default-route input binding is stale or unavailable: " + path)
                    from target_adapter_validation.repair_review import _observation_artifact
                    result = _observation_artifact(sink, run)
                    if result is None:
                        failures.append("default-route observed result is missing or stale")
                    else:
                        expected = {"argv": declaration["argv"], "cwd": ".", "task_id": selected,
                                    "task_class": getattr(sink, "current_task_class", None),
                                    "injected_overrides": False, "exit_code": 0}
                        for field, value in expected.items():
                            if result.get(field) != value or field == "exit_code" and type(result.get(field)) is not int or field == "injected_overrides" and result.get(field) is not False:
                                failures.append("default-route observed " + field + " differs from the declared current invocation")
                        if expected["task_class"] is None or run_window(result) is None:
                            failures.append("default-route observation needs current task class and a bounded execution window")
                        for field, key in (("framework_version", ("framework", "version")), ("framework_source_commit", ("framework", "source_commit"))):
                            binding = manifest.scalars.get(key) if manifest is not None else None
                            if binding is None or not isinstance(result.get(field), str) or result[field] != binding.value:
                                failures.append("default-route selected framework identity differs from the installed baseline")
                        head = sink.git.head_revision()
                        if sink.git.is_ancestor(run["repository_revision"], head) is not True:
                            failures.append("default-route execution revision is unavailable or outside the current lineage")
                        changed = sink.git.changed_files(run["repository_revision"])
                        permitted = set(run["input_sha256"]) | {declaration["execution_record"], artifact["path"]}
                        if changed is None or set(changed) - permitted:
                            failures.append("default-route execution has unbound current changes")
        if contract.view.finalize():
            failures.append("default-route canonical execution schema changed during validation")
    for failure in failures:
        sink.error("DEFAULT_ROUTE_EVIDENCE", failure, CONTRACT)
    if not failures:
        sink.info("DEFAULT_ROUTE_VERIFIED", "selected default invocation has current recorded execution evidence; this is not canonical acceptance or provider authentication", CONTRACT)
