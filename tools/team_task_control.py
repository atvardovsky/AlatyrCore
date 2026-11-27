"""Bounded team-record discovery and shared hold decisions, not authority."""

from __future__ import annotations

import os
import json
from pathlib import Path

from cli_inputs import json_object
from path_spec import logical_path

TASKS = ".ai/assistant/team/tasks"
REGISTRY = ".ai/assistant/team/work-registry.json"
INDEX_NAME = "context-index.json"
MAX_RECORDS = 128
MAX_BYTES = 8 * 1024 * 1024
RUNNABLE_STATES = frozenset({
    "proposed", "planned", "assigned", "ready", "pending", "todo", "backlog",
    "claimed", "active", "in_progress", "implementing", "started", "review", "in_review",
    "reviewing", "awaiting_review", "merge-ready", "done", "complete", "completed", "reviewed", "frozen",
})


def is_task_file(name: str) -> bool:
    return name.endswith(".json") and name != INDEX_NAME


def execution_hold(record: dict) -> str | None:
    status = record.get("status")
    if not isinstance(status, str) or status.strip().lower() not in RUNNABLE_STATES:
        return "task-not-runnable"
    blockers = record.get("blockers", [])
    if not isinstance(blockers, list) or blockers:
        return "task-blockers-present"
    return None


def read_team_tasks(view) -> dict[str, tuple[str, dict]]:
    """Read authoritative task records only when team storage is present."""
    registry_path = view.target / REGISTRY
    directory = view.target / TASKS
    manifest_path = view.target / ".ai/alatyr.yaml"
    manifest = view.read_bytes_result(manifest_path, max_bytes=512 * 1024, aggregate_max_bytes=MAX_BYTES)
    if manifest.value is not None:
        from yaml import YAMLError
        from yaml_support import safe_load
        try:
            data = safe_load(manifest.value.decode("utf-8"))
        except YAMLError as exc:
            raise ValueError("team task routing manifest is invalid") from exc
        team = data.get("team_collaboration") if isinstance(data, dict) else None
        if isinstance(team, dict):
            registry = team.get("work_registry", REGISTRY)
            if isinstance(registry, str) and not registry.startswith("{"):
                registry_path = view.target / logical_path(registry)
            tasks = team.get("task_records_directory", TASKS)
            if isinstance(tasks, str) and not tasks.startswith("{"):
                directory = view.target / logical_path(tasks)
    elif manifest.status.exists:
        raise ValueError("team task routing manifest is unreadable or oversized")
    if view.target_exists(registry_path):
        result = view.read_bytes_result(registry_path, max_bytes=512 * 1024)
        if result.value is None:
            raise ValueError("team registry is unreadable or oversized")
        registry = json_object(result.value, "team registry")
        if registry.get("schema_version") != 2:
            raise ValueError("team records require the current repository registry")
        if "task_records_directory" in registry:
            selected = view.target / logical_path(registry["task_records_directory"])
            if directory != view.target / TASKS and selected != directory:
                raise ValueError("manifest and registry disagree on task storage")
            directory = selected
        if not directory.is_dir() and registry.get("module_state") not in ("disabled", "deferred", "not-applicable"):
            raise ValueError("registered team task directory is unavailable")
    if directory.resolve() != directory:
        raise ValueError("team task directory must not be a symlink")
    if not view.target_exists(directory):
        return {}
    if not view.is_target_dir(directory):
        raise ValueError("team task storage is not a directory")
    records, remaining = {}, MAX_BYTES
    with os.scandir(directory) as entries:
        paths = []
        for entry in entries:
            if is_task_file(entry.name):
                paths.append(directory / entry.name)
                if len(paths) > MAX_RECORDS:
                    raise ValueError("team inventory exceeds 128 records; resolve the registry")
    for path in sorted(paths):
        if remaining <= 0 or path.is_symlink():
            raise ValueError("team task inventory is aliased or exceeds its byte limit")
        read = view.read_bytes_result(path, max_bytes=min(1024 * 1024, remaining), aggregate_max_bytes=MAX_BYTES)
        if read.value is None:
            raise ValueError("team task is unreadable or oversized: " + path.name)
        remaining -= len(read.value)
        record = json_object(read.value, path.name)
        identity = record.get("id")
        if not isinstance(identity, str) or not identity.strip() or len(identity) > 128 or identity in records:
            raise ValueError("missing or duplicate team task identity: " + path.name)
        records[identity] = (path.relative_to(view.target).as_posix(), record)
    return records


def task_holds(view, task_ids) -> dict[str, str]:
    records = read_team_tasks(view)
    return {task_id: reason for task_id in task_ids if task_id in records
            and (reason := execution_hold(records[task_id][1])) is not None}


def takeover_tasks(records, task_id: str, *, limit: int = 16) -> list[dict]:
    """Review only the selected task and its bounded dependency closure."""
    queue, seen, result = [task_id], set(), []
    for identity in queue:
        if identity in seen:
            continue
        if len(seen) >= limit:
            raise ValueError("takeover dependency scope exceeds 16 tasks; decompose it")
        seen.add(identity)
        if identity not in records:
            if identity != task_id:
                result.append({"task_id": identity, "status": "unresolved", "hold": "dependency-record-unavailable",
                               "next_action": "identify the canonical dependency record with the owner before resuming"})
            continue
        path, record = records[identity]
        dependencies = record.get("dependencies", [])
        if not isinstance(dependencies, list) or len(dependencies) > limit or any(not isinstance(item, str) or not item or len(item) > 128 for item in dependencies):
            raise ValueError("takeover dependencies must be a bounded task ID list")
        queue.extend(dependencies)
        hold = execution_hold(record)
        if hold is None and identity != task_id and str(record.get("status")).strip().lower() not in {
                "complete", "completed", "done", "frozen", "reviewed", "merge-ready"}:
            hold = "dependency-not-complete"
        blockers = record.get("blockers", [])
        result.append({"task_id": identity, "record": path, "status": str(record.get("status"))[:40],
                       "hold": hold, "dependencies": dependencies,
                       "goal": str(record.get("goal", ""))[:300] if identity == task_id else "",
                       "blocker_count": len(blockers) if isinstance(blockers, list) else None,
                       "blockers": [str(item)[:240] for item in blockers[:2]] if isinstance(blockers, list) else [],
                       "next_action": ("resolve the listed hold with the owner before resuming"
                                       if hold else str(record.get("next_action", ""))[:300])})
    edges = {row["task_id"]: row.get("dependencies", []) for row in result}
    active, checked = set(), set()
    def visit(identity):
        if identity in active:
            raise ValueError("takeover dependency cycle")
        if identity in checked:
            return
        active.add(identity)
        for dependency in edges.get(identity, []):
            visit(dependency)
        active.remove(identity)
        checked.add(identity)
    visit(task_id)
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > 16 * 1024:
        raise ValueError("takeover view exceeds 16 KiB; decompose dependencies and consult exact record paths")
    return result
