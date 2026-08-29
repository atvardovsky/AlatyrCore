#!/usr/bin/env python3
"""Run dependency-aware AlatyrCore source-repository validation profiles."""

from __future__ import annotations

import argparse
import concurrent.futures
import fnmatch
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


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tools" / "check_manifest.json"
ALLOWED_PROFILES = {"quick", "fast", "full", "change", "platform", "release"}
ALLOWED_WRITE_SCOPES = {"none"}
ALLOWED_PLATFORMS = {"all", "linux", "macos", "windows"}
ALLOWED_RESOURCE_CLASSES = {"light", "standard", "heavy"}
RESOURCE_CLASS_WEIGHTS = {"light": 1, "standard": 1, "heavy": 2}
TIMEOUT_EXIT_CODE = 124


@dataclass(frozen=True)
class RunnerResult:
    """Process result metadata that legacy test runners do not need to provide."""

    result: tuple[int, str, str, list[str]]
    timed_out: bool = False


def _valid_manifest_path(value: str) -> bool:
    """Accept portable repository-relative literal or glob path declarations."""

    path = Path(value)
    return (
        bool(value)
        and "\\" not in value
        and not path.is_absolute()
        and ".." not in path.parts
        and "." not in path.parts
    )


def _validate_path_list(check_id: str, field: str, value: Any) -> list[str]:
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and _valid_manifest_path(item) for item in value
    ):
        raise ValueError(f"{check_id}.{field} is invalid")
    if len(value) != len(set(value)):
        raise ValueError(f"{check_id}.{field} contains duplicate paths")
    return value


def load_manifest() -> list[dict[str, Any]]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("schema_version") != 2 or data.get("manifest_kind") != "alatyr-source-checks":
        raise ValueError("unsupported source check manifest")
    defaults = data.get("defaults")
    checks = data.get("checks")
    if not isinstance(defaults, dict) or not isinstance(checks, list) or not checks:
        raise ValueError("check manifest must define defaults and checks")

    normalized: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, raw in enumerate(checks):
        if not isinstance(raw, dict):
            raise ValueError(f"checks[{index}] must be an object")
        check = {**defaults, **raw}
        check_id = check.get("id")
        command = check.get("command")
        profiles = check.get("profiles")
        platforms = check.get("platforms")
        if "owned_paths" in check:
            raise ValueError(f"{check_id}.owned_paths is obsolete; use contract_inputs")
        contract_inputs = _validate_path_list(
            check_id, "contract_inputs", check.get("contract_inputs")
        )
        implementation_paths = _validate_path_list(
            check_id, "implementation_paths", check.get("implementation_paths")
        )
        trigger_paths = _validate_path_list(
            check_id, "trigger_paths", check.get("trigger_paths")
        )
        dependencies = check.get("depends_on")
        if not isinstance(check_id, str) or not check_id or check_id in ids:
            raise ValueError(f"checks[{index}] has invalid or duplicate id")
        if not isinstance(command, list) or not command or not all(
            isinstance(value, str) and value for value in command
        ):
            raise ValueError(f"{check_id}.command must contain strings")
        script = command[0]
        if not script.startswith("tools/") or Path(script).is_absolute() or ".." in Path(script).parts:
            raise ValueError(f"{check_id}.command has unsafe script path")
        if not (ROOT / script).is_file():
            raise ValueError(f"{check_id}.command script does not exist: {script}")
        if not isinstance(profiles, list) or not profiles or not set(profiles) <= ALLOWED_PROFILES:
            raise ValueError(f"{check_id}.profiles is invalid")
        if (
            not isinstance(platforms, list)
            or not platforms
            or not set(platforms) <= ALLOWED_PLATFORMS
        ):
            raise ValueError(f"{check_id}.platforms is invalid")
        if check.get("write_scope") not in ALLOWED_WRITE_SCOPES:
            raise ValueError(f"{check_id}.write_scope is invalid")
        if script not in implementation_paths:
            raise ValueError(f"{check_id}.implementation_paths must include its command script")
        overlap = sorted(set(contract_inputs) & set(implementation_paths))
        if overlap:
            raise ValueError(
                f"{check_id} declarations overlap between contract_inputs and "
                f"implementation_paths: {overlap}"
            )
        undeclared_triggers = sorted(
            set(contract_inputs + implementation_paths) - set(trigger_paths)
        )
        if undeclared_triggers:
            raise ValueError(
                f"{check_id}.trigger_paths must include every contract or "
                f"implementation input: {undeclared_triggers}"
            )
        timeout_seconds = check.get("timeout_seconds")
        if (
            not isinstance(timeout_seconds, int)
            or isinstance(timeout_seconds, bool)
            or timeout_seconds <= 0
        ):
            raise ValueError(f"{check_id}.timeout_seconds is invalid")
        if check.get("resource_class") not in ALLOWED_RESOURCE_CLASSES:
            raise ValueError(f"{check_id}.resource_class is invalid")
        if not isinstance(check.get("always_for_changed", False), bool):
            raise ValueError(f"{check_id}.always_for_changed must be boolean")
        if not isinstance(dependencies, list) or not all(
            isinstance(value, str) and value for value in dependencies
        ):
            raise ValueError(f"{check_id}.depends_on is invalid")
        ids.add(check_id)
        check["contract_inputs"] = contract_inputs
        check["implementation_paths"] = implementation_paths
        check["trigger_paths"] = trigger_paths
        check["always_for_changed"] = check.get("always_for_changed", False)
        normalized.append(check)

    by_id = {check["id"]: check for check in normalized}
    for check in normalized:
        unknown = sorted(set(check["depends_on"]) - set(by_id))
        if unknown:
            raise ValueError(f"{check['id']} has unknown dependencies: {unknown}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(check_id: str) -> None:
        if check_id in visiting:
            raise ValueError(f"check dependency cycle includes {check_id}")
        if check_id in visited:
            return
        visiting.add(check_id)
        for dependency in by_id[check_id]["depends_on"]:
            visit(dependency)
        visiting.remove(check_id)
        visited.add(check_id)

    for check_id in by_id:
        visit(check_id)
    return normalized


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


def matches(check: dict[str, Any], path: str) -> bool:
    """Whether a path is declared as a checked contract or implementation input."""

    return any(
        fnmatch.fnmatch(path, pattern)
        for pattern in [*check["contract_inputs"], *check["implementation_paths"]]
    )


def routes(check: dict[str, Any], path: str) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in check["trigger_paths"])


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


def select_checks(
    checks: list[dict[str, Any]],
    profile: str,
    changed_from: str | None,
    *,
    platform: str | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    selected_platform = platform or current_platform()
    if profile == "release":
        selected_ids = {
            check["id"]
            for check in checks
            if "full" in check["profiles"] or "release" in check["profiles"]
            if supports_platform(check, selected_platform)
        }
    elif profile == "fast" and changed_from:
        selected_ids = {
            check["id"]
            for check in checks
            if check.get("always_for_changed", False)
            and supports_platform(check, selected_platform)
        }
    else:
        selected_ids = {
            check["id"]
            for check in checks
            if profile in check["profiles"] and supports_platform(check, selected_platform)
        }

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
        else:
            selected_ids.update(
                check["id"]
                for check in full_checks
                if any(routes(check, path) for path in changed)
            )

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
                add_dependencies(dependency)

    for check_id in list(selected_ids):
        add_dependencies(check_id)
    return [check for check in checks if check["id"] in selected_ids], fell_back_to_full


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


def render_report(
    *,
    profile: str,
    selected: list[dict[str, Any]],
    results: dict[str, tuple[int, str, str, list[str]]],
    blocked: dict[str, list[str]],
    source_changes: list[str],
    telemetry: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    telemetry = telemetry or {}
    for check in selected:
        check_id = check["id"]
        observation = telemetry.get(check_id, {})
        common = {
            "resource_class": check.get("resource_class", "standard"),
            "timeout_seconds": check.get("timeout_seconds"),
            "duration_seconds": observation.get("duration_seconds", 0.0),
            "timed_out": observation.get("timed_out", False),
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
        while remaining:
            newly_blocked: list[str] = []
            for check_id, check in remaining.items():
                failed_dependencies = [
                    dependency
                    for dependency in check["depends_on"]
                    if dependency in blocked
                    or (dependency in results and results[dependency][0] != 0)
                ]
                if failed_dependencies:
                    blocked[check_id] = sorted(failed_dependencies)
                    newly_blocked.append(check_id)
            for check_id in newly_blocked:
                remaining.pop(check_id)

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
            if not ready:
                if remaining:
                    unresolved = ", ".join(sorted(remaining))
                    raise ValueError(f"unresolvable selected check dependencies: {unresolved}")
                break

            batch: list[dict[str, Any]] = []
            remaining_capacity = jobs
            for check in ready:
                weight = resource_weight(check)
                if weight <= remaining_capacity:
                    batch.append(check)
                    remaining_capacity -= weight
            if not batch:
                batch = [ready[0]]

            futures = {
                executor.submit(run_with_observation, check): check for check in batch
            }
            for future in concurrent.futures.as_completed(futures):
                check = futures[future]
                check_id = check["id"]
                try:
                    result, timed_out, duration_seconds = future.result()
                    results[check_id] = result
                    observations[check_id] = {
                        "duration_seconds": duration_seconds,
                        "timed_out": timed_out,
                    }
                except Exception as exc:  # pragma: no cover - executor boundary
                    results[check_id] = (1, "", str(exc), [])
                    observations[check_id] = {
                        "duration_seconds": 0.0,
                        "timed_out": False,
                    }
                remaining.pop(check_id)

    return results, blocked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(ALLOWED_PROFILES), default="full")
    parser.add_argument(
        "--changed-from",
        help=(
            "Select checks from changed paths for focused profiles. For the "
            "change profile, this also acts as --from-ref when --from-ref is omitted."
        ),
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

    try:
        checks = load_manifest()
        baseline = effective_baseline(args.profile, args.changed_from, args.from_ref)
        selected, fell_back = select_checks(checks, args.profile, args.changed_from)
        commands = [resolved_command(check, baseline) for check in selected]
        report_path = resolve_report_path(args.report) if args.report else None
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    if args.list:
        for command in commands:
            print(" ".join(command))
        return 0
    if fell_back:
        print("INFO: unmatched changed paths selected the full check profile", flush=True)

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
