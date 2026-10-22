#!/usr/bin/env python3
"""Plan or transactionally publish one active model, projection, and registration."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from analysis_strategy_contract import (build_active_problem_model_projection, load_json_object,
    validate_problem_model, validate_active_problem_model_projection, MAX_PROBLEM_MODEL_FILE_BYTES,
    MAX_ACTIVE_PROJECTION_FILE_BYTES, PROBLEM_MODEL_RUNTIME_PREFIX)
from support_write_transaction import SupportTransaction, read_output, support_writer_lock
from task_evidence_contract import task_schema, task_model_header_failures, task_predecessor_failures
from target_tool_compat import assert_write_compatible
from target_validation_support import GitEvidenceView, is_target_relative_path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ".ai/assistant/active-tasks.json"


@dataclass(frozen=True)
class TaskPublication:
    outputs: dict[Path, bytes]
    inputs: dict[Path, bytes | None]


def _render(value: dict) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def _portable_identity(path: str) -> str:
    return PurePosixPath(path).as_posix().casefold()


def _object(target: Path, relative: str, limit: int) -> tuple[bytes, dict]:
    if not is_target_relative_path(relative) or "\\" in relative:
        raise ValueError("task inputs must be contained forward-slash target paths")
    raw = read_output(target, target / relative, max_bytes=limit)
    if raw is None:
        raise ValueError(f"task input is missing: {relative}")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError(f"task input must contain an object: {relative}")
    return raw, value


def prepare(target: Path, task_id: str, draft: str, registration: str | None = None) -> TaskPublication:
    if not isinstance(task_id, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", task_id) is None:
        raise ValueError("task ID must be a safe resolved identifier")
    raw_index, index = _object(target, INDEX, 512 * 1024)
    if not task_schema("active-task-index").is_valid(index):
        raise ValueError("active-task index schema is invalid")
    ids = [task["task_id"] for task in index["tasks"]]
    if len(ids) != len(set(ids)):
        raise ValueError("active-task index contains duplicate identities")
    old = next((task for task in index["tasks"] if task["task_id"] == task_id), None)
    if old is not None and old["state"] != "active":
        raise ValueError("closed tasks and retained witnesses are immutable; create a successor task")
    if old is not None and any(task_id in task["predecessor_task_ids"] for task in index["tasks"] if task["task_id"] != task_id):
        raise ValueError("task has registered successors; a coordinated lineage update requires separate review")
    inputs = {target / INDEX: raw_index}
    if registration:
        raw_registration, task = _object(target, registration, 64 * 1024)
        inputs[target / registration] = raw_registration
        if old is not None and any(task.get(key) != old.get(key) for key in ("task_id", "operation_id", "task_class", "predecessor_task_ids", "incident_family_id")):
            raise ValueError("active task identity, class, incident family, and predecessor lineage cannot be replaced")
    elif old is not None:
        task = copy.deepcopy(old)
    else:
        raise ValueError("new task publication requires an explicit registration draft")
    if task.get("task_id") != task_id or task.get("state") != "active" or task.get("completion_evidence") is not None or task.get("task_class") == "small-task":
        raise ValueError("publication requires one active non-small task without completion claims")
    raw_draft, model = _object(target, draft, MAX_PROBLEM_MODEL_FILE_BYTES)
    inputs[target / draft] = raw_draft
    failures = validate_problem_model(model, load_json_object(ROOT / "schemas/alatyr-problem-model.schema.json"))
    if failures:
        raise ValueError("invalid proposed model: " + "; ".join(failures))
    if model["task_binding"]["task_ids"] != [task_id]:
        raise ValueError("single-task publication cannot update shared model bindings")
    model_relpath = f"{PROBLEM_MODEL_RUNTIME_PREFIX}{model['model_id']}.json"
    if old is not None and isinstance(old.get("problem_model"), dict):
        model_relpath = old["problem_model"]["path"]
        if not model_relpath.startswith(PROBLEM_MODEL_RUNTIME_PREFIX) or not model_relpath.endswith(".json") or "\\" in model_relpath or not is_target_relative_path(model_relpath):
            raise ValueError("registered model must retain a safe runtime location")
    # The writer owns the derived binding; validate all caller-owned header fields first.
    task["problem_model"] = {"path": model_relpath, "sha256": "0" * 64}
    if not task_schema("active-task-index").is_valid({"schema_version": 1, "index_kind": "target-active-task-index", "tasks": [task]}):
        raise ValueError("registration draft violates the active-task header schema")
    failures = task_model_header_failures(task, model)
    if failures:
        raise ValueError("task header differs from model: " + "; ".join(message for _, message in failures))
    projection_relpath = model["active_projection"]["path"]
    git = GitEvidenceView(target)
    if any(git.is_ignored(path) is not True or git.is_tracked(path) is not False for path in (model_relpath, projection_relpath, draft)):
        raise ValueError("draft, active model, and projection must be ignored untracked runtime files")
    for other in index["tasks"]:
        binding = other.get("problem_model")
        if other["task_id"] != task_id and isinstance(binding, dict) and _portable_identity(binding["path"]) == _portable_identity(model_relpath):
            raise ValueError("model path is also bound to another task")
    raw_model = _render(model)
    model_sha = hashlib.sha256(raw_model).hexdigest()
    projection = build_active_problem_model_projection(model, source_path=model_relpath, source_sha256=model_sha)
    failures = validate_active_problem_model_projection(projection, load_json_object(ROOT / "schemas/alatyr-problem-model-active-projection.schema.json"), expected=projection)
    if failures:
        raise ValueError("invalid derived projection: " + "; ".join(failures))
    task["problem_model"] = {"path": model_relpath, "sha256": model_sha}
    index["tasks"] = [task if item["task_id"] == task_id else item for item in index["tasks"]]
    if old is None:
        index["tasks"].append(task)
    if not task_schema("active-task-index").is_valid(index):
        raise ValueError("proposed registration violates the active-task index schema")
    graph_failures = task_predecessor_failures(index["tasks"])
    if graph_failures:
        raise ValueError("invalid task predecessor graph: " + "; ".join(graph_failures))
    outputs = {target / model_relpath: raw_model, target / projection_relpath: _render(projection), target / INDEX: _render(index)}
    published = {_portable_identity(path) for path in (model_relpath, projection_relpath, INDEX)}
    if _portable_identity(draft) in published or registration is not None and _portable_identity(registration) in published:
        raise ValueError("authoring drafts must be separate from published outputs")
    for path, limit in ((target / model_relpath, MAX_PROBLEM_MODEL_FILE_BYTES), (target / projection_relpath, MAX_ACTIVE_PROJECTION_FILE_BYTES)):
        inputs[path] = read_output(target, path, max_bytes=limit)
    prior_projection = inputs[target / projection_relpath]
    if prior_projection is not None:
        previous_projection = json.loads(prior_projection)
        source = previous_projection.get("source_model") if isinstance(previous_projection, dict) else None
        if not isinstance(source, dict) or not isinstance(source.get("path"), str) or previous_projection.get("model_id") != model["model_id"] or _portable_identity(source["path"]) != _portable_identity(model_relpath):
            raise ValueError("existing projection belongs to another model or has unresolved ownership")
    if old is not None and isinstance(old.get("problem_model"), dict) and (inputs[target / model_relpath] is None or hashlib.sha256(inputs[target / model_relpath]).hexdigest() != old["problem_model"]["sha256"]):
        raise ValueError("registered model changed outside its digest binding; reconcile the conflict before publication")
    if old is not None and isinstance(old.get("problem_model"), dict):
        previous = json.loads(inputs[target / model_relpath])
        if not isinstance(previous, dict) or previous.get("model_id") != model["model_id"]:
            raise ValueError("changing a registered model identity requires an explicit successor task")
        if not isinstance(previous.get("proof_obligations"), list) or any(not isinstance(item, dict) for item in previous["proof_obligations"]):
            raise ValueError("registered proof obligations are malformed; reconcile before publication")
        required_review = lambda value: any(item.get("id") == "repair-evidence-review" and item.get("required") is True for item in value.get("proof_obligations", []))
        if required_review(previous) and not required_review(model):
            raise ValueError("a captured repair-evidence-review obligation cannot be removed or downgraded")
    return TaskPublication(outputs, inputs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--draft", required=True, help="Ignored target-relative JSON authoring draft; never a completion receipt.")
    parser.add_argument("--registration", help="Target-relative active registration draft, required for a new task.")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    target = args.target.resolve()
    try:
        if args.write:
            assert_write_compatible(target, tool_name="publish_active_task.py")
            with support_writer_lock(target):
                plan = prepare(target, args.task_id, args.draft, args.registration)
                transaction = SupportTransaction(target)
                try:
                    transaction.apply(plan.outputs, expected_inputs=plan.inputs)
                except Exception:
                    conflicts = transaction.rollback()
                    if conflicts:
                        print(f"Rollback conflicts preserved: {conflicts}", file=sys.stderr)
                    raise
        else:
            plan = prepare(target, args.task_id, args.draft, args.registration)
        print(json.dumps({"write": args.write, "task_id": args.task_id, "acceptance_granted": False,
            "changed_paths": [path.relative_to(target).as_posix() for path, value in plan.outputs.items() if value != plan.inputs.get(path)]}, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
