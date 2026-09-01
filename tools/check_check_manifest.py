#!/usr/bin/env python3
"""Validate source-check manifest coverage and selection contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from check_all import load_manifest, matches, routes
from evidence_contract import CONTRACT_FILES, CONTRACT_PREFIXES
from source_check_manifest import (
    SourcePathIndex,
    broad_trigger_patterns,
    declaration_matches_source,
    declared_implementation_path,
    direct_local_tool_dependencies,
)


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_CHECKERS = {"check_all.py", "check_check_manifest.py"}


def evidence_contract_routing_failures(checks: list[dict[str, Any]]) -> list[str]:
    """Require evidence-status routing to cover every digest input.

    Evidence inputs are partly computed in Python, so the general import scan
    cannot infer them from the checker command alone.
    """

    evidence_checks = [check for check in checks if check["id"] == "evidence-status"]
    if len(evidence_checks) != 1:
        return ["manifest must define exactly one evidence-status check"]
    check = evidence_checks[0]
    failures: list[str] = []
    for path in sorted(CONTRACT_FILES):
        if not routes(check, path):
            failures.append(f"evidence-status does not route contract file: {path}")
    for prefix in CONTRACT_PREFIXES:
        probe = f"{prefix}__contract_probe__"
        if not routes(check, probe):
            failures.append(f"evidence-status does not route contract prefix: {prefix}")
    return failures


def tool_command_routing_failures(checks: list[dict[str, Any]]) -> list[str]:
    """Require every stable tool command script to be routed by source checks."""

    path = ROOT / "tools" / "tool_commands.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    commands = data.get("commands") if isinstance(data, dict) else None
    if not isinstance(commands, list):
        return ["tool command manifest must define commands"]
    failures: list[str] = []
    for command in commands:
        if not isinstance(command, dict) or not isinstance(command.get("script"), str):
            failures.append("tool command manifest contains an invalid script entry")
            continue
        script = f"tools/{command['script']}"
        if not any(declared_implementation_path(check, script) for check in checks):
            failures.append(f"tool command script lacks implementation owner: {script}")
        if not any(routes(check, script) for check in checks):
            failures.append(f"tool command script lacks trigger route: {script}")
    return failures


def main() -> int:
    failures: list[str] = []
    try:
        checks = load_manifest()
        source_index = SourcePathIndex.from_root(ROOT)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    commands = [check["command"] for check in checks]
    represented = {Path(command[0]).name for command in commands}
    checker_files = {
        path.name
        for path in (ROOT / "tools").glob("check_*.py")
        if path.name not in EXCLUDED_CHECKERS
    }
    missing = sorted(checker_files - represented)
    if missing:
        failures.append(f"checker scripts missing from manifest: {missing}")

    for check in checks:
        script = check["command"][0]
        if not matches(check, script):
            failures.append(f"{check['id']} does not declare its command script as an input")
        if not declared_implementation_path(check, script):
            failures.append(
                f"{check['id']} implementation_paths do not include its command script"
            )
        for field in ["contract_inputs", "implementation_paths", "trigger_paths"]:
            for path in check[field]:
                if not declaration_matches_source(path, source_index):
                    failures.append(
                        f"{check['id']}.{field} has no matching source path: {path}"
                    )
        for dependency in sorted(direct_local_tool_dependencies(script)):
            if not declared_implementation_path(check, dependency):
                failures.append(
                    f"{check['id']} omits direct local implementation dependency: "
                    f"{dependency}"
                )
        if "release" in check["profiles"] and check["id"] != "release-drift-release" and (
            "full" not in check["profiles"]
        ):
            failures.append(f"release-only helper is not an approved release gate: {check['id']}")

    failures.extend(evidence_contract_routing_failures(checks))
    failures.extend(tool_command_routing_failures(checks))

    drift_commands = [
        command for command in commands if command[0] == "tools/check_release_drift.py"
    ]
    if not any("change" in command for command in drift_commands):
        failures.append("check manifest omits change-baseline release drift")
    if not any("release" in command for command in drift_commands):
        failures.append("check manifest omits tag-baseline release drift")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    broad = {
        check["id"]: broad_trigger_patterns(check)
        for check in checks
        if broad_trigger_patterns(check)
    }
    if broad:
        print(
            "INFO: broad trigger diagnostics are report-visible for "
            f"{len(broad)} check entries"
        )
    print(f"OK: checked {len(checks)} manifest check entries and checker coverage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
