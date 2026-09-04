#!/usr/bin/env python3
"""Run dependency-aware AlatyrCore source-repository validation profiles."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import locale
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
    micro_routes,
    routes,
)
from source_check_reuse import (
    REUSE_CONTRACT,
    RUN_IDENTITY_CONTRACT,
    SourceSnapshotIndex,
    canonical_digest,
    cached_check_decision,
    check_cache_identity,
    check_input_fingerprint,
    environment_fingerprint,
    load_reuse_report,
    reuse_decisions,
)
from parallel_execution import CHILD_CAPACITY_ENV
from source_check_cache import (
    CHECK_RESULT_CONTRACT,
    MAX_CHECK_CACHE_RECORDS,
    SourceCheckCache,
    cache_key,
    check_result_key,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tools" / "check_manifest.json"
RESOURCE_CLASS_WEIGHTS = {"light": 1, "standard": 1, "heavy": 2}
TIMEOUT_EXIT_CODE = 124
DEFAULT_JOBS = min(4, os.cpu_count() or 1)
MAX_AUTO_JOBS = 8


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
    effective_profile: str
    escalated_from_micro: bool = False
    micro_escalation_reasons: list[str] | None = None


@dataclass
class CompletedSourceCheckRun:
    """State passed from execution into verification and evidence publication."""

    args: argparse.Namespace
    jobs: int
    changed_from: str | None
    baseline: str | None
    plan: SelectionResult
    selected: list[dict[str, Any]]
    results: dict[str, tuple[int, str, str, list[str]]]
    blocked: dict[str, list[str]]
    telemetry: dict[str, dict[str, Any]]
    before: dict[str, Any]
    source_changes: list[str]
    input_fingerprints: dict[str, dict[str, Any]]
    reuse: dict[str, dict[str, Any]]
    selection: dict[str, Any]
    current_source: dict[str, Any]
    current_environment: dict[str, Any]
    run_identity: dict[str, Any]
    report_path: Path | None
    cache: SourceCheckCache | None
    cache_events: list[str]


def _cpu_quota_count() -> int | None:
    """Return a conservative Linux cgroup CPU quota when one is available."""

    try:
        quota, period = (Path("/sys/fs/cgroup/cpu.max").read_text().strip().split())
        if quota != "max":
            return max(1, int(quota) // int(period))
    except (OSError, ValueError, ZeroDivisionError):
        pass
    try:
        quota = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text().strip())
        period = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text().strip())
        if quota > 0:
            return max(1, quota // period)
    except (OSError, ValueError, ZeroDivisionError):
        pass
    return None


def available_cpu_count() -> int:
    """Return CPU capacity bounded by host, affinity, and portable quota evidence."""

    candidates = [max(1, os.cpu_count() or 1)]
    affinity = getattr(os, "sched_getaffinity", None)
    if affinity is not None:
        try:
            candidates.append(max(1, len(affinity(0))))
        except OSError:
            pass
    quota = _cpu_quota_count()
    if quota is not None:
        candidates.append(quota)
    return min(candidates)


def resolve_job_count(value: int | str) -> int:
    """Resolve an explicit worker count or the conservative opt-in auto mode."""

    if isinstance(value, str) and value.strip().lower() == "auto":
        return min(MAX_AUTO_JOBS, available_cpu_count())
    try:
        jobs = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("--jobs must be a positive integer or 'auto'") from exc
    if jobs <= 0:
        raise ValueError("--jobs must be positive")
    return jobs


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


def resolve_ref_oid(ref: str | None) -> str | None:
    """Resolve a relevant Git reference to the commit identity used by this run."""

    if ref is None:
        return None
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or f"cannot resolve Git ref {ref}")
    return result.stdout.strip()


def default_changed_from() -> str:
    return "origin/main" if git_ref_exists("origin/main") else "HEAD"


def resolve_changed_from(
    profile: str, changed_from: str | None, *, all_fast: bool = False
) -> str | None:
    if profile not in {"fast", "micro", "full"}:
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
    selected_ids: set[str] = set()

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
    elif profile == "micro":
        changed = git_changed_paths(changed_from or default_changed_from())
        full_checks = [
            check
            for check in checks
            if "full" in check["profiles"]
            and supports_platform(check, selected_platform)
        ]
        escalation_reasons: list[str] = []
        for path in changed:
            matching_checks = [check for check in full_checks if routes(check, path)]
            micro_checks = [
                check
                for check in matching_checks
                if "micro" in check["profiles"] and micro_routes(check, path)
            ]
            if not matching_checks:
                unmatched.append(path)
                escalation_reasons.append(f"unmatched changed path: {path}")
                continue
            if not micro_checks:
                escalation_reasons.append(f"path requires non-micro checks: {path}")
                continue
            for check in micro_checks:
                selected_ids.add(check["id"])
                note(check["id"], "micro-changed-path-trigger", [path])
        if escalation_reasons:
            fast_plan = select_check_plan(
                checks, "fast", changed_from or default_changed_from(), platform=selected_platform
            )
            return SelectionResult(
                selected=fast_plan.selected,
                fell_back_to_full=fast_plan.fell_back_to_full,
                changed_paths=fast_plan.changed_paths,
                unmatched_changed_paths=fast_plan.unmatched_changed_paths,
                platform=selected_platform,
                selection_details=fast_plan.selection_details,
                effective_profile=fast_plan.effective_profile,
                escalated_from_micro=True,
                micro_escalation_reasons=sorted(set(escalation_reasons)),
            )
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

    for check_id in sorted(selected_ids):
        add_dependencies(check_id)
    if profile == "micro":
        non_micro_dependencies = sorted(
            check_id
            for check_id in selected_ids
            if "micro" not in by_id[check_id]["profiles"]
        )
        if non_micro_dependencies:
            fast_plan = select_check_plan(
                checks, "fast", changed_from or default_changed_from(), platform=selected_platform
            )
            return SelectionResult(
                selected=fast_plan.selected,
                fell_back_to_full=fast_plan.fell_back_to_full,
                changed_paths=fast_plan.changed_paths,
                unmatched_changed_paths=fast_plan.unmatched_changed_paths,
                platform=selected_platform,
                selection_details=fast_plan.selection_details,
                effective_profile=fast_plan.effective_profile,
                escalated_from_micro=True,
                micro_escalation_reasons=[
                    "micro check dependency is not micro-eligible: " + check_id
                    for check_id in non_micro_dependencies
                ],
            )
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
        effective_profile=profile,
        escalated_from_micro=False,
        micro_escalation_reasons=[],
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
        "effective_profile": plan.effective_profile,
        "platform": plan.platform,
        "changed_from": changed_from,
        "changed_path_count": len(plan.changed_paths),
        "changed_paths": plan.changed_paths,
        "unmatched_changed_paths": plan.unmatched_changed_paths,
        "fell_back_to_full": plan.fell_back_to_full,
        "escalated_from_micro": plan.escalated_from_micro,
        "micro_escalation_reasons": plan.micro_escalation_reasons or [],
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


def build_run_identity(
    *,
    requested_profile: str,
    selection: dict[str, Any],
    changed_from: str | None,
    baseline: str | None,
    source: dict[str, Any],
    jobs: int | None = None,
) -> dict[str, Any]:
    """Bind a reusable result to exact selection scope and resolved Git refs."""

    refs: dict[str, str | None] = {}
    for ref in [changed_from, baseline]:
        if ref is not None and ref not in refs:
            refs[ref] = resolve_ref_oid(ref)
    return {
        "contract": RUN_IDENTITY_CONTRACT,
        "requested_profile": requested_profile,
        "effective_profile": selection.get("effective_profile", requested_profile),
        "platform": selection.get("platform"),
        "jobs": jobs,
        "selected_check_ids": selection.get("selected_check_ids", []),
        "changed_paths": selection.get("changed_paths", []),
        "unmatched_changed_paths": selection.get("unmatched_changed_paths", []),
        "fell_back_to_full": selection.get("fell_back_to_full", False),
        "escalated_from_micro": selection.get("escalated_from_micro", False),
        "micro_escalation_reasons": selection.get("micro_escalation_reasons", []),
        "check_scope": [
            {
                "id": item.get("id"),
                "selection_reasons": item.get("selection_reasons", []),
                "matched_changed_paths": item.get("matched_changed_paths", []),
            }
            for item in selection.get("checks", [])
            if isinstance(item, dict)
        ],
        "changed_from": {
            "name": changed_from,
            "commit_oid": refs.get(changed_from),
        },
        "baseline": {
            "name": baseline,
            "commit_oid": refs.get(baseline),
        },
        "source_commit": source.get("source_commit"),
        "source_snapshot_sha256": source.get("source_snapshot_sha256"),
        "manifest_sha256": source.get("manifest_sha256"),
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
    environment[CHILD_CAPACITY_ENV] = str(
        max(1, int(check.get("_child_capacity", 1)))
    )
    environment["ALATYR_CHECK_VERBOSE"] = "1" if check.get("_verbose") else "0"
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


def reusable_results(
    *,
    selected: list[dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
    commands_by_id: dict[str, list[str]],
) -> dict[str, tuple[int, str, str, list[str]]]:
    results: dict[str, tuple[int, str, str, list[str]]] = {}
    for check in selected:
        check_id = check["id"]
        decision = decisions.get(check_id, {})
        if decision.get("reusable") is True:
            results[check_id] = (
                0,
                f"REUSED: {decision.get('reason', 'previous result reused')}\n",
                "",
                commands_by_id[check_id],
            )
    return results


def effective_baseline(
    profile: str, changed_from: str | None, from_ref: str | None
) -> str | None:
    """Use changed-file baseline as the change-drift baseline when unambiguous."""

    if from_ref:
        return from_ref
    if profile in {"change", "full"}:
        return changed_from
    return None


def environment_report() -> dict[str, Any]:
    dependencies: dict[str, str] = {}
    for dependency in ["jsonschema", "PyYAML"]:
        try:
            dependencies[dependency] = package_version(dependency)
        except PackageNotFoundError:
            dependencies[dependency] = "not-installed"
    git_version = subprocess.run(
        ["git", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    visible_environment = {
        name: os.environ.get(name)
        for name in [
            "LANG",
            "LC_ALL",
            "PYTHONHASHSEED",
            "PYTHONIOENCODING",
            "TZ",
        ]
    }
    return {
        "platform": current_platform(),
        "platform_detail": platform.platform(),
        "python": sys.version,
        "python_executable": sys.executable,
        "python_implementation": platform.python_implementation(),
        "filesystem_encoding": sys.getfilesystemencoding(),
        "preferred_encoding": locale.getpreferredencoding(False),
        "dependencies": dependencies,
        "external_tools": {
            "git": (
                git_version.stdout.strip()
                if git_version.returncode == 0
                else "unavailable"
            )
        },
        "visible_environment": visible_environment,
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
    manifest_bytes = MANIFEST.read_bytes()
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    manifest_data = json.loads(manifest_bytes.decode("utf-8"))
    return {
        "source_commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "source_tree_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
        "manifest_path": MANIFEST.relative_to(ROOT).as_posix(),
        "manifest_sha256": manifest_digest,
        "check_manifest_schema_version": manifest_data.get("schema_version"),
    }


def historical_duration_estimates(
    previous_report: dict[str, Any] | None,
    *,
    current_source: dict[str, Any],
    current_environment: dict[str, Any],
) -> dict[str, float]:
    """Return ordering hints only for a compatible report/runtime contract."""

    if (
        not isinstance(previous_report, dict)
        or previous_report.get("schema_version") != 3
    ):
        return {}
    previous_source = previous_report.get("source")
    previous_environment = previous_report.get("environment")
    if not isinstance(previous_source, dict) or not isinstance(
        previous_environment, dict
    ):
        return {}
    if previous_source.get("check_manifest_schema_version") != current_source.get(
        "check_manifest_schema_version"
    ):
        return {}
    if previous_environment.get("platform") != current_environment.get("platform"):
        return {}
    previous_python = str(previous_environment.get("python", "")).split()[0]
    current_python = str(current_environment.get("python", "")).split()[0]
    if previous_python.split(".")[:2] != current_python.split(".")[:2]:
        return {}
    return {
        item["id"]: float(
            item.get("duration_hint_seconds", item.get("duration_seconds", 0.0))
        )
        for item in previous_report.get("checks", [])
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and item.get("status") in {"passed", "reused-pass"}
        and isinstance(
            item.get("duration_hint_seconds", item.get("duration_seconds")),
            (int, float),
        )
        and item.get("duration_hint_seconds", item.get("duration_seconds", 0.0)) > 0
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
    input_fingerprints: dict[str, dict[str, Any]] | None = None,
    reuse: dict[str, dict[str, Any]] | None = None,
    source: dict[str, Any] | None = None,
    environment: dict[str, Any] | None = None,
    run_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    telemetry = telemetry or {}
    input_fingerprints = input_fingerprints or {}
    reuse = reuse or {}
    resolved_source = source or source_identity()
    resolved_environment = environment or environment_report()
    resolved_selection = selection or {
        "profile": profile,
        "effective_profile": profile,
        "platform": current_platform(),
        "changed_from": None,
        "changed_path_count": 0,
        "changed_paths": [],
        "unmatched_changed_paths": [],
        "fell_back_to_full": False,
        "escalated_from_micro": False,
        "micro_escalation_reasons": [],
        "selected_check_ids": [check["id"] for check in selected],
        "resource_class_counts": {},
        "checks": [],
        "broad_trigger_diagnostics": {
            "selected_count": 0,
            "checks": [],
            "limitation": "selection details unavailable",
        },
    }
    resolved_run_identity = run_identity or {
        "contract": RUN_IDENTITY_CONTRACT,
        "requested_profile": profile,
        "effective_profile": resolved_selection.get("effective_profile", profile),
        "platform": resolved_selection.get("platform"),
        "jobs": None,
        "selected_check_ids": resolved_selection.get("selected_check_ids", []),
        "changed_paths": resolved_selection.get("changed_paths", []),
        "unmatched_changed_paths": resolved_selection.get(
            "unmatched_changed_paths", []
        ),
        "fell_back_to_full": resolved_selection.get("fell_back_to_full", False),
        "escalated_from_micro": resolved_selection.get(
            "escalated_from_micro", False
        ),
        "micro_escalation_reasons": resolved_selection.get(
            "micro_escalation_reasons", []
        ),
        "check_scope": [],
        "changed_from": {"name": None, "commit_oid": None},
        "baseline": {"name": None, "commit_oid": None},
        "source_commit": resolved_source.get("source_commit"),
        "source_snapshot_sha256": resolved_source.get("source_snapshot_sha256"),
        "manifest_sha256": resolved_source.get("manifest_sha256"),
    }
    run_identity_sha256 = canonical_digest(resolved_run_identity)
    def catalog_key(entry: dict[str, Any]) -> tuple[str, str, int, str | None]:
        return (
            str(entry.get("path")),
            str(entry.get("kind")),
            int(entry.get("mode", 0)),
            entry.get("digest") if isinstance(entry.get("digest"), str) else None,
        )

    catalog_entries: dict[tuple[str, str, int, str | None], dict[str, Any]] = {}
    for fingerprint in input_fingerprints.values():
        for entry in fingerprint.get("entries", []):
            if not isinstance(entry, dict):
                continue
            catalog_entries[catalog_key(entry)] = entry
    ordered_catalog = [catalog_entries[key] for key in sorted(catalog_entries)]
    catalog_ids = {
        catalog_key(entry): index for index, entry in enumerate(ordered_catalog)
    }

    def compact_fingerprint(check_id: str) -> dict[str, Any] | None:
        fingerprint = input_fingerprints.get(check_id)
        if not isinstance(fingerprint, dict):
            return None
        compact = {
            key: value
            for key, value in fingerprint.items()
            if key != "entries"
        }
        compact["entry_ids"] = [
            catalog_ids[catalog_key(entry)]
            for entry in fingerprint.get("entries", [])
            if isinstance(entry, dict) and catalog_key(entry) in catalog_ids
        ]
        return compact

    def compact_reuse(check_id: str) -> dict[str, Any] | None:
        decision = reuse.get(check_id)
        if not isinstance(decision, dict):
            return None
        return {key: value for key, value in decision.items() if key != "input_fingerprint"}
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
            "duration_hint_seconds": observation.get(
                "duration_hint_seconds", observation.get("duration_seconds", 0.0)
            ),
            "queued_seconds": observation.get("queued_seconds", 0.0),
            "completed_after_seconds": observation.get("completed_after_seconds", 0.0),
            "timed_out": observation.get("timed_out", False),
            "selection_reasons": selected_metadata.get("reasons", []),
            "matched_changed_paths": selected_metadata.get("matched_changed_paths", []),
            "broad_trigger_patterns": selected_metadata.get("broad_trigger_patterns", []),
            "input_fingerprint": compact_fingerprint(check_id),
            "reuse": compact_reuse(check_id),
        }
        if check_id in blocked:
            checks.append(
                {
                    "id": check_id,
                    "status": "blocked",
                    "blocked_by": blocked[check_id],
                    "result_provenance": {
                        "kind": "not-executed",
                        "run_identity_sha256": run_identity_sha256,
                    },
                    **common,
                }
            )
            continue
        code, stdout, stderr, command = results[check_id]
        status = "passed" if code == 0 else "failed"
        if observation.get("reused") is True and code == 0:
            status = "reused-pass"
        provenance_kind = (
            "reused" if observation.get("reused") is True else "executed"
        )
        checks.append(
            {
                "id": check_id,
                "status": status,
                "exit_code": code,
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "result_provenance": {
                    "kind": provenance_kind,
                    "run_identity_sha256": run_identity_sha256,
                },
                **common,
            }
        )
    completed = len(checks) == len(selected)
    successful = completed and not source_changes and all(
        item.get("status") in {"passed", "reused-pass"} for item in checks
    )
    reused_check_ids = [
        item["id"] for item in checks if item.get("status") == "reused-pass"
    ]
    return {
        "schema_version": 3,
        "report_kind": "alatyr-source-check-run",
        "profile": profile,
        "source": resolved_source,
        "timing": timing,
        "selection": resolved_selection,
        "reuse_contract": {
            "contract": REUSE_CONTRACT,
            "completed": completed,
            "successful": successful,
            "run_identity": resolved_run_identity,
            "run_identity_sha256": run_identity_sha256,
            "environment_sha256": environment_fingerprint(resolved_environment)[
                "sha256"
            ],
        },
        "acceptance_evidence": {
            "eligible": successful and not reused_check_ids,
            "mode": "cold-execution" if not reused_check_ids else "local-result-reuse",
            "reused_check_ids": reused_check_ids,
            "limitation": (
                None
                if not reused_check_ids
                else "reused local results are optimization evidence, not cold release evidence"
            ),
        },
        "environment": resolved_environment,
        "source_write_scope": {
            "declared": "none",
            "preserved": not source_changes,
            "changes": source_changes,
        },
        "input_catalog": {
            "contract": "alatyr-source-check-input-catalog-v1",
            "entries": ordered_catalog,
        },
        "checks": checks,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_timed_report(
    *,
    profile: str,
    selected: list[dict[str, Any]],
    results: dict[str, tuple[int, str, str, list[str]]],
    blocked: dict[str, list[str]],
    source_changes: list[str],
    telemetry: dict[str, dict[str, Any]],
    input_fingerprints: dict[str, dict[str, Any]],
    reuse: dict[str, dict[str, Any]],
    selection: dict[str, Any],
    source: dict[str, Any],
    environment: dict[str, Any],
    run_identity: dict[str, Any],
) -> dict[str, Any]:
    """Build a report and state the timing boundary it can measure honestly."""

    started = time.monotonic()
    report = render_report(
        profile=profile,
        selected=selected,
        results=results,
        blocked=blocked,
        source_changes=source_changes,
        telemetry=telemetry,
        input_fingerprints=input_fingerprints,
        reuse=reuse,
        selection=selection,
        source=source,
        environment=environment,
        run_identity=run_identity,
    )
    report["timing"]["report_preparation_seconds"] = round(
        time.monotonic() - started, 6
    )
    report["timing"]["report_timing_scope"] = (
        "report construction before final JSON serialization"
    )
    return report


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
    initial_results: dict[str, tuple[int, str, str, list[str]]] | None = None,
    duration_estimates: dict[str, float] | None = None,
) -> tuple[
    dict[str, tuple[int, str, str, list[str]]],
    dict[str, list[str]],
]:
    """Run a selected dependency graph and block checks after failed prerequisites."""

    selected_ids = {check["id"] for check in checks}
    results: dict[str, tuple[int, str, str, list[str]]] = dict(initial_results or {})
    remaining = {
        check["id"]: check for check in checks if check["id"] not in results
    }
    blocked: dict[str, list[str]] = {}

    observations = telemetry if telemetry is not None else {}
    run_started = time.monotonic()
    queued_since = {check["id"]: run_started for check in checks}
    estimates = duration_estimates or {}
    for check_id in results:
        observations[check_id] = {
            "duration_seconds": 0.0,
            "duration_hint_seconds": max(0.0, float(estimates.get(check_id, 0.0))),
            "queued_seconds": 0.0,
            "completed_after_seconds": 0.0,
            "timed_out": False,
            "reused": True,
        }

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

    direct_dependents: dict[str, set[str]] = {check_id: set() for check_id in selected_ids}
    for check in checks:
        for dependency in check["depends_on"]:
            if dependency in direct_dependents:
                direct_dependents[dependency].add(check["id"])

    descendant_counts: dict[str, int] = {}

    def descendant_count(check_id: str) -> int:
        cached = descendant_counts.get(check_id)
        if cached is not None:
            return cached
        descendants: set[str] = set()
        pending = list(direct_dependents[check_id])
        while pending:
            dependent = pending.pop()
            if dependent in descendants:
                continue
            descendants.add(dependent)
            pending.extend(direct_dependents[dependent])
        descendant_counts[check_id] = len(descendants)
        return len(descendants)

    manifest_order = {check["id"]: index for index, check in enumerate(checks)}
    dependency_depths: dict[str, int] = {}

    def dependency_depth(check_id: str) -> int:
        cached = dependency_depths.get(check_id)
        if cached is not None:
            return cached
        dependencies = [
            dependency
            for dependency in remaining.get(check_id, {}).get("depends_on", [])
            if dependency in selected_ids
        ]
        depth = 0 if not dependencies else 1 + max(
            dependency_depth(dependency) for dependency in dependencies
        )
        dependency_depths[check_id] = depth
        return depth

    remaining_duration: dict[str, float] = {}

    def critical_path_duration(check_id: str) -> float:
        cached = remaining_duration.get(check_id)
        if cached is not None:
            return cached
        own = max(0.001, float(estimates.get(check_id, 0.0)))
        downstream = [
            critical_path_duration(item) for item in direct_dependents[check_id]
        ]
        value = own + (max(downstream) if downstream else 0.0)
        remaining_duration[check_id] = value
        return value

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
                            "duration_hint_seconds": max(
                                0.0, float(estimates.get(check_id, 0.0))
                            ),
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
            ready = [
                check
                for check in checks
                if check["id"] in remaining
                and all(
                    dependency not in selected_ids
                    or (dependency in results and results[dependency][0] == 0)
                    for dependency in check["depends_on"]
                )
            ]
            return sorted(
                ready,
                key=lambda check: (
                    -critical_path_duration(check["id"]),
                    -descendant_count(check["id"]),
                    -dependency_depth(check["id"]),
                    resource_weight(check),
                    manifest_order[check["id"]],
                ),
            )

        def submit_ready() -> bool:
            nonlocal running_weight
            submitted = False
            for check in ready_checks():
                weight = resource_weight(check)
                if running and running_weight + weight > jobs:
                    continue
                scheduled_check = {**check, "_child_capacity": weight}
                future = executor.submit(run_with_observation, scheduled_check)
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
                            "duration_hint_seconds": duration_seconds,
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
                            "duration_hint_seconds": max(
                                0.0, float(estimates.get(check_id, 0.0))
                            ),
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
            "schedule": (
                "historical-critical-path" if estimates else "dependency-critical-path"
            ),
        }

    return results, blocked


def _warning_lines(text: str) -> list[str]:
    return [
        line
        for line in text.splitlines()
        if line.lstrip().upper().startswith(("WARN", "WARNING"))
    ]


def print_check_result(
    *,
    check_id: str,
    result: tuple[int, str, str, list[str]],
    observation: dict[str, Any],
    verbose: bool,
) -> None:
    """Render concise successful output while retaining complete failure evidence."""

    code, stdout, stderr, command = result
    if observation.get("reused") is True:
        print(f"REUSED {check_id}", flush=True)
        return
    if verbose or code != 0:
        print("$ " + " ".join(command), flush=True)
        if stdout:
            print(stdout, end="" if stdout.endswith("\n") else "\n")
        if stderr:
            print(stderr, end="" if stderr.endswith("\n") else "\n", file=sys.stderr)
        return
    duration = float(observation.get("duration_seconds", 0.0))
    print(f"PASS {check_id} ({duration:.3f}s)", flush=True)
    for line in _warning_lines(stdout):
        print(line)
    for line in _warning_lines(stderr):
        print(line, file=sys.stderr)


def finalize_run(run: CompletedSourceCheckRun) -> int:
    """Verify write scope, publish evidence, and report the completed run."""

    failures: list[str] = []
    for check in run.selected:
        if check["id"] in run.blocked:
            dependencies = ", ".join(run.blocked[check["id"]])
            print(
                f"SKIPPED {check['id']}: blocked by failed dependencies: {dependencies}",
                file=sys.stderr,
            )
            failures.append(check["id"])
            continue
        result = run.results[check["id"]]
        print_check_result(
            check_id=check["id"],
            result=result,
            observation=run.telemetry.get(check["id"], {}),
            verbose=run.args.verbose,
        )
        if result[0] != 0:
            failures.append(check["id"])

    try:
        final_snapshot = source_snapshot(ROOT)
        final_source_changes = snapshot_changes(run.before, final_snapshot)
        final_index = SourceSnapshotIndex(final_snapshot)
        final_identity = build_run_identity(
            requested_profile=run.args.profile,
            selection=run.selection,
            changed_from=run.changed_from,
            baseline=run.baseline,
            source={
                **source_identity(),
                "source_snapshot_sha256": final_index.sha256,
            },
            jobs=run.jobs,
        )
        if final_identity != run.run_identity:
            final_source_changes = sorted(
                {
                    *final_source_changes,
                    "execution identity changed during source checks",
                }
            )
    except (OSError, ValueError) as exc:
        print(f"FAIL: cannot verify final source write scope: {exc}", file=sys.stderr)
        failures.append("source-write-scope")
        final_source_changes = run.source_changes
    source_changes = final_source_changes
    if source_changes:
        print("\nFAILED read-only source-check write scope:", file=sys.stderr)
        for change in source_changes:
            print(f"- {change}", file=sys.stderr)
        failures.append("source-write-scope")

    generated_report: dict[str, Any] | None = None
    if run.report_path is not None or run.cache is not None:
        generated_report = render_timed_report(
            profile=run.args.profile,
            selected=run.selected,
            results=run.results,
            blocked=run.blocked,
            source_changes=source_changes,
            telemetry=run.telemetry,
            input_fingerprints=run.input_fingerprints,
            reuse=run.reuse,
            selection=run.selection,
            source=run.current_source,
            environment=run.current_environment,
            run_identity=run.run_identity,
        )
    if run.report_path is not None and generated_report is not None:
        try:
            write_report(run.report_path, generated_report)
        except OSError as exc:
            print(f"FAIL: cannot write source-check report: {exc}", file=sys.stderr)
            failures.append("source-check-report")

    if run.cache is not None and generated_report is not None and not failures:
        try:
            stored_checks = 0
            for check in run.selected:
                check_id = check["id"]
                fingerprint = run.input_fingerprints.get(check_id, {})
                observation = run.telemetry.get(check_id, {})
                result = run.results.get(check_id)
                if (
                    result is None
                    or result[0] != 0
                    or observation.get("reused") is True
                    or fingerprint.get("reuse_eligible") is not True
                ):
                    continue
                identity = check_cache_identity(
                    check=check,
                    command=result[3],
                    input_fingerprint=fingerprint,
                    environment=run.current_environment,
                    run_identity=run.run_identity,
                )
                run.cache.store(
                    "checks",
                    check_result_key(check_id, identity),
                    {
                        "contract": CHECK_RESULT_CONTRACT,
                        "identity": identity,
                        "status": "passed",
                        "timed_out": False,
                    },
                )
                stored_checks += 1
            run.cache_events.append(f"checks:stored={stored_checks}")
            run.cache.prune("checks", max_records=MAX_CHECK_CACHE_RECORDS)
            run.cache.store(
                "timing",
                cache_key(run.args.profile, include_profile=False),
                generated_report,
            )
            run.cache_events.append("timing:stored")
            if (
                run.args.cache_mode == "local"
                and generated_report["acceptance_evidence"]["eligible"] is True
            ):
                run.cache.store(
                    "results", cache_key(run.args.profile), generated_report
                )
                run.cache_events.append("results:stored")
        except (OSError, ValueError) as exc:
            run.cache_events.append(f"store-skipped:{exc}")

    for event in run.cache_events:
        if event.startswith(("disabled:", "store-skipped:")):
            print(f"WARNING: source-check cache {event}", file=sys.stderr)
    if failures:
        print("\nFAILED source checks:", file=sys.stderr)
        for check_id in failures:
            print(f"- {check_id}", file=sys.stderr)
        return 1

    profile_label = run.args.profile
    if run.plan.effective_profile != run.args.profile:
        profile_label = f"{run.args.profile} (effective {run.plan.effective_profile})"
    reused_count = sum(
        run.telemetry.get(check["id"], {}).get("reused") is True
        for check in run.selected
    )
    suffix = (
        "; local reused results are not cold release evidence"
        if reused_count
        else ""
    )
    print(
        f"\nOK: ran {len(run.selected)} source checks from profile {profile_label}{suffix}"
    )
    return 0


def argument_parser() -> argparse.ArgumentParser:
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
        help="With --profile fast, run all fast checks without changed-path selection.",
    )
    parser.add_argument("--from-ref", help="Baseline substituted into change checks.")
    parser.add_argument(
        "--jobs",
        default=DEFAULT_JOBS,
        help=(
            "Parallel source-check capacity. Use a positive integer, or opt in "
            "to affinity/quota-aware sizing with 'auto'."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print complete output for successful checks as well as failures.",
    )
    parser.add_argument("--list", action="store_true")
    parser.add_argument(
        "--report",
        type=Path,
        help="Write a machine-readable run report to this explicit output path.",
    )
    parser.add_argument(
        "--reuse-report",
        type=Path,
        help=(
            "Optionally reuse passed checks from a previous source-check report "
            "when manifest, command, runtime, and input fingerprints match."
        ),
    )
    parser.add_argument(
        "--cache-mode",
        choices=("off", "timing", "local"),
        default="off",
        help=(
            "Optional Git-local optimization cache: 'timing' changes scheduling "
            "only; 'local' also attempts exact result reuse."
        ),
    )
    return parser


def main() -> int:
    process_started = time.monotonic()
    parser = argument_parser()
    args = parser.parse_args()
    try:
        jobs = resolve_job_count(args.jobs)
    except ValueError as exc:
        parser.error(str(exc))
    jobs_mode = "auto" if str(args.jobs).lower() == "auto" else "fixed"
    if args.all_fast and args.profile != "fast":
        parser.error("--all-fast is only valid with --profile fast")
    if args.all_fast and args.changed_from:
        parser.error("--all-fast cannot be combined with --changed-from")
    if args.profile == "release" and args.reuse_report is not None:
        parser.error("--reuse-report is not permitted for release validation")
    if args.profile == "release" and args.cache_mode == "local":
        parser.error("--cache-mode local is not permitted for release validation")

    cache: SourceCheckCache | None = None
    cache_events: list[str] = []
    try:
        checks = load_manifest()
        changed_from = resolve_changed_from(
            args.profile, args.changed_from, all_fast=args.all_fast
        )
        baseline = effective_baseline(args.profile, changed_from, args.from_ref)
        plan = select_check_plan(checks, args.profile, changed_from)
        selected = [{**check, "_verbose": args.verbose} for check in plan.selected]
        commands = [resolved_command(check, baseline) for check in selected]
        commands_by_id = {
            check["id"]: command for check, command in zip(selected, commands)
        }
        selection = selection_report(
            profile=args.profile,
            changed_from=changed_from,
            plan=plan,
        )
        report_path = resolve_report_path(args.report) if args.report else None
        previous_report = load_reuse_report(args.reuse_report) if args.reuse_report else None
        timing_report = previous_report
        if args.cache_mode != "off":
            try:
                cache = SourceCheckCache(ROOT)
                timing_load = cache.load(
                    "timing", cache_key(args.profile, include_profile=False)
                )
                cache_events.append(f"timing:{timing_load.status}")
                if timing_report is None and timing_load.status == "hit":
                    timing_report = timing_load.value
            except (OSError, ValueError) as exc:
                cache_events.append(f"disabled:{exc}")
                cache = None
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
    if plan.escalated_from_micro:
        print("INFO: micro profile escalated to fast", flush=True)
        for reason in plan.micro_escalation_reasons or []:
            print(f"INFO: micro escalation: {reason}", flush=True)

    try:
        before = source_snapshot(ROOT)
        snapshot_index = SourceSnapshotIndex(before)
        fingerprint_started = time.monotonic()
        input_fingerprints = (
            {
                check["id"]: check_input_fingerprint(check, snapshot_index)
                for check in selected
            }
            if report_path is not None
            or previous_report is not None
            or args.cache_mode == "local"
            else {}
        )
        fingerprint_seconds = time.monotonic() - fingerprint_started
        current_source = {
            **source_identity(),
            "source_snapshot_sha256": snapshot_index.sha256,
        }
        current_environment = environment_report()
        run_identity = build_run_identity(
            requested_profile=args.profile,
            selection=selection,
            changed_from=changed_from,
            baseline=baseline,
            source=current_source,
            jobs=jobs,
        )
        if previous_report is not None:
            reuse = reuse_decisions(
                selected=selected,
                previous_report=previous_report,
                current_source=current_source,
                current_environment=current_environment,
                input_fingerprints=input_fingerprints,
                commands_by_id=commands_by_id,
                current_run_identity=run_identity,
            )
        elif cache is not None and args.cache_mode == "local":
            reuse = {}
            cache_hits = 0
            cache_misses = 0
            for check in selected:
                check_id = check["id"]
                identity = check_cache_identity(
                    check=check,
                    command=commands_by_id[check_id],
                    input_fingerprint=input_fingerprints[check_id],
                    environment=current_environment,
                    run_identity=run_identity,
                )
                loaded = cache.load(
                    "checks", check_result_key(check_id, identity)
                )
                decision = cached_check_decision(
                    record=loaded.value if loaded.status == "hit" else None,
                    identity=identity,
                    input_fingerprint=input_fingerprints[check_id],
                )
                reuse[check_id] = decision
                if decision["reusable"]:
                    cache_hits += 1
                else:
                    cache_misses += 1
            cache_events.append(
                f"checks:hits={cache_hits},misses={cache_misses}"
            )
        else:
            reuse = {}
        initial_results = reusable_results(
            selected=selected,
            decisions=reuse,
            commands_by_id=commands_by_id,
        )
        telemetry: dict[str, dict[str, Any]] = {}
        duration_estimates = historical_duration_estimates(
            timing_report,
            current_source=current_source,
            current_environment=current_environment,
        )
        execution_started = time.monotonic()
        results, blocked = execute_checks(
            selected,
            baseline,
            jobs,
            telemetry=telemetry,
            initial_results=initial_results,
            duration_estimates=duration_estimates,
        )
        execution_finished = time.monotonic()
        source_changes: list[str] = []
        verification_finished = execution_finished
        telemetry.setdefault("_summary", {}).update(
            {
                "setup_seconds": round(
                    max(
                        0.0,
                        execution_started - process_started - fingerprint_seconds,
                    ),
                    6,
                ),
                "fingerprint_seconds": round(fingerprint_seconds, 6),
                "execution_seconds": round(execution_finished - execution_started, 6),
                "post_execution_verification_seconds": round(
                    verification_finished - execution_finished, 6
                ),
                "elapsed_before_reporting_seconds": round(
                    verification_finished - process_started, 6
                ),
                "jobs_mode": jobs_mode,
                "resolved_jobs": jobs,
            }
        )
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    return finalize_run(
        CompletedSourceCheckRun(
            args=args,
            jobs=jobs,
            changed_from=changed_from,
            baseline=baseline,
            plan=plan,
            selected=selected,
            results=results,
            blocked=blocked,
            telemetry=telemetry,
            before=before,
            source_changes=source_changes,
            input_fingerprints=input_fingerprints,
            reuse=reuse,
            selection=selection,
            current_source=current_source,
            current_environment=current_environment,
            run_identity=run_identity,
            report_path=report_path,
            cache=cache,
            cache_events=cache_events,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
