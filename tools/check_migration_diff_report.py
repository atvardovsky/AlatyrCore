#!/usr/bin/env python3
"""Execute and validate the migration diff reporter output shape.

This validates the AlatyrCore source repository only. It is not a portable
framework requirement for target projects.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_OUTPUT_TEXT = [
    "# Alatyr Release Migration Report",
    "## Version Scope",
    "From contract SHA-256:",
    "To contract SHA-256:",
    "## Summary",
    "## Adapter Contract Impact",
    "Framework version:",
    "Adapter schema version:",
    "Template version:",
    "Rule registry:",
    "Rule ownership:",
    "Framework files:",
    "Schema contracts:",
    "Target template surfaces:",
    "## Affected Rule Categories",
    "## Affected Task Profiles",
    "## Affected Canonical Sources",
    "## Migration Action Hints",
    "## Rule Changes",
    "## Rule Owner Changes",
    "## Framework File Changes",
    "## Schema Contract Changes",
    "## Target Template Surface Changes",
    "## Required Target Actions",
    "## Optional Target Actions",
    "## Approval Needs",
    "## Validation Run",
    "## Residual Risks",
    "## Safety",
]

ZERO_CHANGE_TEXT = [
    "- Added rules: 0",
    "- Changed rules: 0",
    "- Removed rules: 0",
    "- Added framework files: 0",
    "- Changed framework files: 0",
    "- Removed framework files: 0",
    "- Added schema contracts: 0",
    "- Changed schema contracts: 0",
    "- Removed schema contracts: 0",
    "- Added target template surfaces: 0",
    "- Changed target template surfaces: 0",
    "- Removed target template surfaces: 0",
]


def run_reporter() -> tuple[str, dict[str, object]]:
    with tempfile.TemporaryDirectory(prefix="alatyr-impact-") as directory:
        json_output = Path(directory) / "upgrade-impact.json"
        result = subprocess.run(
            [
                sys.executable,
                "tools/report_migration_diff.py",
                "--from-rules",
                "framework/rule-registry.json",
                "--to-rules",
                "framework/rule-registry.json",
                "--from-version",
                "current",
                "--to-version",
                "current",
                "--from-adapter-schema-version",
                "current",
                "--to-adapter-schema-version",
                "current",
                "--from-template-version",
                "current",
                "--to-template-version",
                "current",
                "--from-framework-dir",
                "framework",
                "--to-framework-dir",
                "framework",
                "--from-schema-dir",
                "schemas",
                "--to-schema-dir",
                "schemas",
                "--from-template-dir",
                "templates/target",
                "--to-template-dir",
                "templates/target",
                "--json-output",
                str(json_output),
            ],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result.stdout, json.loads(json_output.read_text(encoding="utf-8"))


def main() -> int:
    failures: list[str] = []
    try:
        output, impact = run_reporter()
    except (RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    for required_text in REQUIRED_OUTPUT_TEXT:
        if required_text not in output:
            failures.append(f"migration diff output missing {required_text}")
    for required_text in ZERO_CHANGE_TEXT:
        if required_text not in output:
            failures.append(f"self-compare output missing {required_text}")
    for changed_marker in [
        "- Framework version: `changed`",
        "- Adapter schema version: `changed`",
        "- Template version: `changed`",
    ]:
        if changed_marker in output:
            failures.append(f"self-compare output should not mark {changed_marker}")
    if "contract SHA-256: `not compared`" in output:
        failures.append("self-compare output must bind both contract-tree digests")

    if impact.get("schema_version") != 1:
        failures.append("upgrade impact schema_version must be 1")
    if impact.get("impact_kind") != "alatyr-upgrade-impact":
        failures.append("upgrade impact kind is invalid")
    affected = impact.get("affected")
    if not isinstance(affected, dict) or any(affected.get(field) for field in [
        "rule_ids", "categories", "task_profiles", "canonical_sources"
    ]):
        failures.append("self-compare upgrade impact should have no affected rule surfaces")
    framework_files = impact.get("framework_files")
    if not isinstance(framework_files, dict) or framework_files.get("compared") is not True:
        failures.append("upgrade impact should record compared framework files")
    schema_contracts = impact.get("schema_contracts")
    if (
        not isinstance(schema_contracts, dict)
        or schema_contracts.get("compared") is not True
    ):
        failures.append("upgrade impact should record compared schema contracts")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("OK: checked migration diff reporter output shape")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
