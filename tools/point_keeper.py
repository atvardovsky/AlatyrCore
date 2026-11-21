#!/usr/bin/env python3
"""Read-only point keeper for scoped worker attention and deploy preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
KIND = "alatyr-point-keeper"
TASKS_REL = ".ai/assistant/team/tasks"
PACKAGES_REL = ".ai/assistant/change-packages/index.json"
ACTIVE_WORK_REL = ".ai/assistant/team/active-work-index.json"
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_POINTS = 4096
MAX_ATTENTION = 20
ROLES = {
    "coordinator",
    "explorer",
    "reviewer",
    "implementer",
    "test-runner",
    "documentation-worker",
    "fast-focused-worker",
    "deploy",
}
ACTIONS = {
    "read", "modify", "modify-docs", "test", "review",
    "freeze", "deploy", "assign", "integrate",
}
STATE_ALIASES = {
    "proposed": "pending", "ready": "pending", "pending": "pending",
    "todo": "pending", "backlog": "pending",
    "in_progress": "in_progress", "implementing": "in_progress",
    "active": "in_progress", "started": "in_progress",
    "in_review": "in_review", "review": "in_review",
    "reviewing": "in_review", "awaiting_review": "in_review",
    "done": "done", "complete": "done", "completed": "done",
    "frozen": "done", "reviewed": "done",
    "blocked": "blocked", "failed": "blocked", "needs_check": "blocked",
    "cancelled": "cancelled", "canceled": "cancelled",
    "superseded": "cancelled", "archived": "cancelled",
}
REVIEW_ALIASES = {
    "not-required": "not-required", "not_required": "not-required",
    "none": "not-required", "required": "required",
    "pending": "required", "in-review": "in-review",
    "in_review": "in-review", "reviewing": "in-review",
    "reviewed": "reviewed", "approved": "reviewed",
    "rejected": "rejected", "stale": "stale",
}


class KeeperError(ValueError):
    """Invalid input or an unsafe target path."""


def _target(value: str) -> Path:
    target = Path(value).expanduser().resolve()
    if not target.is_dir():
        raise KeeperError(f"target is not a directory: {value}")
    return target


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink():
        raise KeeperError(f"{label} must not be a symlink")
    try:
        info = path.stat()
    except OSError as exc:
        raise KeeperError(f"{label} is unavailable") from exc
    if not stat.S_ISREG(info.st_mode):
        raise KeeperError(f"{label} must be a regular file")
    if info.st_size > MAX_JSON_BYTES:
        raise KeeperError(f"{label} exceeds {MAX_JSON_BYTES} bytes")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise KeeperError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise KeeperError(f"{label} must contain an object")
    return value


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        item.strip()
        for item in value
        if isinstance(item, str)
        and item.strip()
        and item.strip().lower() not in {"none", "n/a", "unavailable"}
    ]


def _state(value: Any) -> str:
    text = str(value or "unknown").strip().lower().replace(" ", "_")
    return STATE_ALIASES.get(text, "unknown")


def _review(value: Any) -> str:
    text = str(value or "not-required").strip().lower().replace(" ", "-")
    return REVIEW_ALIASES.get(text, "unknown")


def _point_view(raw: dict[str, Any], source: Path) -> dict[str, Any] | None:
    point_id = raw.get("id") or raw.get("task_id") or raw.get("point_id")
    if not isinstance(point_id, str) or not point_id.strip():
        return None
    status_raw = str(raw.get("status") or "unknown")
    state = _state(status_raw)
    review_raw = str(raw.get("review_state") or "not-required")
    review_state = _review(review_raw)
    reviewers = _strings(raw.get("reviewer_actor_ids"))
    evidence = _strings(raw.get("review_evidence_refs"))
    review_required = review_state != "not-required" or bool(reviewers)
    if state == "done" and review_raw.strip().lower() in {"frozen", "reviewed"}:
        review_state = "reviewed"
    frozen = (
        state == "done"
        and review_state in {"reviewed", "not-required"}
        and (not review_required or bool(evidence))
    )
    return {
        "id": point_id.strip(),
        "title": str(raw.get("goal") or raw.get("title") or point_id).strip()[:240],
        "state": state,
        "state_raw": status_raw,
        "review_state": review_state,
        "review_required": review_required,
        "reviewers": reviewers,
        "review_evidence": evidence,
        "reviewed_head_revision": str(raw.get("reviewed_head_revision") or "none"),
        "reviewed_base_revision": str(raw.get("reviewed_base_revision") or "none"),
        "validation_state": str(raw.get("validation_state") or "not-run").strip().lower(),
        "blockers": _strings(raw.get("blockers")),
        "related": _strings(raw.get("related_task_ids")),
        "branch": str(raw.get("branch_or_worktree") or "unknown"),
        "priority": str(raw.get("priority") or "normal"),
        "frozen": frozen,
        "next_action": str(raw.get("next_action") or ""),
        "source": source.as_posix(),
    }


def _load_points(target: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    directory = target / TASKS_REL
    if not directory.is_dir():
        return [], [{"path": TASKS_REL, "reason": "tasks-directory-missing"}]
    points: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    files = sorted(directory.glob("*.json"))[:MAX_POINTS]
    for path in files:
        try:
            raw = _read_json(path, f"point {path.name}")
        except KeeperError as exc:
            errors.append({"path": path.as_posix(), "reason": str(exc)})
            continue
        view = _point_view(raw, path)
        if view is None:
            errors.append({"path": path.as_posix(), "reason": "point id is missing"})
            continue
        if any(item["id"] == view["id"] for item in points):
            errors.append({"path": path.as_posix(), "reason": "duplicate point id"})
            continue
        points.append(view)
    return points, errors


def _load_packages(target: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    path = target / PACKAGES_REL
    if not path.exists():
        return {}, ["package-index-missing"]
    try:
        data = _read_json(path, "package index")
    except KeeperError as exc:
        return {}, [str(exc)]
    records = data.get("records")
    if not isinstance(records, list):
        return {}, ["package-index-invalid"]
    packages: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("package_id"), str):
            continue
        packages[record["package_id"]] = {
            "status": str(record.get("status") or "unknown"),
            "active_workstream": str(record.get("active_workstream") or "unknown"),
            "residual_risk": str(record.get("residual_risk") or ""),
        }
    return packages, []


def _active_work(target: Path) -> int:
    path = target / ACTIVE_WORK_REL
    if not path.exists():
        return 0
    try:
        data = _read_json(path, "active work index")
    except KeeperError:
        return 0
    entries = data.get("entries")
    return len(entries) if isinstance(entries, list) else 0


def _revision(target: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", value) else None


def _blockers(
    point: dict[str, Any],
    current_revision: str | None,
    *,
    require_revision: bool,
    package_blocked: bool = False,
) -> list[str]:
    reasons: list[str] = []
    if point["state"] != "done":
        reasons.append(f"not-done:{point['state']}")
    elif not point["frozen"]:
        reasons.append(f"not-frozen:{point['review_state']}")
    if point["review_required"] and not point["review_evidence"]:
        reasons.append("review-evidence-missing")
    if point["review_state"] in {"required", "in-review", "rejected", "stale", "unknown"}:
        reasons.append(f"review:{point['review_state']}")
    validation = point["validation_state"]
    if validation not in {"passed", "current", "not-required", "ok"}:
        reasons.append(f"validation:{validation}")
    for blocker in point["blockers"]:
        reasons.append(f"blocker:{blocker}")
    reviewed = point["reviewed_head_revision"].strip().lower()
    if point["frozen"] and reviewed in {"", "none"}:
        reasons.append("reviewed-revision-missing")
    if current_revision is not None and reviewed not in {"", "none"} and reviewed != current_revision:
        reasons.append("frozen-drift")
    if require_revision and current_revision is None and reviewed not in {"", "none"}:
        reasons.append("revision-unknown")
    if package_blocked:
        reasons.append("deploy-package-blocked")
    return reasons


def _actions(role: str, point: dict[str, Any]) -> tuple[list[str], list[str]]:
    allowed = {"read"}
    if role == "coordinator":
        allowed |= {"assign", "integrate"}
        if not point["frozen"]:
            allowed |= {"review", "freeze", "deploy"}
        else:
            allowed.add("deploy")
    elif role == "reviewer":
        if point["state"] == "in_review" and not point["frozen"]:
            allowed.add("review")
    elif role in {"implementer", "fast-focused-worker"}:
        if point["state"] in {"pending", "in_progress"} and not point["frozen"]:
            allowed.add("modify")
    elif role == "documentation-worker":
        if point["state"] in {"pending", "in_progress"} and not point["frozen"]:
            allowed.add("modify-docs")
    elif role == "test-runner":
        allowed.add("test")
    elif role == "deploy":
        if point["frozen"]:
            allowed.add("deploy")
    return sorted(allowed), sorted(ACTIONS - allowed)


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def status_view(target: Path, *, current_revision: str | None) -> dict[str, Any]:
    points, errors = _load_points(target)
    packages, package_errors = _load_packages(target)
    counts: dict[str, int] = {}
    attention: list[dict[str, Any]] = []
    for point in points:
        counts[point["state"]] = counts.get(point["state"], 0) + 1
        reasons = _blockers(point, current_revision, require_revision=False)
        if reasons and len(attention) < MAX_ATTENTION:
            attention.append(
                {"point_id": point["id"], "state": point["state"], "reasons": reasons}
            )
    package_counts: dict[str, int] = {}
    for package in packages.values():
        package_counts[package["status"]] = package_counts.get(package["status"], 0) + 1
    state = "current" if points and not errors else "unavailable"
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "view": "coordinator",
        "state": state,
        "points": len(points),
        "counts": dict(sorted(counts.items())),
        "frozen": sum(1 for item in points if item["frozen"]),
        "attention": attention,
        "attention_omitted": max(0, len(points) - len(attention)),
        "invalid_points": errors[:MAX_ATTENTION],
        "invalid_point_count": len(errors),
        "packages": len(packages),
        "package_counts": dict(sorted(package_counts.items())),
        "package_errors": package_errors,
        "active_work_entries": _active_work(target),
        "current_revision": current_revision,
        "authority": "none",
        "authority_granted": False,
    }


def check_view(
    target: Path, *, point_id: str, role: str, current_revision: str | None
) -> dict[str, Any]:
    if role not in ROLES:
        raise KeeperError(f"unknown role: {role}")
    if role == "coordinator":
        result = status_view(target, current_revision=current_revision)
        result["kind"] = KIND
        result["view"] = "coordinator"
        return result
    points, errors = _load_points(target)
    point = next((item for item in points if item["id"] == point_id), None)
    if point is None:
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": KIND,
            "view": role,
            "state": "unavailable",
            "point_id": point_id,
            "reason": "point-missing-or-invalid",
            "invalid_points": errors[:MAX_ATTENTION],
            "authority": "none",
            "authority_granted": False,
        }
    allowed, forbidden = _actions(role, point)
    view = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "view": role,
        "state": "current",
        "point": point,
        "allowed_actions": allowed,
        "forbidden_actions": forbidden,
        "blockers": _blockers(point, current_revision, require_revision=False),
        "deploy_sets": point["related"],
        "dependencies": point["related"],
        "current_revision": current_revision,
        "authority": "none",
        "authority_granted": False,
    }
    view["keeper_digest"] = _digest(view)
    return view


def preflight_view(
    target: Path, *, deploy_set: str, current_revision: str | None
) -> dict[str, Any]:
    if not deploy_set.strip():
        raise KeeperError("--deploy-set must be non-empty")
    points, errors = _load_points(target)
    packages, package_errors = _load_packages(target)
    package = packages.get(deploy_set)
    package_blocked = package is None or package["status"] not in {"complete", "validated"}
    members = [point for point in points if deploy_set in point["related"]]
    blockers: list[str] = []
    if package is None:
        blockers.append(f"{deploy_set}: deploy-set-unknown")
    elif package_blocked:
        blockers.append(f"{deploy_set}: deploy-package-{package['status']}")
    if not members:
        blockers.append(f"{deploy_set}: deploy-set-empty")
    results = []
    for point in members:
        reasons = _blockers(
            point, current_revision, require_revision=True, package_blocked=package_blocked
        )
        results.append(
            {
                "point_id": point["id"],
                "state": point["state"],
                "frozen": point["frozen"],
                "review_state": point["review_state"],
                "reasons": reasons,
            }
        )
        blockers.extend(f"{point['id']}: {reason}" for reason in reasons)
    if errors:
        blockers.extend(f"invalid-point-record: {item['path']}" for item in errors)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "view": "deploy",
        "state": "ready" if not blockers else "blocked",
        "deploy_set": deploy_set,
        "package": package,
        "package_errors": package_errors,
        "points": results,
        "blockers": blockers,
        "current_revision": current_revision,
        "authority": "none",
        "authority_granted": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--current-revision")
    actions = parser.add_subparsers(dest="action", required=True)
    status = actions.add_parser("status", allow_abbrev=False)
    status.add_argument("--role", choices=sorted(ROLES), default="coordinator")
    status.add_argument("--current-revision", default=argparse.SUPPRESS)
    check = actions.add_parser("check", allow_abbrev=False)
    check.add_argument("--point", required=True)
    check.add_argument("--role", choices=sorted(ROLES), required=True)
    check.add_argument("--current-revision", default=argparse.SUPPRESS)
    preflight = actions.add_parser("preflight", allow_abbrev=False)
    preflight.add_argument("--deploy-set", required=True)
    preflight.add_argument("--current-revision", default=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        target = _target(str(args.target))
        current = getattr(args, "current_revision", None) or _revision(target)
        if args.action == "status":
            if args.role != "coordinator":
                raise KeeperError("status is coordinator-only; use check --point")
            result = status_view(target, current_revision=current)
        elif args.action == "check":
            result = check_view(
                target, point_id=args.point, role=args.role, current_revision=current
            )
        else:
            result = preflight_view(
                target, deploy_set=args.deploy_set, current_revision=current
            )
    except (OSError, KeeperError, ValueError) as exc:
        print(f"FAIL: point keeper: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.action == "preflight":
        return 0 if result["state"] == "ready" else 1
    return 0 if result["state"] != "unavailable" else 1


if __name__ == "__main__":
    raise SystemExit(main())
