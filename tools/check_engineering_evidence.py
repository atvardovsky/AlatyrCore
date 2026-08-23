#!/usr/bin/env python3
"""Validate durable engineering-evidence rules, templates, and enforcement."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import jsonschema

from validate_target_adapter import AdapterValidatorConfig, Validator


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
FRAMEWORK = ROOT / "framework" / "engineering-evidence.md"
INDEX = TARGET / ".ai" / "project" / "engineering-evidence" / "index.json"
POLICY = TARGET / ".ai" / "project" / "engineering-evidence" / "README.md"
FLOW = TARGET / ".ai" / "assistant" / "flows" / "engineering-evidence-capture.flow.md"
GATE = TARGET / ".ai" / "assistant" / "gates" / "engineering-evidence.md"
RECORD = TARGET / ".ai" / "assistant" / "templates" / "engineering-evidence-record.json"
OVERLAY = TARGET / ".ai" / "assistant" / "context" / "task-scales" / "engineering-evidence.json"
SCHEMA = ROOT / "schemas" / "alatyr-engineering-evidence.schema.json"
SCENARIOS = ROOT / "conformance" / "engineering-evidence-scenarios.json"
TARGET_AGENTS = TARGET / "AGENTS.md"
OPERATION_ROUTING = TARGET / ".ai" / "assistant" / "flows" / "operation-routing.flow.md"


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


def fixture_record(base: str, result: str) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "record_kind": "alatyr-engineering-evidence",
        "evidence_classification": "historical-record",
        "evidence_id": "ENG-1",
        "status": "validated",
        "owner": "engineering",
        "captured_at": "2026-08-21T12:00:00Z",
        "task": {
            "summary": "Preserve one identity invariant",
            "references": ["issue-1"],
            "operation_id": "operation-1",
        },
        "repository_binding": {
            "kind": "commit",
            "binding_state": "final",
            "base_revision": base,
            "result_revision": result,
            "review_reference": "not applicable",
            "selected_paths": [],
            "snapshot_sha256": "not applicable",
            "prior_bindings": [],
        },
        "observed_failure": "Distinct identities collided in one map",
        "affected_architecture": [
            {"area": "identity-map", "owner_or_source": "design.md", "effect": "identity ownership changed"}
        ],
        "invariants": [
            {
                "statement": "Distinct identity tuples remain distinct",
                "status": "accepted",
                "canonical_owner": "design.md",
                "evidence": ["src/example.txt"],
            }
        ],
        "hypotheses": [
            {
                "statement": "String concatenation preserves tuple identity",
                "outcome": "rejected",
                "evidence": ["src/example.txt"],
                "decision_impact": "Use a typed tuple key",
            }
        ],
        "root_cause": {"statement": "A lossy key representation was used", "evidence": ["src/example.txt"]},
        "chosen_solution": {
            "summary": "Use an unambiguous identity key",
            "rationale": "It preserves tuple identity",
            "material_rejected_alternatives": [
                {"alternative": "Add another delimiter", "reason": "Input may still contain it"}
            ],
        },
        "impact": {
            "changed_fact_ids": ["FACT-IDENTITY"],
            "code_and_test_surfaces": ["src/example.txt"],
            "companion_surfaces": ["design.md"],
            "canonical_knowledge_updates": ["design.md"],
        },
        "regression_matrix": [
            {
                "case": "ambiguous tuple values",
                "protects": "Distinct identity tuples remain distinct",
                "expected_result": "separate entries",
                "validation_evidence": "src/example.txt",
            }
        ],
        "validation": {"results": ["fixture review passed"], "skipped": []},
        "residual_uncertainty": [],
        "related_records": {
            "change_package_ids": [],
            "approval_records": [],
            "architecture_decisions": ["design.md"],
            "development_evidence_pattern_ids": [],
        },
        "publication": {
            "storage_mode": "repository",
            "included_in_external_patch": False,
            "visibility": "internal",
            "policy_evidence": "policy.md",
        },
        "privacy": {
            "raw_chat_stored": False,
            "chain_of_thought_stored": False,
            "secrets_stored": False,
            "unrelated_session_history_stored": False,
            "redactions": [],
        },
    }


def fixture_index(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 3,
        "index_kind": "target-engineering-evidence-index",
        "project": "fixture",
        "owner": "engineering",
        "storage_mode": "repository",
        "external_patch_policy": "exclude from external patch",
        "retention_policy": "retain validated records",
        "redaction_policy": "exclude raw conversations and secrets",
        "records": [
            {
                "evidence_id": record["evidence_id"],
                "status": record["status"],
                "record": ".ai/project/engineering-evidence/records/ENG-1.json",
                "task_references": record["task"]["references"],
                "changed_fact_ids": record["impact"]["changed_fact_ids"],
                "architecture_areas": [record["affected_architecture"][0]["area"]],
                "repository_binding_kind": record["repository_binding"]["kind"],
                "record_schema_version": record["schema_version"],
                "repository_binding_state": record["repository_binding"].get("binding_state", "legacy"),
                "result_revision": record["repository_binding"]["result_revision"],
                "residual_uncertainty": record["residual_uncertainty"],
            }
        ],
    }


def run_validator(repo: Path) -> list[Any]:
    validator = Validator(
        repo,
        framework_source=None,
        diff_ref=None,
        approval_records=[],
        enforce_approval_scope=False,
        change_packages=[],
        enforce_change_package=False,
        migration_diff=None,
        allow_placeholders=False,
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
    )
    validator.check_engineering_evidence(None)
    return validator.findings


def validate_fixture(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="alatyr-engineering-evidence-") as directory:
        repo = Path(directory)
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "alatyr@example.invalid")
        git(repo, "config", "user.name", "Alatyr Check")
        (repo / "design.md").write_text("identity invariant\n", encoding="utf-8")
        (repo / "src").mkdir()
        (repo / "src" / "example.txt").write_text("lossy key\n", encoding="utf-8")
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "base")
        base = git(repo, "rev-parse", "HEAD")
        (repo / "src" / "example.txt").write_text("typed tuple key\n", encoding="utf-8")
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "fix identity")
        result = git(repo, "rev-parse", "HEAD")

        record = fixture_record(base, result)
        record_path = repo / ".ai/project/engineering-evidence/records/ENG-1.json"
        record_path.parent.mkdir(parents=True)
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        index_path = record_path.parent.parent / "index.json"
        index_path.write_text(json.dumps(fixture_index(record), indent=2) + "\n", encoding="utf-8")
        (index_path.parent / "README.md").write_text(
            "# Durable Engineering Evidence\n\n"
            "Owner: engineering\n\n"
            "Storage mode: repository\n\n"
            "External patch policy: exclude from external patch\n\n"
            "Retention policy: retain validated records\n\n"
            "Redaction policy: exclude raw conversations and secrets\n",
            encoding="utf-8",
        )
        authoring_template = repo / ".ai/assistant/templates/engineering-evidence-record.json"
        authoring_template.parent.mkdir(parents=True)
        authoring_template.write_text(RECORD.read_text(encoding="utf-8"), encoding="utf-8")

        def write(value: dict[str, Any]) -> None:
            record_path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
            index_path.write_text(json.dumps(fixture_index(value), indent=2) + "\n", encoding="utf-8")

        errors = [finding for finding in run_validator(repo) if finding.level == "error"]
        if errors:
            failures.append("valid fixture failed: " + "; ".join(f"{item.code}: {item.message}" for item in errors))

        invalid_cases = [
            (
                "raw-chat retention",
                lambda value: value["privacy"].update(raw_chat_stored=True),
                {"ENGINEERING_EVIDENCE_PRIVACY", "ENGINEERING_EVIDENCE_RECORD_SCHEMA"},
            ),
            (
                "missing architecture evidence",
                lambda value: value.update(affected_architecture=[{}]),
                {"ENGINEERING_EVIDENCE_RECORD_SCHEMA"},
            ),
            (
                "missing validation evidence",
                lambda value: value.update(validation={}),
                {"ENGINEERING_EVIDENCE_RECORD_SCHEMA"},
            ),
            (
                "unexplained regression case",
                lambda value: value["regression_matrix"][0].pop("protects"),
                {"ENGINEERING_EVIDENCE_RECORD_SCHEMA", "ENGINEERING_EVIDENCE_REGRESSION"},
            ),
            (
                "unresolvable result revision",
                lambda value: value["repository_binding"].update(result_revision="missing-revision"),
                {"ENGINEERING_EVIDENCE_REVISION"},
            ),
            (
                "reversed repository range",
                lambda value: value["repository_binding"].update(base_revision=result, result_revision=base),
                {"ENGINEERING_EVIDENCE_REVISION_ANCESTRY"},
            ),
            (
                "symbolic final revision",
                lambda value: value["repository_binding"].update(result_revision="HEAD"),
                {"ENGINEERING_EVIDENCE_REVISION_EXACT"},
            ),
        ]
        for label, mutate, expected_codes in invalid_cases:
            invalid = copy.deepcopy(record)
            mutate(invalid)
            record_path.write_text(json.dumps(invalid, indent=2) + "\n", encoding="utf-8")
            findings = run_validator(repo)
            if not any(
                finding.level == "error" and finding.code in expected_codes
                for finding in findings
            ):
                failures.append(f"validator did not reject {label}")

        tree_record = copy.deepcopy(record)
        tree_record["repository_binding"].update(
            kind="tree",
            result_revision=git(repo, "rev-parse", f"{result}^{{tree}}"),
        )
        write(tree_record)
        tree_errors = [finding for finding in run_validator(repo) if finding.level == "error"]
        if tree_errors:
            failures.append("valid tree binding failed: " + "; ".join(f"{item.code}: {item.message}" for item in tree_errors))

        legacy = copy.deepcopy(record)
        legacy["schema_version"] = 1
        legacy["repository_binding"].pop("binding_state")
        legacy["repository_binding"].pop("prior_bindings")
        write(legacy)
        legacy_findings = run_validator(repo)
        if any(item.level == "error" for item in legacy_findings):
            failures.append("schema-version-1 engineering evidence was not preserved as compatible")
        if not any(item.code == "ENGINEERING_EVIDENCE_LEGACY_BINDING" for item in legacy_findings):
            failures.append("legacy engineering evidence did not report binding limitations")

        snapshot_record = copy.deepcopy(record)
        digest = hashlib.sha256()
        digest.update(b"src/example.txt\0")
        digest.update((repo / "src/example.txt").read_bytes())
        digest.update(b"\0")
        snapshot_digest = digest.hexdigest()
        snapshot_record["repository_binding"].update(
            kind="selected-file-snapshot",
            result_revision=snapshot_digest,
            selected_paths=["src/example.txt"],
            snapshot_sha256=snapshot_digest,
        )
        write(snapshot_record)
        (repo / "src/example.txt").write_text("later legitimate edit\n", encoding="utf-8")
        historical_findings = run_validator(repo)
        if any(item.level == "error" and item.code.startswith("ENGINEERING_EVIDENCE_SNAPSHOT") for item in historical_findings):
            failures.append("later edits invalidated a finalized historical snapshot")
        if not any(item.code == "ENGINEERING_EVIDENCE_SNAPSHOT_HISTORICAL" for item in historical_findings):
            failures.append("historical snapshot drift was not reported as non-corrupting evidence")


def main() -> int:
    failures: list[str] = []
    require_text(FRAMEWORK, ["ALATYR-ENGINEERING-EVIDENCE-001", "## Capture Decision", "## Publication Boundary", "Do not store raw chat", "materiality", "source-of-truth registry"], failures)
    require_text(FLOW, ["## Steps", "captured", "skipped", "blocked", "Reject raw chats", "applicable, not applicable, or unknown", "canonical source"], failures)
    require_text(GATE, ["reusable engineering knowledge", "durable_engineering_evidence", "structured materiality", "registered for the named project fact"], failures)
    require_text(TARGET_AGENTS, ["durable_engineering_evidence", "captured/skipped/blocked"], failures)
    require_text(OPERATION_ROUTING, ["durable_engineering_evidence", "fact-specific reason"], failures)
    require_text(
        POLICY,
        ["Owner:", "Storage mode:", "External patch policy:", "Retention policy:", "Redaction policy:"],
        failures,
    )

    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        jsonschema.Draft7Validator.check_schema(schema)
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
        scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        failures.append(f"invalid engineering-evidence artifact: {exc}")
    else:
        if index.get("records") != []:
            failures.append("source engineering-evidence index must start empty")
        if index.get("schema_version") != 3 or "redaction_policy" not in index:
            failures.append("source engineering-evidence index must use contract-projection schema 3")
        if record.get("record_kind") != "alatyr-engineering-evidence":
            failures.append("record template kind is invalid")
        if record.get("schema_version") != 2:
            failures.append("record template must use repository-binding schema 2")
        if overlay.get("overlay") != "engineering-evidence":
            failures.append("engineering-evidence overlay identity is invalid")
        scenario_states = {item.get("expected_capture_status") for item in scenarios.get("scenarios", []) if isinstance(item, dict)}
        if scenario_states != {"captured", "skipped", "blocked"}:
            failures.append("conformance scenarios must cover captured, skipped, and blocked decisions")

    validate_fixture(failures)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: checked durable engineering-evidence contracts and validator enforcement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
