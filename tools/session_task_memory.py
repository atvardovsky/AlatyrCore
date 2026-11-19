"""Read-only check that stale session tasks still have durable task memory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from target_adapter_validation.context import TargetRepositoryView
from target_validation_support import is_target_relative_path


ACTIVE_TASKS = ".ai/assistant/active-tasks.json"
TEAM_WORK = ".ai/assistant/team/work-registry.json"
MAX_BYTES = 512 * 1024


def _read_object(view: TargetRepositoryView, relpath: str) -> tuple[dict[str, Any] | None, str]:
    result = view.read_bytes_result(view.target / relpath, max_bytes=MAX_BYTES)
    if result.value is None:
        return None, "missing"
    try:
        value = json.loads(result.value)
    except (UnicodeError, ValueError, RecursionError):
        return None, "invalid"
    if not isinstance(value, dict):
        return None, "invalid"
    return value, "current"


def _task_ids(value: dict[str, Any] | None, key: str) -> set[str]:
    if not isinstance(value, dict):
        return set()
    records = value.get(key)
    if not isinstance(records, list):
        return set()
    return {
        record["task_id"]
        for record in records
        if isinstance(record, dict) and isinstance(record.get("task_id"), str)
    }


def task_memory(
    target: Path,
    sessions: list[dict[str, Any]],
    *,
    source_contour: bool = False,
) -> dict[str, Any]:
    """Report stale same-worktree sessions whose task lacks durable registration."""

    if source_contour:
        return {
            "schema_version": 1,
            "report_kind": "alatyr-session-task-memory",
            "state": "not-applicable",
            "lost_candidates": [],
            "limitation": "Source-contour sessions are not target task-memory records.",
        }
    view = TargetRepositoryView(target)
    active, active_state = _read_object(view, ACTIVE_TASKS)
    if active_state == "current" and not isinstance(active.get("tasks"), list):
        active_state = "invalid"
    active_ids = _task_ids(active, "tasks")
    team, team_state = _read_object(view, TEAM_WORK)
    team_ids: set[str] = set()
    team_verification = team_state
    if team_state == "current":
        if isinstance(team.get("entries"), list):
            team_ids = _task_ids(team, "entries")
        else:
            index_reference = team.get("active_work_index")
            if (
                not isinstance(index_reference, str)
                or not is_target_relative_path(index_reference)
            ):
                team_verification = "invalid-index-reference"
            else:
                index, index_state = _read_object(view, index_reference)
                if index_state != "current":
                    team_verification = f"index-{index_state}"
                elif not isinstance(index.get("entries"), list):
                    team_verification = "index-invalid"
                else:
                    team_ids = _task_ids(index, "entries")
    team_unverified = team_verification in {
        "invalid",
        "invalid-index-reference",
        "index-missing",
        "index-invalid",
    }
    stale_sessions = [
        session
        for session in sessions
        if isinstance(session, dict)
        and session.get("same_worktree")
        and session.get("freshness") != "recent"
    ]
    lost: list[dict[str, Any]] = []
    if active_state == "current" and not team_unverified:
        for session in stale_sessions:
            task = session.get("task")
            if not isinstance(task, str) or not task or task in active_ids or task in team_ids:
                continue
            lost.append(
                {
                    "action": "register-task-or-leave",
                    "session_uid": session.get("session_uid"),
                    "expected_version": session.get("version"),
                    "task": task,
                    "freshness": session.get("freshness"),
                    "reason": "stale-session-task-not-registered",
                }
            )
    state = (
        "attention"
        if lost
        else "current"
        if not stale_sessions
        else "unavailable"
        if active_state != "current" or team_unverified
        else "current"
    )
    return {
        "schema_version": 1,
        "report_kind": "alatyr-session-task-memory",
        "state": state,
        "active_task_source": ACTIVE_TASKS,
        "active_task_state": active_state,
        "team_work_source": TEAM_WORK,
        "team_work_state": team_verification,
        "team_index_required": team_state != "missing",
        "team_index_verified": team_verification == "current",
        "active_task_count": len(active_ids),
        "team_task_count": len(team_ids),
        "stale_session_count": len(stale_sessions),
        "lost_candidates": lost,
        "limitation": (
            "Presence task labels are matched by exact task_id only. "
            "Registration requires a reviewed active-task/problem-model record; "
            "this check never writes or promotes a task."
        ),
    }
