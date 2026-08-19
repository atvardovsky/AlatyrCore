#!/usr/bin/env python3
"""Run dependency-aware AlatyrCore source-repository validation profiles."""

from __future__ import annotations

import argparse
import concurrent.futures
import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tools" / "check_manifest.json"
ALLOWED_PROFILES = {"fast", "full", "change", "platform", "release"}
ALLOWED_WRITE_SCOPES = {"none", "explicit-output-only"}
ALLOWED_PLATFORMS = {"all", "linux", "macos", "windows"}


def load_manifest() -> list[dict[str, Any]]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("manifest_kind") != "alatyr-source-checks":
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
        owned_paths = check.get("owned_paths")
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
        if not isinstance(owned_paths, list) or not owned_paths or not all(
            isinstance(value, str) and value for value in owned_paths
        ):
            raise ValueError(f"{check_id}.owned_paths is invalid")
        if not isinstance(dependencies, list) or not all(
            isinstance(value, str) and value for value in dependencies
        ):
            raise ValueError(f"{check_id}.depends_on is invalid")
        ids.add(check_id)
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
    return any(fnmatch.fnmatch(path, pattern) for pattern in check["owned_paths"])


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
            path for path in changed if not any(matches(check, path) for check in full_checks)
        ]
        if unmatched:
            fell_back_to_full = True
            selected_ids.update(check["id"] for check in full_checks)
        else:
            selected_ids.update(
                check["id"]
                for check in full_checks
                if any(matches(check, path) for path in changed)
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


def run_check(check: dict[str, Any], baseline: str | None) -> tuple[int, str, str, list[str]]:
    command = resolved_command(check, baseline)
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr, command


def execute_checks(
    checks: list[dict[str, Any]],
    baseline: str | None,
    jobs: int,
    *,
    runner: Any = run_check,
) -> tuple[
    dict[str, tuple[int, str, str, list[str]]],
    dict[str, list[str]],
]:
    """Run a selected dependency graph and block checks after failed prerequisites."""

    selected_ids = {check["id"] for check in checks}
    remaining = {check["id"]: check for check in checks}
    results: dict[str, tuple[int, str, str, list[str]]] = {}
    blocked: dict[str, list[str]] = {}

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

            futures = {
                executor.submit(runner, check, baseline): check["id"] for check in ready
            }
            for future in concurrent.futures.as_completed(futures):
                check_id = futures[future]
                try:
                    results[check_id] = future.result()
                except Exception as exc:  # pragma: no cover - defensive process boundary
                    results[check_id] = (1, "", str(exc), [])
                remaining.pop(check_id)

    return results, blocked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(ALLOWED_PROFILES), default="full")
    parser.add_argument("--changed-from", help="Select matching checks for a fast profile.")
    parser.add_argument("--from-ref", help="Baseline substituted into change checks.")
    parser.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.jobs <= 0:
        parser.error("--jobs must be positive")

    try:
        checks = load_manifest()
        selected, fell_back = select_checks(checks, args.profile, args.changed_from)
        commands = [resolved_command(check, args.from_ref) for check in selected]
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
        results, blocked = execute_checks(selected, args.from_ref, args.jobs)
    except ValueError as exc:
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

    if failures:
        print("\nFAILED source checks:", file=sys.stderr)
        for check_id in failures:
            print(f"- {check_id}", file=sys.stderr)
        return 1
    print(f"\nOK: ran {len(selected)} source checks from profile {args.profile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
