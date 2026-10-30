#!/usr/bin/env python3
"""Read bounded worktree prerequisites before task work; not adapter acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path

from adapter_health_views import tooling_comparison
from target_adapter_validation.context import TargetRepositoryView
from task_evidence_contract import task_schema
from target_validation_support import is_target_relative_path
from yaml_support import safe_load
from yaml import YAMLError
from analysis_strategy_contract import MAX_PROBLEM_MODEL_FILE_BYTES, MAX_ACTIVE_PROJECTION_FILE_BYTES

ROOT = Path(__file__).resolve().parents[1]
INDEX = ".ai/assistant/active-tasks.json"


def bound_bytes(view: TargetRepositoryView, binding: dict, *, limit: int = MAX_PROBLEM_MODEL_FILE_BYTES) -> tuple[bytes | None, str]:
    path = binding.get("path")
    if not isinstance(path, str) or not is_target_relative_path(path):
        return None, "unsafe"
    try:
        result = view.read_bytes_result(view.target / path, max_bytes=limit)
    except (OSError, ValueError):
        return None, "unavailable"
    if result.value is None:
        return None, "missing" if result.status.state.value == "missing" else "unavailable"
    if hashlib.sha256(result.value).hexdigest() != binding.get("sha256"):
        return result.value, "conflict"
    return result.value, "bound"


def readiness(target: Path, source: Path | None = None, task_id: str | None = None) -> dict:
    target = target.resolve()
    view = TargetRepositoryView(target)
    issues = []
    source_path = None
    try:
        resolver = runpy.run_path(str(ROOT / "templates/target/.ai/assistant/tools/alatyr_delegate.py"))["resolve_source"]
        source_path = resolver(target, source)
        baseline = tooling_comparison(view, source_path)
        if baseline["state"] != "same-declared-versions":
            issues.append({"code": "WORKTREE_BASELINE", "path": ".ai/alatyr.yaml", "next_action": "assess-upgrade; do not use mismatched source tools for target writes"})
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        baseline = {"state": "unknown"}
        issues.append({"code": "WORKTREE_SOURCE", "path": ".ai/local/framework-source", "next_action": str(exc)})
    state_path = ".ai/assistant/installation-state.json"
    accepted = False
    try:
        manifest = view.read_bytes_result(target / ".ai/alatyr.yaml", max_bytes=512 * 1024)
        data = safe_load(manifest.value.decode("utf-8")) if manifest.value is not None else None
        installation = data.get("installation") if isinstance(data, dict) else None
        route = installation.get("state_record") if isinstance(installation, dict) else None
        if isinstance(route, str) and is_target_relative_path(route):
            state_path = route
            bounded = view.read_bytes_result(target / route, max_bytes=512 * 1024)
            state = view.read_json_result(target / route) if bounded.value is not None else None
            accepted = (installation.get("state") == "accepted" and state is not None and not state.error
                        and isinstance(state.value, dict) and state.value.get("current_state") == "accepted")
    except (OSError, UnicodeError, ValueError, YAMLError):
        pass
    if not accepted:
        issues.append({"code": "WORKTREE_INSTALLATION", "path": state_path, "next_action": "inspect installation state; finish or repair the target update"})
    raw = view.read_bytes_result(target / INDEX, max_bytes=512 * 1024)
    tasks = None
    if raw.value is not None:
        try:
            index = json.loads(raw.value)
            if task_schema("active-task-index").is_valid(index):
                tasks = index["tasks"]
        except (ValueError, UnicodeError, RecursionError):
            pass
    bindings = []
    if tasks is None or len({task["task_id"] for task in tasks}) != len(tasks):
        issues.append({"code": "WORKTREE_TASK_INDEX", "path": INDEX, "next_action": "repair the registered task index"})
    else:
        if task_id is not None and not any(task["task_id"] == task_id for task in tasks):
            issues.append({"code": "WORKTREE_TASK_UNREGISTERED", "path": INDEX, "task_id": task_id, "next_action": "register the selected task explicitly"})
        for task in tasks:
            binding = task["problem_model"]
            if task["state"] != "active" or binding is None:
                continue
            current, runtime_state = bound_bytes(view, binding)
            witness = task.get("analysis_handoff")
            retained = {}
            if isinstance(witness, dict):
                for name in ("model", "projection"):
                    entry = witness[name]
                    raw, status = bound_bytes(view, entry, limit=MAX_PROBLEM_MODEL_FILE_BYTES if name == "model" else MAX_ACTIVE_PROJECTION_FILE_BYTES)
                    valid = (status == "bound" and entry["path"].startswith(f".ai/assistant/task-evidence/{task['task_id']}/")
                             and (name != "model" or entry["sha256"] == binding["sha256"]))
                    if valid:
                        retained[name] = raw
                    else:
                        issues.append({"code": "WORKTREE_HANDOFF_EVIDENCE", "task_id": task["task_id"], "path": entry["path"],
                                       "next_action": "recover exact reviewed handoff evidence; do not restore from missing or conflicting bytes"})
            foreign_retained = runtime_state == "missing" and task_id != task["task_id"] and len(retained) == 2
            present = runtime_state == "bound" or foreign_retained
            item = {"task_id": task["task_id"], "path": binding["path"],
                    "state": "retained-bound" if foreign_retained else "runtime-bound" if present else "recovery-required"}
            bindings.append(item)
            if not present:
                action = ("restore-task from the reviewed analysis_handoff, then recheck" if runtime_state == "missing" and len(retained) == 2
                          else "preserve and reconcile conflicting runtime evidence" if runtime_state == "conflict"
                          else "recover exact original bytes; do not copy a different model or retire the task")
                issues.append({"code": "WORKTREE_TASK_EVIDENCE", **item, "next_action": action})
            raw_model = current if runtime_state == "bound" else retained.get("model")
            if raw_model is None:
                continue
            try:
                model = json.loads(raw_model)
                route = model.get("active_projection") if isinstance(model, dict) else None
                relative = route.get("path") if isinstance(route, dict) else None
                if not isinstance(relative, str) or not is_target_relative_path(relative):
                    raise ValueError("active projection route is unavailable")
                projection = view.read_bytes_result(target / relative, max_bytes=MAX_ACTIVE_PROJECTION_FILE_BYTES)
                expected = witness["projection"]["sha256"] if isinstance(witness, dict) else None
                if projection.value is None:
                    if not foreign_retained:
                        raise ValueError("active runtime projection is unavailable; restore exact handoff bytes or recover original evidence")
                elif expected is not None:
                    if hashlib.sha256(projection.value).hexdigest() != expected:
                        raise ValueError("preserve and reconcile conflicting runtime projection")
                else:
                    value = json.loads(projection.value)
                    source = value.get("source_model") if isinstance(value, dict) else None
                    if not isinstance(source, dict) or source.get("path") != binding["path"] or source.get("sha256") != binding["sha256"]:
                        raise ValueError("active projection source binding differs")
            except (OSError, ValueError, UnicodeError, RecursionError) as exc:
                issues.append({"code": "WORKTREE_TASK_PROJECTION", "task_id": task["task_id"], "path": binding["path"], "next_action": str(exc)})
    return {"schema_version": 1, "report_kind": "alatyr-worktree-readiness",
            "state": "ready-for-context-review" if not issues else "blocked",
            "source": str(source_path) if source_path is not None else None,
            "baseline": baseline, "task_bindings": bindings, "issues": issues,
            "authorization_granted": False, "acceptance_granted": False,
            "limitation": "Prerequisite identities only, not content integrity, semantic readiness, permission or full adapter validation."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--framework-source", type=Path)
    parser.add_argument("--task-id")
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    try:
        report = readiness(args.target, args.framework_source, args.task_id)
        print(json.dumps(report, indent=2))
        return 1 if args.require_ready and report["state"] != "ready-for-context-review" else 0
    except (OSError, ValueError, RecursionError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
