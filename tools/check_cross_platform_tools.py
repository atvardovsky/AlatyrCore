#!/usr/bin/env python3
"""Validate cross-platform tool routing and migration-first assessment safety."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MANIFEST = TOOLS / "tool_commands.json"
NATIVE_WORKFLOW = ROOT / ".github" / "workflows" / "cross-platform-source-checks.yml"
EXPECTED_COMMANDS = {
    "check-source",
    "scaffold",
    "validate-adapter",
    "migration-report",
    "assess-upgrade",
    "context-costs",
    "prepare-conformance",
    "check-conformance",
    "prepare-benchmark",
    "check-benchmark",
    "summarize-benchmark",
}
ALLOWED_WRITE_SCOPES = {
    "none",
    "target-structure-with-explicit-write",
    "explicit-report-output-only",
    "explicit-evidence-output-only",
}


def run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOLS / "alatyr.py"), *arguments],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def main() -> int:
    failures: list[str] = []
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: invalid tool command manifest: {exc}", file=sys.stderr)
        return 1

    if data.get("schema_version") != 1:
        failures.append("tool command manifest schema_version must be 1")
    commands = data.get("commands")
    if not isinstance(commands, list):
        failures.append("tool command manifest commands must be a list")
        commands = []
    names = {command.get("name") for command in commands if isinstance(command, dict)}
    if names != EXPECTED_COMMANDS:
        failures.append("tool command manifest command set is incomplete")
    for command in commands:
        if not isinstance(command, dict):
            failures.append("tool command entries must be objects")
            continue
        script = command.get("script")
        if not isinstance(script, str) or not (TOOLS / script).is_file():
            failures.append(f"tool command script is missing: {script}")
        if command.get("write_scope") not in ALLOWED_WRITE_SCOPES:
            failures.append(f"tool command write scope is invalid: {command.get('name')}")
        if not isinstance(command.get("purpose"), str) or not command.get("purpose"):
            failures.append(f"tool command purpose is missing: {command.get('name')}")

    help_result = run("--help")
    if help_result.returncode != 0:
        failures.append("cross-platform tool help failed")
    for command in sorted(EXPECTED_COMMANDS):
        result = run(command, "--help")
        if result.returncode != 0:
            failures.append(f"tool command help failed: {command}")

    cmd_text = (TOOLS / "alatyr.cmd").read_text(encoding="utf-8")
    ps_text = (TOOLS / "alatyr.ps1").read_text(encoding="utf-8")
    for required in ["alatyr.py", "%*", "py -3", "python"]:
        if required not in cmd_text:
            failures.append(f"alatyr.cmd missing {required}")
    for required in ["alatyr.py", "@args", "py -3", "python"]:
        if required not in ps_text:
            failures.append(f"alatyr.ps1 missing {required}")

    if not NATIVE_WORKFLOW.is_file():
        failures.append("native cross-platform source-check workflow is missing")
    else:
        workflow = NATIVE_WORKFLOW.read_text(encoding="utf-8")
        for required in [
            "ubuntu-latest",
            "macos-latest",
            "windows-latest",
            "actions/checkout@v7",
            "actions/setup-python@v6",
            "python tools/check_all.py",
            "workflow_dispatch:",
            "contents: read",
        ]:
            if required not in workflow:
                failures.append(f"native cross-platform workflow missing {required}")

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        target = base / "target"
        target.mkdir()
        scaffold = run("scaffold", "--target", str(target), "--write")
        if scaffold.returncode != 0:
            failures.append("scaffold smoke setup failed")
        before = tree_hashes(target)
        output = base / "assessment"
        assessment = run(
            "assess-upgrade",
            "--target",
            str(target),
            "--framework-source",
            str(ROOT),
            "--output-dir",
            str(output),
            "--allow-placeholders",
        )
        if assessment.returncode != 0:
            failures.append("fresh scaffold upgrade assessment reported structural errors")
        after = tree_hashes(target)
        if before != after:
            failures.append("upgrade assessment modified target repository files")
        for filename in [
            "migration-report.md",
            "adapter-validation.json",
            "upgrade-assessment.md",
        ]:
            if not (output / filename).is_file():
                failures.append(f"upgrade assessment missing output: {filename}")
        plan = (output / "upgrade-assessment.md").read_text(encoding="utf-8")
        for required in [
            "Evidence basis: `current-state`",
            "This assessment does not apply an upgrade",
            "affected canonical sources",
        ]:
            if required not in plan:
                failures.append(f"upgrade assessment missing safety text: {required}")
        payload = json.loads((output / "adapter-validation.json").read_text(encoding="utf-8"))
        if payload.get("evidence", {}).get("basis") != "current-state-structural":
            failures.append("upgrade assessment validator evidence is not current-state")
        if payload.get("counts", {}).get("errors") != 0:
            failures.append("fresh scaffold validator evidence contains errors")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked cross-platform tool commands and migration-first assessment safety"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
