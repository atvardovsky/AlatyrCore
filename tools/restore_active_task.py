#!/usr/bin/env python3
"""Restore exact reviewed active-task bytes, never reconstruct missing evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from analysis_strategy_contract import (MAX_PROBLEM_MODEL_FILE_BYTES,
    MAX_ACTIVE_PROJECTION_FILE_BYTES, build_active_problem_model_projection,
    load_json_object, validate_problem_model, validate_active_problem_model_projection)
from publish_active_task import TaskPublication, _object, INDEX, ROOT
from support_write_transaction import SupportTransaction, read_output, support_writer_lock
from target_tool_compat import assert_write_compatible
from target_validation_support import GitEvidenceView, is_target_relative_path
from task_evidence_contract import task_schema, task_model_header_failures
from target_adapter_validation.values import is_resolved_string


def prepare(target: Path, task_id: str) -> TaskPublication:
    if not isinstance(task_id, str) or re.fullmatch(r"[A-Za-z0-9._-]+", task_id) is None or task_id in (".", ".."):
        raise ValueError("restore requires a safe task identity")
    raw_index, index = _object(target, INDEX, 512 * 1024)
    if not task_schema("active-task-index").is_valid(index):
        raise ValueError("invalid active-task index")
    tasks = [task for task in index["tasks"] if task["task_id"] == task_id]
    if len(tasks) != 1 or tasks[0]["state"] != "active":
        raise ValueError("restore requires one active registered task")
    task = tasks[0]
    witness, binding = task.get("analysis_handoff"), task.get("problem_model")
    if not isinstance(witness, dict) or not isinstance(binding, dict):
        raise ValueError("no reviewed active handoff; recover the exact original evidence or create an explicit successor")
    if not is_resolved_string(witness["retention_review"]):
        raise ValueError("active handoff requires a resolved retention-review source")
    if witness["model"]["sha256"] != binding["sha256"]:
        raise ValueError("handoff does not match the registered runtime digest")
    inputs = {target / INDEX: raw_index}
    values = {}
    git = GitEvidenceView(target)
    prefix = f".ai/assistant/task-evidence/{task_id}/"
    for name, limit in (("model", MAX_PROBLEM_MODEL_FILE_BYTES), ("projection", MAX_ACTIVE_PROJECTION_FILE_BYTES)):
        item = witness[name]
        relative = item["path"]
        if not relative.startswith(prefix) or git.is_ignored(relative) is not False:
            raise ValueError("handoff must be retainable within its task evidence directory")
        raw, value = _object(target, relative, limit)
        if hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise ValueError(f"{name} handoff digest differs")
        inputs[target / relative] = raw
        values[name] = (raw, value)
    raw_model, model = values["model"]
    failures = validate_problem_model(model, load_json_object(ROOT / "schemas/alatyr-problem-model.schema.json"))
    if not failures:
        from analysis_evidence import active_retention_failures
        failures += active_retention_failures(model, git.is_ignored)
        failures += [message for _, message in task_model_header_failures(task, model)]
    if failures:
        raise ValueError("invalid active handoff: " + "; ".join(failures))
    expected = build_active_problem_model_projection(model, source_path=binding["path"], source_sha256=binding["sha256"])
    failures = validate_active_problem_model_projection(values["projection"][1],
        load_json_object(ROOT / "schemas/alatyr-problem-model-active-projection.schema.json"), expected=expected)
    if failures:
        raise ValueError("invalid handoff projection: " + "; ".join(failures))
    outputs = {}
    for name, relative, prefix in (("model", binding["path"], ".ai/.runtime/problem-models/"),
                                   ("projection", model["active_projection"]["path"], ".ai/.runtime/problem-model-projections/")):
        if not is_target_relative_path(relative) or "\\" in relative or not relative.startswith(prefix) or not relative.endswith(".json"):
            raise ValueError("restore destinations must retain canonical runtime locations")
        if git.is_ignored(relative) is not True or git.is_tracked(relative) is not False:
            raise ValueError("restore destinations must be ignored untracked runtime files")
        path = target / relative
        previous = read_output(target, path, max_bytes=MAX_PROBLEM_MODEL_FILE_BYTES)
        if previous is not None and previous != values[name][0]:
            raise ValueError(f"conflicting runtime postimage preserved: {relative}")
        inputs[path] = previous
        outputs[path] = values[name][0]
    return TaskPublication(outputs, inputs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    target = args.target.resolve()
    try:
        if args.write:
            assert_write_compatible(target, tool_name="restore_active_task.py")
            with support_writer_lock(target):
                plan = prepare(target, args.task_id)
                transaction = SupportTransaction(target)
                try:
                    transaction.apply(plan.outputs, expected_inputs=plan.inputs)
                except Exception:
                    conflicts = transaction.rollback()
                    if conflicts:
                        print(f"Rollback conflicts preserved: {conflicts}", file=sys.stderr)
                    raise
        else:
            plan = prepare(target, args.task_id)
        print(json.dumps({"write": args.write, "task_id": args.task_id,
            "changed_paths": [path.relative_to(target).as_posix() for path in plan.outputs if plan.outputs[path] != plan.inputs[path]],
            "acceptance_granted": False, "authorization_granted": False,
            "next_action": "rehydrate current authorization, owners and evidence freshness before continuing"}, indent=2))
        return 0
    except (OSError, ValueError, RecursionError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
