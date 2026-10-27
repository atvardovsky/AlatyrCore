#!/usr/bin/env python3
"""Freeze reviewed closed-task witnesses without publishing runtime session state."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from analysis_strategy_contract import (build_active_problem_model_projection, load_json_object,
    required_obligations_resolved, required_reviews_passed, validate_active_problem_model_projection,
    validate_problem_model, MAX_PROBLEM_MODEL_FILE_BYTES, MAX_ACTIVE_PROJECTION_FILE_BYTES)
from behavior_acceptance import behavior_failures, resolved
from support_write_transaction import SupportTransaction, read_output, support_writer_lock
from target_validation_support import is_target_relative_path, GitEvidenceView
from task_evidence_contract import task_schema
from target_tool_compat import assert_write_compatible

ROOT = Path(__file__).resolve().parents[1]
INDEX = ".ai/assistant/active-tasks.json"


@dataclass(frozen=True)
class EvidencePlan:
    outputs: dict[Path, bytes]
    inputs: dict[Path, bytes | None]


def _object(target: Path, path: str, digest: str | None = None, *, max_bytes: int = 512 * 1024) -> tuple[bytes, dict]:
    if not is_target_relative_path(path):
        raise ValueError("witness input must be a contained target-relative path")
    raw = read_output(target, target / path, max_bytes=max_bytes)
    if raw is None or (digest is not None and hashlib.sha256(raw).hexdigest() != digest):
        raise ValueError(f"missing, oversized or stale witness: {path}")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"witness must contain an object: {path}")
    return raw, value


def prepare(target: Path, task_id: str, retention_review: str) -> EvidencePlan:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", task_id) or task_id in (".", "..") or not resolved(retention_review):
        raise ValueError("task identity and explicit retention-review source must be resolved")
    raw_index, index = _object(target, INDEX)
    errors = list(task_schema("active-task-index").iter_errors(index))
    if errors:
        raise ValueError("invalid active-task index: " + errors[0].message)
    tasks = [task for task in index["tasks"] if task["task_id"] == task_id]
    if len(tasks) != 1 or tasks[0]["state"] != "closed" or not tasks[0]["problem_model"]:
        raise ValueError("archival requires one closed task with a registered model")
    task = tasks[0]
    closure_binding = task["completion_evidence"]
    raw_closure, closure = _object(target, closure_binding["path"], closure_binding["sha256"])
    errors = list(task_schema("task-closure").iter_errors(closure))
    if errors or closure.get("task_id") != task_id or closure.get("operation_id") != task["operation_id"]:
        raise ValueError("closure shape or identity is inconsistent")
    witness = closure.get("analysis_witness")
    if not task["problem_model"]["path"].startswith(".ai/.runtime/problem-models/") or not is_target_relative_path(task["problem_model"]["path"]):
        raise ValueError("registered source model must retain its runtime identity")
    model_binding = witness["model"] if isinstance(witness, dict) else task["problem_model"]
    raw_model, model = _object(target, model_binding["path"], task["problem_model"]["sha256"], max_bytes=MAX_PROBLEM_MODEL_FILE_BYTES)
    version = model.get("schema_version")
    if type(version) is not int or version not in (4, 5, 6, 7):
        raise ValueError("only explicit model schemas 4, 5, 6 and 7 can be retained")
    schema = load_json_object(ROOT / "schemas" / (f"alatyr-problem-model-v{version}.schema.json" if version in (4, 5, 6) else "alatyr-problem-model.schema.json"))
    failures = validate_problem_model(model, schema)
    if failures:
        raise ValueError("invalid model: " + "; ".join(failures))
    if model["operation_id"] != task["operation_id"] or task_id not in model["task_binding"]["task_ids"] or set(task["changed_fact_ids"]) != {fact["id"] for fact in model["changed_facts"]}:
        raise ValueError("model lineage or changed facts differ from the registered task")
    if closure["delivery"]["evidence_finalization"] == "final":
        if not required_obligations_resolved(model) or not required_reviews_passed(model):
            raise ValueError("final closure cannot archive unresolved required evidence")
        if version in (5, 6, 7) and behavior_failures(model, completion=True):
            raise ValueError("final closure cannot archive unresolved behavior or original-case acceptance")
        if version == 7:
            from analysis_evidence import evidence_failures
            if evidence_failures(model, completion=True):
                raise ValueError("final closure cannot archive unresolved analysis evidence")
    projection_binding = witness["projection"] if isinstance(witness, dict) else None
    projection_path = projection_binding["path"] if projection_binding else model["active_projection"]["path"]
    raw_projection, projection = _object(target, projection_path, projection_binding["sha256"] if projection_binding else None, max_bytes=MAX_ACTIVE_PROJECTION_FILE_BYTES)
    projection_source = target / projection_path
    projection_schema = load_json_object(ROOT / "schemas" / ("alatyr-problem-model-active-projection-v3.schema.json" if version == 4 else "alatyr-problem-model-active-projection-v4.schema.json" if version in (5, 6) else "alatyr-problem-model-active-projection.schema.json"))
    expected = build_active_problem_model_projection(model, source_path=task["problem_model"]["path"], source_sha256=hashlib.sha256(raw_model).hexdigest())
    failures = validate_active_problem_model_projection(projection, projection_schema, expected=expected)
    if failures:
        raise ValueError("invalid projection: " + "; ".join(failures))
    destination = Path(".ai/assistant/task-evidence") / task_id / hashlib.sha256(raw_model).hexdigest()
    model_path, projection_path = destination / "model.json", destination / "projection.json"
    git = GitEvidenceView(target)
    if any(git.is_ignored(path.as_posix()) is not False for path in (model_path, projection_path)):
        raise ValueError("durable witness destinations must be retainable by Git")
    closure["analysis_witness"] = {
        "model": {"path": model_path.as_posix(), "sha256": hashlib.sha256(raw_model).hexdigest()},
        "projection": {"path": projection_path.as_posix(), "sha256": hashlib.sha256(raw_projection).hexdigest()},
        "retention_review": retention_review,
    }
    closure_raw = (json.dumps(closure, indent=2) + "\n").encode("utf-8")
    task["completion_evidence"]["sha256"] = hashlib.sha256(closure_raw).hexdigest()
    outputs = {target / model_path: raw_model, target / projection_path: raw_projection,
               target / closure_binding["path"]: closure_raw,
               target / INDEX: (json.dumps(index, indent=2) + "\n").encode("utf-8")}
    inputs = {target / INDEX: raw_index, target / closure_binding["path"]: raw_closure,
              target / model_binding["path"]: raw_model, projection_source: raw_projection}
    for path in (target / model_path, target / projection_path):
        previous = read_output(target, path)
        if previous is not None and previous != outputs[path]:
            raise ValueError("existing immutable witness differs from the retained content")
        inputs[path] = previous
    return EvidencePlan(outputs, inputs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--retention-review", required=True, help="Source of the explicit review permitting retention; never a claim that secrets were detected automatically.")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--migration-staging", action="store_true")
    args = parser.parse_args()
    target = args.target.resolve()
    try:
        if args.write:
            assert_write_compatible(target, tool_name="archive_task_evidence.py", migration_staging=args.migration_staging)
            with support_writer_lock(target):
                plan = prepare(target, args.task_id, args.retention_review)
                transaction = SupportTransaction(target)
                try:
                    transaction.apply(plan.outputs, expected_inputs=plan.inputs)
                except (OSError, ValueError):
                    conflicts = transaction.rollback()
                    if conflicts:
                        print(f"Rollback conflicts preserved: {conflicts}", file=sys.stderr)
                    raise
        else:
            plan = prepare(target, args.task_id, args.retention_review)
        print(json.dumps({"write": args.write, "task_id": args.task_id, "paths": [path.relative_to(target).as_posix() for path in plan.outputs], "limitation": "Retention review is caller supplied; no business approval, secret-free proof or task acceptance is inferred."}, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
