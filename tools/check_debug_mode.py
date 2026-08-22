#!/usr/bin/env python3
"""Validate Debug Mode contracts, templates, and installed enforcement."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

import jsonschema

from validate_target_adapter import AdapterValidatorConfig, Validator


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
FRAMEWORK = ROOT / "framework" / "debug-mode.md"
INDEX = TARGET / ".ai" / "project" / "debug" / "index.json"
POLICY = TARGET / ".ai" / "project" / "debug" / "README.md"
RECORD_POLICY = TARGET / ".ai" / "project" / "debug" / "records" / "README.md"
FLOW = TARGET / ".ai" / "assistant" / "flows" / "debug-mode.flow.md"
GATE = TARGET / ".ai" / "assistant" / "gates" / "debug-mode.md"
RECORD = TARGET / ".ai" / "assistant" / "templates" / "debug-session-record.json"
SUMMARY = TARGET / ".ai" / "assistant" / "templates" / "debug-summary.md"
OVERLAY = TARGET / ".ai" / "assistant" / "context" / "task-scales" / "debug-mode.json"
SCHEMA = ROOT / "schemas" / "alatyr-debug-session.schema.json"
SCENARIOS = ROOT / "conformance" / "debug-mode-scenarios.json"

METRIC_NAMES = [
    "human_interventions",
    "human_architectural_interventions",
    "alatyr_independent_findings",
    "derived_findings_after_human",
    "alatyr_independent_dependency_checks",
    "human_requested_dependency_checks",
    "derived_dependency_expansions_after_human",
    "hypotheses_tested",
    "hypotheses_rejected",
    "implementation_revisions",
    "implementation_corrections_after_human",
    "validation_expansions",
    "regression_scenarios_added",
    "maintainer_corrections",
    "post_review_rework",
]


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


def event(
    event_id: str,
    sequence: int,
    origin: str,
    category: str,
    *,
    causes: list[str] | None = None,
    architectural: bool = False,
    architectural_impacts: list[str] | None = None,
    decision_effect: str = "none",
    dependency: bool = False,
    validation: bool = False,
    post_review: bool = False,
    hypothesis: str = "not-applicable",
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "sequence": sequence,
        "occurred_at": {
            "value": f"2026-08-21T12:0{sequence}:00Z",
            "evidence_kind": "observed",
        },
        "origin": origin,
        "category": category,
        "summary": f"Material event {event_id}",
        "material_effect": f"Changed investigation outcome {event_id}",
        "evidence": ["src/example.txt"],
        "caused_by_event_ids": causes or [],
        "architectural_supervision": architectural,
        "architectural_impacts": architectural_impacts or [],
        "decision_effect": decision_effect,
        "dependency_expansion": dependency,
        "validation_expansion": validation,
        "post_review_rework": post_review,
        "hypothesis_outcome": hypothesis,
    }


def fixture_events() -> list[dict[str, Any]]:
    return [
        event("EVT-1", 1, "alatyr-initiated", "dependency", dependency=True),
        event(
            "EVT-2",
            2,
            "human-initiated",
            "review-correction",
            architectural=True,
            architectural_impacts=["accepted-invariant", "solution-class"],
            decision_effect="changes-direction",
        ),
        event(
            "EVT-3",
            3,
            "derived-after-human-intervention",
            "implementation-revision",
            causes=["EVT-2"],
            dependency=True,
            validation=True,
        ),
        event(
            "EVT-4",
            4,
            "derived-after-human-intervention",
            "hypothesis",
            causes=["EVT-3"],
            hypothesis="rejected",
        ),
        event(
            "EVT-5",
            5,
            "external-maintainer",
            "review-correction",
            post_review=True,
        ),
        event(
            "EVT-6",
            6,
            "derived-after-human-intervention",
            "regression-scenario",
            causes=["EVT-2"],
        ),
        event(
            "EVT-7",
            7,
            "derived-after-human-intervention",
            "invariant",
            causes=["EVT-4"],
            architectural_impacts=["accepted-invariant"],
        ),
    ]


def fixture_metrics() -> dict[str, Any]:
    event_ids = {
        "human_interventions": ["EVT-2"],
        "human_architectural_interventions": ["EVT-2"],
        "alatyr_independent_findings": ["EVT-1"],
        "derived_findings_after_human": ["EVT-3", "EVT-4", "EVT-6", "EVT-7"],
        "alatyr_independent_dependency_checks": ["EVT-1"],
        "human_requested_dependency_checks": [],
        "derived_dependency_expansions_after_human": ["EVT-3"],
        "hypotheses_tested": ["EVT-4"],
        "hypotheses_rejected": ["EVT-4"],
        "implementation_revisions": ["EVT-3"],
        "implementation_corrections_after_human": ["EVT-3"],
        "validation_expansions": ["EVT-3"],
        "regression_scenarios_added": ["EVT-6"],
        "maintainer_corrections": ["EVT-5"],
        "post_review_rework": ["EVT-5"],
    }
    return {
        name: {
            "value": len(event_ids[name]),
            "evidence_kind": "event-derived",
            "event_ids": event_ids[name],
        }
        for name in METRIC_NAMES
    }


def fixture_record(base: str, result: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "record_kind": "alatyr-debug-session",
        "evidence_classification": "non-canonical-observability",
        "debug_id": "DEBUG-1",
        "status": "completed",
        "authority": "non-canonical",
        "owner": "engineering",
        "task": {
            "summary": "Repair one identity invariant",
            "references": ["issue-1"],
            "scope_kind": "task",
            "scope_id": "task-1",
            "operation_ids": ["product-change"],
            "task_class": "defect-repair",
        },
        "activation": {
            "enabled_by": "explicit-user-request",
            "request_reference": "request-1",
            "enabled_at": {"value": "2026-08-21T12:00:00Z", "evidence_kind": "observed"},
            "initial_revision": base,
            "expires_on": "task-completion",
            "ended_by": "task-completion",
        },
        "timing": {
            "started_at": {"value": "2026-08-21T12:00:00Z", "evidence_kind": "observed"},
            "completed_at": {"value": "2026-08-21T12:10:00Z", "evidence_kind": "observed"},
            "elapsed_seconds": {"value": 600, "evidence_kind": "observed"},
            "active_work_seconds": {"value": None, "evidence_kind": "unknown"},
        },
        "capture_quality": {
            "event_coverage": "complete",
            "missing_intervals": [],
            "observer_effect": "negligible",
            "estimated_overhead_seconds": {"value": 30, "evidence_kind": "estimated"},
        },
        "events": fixture_events(),
        "metrics": fixture_metrics(),
        "final_result": {
            "summary": "Identity invariant repaired and validated",
            "repository_binding": {
                "kind": "commit",
                "base_revision": base,
                "result_revision": result,
                "review_reference": "not applicable",
                "selected_paths": [],
                "snapshot_sha256": "not applicable",
            },
            "implementation_surfaces": ["src/example.txt"],
            "validation": {"results": ["fixture review passed"], "skipped": []},
            "engineering_evidence_ids": ["ENG-1"],
            "upstream_projection": {
                "kind": "clean-external",
                "included_debug_files": False,
                "projected_paths": ["src/example.txt"],
                "evidence": [result],
            },
        },
        "publication": {
            "storage_mode": "repository support branch",
            "visibility": "internal",
            "included_in_external_patch": False,
            "policy_evidence": ".ai/project/debug/README.md",
        },
        "privacy": {
            "raw_ai_conversation_stored": False,
            "raw_human_conversation_stored": False,
            "chain_of_thought_stored": False,
            "prompts_stored": False,
            "secrets_stored": False,
            "credentials_stored": False,
            "unrelated_personal_data_stored": False,
            "unrelated_session_history_stored": False,
            "unused_speculation_stored": False,
            "complete_diffs_stored": False,
            "verbose_logs_stored": False,
            "redactions": [],
        },
        "residual_uncertainty": [],
        "limitations": ["Event completeness and attribution require review."],
    }


def fixture_index(record: dict[str, Any]) -> dict[str, Any]:
    binding = record["final_result"]["repository_binding"]
    elapsed = record["timing"]["elapsed_seconds"]
    return {
        "schema_version": 2,
        "index_kind": "target-alatyr-debug-index",
        "project": "fixture",
        "owner": "engineering",
        "storage_mode": "repository support branch",
        "visibility": "internal",
        "retention_policy": "retain reviewed records",
        "redaction_policy": "exclude raw conversations and secrets",
        "external_patch_policy": "exclude from external patch",
        "records": [
            {
                "debug_id": record["debug_id"],
                "status": record["status"],
                "record": ".ai/project/debug/records/DEBUG-1.json",
                "task_references": record["task"]["references"],
                "scope_kind": record["task"]["scope_kind"],
                "scope_id": record["task"]["scope_id"],
                "task_class": record["task"]["task_class"],
                "repository_binding_kind": binding["kind"],
                "result_revision": binding["result_revision"],
                "event_coverage": record["capture_quality"]["event_coverage"],
                "observer_effect": record["capture_quality"]["observer_effect"],
                "elapsed_seconds": elapsed["value"],
                "elapsed_evidence_kind": elapsed["evidence_kind"],
                "metrics": {
                    name: record["metrics"][name]["value"] for name in METRIC_NAMES
                },
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
    validator.check_debug_mode(None)
    return validator.findings


def validate_fixture(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="alatyr-debug-mode-") as directory:
        repo = Path(directory)
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "alatyr@example.invalid")
        git(repo, "config", "user.name", "Alatyr Check")
        (repo / "src").mkdir()
        (repo / "src" / "example.txt").write_text("before\n", encoding="utf-8")
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "base")
        base = git(repo, "rev-parse", "HEAD")
        (repo / "src" / "example.txt").write_text("after\n", encoding="utf-8")
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "result")
        result = git(repo, "rev-parse", "HEAD")

        record = fixture_record(base, result)
        record_path = repo / ".ai/project/debug/records/DEBUG-1.json"
        record_path.parent.mkdir(parents=True)
        index_path = record_path.parent.parent / "index.json"
        (index_path.parent / "README.md").write_text(
            "# Alatyr Debug Evidence\n\n"
            "Owner: engineering\n"
            "Storage mode: repository support branch\n"
            "Visibility: internal\n"
            "Retention policy: retain reviewed records\n"
            "Redaction policy: exclude raw conversations and secrets\n"
            "External patch policy: exclude from external patch\n",
            encoding="utf-8",
        )
        engineering_index_path = (
            repo / ".ai/project/engineering-evidence/index.json"
        )
        engineering_index_path.parent.mkdir(parents=True)
        engineering_index_path.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "index_kind": "target-engineering-evidence-index",
                    "records": [{"evidence_id": "ENG-1"}],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        def write(value: dict[str, Any]) -> None:
            record_path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
            index_path.write_text(json.dumps(fixture_index(value), indent=2) + "\n", encoding="utf-8")

        write(record)
        errors = [finding for finding in run_validator(repo) if finding.level == "error"]
        if errors:
            failures.append(
                "valid fixture failed: "
                + "; ".join(f"{item.code}: {item.message}" for item in errors)
            )

        invalid_cases: list[tuple[str, Callable[[dict[str, Any]], None], set[str]]] = [
            (
                "raw conversation retention",
                lambda value: value["privacy"].update(raw_ai_conversation_stored=True),
                {"DEBUG_MODE_PRIVACY", "DEBUG_MODE_RECORD_SCHEMA"},
            ),
            (
                "derived event without human cause",
                lambda value: value["events"][2].update(caused_by_event_ids=[]),
                {"DEBUG_MODE_DERIVATION_CAUSE"},
            ),
            (
                "independent claim after human direction",
                lambda value: value["events"][2].update(origin="alatyr-initiated"),
                {"DEBUG_MODE_INDEPENDENCE"},
            ),
            (
                "event-derived metric drift",
                lambda value: value["metrics"]["human_interventions"].update(value=2),
                {"DEBUG_MODE_METRIC_DRIFT"},
            ),
            (
                "observed timing drift",
                lambda value: value["timing"]["elapsed_seconds"].update(value=300),
                {"DEBUG_MODE_TIMING_DRIFT"},
            ),
            (
                "Alatyr path in clean upstream projection",
                lambda value: value["final_result"]["upstream_projection"].update(projected_paths=[".ai/project/debug/index.json"]),
                {"DEBUG_MODE_UPSTREAM_PATH"},
            ),
            (
                "implicit activation",
                lambda value: value["activation"].update(enabled_by="inferred"),
                {"DEBUG_MODE_ACTIVATION", "DEBUG_MODE_RECORD_SCHEMA"},
            ),
            (
                "human architectural impact without supervision",
                lambda value: value["events"][1].update(architectural_supervision=False),
                {"DEBUG_MODE_ARCHITECTURAL_SUPERVISION_DRIFT"},
            ),
            (
                "architectural supervision without structured impacts",
                lambda value: value["events"][1].update(architectural_impacts=[]),
                {"DEBUG_MODE_ARCHITECTURAL_IMPACT_MISSING"},
            ),
            (
                "direction change without rejected hypothesis",
                lambda value: value["events"][3].update(hypothesis_outcome="confirmed"),
                {"DEBUG_MODE_DIRECTION_HYPOTHESIS_MISSING"},
            ),
            (
                "direction change without replacement invariant",
                lambda value: value["events"][6].update(category="validation"),
                {"DEBUG_MODE_DIRECTION_REPLACEMENT_MISSING"},
            ),
            (
                "Debug event used as durable evidence",
                lambda value: value["final_result"].update(engineering_evidence_ids=["EVT-1"]),
                {"DEBUG_MODE_ENGINEERING_EVIDENCE_EVENT_ID"},
            ),
            (
                "unknown durable engineering evidence",
                lambda value: value["final_result"].update(engineering_evidence_ids=["ENG-UNKNOWN"]),
                {"DEBUG_MODE_ENGINEERING_EVIDENCE_REFERENCE"},
            ),
        ]
        for label, mutate, expected_codes in invalid_cases:
            invalid = copy.deepcopy(record)
            mutate(invalid)
            write(invalid)
            findings = run_validator(repo)
            if not any(
                finding.level == "error" and finding.code in expected_codes
                for finding in findings
            ):
                failures.append(f"validator did not reject {label}")

        legacy = copy.deepcopy(record)
        for legacy_event in legacy["events"]:
            legacy_event.pop("architectural_impacts")
            legacy_event.pop("decision_effect")
        write(legacy)
        legacy_findings = run_validator(repo)
        legacy_errors = [item for item in legacy_findings if item.level == "error"]
        if legacy_errors:
            failures.append(
                "legacy structured-classification compatibility failed: "
                + "; ".join(
                    f"{item.code}: {item.message}" for item in legacy_errors
                )
            )
        if not any(
            item.code == "DEBUG_MODE_STRUCTURED_CLASSIFICATION_MISSING"
            for item in legacy_findings
        ):
            failures.append("legacy events did not report structured classification migration warnings")

        duplicate_index = {
            "schema_version": 2,
            "index_kind": "target-engineering-evidence-index",
            "records": [{"evidence_id": "ENG-1"}, {"evidence_id": "ENG-1"}],
        }
        engineering_index_path.write_text(
            json.dumps(duplicate_index, indent=2) + "\n", encoding="utf-8"
        )
        write(record)
        if not any(
            finding.level == "error"
            and finding.code == "DEBUG_MODE_ENGINEERING_EVIDENCE_REFERENCE"
            for finding in run_validator(repo)
        ):
            failures.append("validator did not reject duplicate durable evidence resolution")


def main() -> int:
    failures: list[str] = []
    require_text(
        FRAMEWORK,
        [
            "ALATYR-DEBUG-001",
            "## Activation And Expiry",
            "## Normalized Event Model",
            "## Architectural Supervision",
            "## Privacy Boundary",
            "## Final Result And External Projection",
        ],
        failures,
    )
    require_text(FLOW, ["## Modes", "explicit current user request", "derived-after-human-intervention", "architectural_impacts", "rejected-hypothesis"], failures)
    require_text(GATE, ["non-canonical observability evidence", "logical scope", "engineering-evidence ID", "direction-changing correction"], failures)
    require_text(SUMMARY, ["# Alatyr Debug Summary", "Human architectural interventions", "External projection"], failures)
    require_text(
        POLICY,
        ["Owner:", "Storage mode:", "Visibility:", "Retention policy:", "Redaction policy:", "External patch policy:"],
        failures,
    )
    require_text(
        RECORD_POLICY,
        ["architectural_impacts", "decision_effect", "migration-limited"],
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
        failures.append(f"invalid Debug Mode artifact: {exc}")
    else:
        if index.get("records") != []:
            failures.append("source Debug Mode index must start empty")
        if index.get("schema_version") != 2 or "redaction_policy" not in index:
            failures.append("source Debug Mode index must use policy schema 2")
        if record.get("record_kind") != "alatyr-debug-session":
            failures.append("debug record template kind is invalid")
        if record.get("evidence_classification") != "non-canonical-observability":
            failures.append("debug record template must be non-canonical")
        if overlay.get("overlay") != "debug-mode":
            failures.append("Debug Mode overlay identity is invalid")
        modes = {
            item.get("expected_mode")
            for item in scenarios.get("scenarios", [])
            if isinstance(item, dict)
        }
        if modes != {"enabled", "inactive", "checkpointed", "redacted", "finalized", "compared", "rejected", "excluded"}:
            failures.append("conformance scenarios do not cover the required Debug Mode lifecycle")

    validate_fixture(failures)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: checked Debug Mode contracts, privacy, attribution, metrics, and validator enforcement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
