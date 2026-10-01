#!/usr/bin/env python3
"""Validate change-package framework, target-template, and validator contracts."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from change_package_contract import (
    CHANGE_PACKAGE_STATUS_PLACEHOLDER,
    incident_continuity_failures,
)
from validate_target_adapter import AdapterValidatorConfig, Validator


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
FRAMEWORK = ROOT / "framework" / "change-packages.md"
FLOW = TARGET / ".ai" / "assistant" / "flows" / "change-package.flow.md"
RECORD = TARGET / ".ai" / "assistant" / "templates" / "change-package-record.json"
REPORT = TARGET / ".ai" / "assistant" / "templates" / "change-package-report.md"
INDEX = TARGET / ".ai" / "assistant" / "change-packages" / "index.json"
SHARD = TARGET / ".ai" / "assistant" / "templates" / "change-package-index-shard.json"
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
        "operation": {
            "id": "operation-1",
            "type": "product-change",
            "large_task_packet": "not active",
            "active_workstream": "not active",
        },
        "routing": {
            "task_profile": "architecture-change",
            "project_areas": ["area-1"],
            "context_receipt": "not available with reason",
        },
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
        "engineering_evidence_ids": [],
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


def changed_index_validator(repo: Path) -> Validator:
    return Validator(
        repo,
        framework_source=None,
        diff_ref="HEAD",
        approval_records=[],
        enforce_approval_scope=False,
        change_packages=[],
        enforce_change_package=False,
        migration_diff=None,
        allow_placeholders=True,
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
        validation_scope="changed",
    )


def validate_unchanged_shard_routing(
    repo: Path,
    package_path: Path,
    package: dict[str, object],
    failures: list[str],
) -> None:
    index_path = repo / ".ai" / "assistant" / "change-packages" / "index.json"
    shard_path = (
        repo
        / ".ai"
        / "assistant"
        / "change-packages"
        / "archive"
        / "2026-09"
        / "index.json"
    )
    original_index = index_path.read_bytes()
    original_shard = shard_path.read_bytes()
    shard = json.loads(original_shard)
    historical_path = (
        repo / ".ai" / "assistant" / "change-packages" / "historical.json"
    )
    historical_package = copy.deepcopy(package)
    historical_package["package_id"] = "package-2"
    historical_path.write_text(
        json.dumps(historical_package, indent=2) + "\n", encoding="utf-8"
    )
    historical_entry = copy.deepcopy(shard["records"][0])
    historical_entry.update(
        package_id="package-2",
        record=historical_path.relative_to(repo).as_posix(),
    )
    shard["records"].append(historical_entry)
    shard_path.write_text(json.dumps(shard, indent=2) + "\n", encoding="utf-8")
    committed_shard = shard_path.read_bytes()
    root_index = json.loads(original_index)
    root_index["shards"][0].update(
        sha256=hashlib.sha256(shard_path.read_bytes()).hexdigest(),
        record_count=len(shard["records"]),
    )
    index_path.write_text(json.dumps(root_index, indent=2) + "\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "record sharded package projection")

    changed_package = copy.deepcopy(package)
    changed_package["status"] = "blocked"
    package_path.write_text(
        json.dumps(changed_package, indent=2) + "\n", encoding="utf-8"
    )
    changed_record_validator = changed_index_validator(repo)
    loaded_json_paths: list[Path] = []
    read_json = changed_record_validator.context.read_json

    def tracked_read_json(path: Path):
        loaded_json_paths.append(path.resolve())
        return read_json(path)

    with patch.object(
        changed_record_validator.context,
        "read_json",
        side_effect=tracked_read_json,
    ):
        changed_record_validator.check_change_package_index()
    if not any(
        finding.code == "PACKAGE_INDEX_PROJECTION" and "status" in finding.message
        for finding in changed_record_validator.findings
    ):
        failures.append(
            "changed-scope validation missed projection drift in an unchanged shard"
        )
    if historical_path.resolve() in loaded_json_paths:
        failures.append(
            "changed-scope validation reopened an unrelated historical package record"
        )

    consistent_changed_package = copy.deepcopy(package)
    consistent_changed_package["activation_reason"] = (
        "coherent architecture segment with additional context"
    )
    package_path.write_text(
        json.dumps(consistent_changed_package, indent=2) + "\n",
        encoding="utf-8",
    )
    consistent_record_validator = changed_index_validator(repo)
    consistent_record_validator.check_change_package_index()
    if any(
        finding.code == "PACKAGE_INDEX_PROJECTION"
        for finding in consistent_record_validator.findings
    ):
        failures.append(
            "changed-scope validation rejected a consistent unchanged-shard projection"
        )

    package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    changed_shard = json.loads(committed_shard)
    changed_shard["records"][0]["status"] = "blocked"
    shard_path.write_text(
        json.dumps(changed_shard, indent=2) + "\n", encoding="utf-8"
    )
    changed_shard_validator = changed_index_validator(repo)
    changed_shard_validator.check_change_package_index()
    changed_shard_codes = {
        finding.code for finding in changed_shard_validator.findings
    }
    if not {"PACKAGE_INDEX_SHARD_DIGEST", "PACKAGE_INDEX_PROJECTION"}.issubset(
        changed_shard_codes
    ):
        failures.append("changed-scope validation lost changed-shard detection")
    shard_path.write_bytes(committed_shard)

    changed_root_index = copy.deepcopy(root_index)
    changed_root_index["shards"][0]["record_count"] += 1
    index_path.write_text(
        json.dumps(changed_root_index, indent=2) + "\n", encoding="utf-8"
    )
    changed_root_validator = changed_index_validator(repo)
    changed_root_validator.check_change_package_index()
    if not any(
        finding.code == "PACKAGE_INDEX_SHARD_COUNT"
        for finding in changed_root_validator.findings
    ):
        failures.append("changed-scope validation lost changed-root detection")

    index_path.write_bytes(original_index)
    shard_path.write_bytes(original_shard)
    historical_path.unlink()


def validate_active_incident_routing(
    repo: Path,
    package_path: Path,
    package: dict[str, object],
    failures: list[str],
) -> None:
    index_path = repo / ".ai" / "assistant" / "change-packages" / "index.json"
    active_package = copy.deepcopy(package)
    active_package["status"] = "implementing"
    package_path.write_text(
        json.dumps(active_package, indent=2) + "\n", encoding="utf-8"
    )
    active_index = json.loads(index_path.read_text(encoding="utf-8"))
    active_entry = active_index["records"][0]
    active_entry.update(
        status="implementing",
        incident_family_id=None,
        corrective_iteration=None,
        latest_failed_gate_state=None,
    )
    index_path.write_text(json.dumps(active_index, indent=2) + "\n", encoding="utf-8")
    validator = Validator(
        repo,
        framework_source=None,
        diff_ref=None,
        approval_records=[],
        enforce_approval_scope=False,
        change_packages=[],
        enforce_change_package=False,
        migration_diff=None,
        allow_placeholders=True,
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
    )
    validator.check_change_package_index()
    validator.check_change_packages()
    if not any(
        finding.code == "PACKAGE_INCIDENT_CONTINUITY"
        and finding.level == "error"
        for finding in validator.findings
    ):
        failures.append(
            "active indexed package was not auto-validated for incident continuity"
        )

    package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    active_entry["status"] = "complete"
    for field in (
        "incident_family_id",
        "corrective_iteration",
        "latest_failed_gate_state",
    ):
        active_entry.pop(field, None)
    index_path.write_text(json.dumps(active_index, indent=2) + "\n", encoding="utf-8")
    unindexed_plan_validator = changed_index_validator(repo)
    with patch.object(
        unindexed_plan_validator.git,
        "changed_files",
        return_value=[".ai/assistant/change-packages/unbound-plan.md"],
    ):
        unindexed_plan_validator.check_change_packages()
    if not any(
        finding.code == "PACKAGE_ACTIVE_PLAN_UNINDEXED"
        and finding.level == "error"
        for finding in unindexed_plan_validator.findings
    ):
        failures.append("changed unindexed package plan was not rejected")


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

        index_path = repo / ".ai" / "assistant" / "change-packages" / "index.json"
        validate_active_incident_routing(repo, package_path, package, failures)

        invalid_index = json.loads(index_path.read_text(encoding="utf-8"))
        invalid_index["records"][0]["status"] = "unvalidated"
        index_path.write_text(json.dumps(invalid_index, indent=2) + "\n", encoding="utf-8")
        index_validator = Validator(
            repo,
            framework_source=None,
            diff_ref=None,
            approval_records=[],
            enforce_approval_scope=False,
            change_packages=[],
            enforce_change_package=False,
            migration_diff=None,
            allow_placeholders=True,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
        )
        index_validator.check_change_package_index()
        if not any(
            finding.code == "PACKAGE_INDEX_STATUS" and finding.level == "error"
            for finding in index_validator.findings
        ):
            failures.append("change-package index accepted a non-canonical status")
        invalid_index["records"][0]["status"] = "complete"
        index_path.write_text(json.dumps(invalid_index, indent=2) + "\n", encoding="utf-8")

        drifted_index = copy.deepcopy(invalid_index)
        drifted_index["records"][0]["project_areas"] = ["other-area"]
        index_path.write_text(json.dumps(drifted_index, indent=2) + "\n", encoding="utf-8")
        projection_validator = Validator(
            repo,
            framework_source=None,
            diff_ref=None,
            approval_records=[],
            enforce_approval_scope=False,
            change_packages=[],
            enforce_change_package=False,
            migration_diff=None,
            allow_placeholders=True,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
        )
        projection_validator.check_change_package_index()
        if not any(
            finding.code == "PACKAGE_INDEX_PROJECTION" and finding.level == "error"
            for finding in projection_validator.findings
        ):
            failures.append("change-package index accepted a stale package projection")
        index_path.write_text(json.dumps(invalid_index, indent=2) + "\n", encoding="utf-8")

        package_path.write_text("not JSON\n", encoding="utf-8")
        changed_scope_validator = Validator(
            repo,
            framework_source=None,
            diff_ref="HEAD",
            approval_records=[],
            enforce_approval_scope=False,
            change_packages=[],
            enforce_change_package=False,
            migration_diff=None,
            allow_placeholders=True,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
            validation_scope="changed",
        )
        with patch.object(
            changed_scope_validator.git,
            "changed_files",
            return_value=["src/feature.txt"],
        ):
            changed_scope_validator.check_change_package_index()
        if any(
            finding.code.startswith("PACKAGE_INDEX_RECORD_")
            for finding in changed_scope_validator.findings
        ):
            failures.append("changed-scope package validation reopened unchanged history")
        package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")

        shard_path = repo / ".ai" / "assistant" / "change-packages" / "archive" / "2026-09" / "index.json"
        shard_path.parent.mkdir(parents=True)
        shard = {
            "schema_version": 1,
            "index_kind": "target-change-package-index-shard",
            "shard_id": "2026-09",
            "records": invalid_index["records"],
        }
        shard_path.write_text(json.dumps(shard, indent=2) + "\n", encoding="utf-8")
        shard_relpath = shard_path.relative_to(repo).as_posix()
        sharded_index = {
            "schema_version": 1,
            "index_kind": "target-change-package-index",
            "records": [],
            "shards": [
                {
                    "shard_id": "2026-09",
                    "path": shard_relpath,
                    "sha256": hashlib.sha256(shard_path.read_bytes()).hexdigest(),
                    "record_count": 1,
                }
            ],
        }
        index_path.write_text(json.dumps(sharded_index, indent=2) + "\n", encoding="utf-8")
        shard_validator = Validator(
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
        shard_validator.check_change_package_index()
        shard_validator.check_change_packages()
        shard_errors = [
            finding for finding in shard_validator.findings if finding.level == "error"
        ]
        if shard_errors:
            failures.append(
                "valid sharded change-package index failed: "
                + "; ".join(f"{item.code}: {item.message}" for item in shard_errors)
            )

        validate_unchanged_shard_routing(repo, package_path, package, failures)
        sharded_index["shards"][0]["sha256"] = "0" * 64
        index_path.write_text(json.dumps(sharded_index, indent=2) + "\n", encoding="utf-8")
        stale_shard_validator = Validator(
            repo,
            framework_source=None,
            diff_ref=None,
            approval_records=[],
            enforce_approval_scope=False,
            change_packages=[],
            enforce_change_package=False,
            migration_diff=None,
            allow_placeholders=True,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
        )
        stale_shard_validator.check_change_package_index()
        if not any(
            finding.code == "PACKAGE_INDEX_SHARD_DIGEST"
            for finding in stale_shard_validator.findings
        ):
            failures.append("change-package validator accepted stale shard digest")
        index_path.write_text(json.dumps(invalid_index, indent=2) + "\n", encoding="utf-8")

        reversed_package = copy.deepcopy(package)
        reversed_provenance = reversed_package["provenance"]
        assert isinstance(reversed_provenance, dict)
        before = reversed_provenance["before_revision"]
        reversed_provenance["before_revision"] = reversed_provenance["after_revision"]
        reversed_provenance["after_revision"] = before
        package_path.write_text(json.dumps(reversed_package, indent=2) + "\n", encoding="utf-8")
        reversed_validator = Validator(
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
        reversed_validator.check_change_packages()
        if not any(finding.code == "PACKAGE_REVISION_ANCESTRY" for finding in reversed_validator.findings):
            failures.append("change-package validator accepted a reversed Git range")

        snapshot_package = copy.deepcopy(package)
        snapshot_provenance = snapshot_package["provenance"]
        assert isinstance(snapshot_provenance, dict)
        digest = hashlib.sha256()
        digest.update(b"src/feature.txt\0")
        digest.update((repo / "src/feature.txt").read_bytes())
        digest.update(b"\0")
        snapshot_provenance.update(
            evidence_quality="selected-file-snapshot",
            public_claim_strength="limited",
            before_revision="not available with reason",
            after_revision="not available with reason",
            selected_file_snapshot={
                "algorithm": "sha256",
                "digest": digest.hexdigest(),
                "paths": ["src/feature.txt"],
            },
        )
        package_path.write_text(json.dumps(snapshot_package, indent=2) + "\n", encoding="utf-8")
        (repo / "src/feature.txt").write_text("later edit\n", encoding="utf-8")
        snapshot_validator = Validator(
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
        snapshot_validator.check_change_packages()
        if any(
            finding.level == "error" and finding.code.startswith("PACKAGE_SNAPSHOT")
            for finding in snapshot_validator.findings
        ):
            failures.append("later edits invalidated a complete historical change-package snapshot")
        if not any(finding.code == "PACKAGE_SNAPSHOT_HISTORICAL" for finding in snapshot_validator.findings):
            failures.append("historical change-package snapshot drift was not reported")

        package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
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
            "## Incident Continuity",
            "second corrective iteration",
            "selected-file-snapshot",
            "Do not create a package for a small task",
        ],
        failures,
    )
    require_text(
        FLOW,
        [
            "## Activation Gate",
            "Use `systemic-repair` plus `recurring-correction`",
            "## Validation Boundary",
        ],
        failures,
    )
    require_text(REPORT, ["Evidence quality:", "Public claim strength:"], failures)

    try:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        shard = json.loads(SHARD.read_text(encoding="utf-8"))
        overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"invalid change-package JSON template: {exc}")
    else:
        if record.get("record_kind") != "alatyr-change-package":
            failures.append("change-package record kind is invalid")
        for field in [
            "incident_continuity",
            "approved_scope",
            "actual_scope",
            "discoveries_and_corrections",
            "companion_decisions",
            "architecture_discussion",
            "engineering_evidence_ids",
            "provenance",
            "validation",
        ]:
            if field not in record:
                failures.append(f"change-package record missing {field}")
        if record.get("status") != CHANGE_PACKAGE_STATUS_PLACEHOLDER:
            failures.append("change-package status placeholder differs from canonical statuses")
        companion_template = record.get("companion_decisions")
        surface_placeholder = (
            companion_template[0].get("surface_type")
            if isinstance(companion_template, list)
            and companion_template
            and isinstance(companion_template[0], dict)
            else ""
        )
        if "PROJECT_CONTOUR_SYNC" not in surface_placeholder:
            failures.append("change-package template omits project-contour-sync evidence")
        if index.get("records") != []:
            failures.append("source change-package index must start empty")
        if index.get("shards") != []:
            failures.append("source change-package shard directory must start empty")
        if (
            shard.get("index_kind") != "target-change-package-index-shard"
            or shard.get("records") != []
        ):
            failures.append("change-package shard template is invalid")
        if overlay.get("overlay") != "change-package":
            failures.append("change-package overlay identity is invalid")

    valid_incident = {
        "incident_continuity": {
            "mode": "systemic-repair",
            "family_id": "incident-1",
            "trigger": "recurring-correction",
            "corrective_iteration": 2,
            "predecessors": [
                {
                    "package_id": "package-previous",
                    "record": ".ai/assistant/change-packages/previous.json",
                    "sha256": "0" * 64,
                }
            ],
            "problem_model": {
                "path": ".ai/assistant/problem-models/incident-1.json",
                "sha256": "1" * 64,
            },
            "latest_failed_gate": {
                "state": "resolved",
                "id": "test-gate",
                "evidence_refs": ["tests/incident-regression.md"],
            },
            "lifecycle_model_required": True,
        }
    }
    if incident_continuity_failures(valid_incident):
        failures.append("valid systemic incident continuity was rejected")
    invalid_repeat = copy.deepcopy(valid_incident)
    incident = invalid_repeat["incident_continuity"]
    assert isinstance(incident, dict)
    incident.update(mode="continuation", trigger="reported-defect")
    if not any(
        "second corrective iteration" in failure
        for failure in incident_continuity_failures(invalid_repeat)
    ):
        failures.append("second corrective iteration did not require systemic repair")

    validate_fixture(failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: checked change-package framework, templates, and validator enforcement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
