#!/usr/bin/env python3
"""Validate change-package framework, target-template, and validator contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_target_adapter import AdapterValidatorConfig, Validator


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
FRAMEWORK = ROOT / "framework" / "change-packages.md"
FLOW = TARGET / ".ai" / "assistant" / "flows" / "change-package.flow.md"
RECORD = TARGET / ".ai" / "assistant" / "templates" / "change-package-record.json"
REPORT = TARGET / ".ai" / "assistant" / "templates" / "change-package-report.md"
INDEX = TARGET / ".ai" / "assistant" / "change-packages" / "index.json"
OVERLAY = (
    TARGET
    / ".ai"
    / "assistant"
    / "context"
    / "task-scales"
    / "change-package.json"
)


def require_text(path: Path, values: list[str], failures: list[str]) -> None:
    if not path.is_file():
        failures.append(f"missing {path.relative_to(ROOT)}")
        return
    text = path.read_text(encoding="utf-8")
    for value in values:
        if value not in text:
            failures.append(f"{path.relative_to(ROOT)} missing {value}")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def valid_package_fixture(repo: Path) -> tuple[Path, dict[str, object]]:
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "alatyr@example.invalid")
    git(repo, "config", "user.name", "Alatyr Check")
    (repo / "plan.md").write_text("approved plan\n", encoding="utf-8")
    approval_path = repo / ".ai" / "assistant" / "approvals" / "package.json"
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval = {
        "schema_version": 2,
        "record_kind": "alatyr-approval-record",
        "evidence_classification": "historical-record",
        "approval_id": "approval-1",
        "scope": {
            "allowed_changed_fact_ids": ["FACT-1"],
            "allowed_architecture_areas": ["area-1"],
            "allowed_behavior_categories": ["behavior"],
            "permitted_external_effects": [],
        },
    }
    approval_path.write_text(json.dumps(approval), encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "approve package")
    before = git(repo, "rev-parse", "HEAD")
    (repo / "src").mkdir()
    (repo / "src" / "feature.txt").write_text("implemented\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "implement package")
    after = git(repo, "rev-parse", "HEAD")

    package_path = repo / ".ai" / "assistant" / "change-packages" / "case.json"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package: dict[str, object] = {
        "schema_version": 1,
        "record_kind": "alatyr-change-package",
        "evidence_classification": "historical-record",
        "package_id": "package-1",
        "package_type": "architecture-segment",
        "status": "complete",
        "activation_reason": "coherent architecture segment",
        "changed_facts": [
            {
                "id": "FACT-1",
                "statement": "feature exists",
                "canonical_owner": "plan.md",
                "invariants": ["feature remains area-owned"],
            }
        ],
        "plan": {
            "version": "1",
            "file": "plan.md",
            "sha256": hashlib.sha256((repo / "plan.md").read_bytes()).hexdigest(),
        },
        "approved_scope": {
            "approval_records": [
                ".ai/assistant/approvals/package.json"
            ],
            "changed_fact_ids": ["FACT-1"],
            "architecture_areas": ["area-1"],
            "behavior_categories": ["behavior"],
            "excluded_semantic_effects": ["live effects"],
            "permitted_external_effects": [],
            "allowed_files_or_surfaces": ["src/*"],
            "excluded_files_or_surfaces": [],
        },
        "actual_scope": {
            "changed_fact_ids": ["FACT-1"],
            "architecture_areas": ["area-1"],
            "behavior_categories": ["behavior"],
            "external_effects": [],
            "changed_paths": ["src/feature.txt"],
        },
        "discoveries_and_corrections": [],
        "companion_decisions": [
            {
                "surface_type": "tests",
                "owner_or_path": "src/feature.txt",
                "decision": "not-required",
                "reason": "source fixture validates structural range only",
                "evidence": "src/feature.txt",
            }
        ],
        "architecture_discussion": {
            "applies": True,
            "problem_and_boundary": "introduce an isolated fixture segment",
            "alternatives": ["no change", "new segment"],
            "selected_direction": "new segment",
            "decision_status": "accepted",
            "sources": ["plan.md"],
            "assumptions_or_disagreement": [],
            "raw_chat_retained": False,
        },
        "provenance": {
            "evidence_quality": "git-range",
            "before_revision": before,
            "after_revision": after,
            "working_tree_at_start": "clean",
            "working_tree_at_validation": "dirty",
            "unrelated_changes_handling": "package record excluded from implementation range",
            "pull_request": "not applicable",
            "selected_file_snapshot": {
                "algorithm": "sha256",
                "digest": "not applicable",
                "paths": [],
            },
            "public_claim_strength": "strong",
        },
        "validation": {"residual_risks": []},
    }
    package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    index_path = repo / ".ai" / "assistant" / "change-packages" / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "index_kind": "target-change-package-index",
                "records": [
                    {
                        "package_id": "package-1",
                        "status": "complete",
                        "record": ".ai/assistant/change-packages/case.json",
                        "changed_fact_ids": ["FACT-1"],
                        "canonical_owners": ["plan.md"],
                        "project_areas": ["area-1"],
                        "evidence_quality": "git-range",
                        "approval_records": [
                            ".ai/assistant/approvals/package.json"
                        ],
                        "active_workstream": "not active",
                        "residual_risk": "none",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return package_path, package


def validate_fixture(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        package_path, package = valid_package_fixture(repo)
        validator = Validator(
            repo,
            framework_source=None,
            diff_ref=None,
            approval_records=[],
            enforce_approval_scope=False,
            change_packages=[package_path],
            enforce_change_package=True,
            migration_diff=None,
            allow_placeholders=True,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
        )
        validator.check_change_packages()
        package_errors = [
            finding for finding in validator.findings if finding.level == "error"
        ]
        if package_errors:
            failures.append(
                "valid change package fixture failed: "
                + "; ".join(f"{item.code}: {item.message}" for item in package_errors)
            )

        actual = package["actual_scope"]
        assert isinstance(actual, dict)
        actual["behavior_categories"] = ["unapproved-behavior"]
        package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
        invalid = Validator(
            repo,
            framework_source=None,
            diff_ref=None,
            approval_records=[],
            enforce_approval_scope=False,
            change_packages=[package_path],
            enforce_change_package=True,
            migration_diff=None,
            allow_placeholders=True,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
        )
        invalid.check_change_packages()
        if not any(
            finding.code in {"PACKAGE_SEMANTIC_SCOPE", "PACKAGE_APPROVAL_SEMANTIC_SCOPE"}
            and finding.level == "error"
            for finding in invalid.findings
        ):
            failures.append("change-package validator did not reject semantic scope drift")


def main() -> int:
    failures: list[str] = []
    require_text(
        FRAMEWORK,
        [
            "ALATYR-PACKAGE-001",
            "## Activation",
            "## Semantic Approval Scope",
            "## Companion-Surface Decisions",
            "## Repository Provenance",
            "selected-file-snapshot",
            "Do not create a package for a small task",
        ],
        failures,
    )
    require_text(FLOW, ["## Activation Gate", "## Validation Boundary"], failures)
    require_text(REPORT, ["Evidence quality:", "Public claim strength:"], failures)

    try:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"invalid change-package JSON template: {exc}")
    else:
        if record.get("record_kind") != "alatyr-change-package":
            failures.append("change-package record kind is invalid")
        for field in [
            "approved_scope",
            "actual_scope",
            "discoveries_and_corrections",
            "companion_decisions",
            "architecture_discussion",
            "provenance",
            "validation",
        ]:
            if field not in record:
                failures.append(f"change-package record missing {field}")
        if index.get("records") != []:
            failures.append("source change-package index must start empty")
        if overlay.get("overlay") != "change-package":
            failures.append("change-package overlay identity is invalid")

    validate_fixture(failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: checked change-package framework, templates, and validator enforcement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
