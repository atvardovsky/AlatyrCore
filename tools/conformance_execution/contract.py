"""Validate and record provider-neutral conformance executor lifecycle evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAPABILITIES = ROOT / "conformance" / "executors" / "executor-capabilities.json"
LIFECYCLE = ("prepare", "invoke-or-manual-import", "collect", "validate")
TERMINAL_STATES = {"validated", "failed"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def capability_contract(path: Path = CAPABILITIES) -> dict[str, Any]:
    data = load_json(path)
    if data.get("schema_version") != 1:
        raise ValueError("executor capability schema_version must be 1")
    if data.get("contract_kind") != "provider-neutral-conformance-executor-capabilities":
        raise ValueError("executor capability contract_kind is invalid")
    if data.get("lifecycle") != list(LIFECYCLE):
        raise ValueError("executor capability lifecycle is invalid")
    executors = data.get("executors")
    if not isinstance(executors, list) or not executors:
        raise ValueError("executor capability contract must define executors")
    seen: set[str] = set()
    for item in executors:
        if not isinstance(item, dict):
            raise ValueError("executor entries must be objects")
        executor_id = item.get("id")
        if not isinstance(executor_id, str) or not executor_id or executor_id in seen:
            raise ValueError("executor entries must have unique non-empty ids")
        seen.add(executor_id)
        for field in ["provider", "availability"]:
            if not isinstance(item.get(field), str) or not item[field]:
                raise ValueError(f"executor {executor_id} {field} must be non-empty")
        for field in ["supported_surfaces", "execution_modes"]:
            value = item.get(field)
            if not isinstance(value, list) or not value or not all(
                isinstance(entry, str) and entry for entry in value
            ):
                raise ValueError(f"executor {executor_id} {field} must be non-empty strings")
        if item.get("adapter") is not None and not isinstance(item.get("adapter"), str):
            raise ValueError(f"executor {executor_id} adapter must be string or null")
    return data


def executor_capability(executor_id: str, path: Path = CAPABILITIES) -> dict[str, Any]:
    for executor in capability_contract(path)["executors"]:
        if executor["id"] == executor_id:
            return executor
    raise ValueError(f"unknown conformance executor: {executor_id}")


def new_execution_record(
    *,
    executor_id: str,
    assistant_surface: str,
    run_id: str,
    source_commit: str,
    record_kind: str,
    contract_path: Path = CAPABILITIES,
) -> dict[str, Any]:
    executor = executor_capability(executor_id, contract_path)
    if assistant_surface not in executor["supported_surfaces"]:
        raise ValueError(
            f"executor {executor_id} does not support assistant surface {assistant_surface}"
        )
    if not run_id or not source_commit or not record_kind:
        raise ValueError("run_id, source_commit, and record_kind must be non-empty")
    return {
        "schema_version": 1,
        "record_kind": record_kind,
        "status": "prepared",
        "executor": {
            "id": executor_id,
            "provider": executor["provider"],
            "availability": executor["availability"],
            "adapter": executor["adapter"],
        },
        "assistant_surface": assistant_surface,
        "run_id": run_id,
        "source_commit": source_commit,
        "created_at": utc_now(),
        "lifecycle": {
            "prepare": {"status": "completed"},
            "invoke-or-manual-import": {"status": "pending"},
            "collect": {"status": "pending"},
            "validate": {"status": "pending"},
        },
        "reports": [],
        "limitations": [
            "Executor capability is not evidence that the provider runtime, model, or account is currently available."
        ],
    }


def write_execution_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def record_execution(
    record: dict[str, Any], *, mode: str, outcome: str, detail: str
) -> None:
    executor = executor_capability(record["executor"]["id"])
    if mode not in executor["execution_modes"]:
        raise ValueError(f"executor {executor['id']} does not support mode {mode}")
    if outcome not in {"completed", "failed", "skipped"}:
        raise ValueError("execution outcome must be completed, failed, or skipped")
    record["lifecycle"]["invoke-or-manual-import"] = {
        "status": outcome,
        "mode": mode,
        "detail": detail,
    }
    if outcome != "completed":
        record["status"] = "failed"


def collect_reports(record: dict[str, Any], paths: list[Path]) -> None:
    execution = record["lifecycle"]["invoke-or-manual-import"]
    if execution.get("status") != "completed":
        raise ValueError("reports cannot be collected before successful execution or import")
    entries = [str(path) for path in paths]
    if not entries or len(entries) != len(set(entries)):
        raise ValueError("collected report paths must be a non-empty unique list")
    record["reports"] = entries
    record["lifecycle"]["collect"] = {"status": "completed", "report_count": len(entries)}


def record_validation(record: dict[str, Any], *, passed: bool, detail: str) -> None:
    if record["lifecycle"]["collect"].get("status") != "completed":
        raise ValueError("validation cannot run before report collection")
    record["lifecycle"]["validate"] = {
        "status": "completed" if passed else "failed",
        "detail": detail,
    }
    record["status"] = "validated" if passed else "failed"


def validate_execution_record(
    record: dict[str, Any], *, contract_path: Path = CAPABILITIES
) -> list[str]:
    failures: list[str] = []
    try:
        if record.get("schema_version") != 1:
            raise ValueError("execution record schema_version must be 1")
        if not isinstance(record.get("record_kind"), str) or not record["record_kind"]:
            raise ValueError("execution record_kind must be non-empty")
        executor_data = record.get("executor")
        if not isinstance(executor_data, dict):
            raise ValueError("execution record executor must be an object")
        executor = executor_capability(str(executor_data.get("id", "")), contract_path)
        for field in ["provider", "availability", "adapter"]:
            if executor_data.get(field) != executor.get(field):
                raise ValueError(f"execution record executor.{field} drifted")
        if record.get("assistant_surface") not in executor["supported_surfaces"]:
            raise ValueError("execution record assistant surface is unsupported")
        for field in ["run_id", "source_commit", "created_at"]:
            if not isinstance(record.get(field), str) or not record[field]:
                raise ValueError(f"execution record {field} must be non-empty")
        lifecycle = record.get("lifecycle")
        if not isinstance(lifecycle, dict) or set(lifecycle) != set(LIFECYCLE):
            raise ValueError("execution record lifecycle is incomplete")
        if lifecycle["prepare"].get("status") != "completed":
            raise ValueError("execution record prepare must be completed")
        invoke = lifecycle["invoke-or-manual-import"]
        if not isinstance(invoke, dict) or invoke.get("status") not in {
            "pending", "completed", "failed", "skipped"
        }:
            raise ValueError("execution record invocation status is invalid")
        if invoke.get("status") == "completed":
            if invoke.get("mode") not in executor["execution_modes"]:
                raise ValueError("execution record invocation mode is invalid")
            if not isinstance(invoke.get("detail"), str) or not invoke["detail"]:
                raise ValueError("execution record invocation detail is required")
        collect = lifecycle["collect"]
        validate = lifecycle["validate"]
        reports = record.get("reports")
        if not isinstance(reports, list) or not all(
            isinstance(item, str) and item for item in reports
        ):
            raise ValueError("execution record reports must be a string list")
        if collect.get("status") == "completed":
            if not reports or collect.get("report_count") != len(reports):
                raise ValueError("execution record collection does not match reports")
        if validate.get("status") in {"completed", "failed"} and collect.get("status") != "completed":
            raise ValueError("execution record validation requires collected reports")
        if record.get("status") == "validated" and validate.get("status") != "completed":
            raise ValueError("validated execution record requires successful validation")
        if record.get("status") == "failed" and validate.get("status") == "completed":
            raise ValueError("failed execution record cannot report successful validation")
        if record.get("status") not in {"prepared", *TERMINAL_STATES}:
            raise ValueError("execution record status is invalid")
    except (KeyError, TypeError, ValueError) as exc:
        failures.append(str(exc))
    return failures
