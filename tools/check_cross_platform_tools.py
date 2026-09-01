#!/usr/bin/env python3
"""Validate cross-platform tool routing and migration-first assessment safety."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
GIT_ATTRIBUTES = ROOT / ".gitattributes"
MANIFEST = TOOLS / "tool_commands.json"
NATIVE_WORKFLOW = ROOT / ".github" / "workflows" / "cross-platform-source-checks.yml"
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release-source-checks.yml"
RUNTIME_COMPATIBILITY = TOOLS / "runtime-compatibility.json"
CI_CONSTRAINTS = ROOT / "constraints-ci.txt"
FRAMEWORK_CHECKER = TOOLS / "check_framework_consistency.py"
SCAFFOLD_CONFORMANCE = TOOLS / "run_conformance_scaffold.py"
SOURCE_CHECK_SUMMARY = TOOLS / "summarize_source_check_report.py"
EXPECTED_COMMANDS = {
    "check-source",
    "check-source-focused",
    "plan-work",
    "compare-check-reports",
    "scaffold",
    "render-bootstrap",
    "render-entry",
    "render-context",
    "snapshot-support",
    "support-diff",
    "support-delta",
    "change-cost",
    "support-costs",
    "impact",
    "generate-support",
    "validate-adapter",
    "approval-check",
    "status",
    "doctor",
    "migration-report",
    "assess-upgrade",
    "context-costs",
    "inspect-extension",
    "inspect-dependency-knowledge",
    "prepare-conformance",
    "check-conformance",
    "prepare-benchmark",
    "check-benchmark",
    "summarize-benchmark",
    "clean-artifacts",
}
ALLOWED_WRITE_SCOPES = {
    "none",
    "target-structure-with-explicit-write",
    "explicit-report-output-only",
    "explicit-evidence-output-only",
    "local-source-artifacts-with-explicit-apply",
    "target-generated-surfaces-with-explicit-apply",
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
    if not GIT_ATTRIBUTES.is_file() or "* text=auto eol=lf" not in (
        GIT_ATTRIBUTES.read_text(encoding="utf-8").splitlines()
    ):
        failures.append(
            ".gitattributes must enforce canonical LF text checkouts for "
            "deterministic cross-platform hashes"
        )
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        runtime = json.loads(RUNTIME_COMPATIBILITY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: invalid tool command manifest: {exc}", file=sys.stderr)
        return 1

    if runtime.get("schema_version") != 1:
        failures.append("runtime compatibility schema_version must be 1")
    python_contract = runtime.get("python")
    if (
        not isinstance(python_contract, dict)
        or python_contract.get("minimum_supported") != "3.10"
        or python_contract.get("ci_versions") != ["3.10", "3.13"]
    ):
        failures.append("runtime compatibility Python contract drifted")
    dependency_contract = runtime.get("dependencies")
    if not isinstance(dependency_contract, dict) or dependency_contract != {
        "requirements": "requirements-dev.txt",
        "ci_constraints": "constraints-ci.txt",
    }:
        failures.append("runtime compatibility dependency contract drifted")
    if not CI_CONSTRAINTS.is_file():
        failures.append("CI dependency constraints are missing")
    else:
        constraints = CI_CONSTRAINTS.read_text(encoding="utf-8")
        for required in ["jsonschema==4.26.0", "PyYAML==6.0.3", "rpds-py=="]:
            if required not in constraints:
                failures.append(f"CI dependency constraints missing {required}")

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
    command_names = sorted(EXPECTED_COMMANDS)
    with ThreadPoolExecutor(max_workers=min(8, len(command_names))) as executor:
        help_results = dict(
            zip(
                command_names,
                executor.map(lambda command: run(command, "--help"), command_names),
            )
        )
    for command, result in help_results.items():
        if result.returncode != 0:
            failures.append(f"tool command help failed: {command}")

    doctor_output = run("doctor", "--output", "should-not-exist.json")
    if doctor_output.returncode != 2 or "does not permit" not in doctor_output.stderr:
        failures.append("doctor must reject report-file output and remain read-only")
    status_output = run("status", "--output", "should-not-exist.json")
    if status_output.returncode != 2 or "does not permit" not in status_output.stderr:
        failures.append("status must reject report-file output and remain read-only")

    extension_output = run(
        "inspect-extension",
        "--package",
        str(ROOT / "templates" / "extension"),
        "--allow-placeholders",
    )
    if extension_output.returncode != 0:
        failures.append("cross-platform extension inspection failed")

    dependency_output = run(
        "inspect-dependency-knowledge",
        "--source",
        str(ROOT / "templates" / "dependency-knowledge"),
        "--allow-placeholders",
        "--no-file-check",
    )
    if dependency_output.returncode != 0:
        failures.append("cross-platform dependency knowledge inspection failed")

    cmd_text = (TOOLS / "alatyr.cmd").read_text(encoding="utf-8")
    ps_text = (TOOLS / "alatyr.ps1").read_text(encoding="utf-8")
    for required in ["alatyr.py", "%*", "py -3", "python"]:
        if required not in cmd_text:
            failures.append(f"alatyr.cmd missing {required}")
    for required in ["alatyr.py", "@args", "py -3", "python"]:
        if required not in ps_text:
            failures.append(f"alatyr.ps1 missing {required}")

    framework_checker = FRAMEWORK_CHECKER.read_text(encoding="utf-8")
    if "path.relative_to(ROOT).as_posix()" not in framework_checker:
        failures.append("framework checker does not normalize contract paths")

    scaffold_conformance = SCAFFOLD_CONFORMANCE.read_text(encoding="utf-8")
    for required in [
        'Path(tempfile.mkdtemp(prefix="alatyr-conformance-")).resolve()',
        "set(skipped_existing_paths(repo, write_blocked))",
    ]:
        if required not in scaffold_conformance:
            failures.append(f"scaffold conformance missing portability guard: {required}")

    if not NATIVE_WORKFLOW.is_file():
        failures.append("native cross-platform source-check workflow is missing")
    else:
        workflow = NATIVE_WORKFLOW.read_text(encoding="utf-8")
        for required in [
            "concurrency:",
            "cancel-in-progress: ${{ github.event_name == 'pull_request' }}",
            "timeout-minutes: 35",
            "timeout-minutes: 25",
            "ubuntu-latest",
            "macos-latest",
            "windows-latest",
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
            'python-version: ["3.10", "3.13"]',
            "cache-dependency-path:",
            "python tools/check_all.py --profile full",
            "python tools/check_all.py --profile platform",
            "-c constraints-ci.txt",
            "python -m pip check",
            "--report",
            "tools/summarize_source_check_report.py",
            "--github-step-summary",
            "--allow-missing",
            "workflow_dispatch:",
            "contents: read",
        ]:
            if required not in workflow:
                failures.append(f"native cross-platform workflow missing {required}")

    if not RELEASE_WORKFLOW.is_file():
        failures.append("release source-check workflow is missing")
    else:
        release_workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        for required in [
            "concurrency:",
            "cancel-in-progress: false",
            "timeout-minutes: 45",
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
            "--require-current-tag",
            "cache-dependency-path:",
            "-c constraints-ci.txt",
            "python -m pip check",
            "--report",
            "tools/summarize_source_check_report.py",
            "--github-step-summary",
            "--allow-missing",
        ]:
            if required not in release_workflow:
                failures.append(f"release source workflow missing {required}")
    if not SOURCE_CHECK_SUMMARY.is_file():
        failures.append("source-check report summary helper is missing")

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        target = base / "target"
        target.mkdir()
        scaffold = run("scaffold", "--target", str(target), "--write")
        if scaffold.returncode != 0:
            failures.append("scaffold smoke setup failed")
        git_setup_commands = [
            ["git", "init", "-q"],
            ["git", "config", "user.email", "alatyr-conformance@example.invalid"],
            ["git", "config", "user.name", "Alatyr Conformance"],
            ["git", "add", "."],
            ["git", "commit", "-qm", "Initialize target fixture"],
            ["git", "switch", "-qc", "feature/adapter-upgrade"],
        ]
        for command in git_setup_commands:
            result = subprocess.run(
                command,
                cwd=target,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                failures.append(f"upgrade branch fixture setup failed: {' '.join(command)}")
                break
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
            failures.append(
                "fresh scaffold upgrade assessment reported structural errors: "
                + (assessment.stderr.strip() or assessment.stdout.strip() or "no diagnostic")
            )
        after = tree_hashes(target)
        if before != after:
            failures.append("upgrade assessment modified target repository files")
        for filename in [
            "migration-report.md",
            "upgrade-impact.json",
            "adapter-validation.json",
            "upgrade-assessment.md",
        ]:
            if not (output / filename).is_file():
                failures.append(f"upgrade assessment missing output: {filename}")
        plan_path = output / "upgrade-assessment.md"
        if plan_path.is_file():
            plan = plan_path.read_text(encoding="utf-8")
            for required in [
                "Evidence basis: `current-state`",
                "Observed target branch: `feature/adapter-upgrade`",
                "This assessment does not apply an upgrade",
                "affected canonical sources",
                "Validation phase: `migration-staging`",
                "Acceptance eligible: `false`",
            ]:
                if required not in plan:
                    failures.append(f"upgrade assessment missing safety text: {required}")
        payload_path = output / "adapter-validation.json"
        payload = json.loads(payload_path.read_text(encoding="utf-8")) if payload_path.is_file() else {}
        if payload.get("evidence", {}).get("basis") != "current-state-structural":
            failures.append("upgrade assessment validator evidence is not current-state")
        if payload.get("counts", {}).get("errors") != 0:
            error_findings = [
                f"{item.get('code')}:{item.get('message')}"
                for item in payload.get("findings", [])
                if isinstance(item, dict) and item.get("level") == "error"
            ]
            failures.append(
                "fresh scaffold validator evidence contains errors: "
                + "; ".join(error_findings[:8])
            )
        if payload.get("status") != "staged":
            failures.append("placeholder-tolerant upgrade assessment must remain staged")
        if payload.get("adapter_health", {}).get("state") != "unverified":
            failures.append("staging assessment must report unverified adapter health")
        if payload.get("placeholder_validation", {}).get("acceptance_eligible") is not False:
            failures.append("staging assessment must not be acceptance eligible")
        if payload.get("evidence", {}).get("observed_branch") != "feature/adapter-upgrade":
            failures.append("validator evidence must bind the checked-out target branch")
        impact_path = output / "upgrade-impact.json"
        impact = json.loads(impact_path.read_text(encoding="utf-8")) if impact_path.is_file() else {}
        if impact.get("target", {}).get("branch") != "feature/adapter-upgrade":
            failures.append("upgrade impact must bind the checked-out target branch")
        if impact.get("impact_kind") != "alatyr-upgrade-impact":
            failures.append("upgrade assessment impact output has an invalid contract")
        if impact.get("routing", {}).get("full_corpus_required") is not False:
            failures.append("upgrade assessment must begin with bounded impact routing")
        if not isinstance(impact.get("routing", {}).get("candidate_context"), list):
            failures.append("upgrade assessment must expose routed candidate context")

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
