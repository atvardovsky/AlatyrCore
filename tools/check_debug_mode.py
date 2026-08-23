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
    actor: str,
    causal_class: str,
    intervention_kind: str,
    contribution_kind: str,
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
            "value": f"2026-08-21T12:{sequence:02d}:00Z",
            "evidence_kind": "observed",
        },
        "actor": actor,
        "causal_class": causal_class,
        "intervention_kind": intervention_kind,
        "contribution_kind": contribution_kind,
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
        event("EVT-1", 1, "alatyr", "independent-within-scope", "not-applicable", "finding", "dependency", dependency=True),
        event(
            "EVT-2",
            2,
            "human",
            "intervention",
            "correction",
            "decision",
            "review-correction",
            architectural=True,
            architectural_impacts=["accepted-invariant", "solution-class"],
            decision_effect="changes-direction",
        ),
        event(
            "EVT-3",
            3,
            "alatyr",
            "derived-from-human",
            "not-applicable",
            "implementation",
            "implementation-revision",
            causes=["EVT-2"],
        ),
        event(
            "EVT-4",
            4,
            "alatyr",
            "derived-from-human",
            "not-applicable",
            "finding",
            "hypothesis",
            causes=["EVT-3"],
            hypothesis="rejected",
        ),
        event(
            "EVT-5",
            5,
            "external-maintainer",
            "intervention",
            "correction",
            "decision",
            "review-correction",
        ),
        event(
            "EVT-6",
            6,
            "alatyr",
            "derived-from-human",
            "not-applicable",
            "validation",
            "regression-scenario",
            causes=["EVT-2"],
        ),
        event(
            "EVT-7",
            7,
            "alatyr",
            "derived-from-human",
            "not-applicable",
            "finding",
            "invariant",
            causes=["EVT-4"],
            architectural_impacts=["accepted-invariant"],
        ),
        event(
            "EVT-8",
            8,
            "alatyr",
            "derived-from-human",
            "not-applicable",
            "finding",
            "dependency",
            causes=["EVT-2"],
            dependency=True,
        ),
        event(
            "EVT-9",
            9,
            "alatyr",
            "derived-from-external",
            "not-applicable",
            "implementation",
            "implementation-revision",
            causes=["EVT-5"],
            post_review=True,
        ),
        event(
            "EVT-10",
            10,
            "alatyr",
            "derived-from-human",
            "not-applicable",
            "validation",
            "validation",
            causes=["EVT-2"],
            validation=True,
        ),
    ]


def fixture_metrics() -> dict[str, Any]:
    event_ids = {
        "human_interventions": ["EVT-2"],
        "human_architectural_interventions": ["EVT-2"],
        "alatyr_independent_findings": ["EVT-1"],
        "derived_findings_after_human": ["EVT-4", "EVT-7", "EVT-8"],
        "alatyr_independent_dependency_checks": ["EVT-1"],
        "human_requested_dependency_checks": [],
        "derived_dependency_expansions_after_human": ["EVT-8"],
        "hypotheses_tested": ["EVT-4"],
        "hypotheses_rejected": ["EVT-4"],
        "implementation_revisions": ["EVT-3", "EVT-9"],
        "implementation_corrections_after_human": ["EVT-3"],
        "validation_expansions": ["EVT-10"],
        "regression_scenarios_added": ["EVT-6"],
        "maintainer_corrections": ["EVT-5"],
        "post_review_rework": ["EVT-9"],
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
        "schema_version": 2,
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
                "binding_state": "final",
                "base_revision": base,
                "result_revision": result,
                "review_reference": "not applicable",
                "selected_paths": [],
                "snapshot_sha256": "not applicable",
                "prior_bindings": [],
            },
            "implementation_surfaces": ["src/example.txt"],
            "validation": {"results": ["fixture review passed"], "skipped": []},
            "engineering_evidence_ids": ["ENG-1"],
            "engineering_evidence_decision": {
                "status": "captured",
                "trigger_event_ids": ["EVT-2", "EVT-4", "EVT-5"],
                "trigger_kinds": ["direction-change", "rejected-hypothesis", "correction"],
                "knowledge_preserved_by": [],
                "reason": "Material investigation knowledge is reusable.",
                "next_safe_action": "No further evidence action is required.",
            },
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
        "schema_version": 3,
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
                "record_schema_version": record["schema_version"],
                "repository_binding_state": binding.get("binding_state", "legacy"),
                "engineering_evidence_status": record["final_result"].get("engineering_evidence_decision", {}).get("status", "legacy"),
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
        authoring_template = repo / ".ai/assistant/templates/debug-session-record.json"
        authoring_template.parent.mkdir(parents=True)
        authoring_template.write_text(RECORD.read_text(encoding="utf-8"), encoding="utf-8")

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

        def set_metric(
            value: dict[str, Any], metric_name: str, event_ids: list[str]
        ) -> None:
            value["metrics"][metric_name].update(
                value=len(event_ids), event_ids=event_ids
            )

        def assert_valid(label: str, value: dict[str, Any]) -> None:
            write(value)
            case_errors = [
                finding for finding in run_validator(repo) if finding.level == "error"
            ]
            if case_errors:
                failures.append(
                    f"valid {label} fixture failed: "
                    + "; ".join(
                        f"{item.code}: {item.message}" for item in case_errors
                    )
                )

        activation_only = copy.deepcopy(record)
        activation_only["events"] = [copy.deepcopy(record["events"][0])]
        activation_only["metrics"] = {
            name: {
                "value": 1
                if name
                in {
                    "alatyr_independent_findings",
                    "alatyr_independent_dependency_checks",
                }
                else 0,
                "evidence_kind": "event-derived",
                "event_ids": ["EVT-1"]
                if name
                in {
                    "alatyr_independent_findings",
                    "alatyr_independent_dependency_checks",
                }
                else [],
            }
            for name in METRIC_NAMES
        }
        activation_only["final_result"]["engineering_evidence_ids"] = []
        activation_only["final_result"]["engineering_evidence_decision"].update(
            status="skipped",
            trigger_event_ids=[],
            trigger_kinds=[],
            knowledge_preserved_by=[],
            reason="No durable material trigger was observed.",
        )
        assert_valid("task activation is not an intervention", activation_only)

        validation_request = copy.deepcopy(record)
        validation_request["events"][1].update(
            intervention_kind="validation-request",
            contribution_kind="coordination",
            category="validation",
            architectural_supervision=False,
            architectural_impacts=[],
            decision_effect="confirms-direction",
        )
        set_metric(validation_request, "human_architectural_interventions", [])
        set_metric(
            validation_request, "implementation_corrections_after_human", []
        )
        validation_request["final_result"]["engineering_evidence_decision"][
            "trigger_event_ids"
        ] = ["EVT-4", "EVT-5"]
        assert_valid(
            "human validation request is not an implementation correction",
            validation_request,
        )

        external_validation_request = copy.deepcopy(record)
        external_validation_request["events"][4].update(
            intervention_kind="validation-request",
            contribution_kind="coordination",
            category="validation",
        )
        external_validation_request["events"][8]["post_review_rework"] = False
        set_metric(external_validation_request, "maintainer_corrections", [])
        set_metric(external_validation_request, "post_review_rework", [])
        external_validation_request["final_result"][
            "engineering_evidence_decision"
        ]["trigger_event_ids"] = ["EVT-2", "EVT-4"]
        assert_valid(
            "external validation request is not a maintainer correction",
            external_validation_request,
        )

        def remove_external_correction_claim(value: dict[str, Any]) -> None:
            value["events"][4].update(
                intervention_kind="validation-request",
                contribution_kind="coordination",
                category="validation",
            )
            set_metric(value, "maintainer_corrections", [])
            set_metric(value, "post_review_rework", [])
            value["final_result"]["engineering_evidence_decision"][
                "trigger_event_ids"
            ] = ["EVT-2", "EVT-4"]

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
                lambda value: value["events"][2].update(causal_class="independent-within-scope"),
                {"DEBUG_MODE_INDEPENDENCE"},
            ),
            (
                "validation request counted as implementation correction",
                lambda value: value["events"][1].update(intervention_kind="validation-request"),
                {"DEBUG_MODE_METRIC_DRIFT"},
            ),
            (
                "external input counted as maintainer correction",
                lambda value: value["events"][4].update(intervention_kind="validation-request"),
                {"DEBUG_MODE_METRIC_DRIFT"},
            ),
            (
                "post-review rework without a correction cause",
                remove_external_correction_claim,
                {"DEBUG_MODE_POST_REVIEW_CAUSE"},
            ),
            (
                "implementation contribution counted as finding",
                lambda value: value["events"][2].update(contribution_kind="finding"),
                {"DEBUG_MODE_METRIC_DRIFT"},
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
            (
                "completed evidence decision left pending",
                lambda value: value["final_result"]["engineering_evidence_decision"].update(status="pending"),
                {"DEBUG_MODE_EVIDENCE_PENDING"},
            ),
            (
                "material evidence skipped without canonical preservation",
                lambda value: (
                    value["final_result"].update(engineering_evidence_ids=[]),
                    value["final_result"]["engineering_evidence_decision"].update(status="skipped", knowledge_preserved_by=[]),
                ),
                {"DEBUG_MODE_EVIDENCE_SKIP"},
            ),
            (
                "material evidence trigger omitted",
                lambda value: value["final_result"]["engineering_evidence_decision"].update(trigger_event_ids=["EVT-2"]),
                {"DEBUG_MODE_EVIDENCE_TRIGGER"},
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
        legacy["schema_version"] = 1
        legacy_event = copy.deepcopy(record["events"][0])
        for field in ["actor", "causal_class", "intervention_kind", "contribution_kind"]:
            legacy_event.pop(field)
        legacy_event["origin"] = "alatyr-initiated"
        legacy["events"] = [legacy_event]
        legacy["metrics"] = {
            name: {
                "value": 1 if name in {"alatyr_independent_findings", "alatyr_independent_dependency_checks"} else 0,
                "evidence_kind": "event-derived",
                "event_ids": ["EVT-1"] if name in {"alatyr_independent_findings", "alatyr_independent_dependency_checks"} else [],
            }
            for name in METRIC_NAMES
        }
        legacy["final_result"].pop("engineering_evidence_decision")
        legacy_binding = legacy["final_result"]["repository_binding"]
        legacy_binding.pop("binding_state")
        legacy_binding.pop("prior_bindings")
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
        if not any(item.code == "DEBUG_MODE_LEGACY_ATTRIBUTION" for item in legacy_findings):
            failures.append("legacy records did not report attribution comparability warning")

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
    require_text(FLOW, ["## Modes", "explicit current user request", "derived-from-human", "contribution kind", "rejected-hypothesis", "prior_bindings"], failures)
    require_text(GATE, ["non-canonical observability evidence", "logical scope", "Engineering Evidence decision", "direction-changing correction"], failures)
    require_text(SUMMARY, ["# Alatyr Debug Summary", "Record schema and attribution model", "Human architectural interventions", "Final result binding", "Durable engineering evidence", "External projection"], failures)
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
        if index.get("schema_version") != 3 or "redaction_policy" not in index:
            failures.append("source Debug Mode index must use contract-projection schema 3")
        if record.get("record_kind") != "alatyr-debug-session":
            failures.append("debug record template kind is invalid")
        if record.get("evidence_classification") != "non-canonical-observability":
            failures.append("debug record template must be non-canonical")
        if record.get("schema_version") != 2:
            failures.append("debug record template must use attribution contract schema 2")
        if "engineering_evidence_decision" not in record.get("final_result", {}):
            failures.append("debug record template must expose durable evidence closure")
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
