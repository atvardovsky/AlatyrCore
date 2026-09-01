#!/usr/bin/env python3
"""Run dependency-aware AlatyrCore source-repository validation profiles."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any

from source_state import snapshot_changes, source_snapshot
from source_check_manifest import (
    ALLOWED_PLATFORMS,
    ALLOWED_PROFILES,
    ALLOWED_RESOURCE_CLASSES,
    ALLOWED_WRITE_SCOPES,
    broad_trigger_patterns as _broad_trigger_patterns,
    load_manifest as load_source_check_manifest,
    matches,
    routes,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tools" / "check_manifest.json"
RESOURCE_CLASS_WEIGHTS = {"light": 1, "standard": 1, "heavy": 2}
TIMEOUT_EXIT_CODE = 124


@dataclass(frozen=True)
class RunnerResult:
    """Process result metadata that legacy test runners do not need to provide."""

    result: tuple[int, str, str, list[str]]
    timed_out: bool = False


@dataclass(frozen=True)
class SelectionResult:
    """Selected checks plus focused-route diagnostics."""

    selected: list[dict[str, Any]]
    fell_back_to_full: bool
    changed_paths: list[str]
    unmatched_changed_paths: list[str]
    platform: str
    selection_details: dict[str, dict[str, Any]]


def load_manifest() -> list[dict[str, Any]]:
    return load_source_check_manifest(MANIFEST, root=ROOT)


def git_changed_paths(ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", ref, "--"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or f"cannot compare changed paths with {ref}")
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if untracked.returncode != 0:
        raise ValueError(untracked.stderr.strip() or "cannot list untracked paths")
    return sorted(
        set(filter(None, result.stdout.splitlines()))
        | set(filter(None, untracked.stdout.splitlines()))
    )


def git_ref_exists(ref: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", ref],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def default_changed_from() -> str:
    return "origin/main" if git_ref_exists("origin/main") else "HEAD"


def resolve_changed_from(
    profile: str, changed_from: str | None, *, all_fast: bool = False
) -> str | None:
    if profile != "fast":
        return changed_from
    if all_fast:
        return None
    return changed_from or default_changed_from()


def current_platform() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform in {"win32", "cygwin"}:
        return "windows"
    raise ValueError(f"unsupported source-check platform: {sys.platform}")


def supports_platform(check: dict[str, Any], platform: str) -> bool:
    return "all" in check["platforms"] or platform in check["platforms"]


def _selected_check(
    check: dict[str, Any],
    *,
    profile: str,
    changed_paths: list[str],
    fell_back_to_full: bool,
    details: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Return a manifest check decorated with non-contract runner metadata."""

    check_id = check["id"]
    detail = details.get(check_id, {"reasons": [], "matched_changed_paths": []})
    metadata = {
        "profile": profile,
        "changed_paths": changed_paths,
        "changed_path_count": len(changed_paths),
        "fell_back_to_full": fell_back_to_full,
        "reasons": sorted(set(detail.get("reasons", []))),
        "matched_changed_paths": sorted(set(detail.get("matched_changed_paths", []))),
        "broad_trigger_patterns": _broad_trigger_patterns(check),
    }
    return {**check, "_selection": metadata}


def select_check_plan(
    checks: list[dict[str, Any]],
    profile: str,
    changed_from: str | None,
    *,
    platform: str | None = None,
) -> SelectionResult:
    selected_platform = platform or current_platform()
    changed: list[str] = []
    unmatched: list[str] = []
    details: dict[str, dict[str, Any]] = {}

    def note(check_id: str, reason: str, paths: list[str] | None = None) -> None:
        detail = details.setdefault(
            check_id, {"reasons": [], "matched_changed_paths": []}
        )
        detail["reasons"].append(reason)
        if paths:
            detail["matched_changed_paths"].extend(paths)

    if profile == "release":
        selected_ids = {
            check["id"]
            for check in checks
            if "full" in check["profiles"] or "release" in check["profiles"]
            if supports_platform(check, selected_platform)
        }
        for check_id in selected_ids:
            note(check_id, "release-profile")
    elif profile == "fast" and changed_from:
        selected_ids = {
            check["id"]
            for check in checks
            if check.get("always_for_changed", False)
            and supports_platform(check, selected_platform)
        }
        for check_id in selected_ids:
            note(check_id, "always-for-changed")
    else:
        selected_ids = {
            check["id"]
            for check in checks
            if profile in check["profiles"] and supports_platform(check, selected_platform)
        }
        for check_id in selected_ids:
            note(check_id, f"profile:{profile}")

    fell_back_to_full = False
    if profile == "fast" and changed_from:
        changed = git_changed_paths(changed_from)
        full_checks = [
            check
            for check in checks
            if "full" in check["profiles"]
            and supports_platform(check, selected_platform)
        ]
        unmatched = [
            path for path in changed if not any(routes(check, path) for check in full_checks)
        ]
        if unmatched:
            fell_back_to_full = True
            selected_ids.update(check["id"] for check in full_checks)
            for check in full_checks:
                matched_paths = [path for path in changed if routes(check, path)]
                note(check["id"], "full-fallback-unmatched", matched_paths)
        else:
            for check in full_checks:
                matched_paths = [path for path in changed if routes(check, path)]
                if matched_paths:
                    selected_ids.add(check["id"])
                    note(check["id"], "changed-path-trigger", matched_paths)

    by_id = {check["id"]: check for check in checks}

    def add_dependencies(check_id: str) -> None:
        for dependency in by_id[check_id]["depends_on"]:
            if not supports_platform(by_id[dependency], selected_platform):
                raise ValueError(
                    f"{check_id} depends on {dependency}, which does not support "
                    f"platform {selected_platform}"
            )
            if dependency not in selected_ids:
                selected_ids.add(dependency)
                note(dependency, f"dependency-of:{check_id}")
                add_dependencies(dependency)

    for check_id in list(selected_ids):
        add_dependencies(check_id)
    selected = [
        _selected_check(
            check,
            profile=profile,
            changed_paths=changed,
            fell_back_to_full=fell_back_to_full,
            details=details,
        )
        for check in checks
        if check["id"] in selected_ids
    ]
    return SelectionResult(
        selected=selected,
        fell_back_to_full=fell_back_to_full,
        changed_paths=changed,
        unmatched_changed_paths=unmatched,
        platform=selected_platform,
        selection_details={check_id: details[check_id] for check_id in selected_ids if check_id in details},
    )


def select_checks(
    checks: list[dict[str, Any]],
    profile: str,
    changed_from: str | None,
    *,
    platform: str | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Backward-compatible check selection API for tests and callers."""

    plan = select_check_plan(checks, profile, changed_from, platform=platform)
    return plan.selected, plan.fell_back_to_full


def selection_report(
    *,
    profile: str,
    changed_from: str | None,
    plan: SelectionResult,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    broad_triggered: list[dict[str, Any]] = []
    resource_classes: dict[str, int] = {}
    for check in plan.selected:
        check_id = check["id"]
        metadata = check.get("_selection", {})
        resource_class = check.get("resource_class", "standard")
        resource_classes[resource_class] = resource_classes.get(resource_class, 0) + 1
        entry = {
            "id": check_id,
            "resource_class": resource_class,
            "selection_reasons": metadata.get("reasons", []),
            "matched_changed_paths": metadata.get("matched_changed_paths", []),
            "broad_trigger_patterns": metadata.get("broad_trigger_patterns", []),
        }
        checks.append(entry)
        if entry["broad_trigger_patterns"] and entry["selection_reasons"]:
            broad_triggered.append(entry)
    return {
        "profile": profile,
        "platform": plan.platform,
        "changed_from": changed_from,
        "changed_path_count": len(plan.changed_paths),
        "changed_paths": plan.changed_paths,
        "unmatched_changed_paths": plan.unmatched_changed_paths,
        "fell_back_to_full": plan.fell_back_to_full,
        "selected_check_ids": [check["id"] for check in plan.selected],
        "resource_class_counts": dict(sorted(resource_classes.items())),
        "checks": checks,
        "broad_trigger_diagnostics": {
            "selected_count": len(broad_triggered),
            "checks": broad_triggered,
            "limitation": (
                "Broad triggers are allowed for source-owned contracts, but "
                "large focused-run fanout should be reviewed before adding more."
            ),
        },
    }


def resolved_command(check: dict[str, Any], baseline: str | None) -> list[str]:
    command: list[str] = []
    for value in check["command"]:
        if value == "{baseline}":
            if not baseline:
                raise ValueError(f"{check['id']} requires --from-ref")
            command.append(baseline)
        else:
            command.append(value)
    return [sys.executable, *command]


def _captured_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_check(check: dict[str, Any], baseline: str | None) -> RunnerResult:
    command = resolved_command(check, baseline)
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    selection = check.get("_selection", {})
    environment["ALATYR_CHECK_ID"] = str(check.get("id", ""))
    environment["ALATYR_SOURCE_CHECK_PROFILE"] = str(selection.get("profile", ""))
    environment["ALATYR_CHANGED_PATHS_JSON"] = json.dumps(
        selection.get("changed_paths", []), ensure_ascii=True
    )
    environment["ALATYR_MATCHED_CHANGED_PATHS_JSON"] = json.dumps(
        selection.get("matched_changed_paths", []), ensure_ascii=True
    )
    environment["ALATYR_SELECTION_REASONS_JSON"] = json.dumps(
        selection.get("reasons", []), ensure_ascii=True
    )
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=check["timeout_seconds"],
        )
    except subprocess.TimeoutExpired as exc:
        timeout_message = (
            f"timed out after {check['timeout_seconds']} seconds "
            f"(resource_class={check['resource_class']})\n"
        )
        return RunnerResult(
            (
                TIMEOUT_EXIT_CODE,
                _captured_text(exc.stdout),
                _captured_text(exc.stderr) + timeout_message,
                command,
            ),
            timed_out=True,
        )
    return RunnerResult((result.returncode, result.stdout, result.stderr, command))


def effective_baseline(
    profile: str, changed_from: str | None, from_ref: str | None
) -> str | None:
    """Use changed-file baseline as the change-drift baseline when unambiguous."""

    if from_ref:
        return from_ref
    if profile == "change":
        return changed_from
    return None


def environment_report() -> dict[str, Any]:
    dependencies: dict[str, str] = {}
    for dependency in ["jsonschema", "PyYAML"]:
        try:
            dependencies[dependency] = package_version(dependency)
        except PackageNotFoundError:
            dependencies[dependency] = "not-installed"
    return {
        "platform": current_platform(),
        "platform_detail": platform.platform(),
        "python": sys.version,
        "python_executable": sys.executable,
        "dependencies": dependencies,
    }


def source_identity() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    manifest_digest = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    manifest_data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {
        "source_commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "source_tree_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
        "manifest_path": MANIFEST.relative_to(ROOT).as_posix(),
        "manifest_sha256": manifest_digest,
        "check_manifest_schema_version": manifest_data.get("schema_version"),
    }


def render_report(
    *,
    profile: str,
    selected: list[dict[str, Any]],
    results: dict[str, tuple[int, str, str, list[str]]],
    blocked: dict[str, list[str]],
    source_changes: list[str],
    telemetry: dict[str, dict[str, Any]] | None = None,
    selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    telemetry = telemetry or {}
    timing = dict(
        telemetry.get(
            "_summary",
            {
                "wall_seconds": 0.0,
                "sum_check_duration_seconds": sum(
                    item.get("duration_seconds", 0.0)
                    for key, item in telemetry.items()
                    if key != "_summary"
                ),
                "critical_path_candidate_seconds": max(
                    [
                        item.get("completed_after_seconds", 0.0)
                        for key, item in telemetry.items()
                        if key != "_summary"
                    ]
                    or [0.0]
                ),
            },
        )
    )
    timing["slowest_checks"] = sorted(
        [
            {
                "id": check["id"],
                "resource_class": check.get("resource_class", "standard"),
                "duration_seconds": telemetry.get(check["id"], {}).get(
                    "duration_seconds", 0.0
                ),
                "queued_seconds": telemetry.get(check["id"], {}).get(
                    "queued_seconds", 0.0
                ),
                "completed_after_seconds": telemetry.get(check["id"], {}).get(
                    "completed_after_seconds", 0.0
                ),
            }
            for check in selected
        ],
        key=lambda item: (-item["duration_seconds"], item["id"]),
    )[:10]
    for check in selected:
        check_id = check["id"]
        observation = telemetry.get(check_id, {})
        selected_metadata = check.get("_selection", {})
        common = {
            "resource_class": check.get("resource_class", "standard"),
            "timeout_seconds": check.get("timeout_seconds"),
            "duration_seconds": observation.get("duration_seconds", 0.0),
            "queued_seconds": observation.get("queued_seconds", 0.0),
            "completed_after_seconds": observation.get("completed_after_seconds", 0.0),
            "timed_out": observation.get("timed_out", False),
            "selection_reasons": selected_metadata.get("reasons", []),
            "matched_changed_paths": selected_metadata.get("matched_changed_paths", []),
            "broad_trigger_patterns": selected_metadata.get("broad_trigger_patterns", []),
        }
        if check_id in blocked:
            checks.append(
                {
                    "id": check_id,
                    "status": "blocked",
                    "blocked_by": blocked[check_id],
                    **common,
                }
            )
            continue
        code, stdout, stderr, command = results[check_id]
        checks.append(
            {
                "id": check_id,
                "status": "passed" if code == 0 else "failed",
                "exit_code": code,
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                **common,
            }
        )
    return {
        "schema_version": 2,
        "report_kind": "alatyr-source-check-run",
        "profile": profile,
        "source": source_identity(),
        "timing": timing,
        "selection": selection or {
            "profile": profile,
            "platform": current_platform(),
            "changed_from": None,
            "changed_path_count": 0,
            "changed_paths": [],
            "unmatched_changed_paths": [],
            "fell_back_to_full": False,
            "selected_check_ids": [check["id"] for check in selected],
            "resource_class_counts": {},
            "checks": [],
            "broad_trigger_diagnostics": {
                "selected_count": 0,
                "checks": [],
                "limitation": "selection details unavailable",
            },
        },
        "environment": environment_report(),
        "source_write_scope": {
            "declared": "none",
            "preserved": not source_changes,
            "changes": source_changes,
        },
        "checks": checks,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_report_path(path: Path, *, root: Path = ROOT) -> Path:
    resolved = path.resolve()
    source_root = root.resolve()
    try:
        relative = resolved.relative_to(source_root)
    except ValueError:
        return resolved
    if not relative.parts or relative.parts[0] != "tmp":
        raise ValueError("--report must be outside the source tree or under ignored tmp/")

    relpath = relative.as_posix()
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relpath],
        cwd=source_root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if tracked.returncode == 0:
        raise ValueError("--report must not replace a tracked source file")
    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", "--no-index", "--", relpath],
        cwd=source_root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if ignored.returncode != 0:
        raise ValueError("--report repository path must be ignored by Git")
    return resolved


def execute_checks(
    checks: list[dict[str, Any]],
    baseline: str | None,
    jobs: int,
    *,
    runner: Any = run_check,
    telemetry: dict[str, dict[str, Any]] | None = None,
) -> tuple[
    dict[str, tuple[int, str, str, list[str]]],
    dict[str, list[str]],
]:
    """Run a selected dependency graph and block checks after failed prerequisites."""

    selected_ids = {check["id"] for check in checks}
    remaining = {check["id"]: check for check in checks}
    results: dict[str, tuple[int, str, str, list[str]]] = {}
    blocked: dict[str, list[str]] = {}

    observations = telemetry if telemetry is not None else {}
    run_started = time.monotonic()
    queued_since = {check["id"]: run_started for check in checks}

    def run_with_observation(
        check: dict[str, Any],
    ) -> tuple[tuple[int, str, str, list[str]], bool, float]:
        started = time.monotonic()
        try:
            outcome = runner(check, baseline)
        except Exception as exc:  # pragma: no cover - defensive process boundary
            return (1, "", str(exc), []), False, round(time.monotonic() - started, 6)
        duration_seconds = round(time.monotonic() - started, 6)
        if isinstance(outcome, RunnerResult):
            return outcome.result, outcome.timed_out, duration_seconds
        if (
            not isinstance(outcome, tuple)
            or len(outcome) != 4
            or not isinstance(outcome[0], int)
        ):
            raise ValueError("runner must return a four-item result tuple or RunnerResult")
        return outcome, False, duration_seconds

    def resource_weight(check: dict[str, Any]) -> int:
        return min(RESOURCE_CLASS_WEIGHTS[check.get("resource_class", "standard")], jobs)

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
        running: dict[concurrent.futures.Future[Any], dict[str, Any]] = {}
        running_weights: dict[concurrent.futures.Future[Any], int] = {}
        running_weight = 0

        def block_failed_dependents() -> None:
            changed = True
            while changed:
                changed = False
                for check_id, check in list(remaining.items()):
                    if any(
                        dependency not in selected_ids
                        for dependency in check["depends_on"]
                    ):
                        continue
                    failed_dependencies = [
                        dependency
                        for dependency in check["depends_on"]
                        if dependency in blocked
                        or (dependency in results and results[dependency][0] != 0)
                    ]
                    if failed_dependencies:
                        blocked[check_id] = sorted(failed_dependencies)
                        remaining.pop(check_id)
                        observations[check_id] = {
                            "duration_seconds": 0.0,
                            "queued_seconds": round(
                                time.monotonic() - queued_since[check_id], 6
                            ),
                            "completed_after_seconds": round(
                                time.monotonic() - run_started, 6
                            ),
                            "timed_out": False,
                        }
                        changed = True

        def ready_checks() -> list[dict[str, Any]]:
            return [
                check
                for check in checks
                if check["id"] in remaining
                and all(
                    dependency not in selected_ids
                    or (dependency in results and results[dependency][0] == 0)
                    for dependency in check["depends_on"]
                )
            ]

        def submit_ready() -> bool:
            nonlocal running_weight
            submitted = False
            for check in ready_checks():
                weight = resource_weight(check)
                if running and running_weight + weight > jobs:
                    continue
                future = executor.submit(run_with_observation, check)
                running[future] = check
                running_weights[future] = weight
                running_weight += weight
                remaining.pop(check["id"])
                observations[check["id"]] = {
                    "queued_seconds": round(time.monotonic() - queued_since[check["id"]], 6)
                }
                submitted = True
            return submitted

        while remaining or running:
            block_failed_dependents()
            submit_ready()
            if not running:
                if remaining:
                    unresolved = ", ".join(sorted(remaining))
                    raise ValueError(f"unresolvable selected check dependencies: {unresolved}")
                break

            done, _pending = concurrent.futures.wait(
                running, return_when=concurrent.futures.FIRST_COMPLETED
            )
            for future in done:
                check = running.pop(future)
                running_weight -= running_weights.pop(future)
                check_id = check["id"]
                try:
                    result, timed_out, duration_seconds = future.result()
                    results[check_id] = result
                    observations[check_id].update(
                        {
                            "duration_seconds": duration_seconds,
                            "completed_after_seconds": round(
                                time.monotonic() - run_started, 6
                            ),
                            "timed_out": timed_out,
                        }
                    )
                except Exception as exc:  # pragma: no cover - executor boundary
                    results[check_id] = (1, "", str(exc), [])
                    observations[check_id].update(
                        {
                            "duration_seconds": 0.0,
                            "completed_after_seconds": round(
                                time.monotonic() - run_started, 6
                            ),
                            "timed_out": False,
                        }
                    )
        observations["_summary"] = {
            "wall_seconds": round(time.monotonic() - run_started, 6),
            "sum_check_duration_seconds": round(
                sum(
                    observation.get("duration_seconds", 0.0)
                    for key, observation in observations.items()
                    if key != "_summary"
                ),
                6,
            ),
            "critical_path_candidate_seconds": round(
                max(
                    [
                        observation.get("completed_after_seconds", 0.0)
                        for key, observation in observations.items()
                        if key != "_summary"
                    ]
                    or [0.0]
                ),
                6,
            ),
            "jobs": jobs,
        }

    return results, blocked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(ALLOWED_PROFILES), default="full")
    parser.add_argument(
        "--changed-from",
        help=(
            "Select checks from changed paths for focused profiles. For fast, "
            "defaults to origin/main when available, otherwise HEAD. For the "
            "change profile, this also acts as --from-ref when --from-ref is omitted."
        ),
    )
    parser.add_argument(
        "--all-fast",
        action="store_true",
        help="With --profile fast, run the complete fast profile without changed-path selection.",
    )
    parser.add_argument("--from-ref", help="Baseline substituted into change checks.")
    parser.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--list", action="store_true")
    parser.add_argument(
        "--report",
        type=Path,
        help="Write a machine-readable run report to this explicit output path.",
    )
    args = parser.parse_args()
    if args.jobs <= 0:
        parser.error("--jobs must be positive")
    if args.all_fast and args.profile != "fast":
        parser.error("--all-fast is only valid with --profile fast")
    if args.all_fast and args.changed_from:
        parser.error("--all-fast cannot be combined with --changed-from")

    try:
        checks = load_manifest()
        changed_from = resolve_changed_from(
            args.profile, args.changed_from, all_fast=args.all_fast
        )
        baseline = effective_baseline(args.profile, changed_from, args.from_ref)
        plan = select_check_plan(checks, args.profile, changed_from)
        selected = plan.selected
        commands = [resolved_command(check, baseline) for check in selected]
        report_path = resolve_report_path(args.report) if args.report else None
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    if args.list:
        for command in commands:
            print(" ".join(command))
        return 0
    if plan.fell_back_to_full:
        print("INFO: unmatched changed paths selected the full check profile", flush=True)
        for path in plan.unmatched_changed_paths:
            print(f"INFO: unmatched changed path: {path}", flush=True)

    try:
        before = source_snapshot(ROOT)
        telemetry: dict[str, dict[str, Any]] = {}
        results, blocked = execute_checks(
            selected, baseline, args.jobs, telemetry=telemetry
        )
        source_changes = snapshot_changes(before, source_snapshot(ROOT))
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    failures: list[str] = []
    for check in selected:
        if check["id"] in blocked:
            dependencies = ", ".join(blocked[check["id"]])
            print(
                f"SKIPPED {check['id']}: blocked by failed dependencies: {dependencies}",
                file=sys.stderr,
            )
            failures.append(check["id"])
            continue
        code, stdout, stderr, command = results[check["id"]]
        print("$ " + " ".join(command), flush=True)
        if stdout:
            print(stdout, end="" if stdout.endswith("\n") else "\n")
        if stderr:
            print(stderr, end="" if stderr.endswith("\n") else "\n", file=sys.stderr)
        if code != 0:
            failures.append(check["id"])

    if report_path:
        try:
            write_report(
                report_path,
                render_report(
                    profile=args.profile,
                    selected=selected,
                    results=results,
                    blocked=blocked,
                    source_changes=source_changes,
                    telemetry=telemetry,
                    selection=selection_report(
                        profile=args.profile,
                        changed_from=changed_from,
                        plan=plan,
                    ),
                ),
            )
        except OSError as exc:
            print(f"FAIL: cannot write source-check report: {exc}", file=sys.stderr)
            failures.append("source-check-report")

    try:
        final_source_changes = snapshot_changes(before, source_snapshot(ROOT))
    except (OSError, ValueError) as exc:
        print(f"FAIL: cannot verify final source write scope: {exc}", file=sys.stderr)
        failures.append("source-write-scope")
        final_source_changes = source_changes
    if final_source_changes != source_changes:
        source_changes = final_source_changes
        if report_path:
            try:
                write_report(
                    report_path,
                    render_report(
                        profile=args.profile,
                        selected=selected,
                        results=results,
                        blocked=blocked,
                        source_changes=source_changes,
                        telemetry=telemetry,
                        selection=selection_report(
                            profile=args.profile,
                            changed_from=changed_from,
                            plan=plan,
                        ),
                    ),
                )
            except OSError as exc:
                print(f"FAIL: cannot refresh source-check report: {exc}", file=sys.stderr)
                failures.append("source-check-report")

    if source_changes:
        print("\nFAILED read-only source-check write scope:", file=sys.stderr)
        for change in source_changes:
            print(f"- {change}", file=sys.stderr)
        failures.append("source-write-scope")

    if failures:
        print("\nFAILED source checks:", file=sys.stderr)
        for check_id in failures:
            print(f"- {check_id}", file=sys.stderr)
        return 1
    print(f"\nOK: ran {len(selected)} source checks from profile {args.profile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
