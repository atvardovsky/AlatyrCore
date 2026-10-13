"""Bounded views of reported presence; no liveness or exclusivity claims."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from session_presence_contract import scope_reference, timestamp

MAX_SUMMARY_SESSIONS = 8


def same_worktree(first: str, second: str) -> bool:
    return os.path.normcase(first) == os.path.normcase(second)


def scope_overlap(first: list[str], second: list[str], *, shared_worktree: bool) -> str:
    def reported_reference(item: str) -> tuple[str, str]:
        try:
            return scope_reference(item)
        except ValueError:
            # Registry v1 allowed free-form references, including typed-looking text.
            return "unknown", item

    left = [reported_reference(item) for item in first]
    right = [reported_reference(item) for item in second]
    unknown = any(kind == "unknown" for kind, _ in [*left, *right])
    for kind, value in left:
        for other_kind, other in right:
            if kind != other_kind:
                if shared_worktree and {kind, other_kind} == {"area", "path"}:
                    unknown = True
                continue
            if kind == "resource" or shared_worktree and kind == "area":
                if value == other:
                    return "reported-overlap"
            elif shared_worktree and kind == "path":
                a, b = (os.path.normcase(part).replace("\\", "/") for part in (value, other))
                if a == "." or b == "." or a == b or a.startswith(b + "/") or b.startswith(a + "/"):
                    return "reported-overlap"
    return "unknown" if unknown else "no-direct-overlap"


def summarize(value: dict[str, Any], worktree: str, policy: dict[str, Any],
              now: datetime, *, session_uid: str | None = None,
              scope: list[str] | None = None, full: bool = False) -> dict[str, Any]:
    own = value["sessions"].get(session_uid)
    compared_scope = scope if scope is not None else own["scope"] if own else None
    entries = []
    recent = uncertain = other_worktrees = overlaps = unknown = 0
    own_view = None
    for entry in value["sessions"].values():
        shared = same_worktree(entry["worktree"], worktree)
        age = (now - timestamp(entry["updated_at"], "updated_at")).total_seconds()
        freshness = "clock-uncertain" if age < 0 else "stale" if age >= policy["stale_after_seconds"] else "recent"
        if shared:
            recent += freshness == "recent"
            uncertain += freshness != "recent"
        else:
            other_worktrees += 1
        view = {key: entry[key] for key in ("session_uid", "task", "scope", "activity", "version")}
        view.update(freshness=freshness, same_worktree=shared)
        if entry["session_uid"] == session_uid:
            own_view = {**view, "refresh_due": age < 0 or age >= policy["stale_after_seconds"] / 2}
            if not full:
                continue
        overlap = scope_overlap(compared_scope, entry["scope"], shared_worktree=shared) if compared_scope is not None and entry["session_uid"] != session_uid else "not-compared"
        overlaps += overlap == "reported-overlap"
        unknown += overlap == "unknown"
        view["overlap"] = overlap
        entries.append({**entry, **view} if full else view)
    state = "multiple-reported" if recent >= 2 else "uncertain" if uncertain else "single-reported" if recent else "no-reported"
    entries.sort(key=lambda entry: (
        entry["overlap"] != "reported-overlap", entry["overlap"] != "unknown",
        not entry["same_worktree"], entry["session_uid"],
    ))
    selected = entries if full else entries[:MAX_SUMMARY_SESSIONS]
    return {
        "observed_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "coordination": {"state": state, "same_worktree_recent": recent,
                         "same_worktree_uncertain": uncertain, "other_worktrees": other_worktrees,
                         "reported_overlaps": overlaps, "unknown_scope_peers": unknown},
        "own_session": own_view, "sessions": selected,
        "omitted_sessions": len(entries) - len(selected),
    }
