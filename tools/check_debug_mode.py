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

LEGACY_METRIC_NAMES = [
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

V4_METRIC_NAMES = [
    "human_interventions",
    "human_architectural_interventions",
    "executor_independent_findings",
    "executor_derived_findings_after_human",
    "executor_independent_dependency_checks",
    "human_requested_dependency_checks",
    "executor_derived_dependency_expansions_after_human",
    "hypotheses_tested",
    "hypotheses_rejected",
    "implementation_revisions",
    "implementation_corrections_after_human",
    "validation_expansions",
    "regression_scenarios_added",
    "maintainer_corrections",
    "post_review_rework",
    "new_guidance_candidates",
    "known_guidance_routing_failures",
    "known_guidance_compliance_failures",
    "task_local_corrections",
    "scope_changes",
    "validation_requests",
]

CORRECTION_DISPOSITIONS = {
    "new-guidance-candidate",
    "known-guidance-routing-failure",
    "known-guidance-compliance-failure",
    "task-local",
    "scope-change",
    "validation-request",
}

IMPLEMENTATION_CORRECTION_DISPOSITIONS = {
    "new-guidance-candidate",
    "known-guidance-routing-failure",
    "known-guidance-compliance-failure",
    "task-local",
}

MATERIALITY_KINDS = [
    "undocumented-invariant",
    "rejected-hypothesis",
    "non-obvious-dependency",
    "cross-area-impact",
    "broad-regression-matrix",
    "compatibility-or-public-contract",
    "reviewer-correction",
    "direction-change",
    "expensive-to-reconstruct",
    "unresolved-authority-or-contract",
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
        for name in LEGACY_METRIC_NAMES
    }


def actor_attribution(role: str) -> tuple[dict[str, str], dict[str, Any]]:
    identities = {
        "human": {"actor_id": "human-reviewer", "identity_kind": "pseudonymous"},
        "executor": {"actor_id": "executor-primary", "identity_kind": "pseudonymous"},
        "alatyr-system": {"actor_id": "alatyr-router", "identity_kind": "service"},
        "external-maintainer": {"actor_id": "maintainer-reviewer", "identity_kind": "pseudonymous"},
        "automation": {"actor_id": "ci-validation", "identity_kind": "service"},
    }
    if role in {"human", "external-maintainer"}:
        provenance = {
            "evidence_kind": "unavailable",
            "provider": None,
            "product": None,
            "model": None,
            "runtime": None,
            "evidence": [],
        }
    elif role == "executor":
        provenance = {
            "evidence_kind": "declared",
            "provider": "fixture-provider",
            "product": "fixture-assistant",
            "model": "fixture-model",
            "runtime": "fixture-runtime",
            "evidence": ["fixture executor declaration"],
        }
    elif role == "alatyr-system":
        provenance = {
            "evidence_kind": "observed",
            "provider": None,
            "product": "AlatyrCore",
            "model": None,
            "runtime": "context-router",
            "evidence": ["fixture router result"],
        }
    else:
        provenance = {
            "evidence_kind": "observed",
            "provider": "fixture-ci",
            "product": "fixture-automation",
            "model": None,
            "runtime": "validation-job",
            "evidence": ["fixture automation result"],
        }
    return identities[role], provenance


def event_v4(
    event_id: str,
    sequence: int,
    actor_role: str,
    causal_class: str,
    intervention_kind: str,
    correction_disposition: str,
    contribution_kind: str,
    category: str,
    *,
    causes: list[str] | None = None,
    guidance_ids: list[str] | None = None,
    correction_evidence: list[str] | None = None,
    architectural: bool = False,
    architectural_impacts: list[str] | None = None,
    decision_effect: str = "none",
    dependency: bool = False,
    validation: bool = False,
    post_review: bool = False,
    hypothesis: str = "not-applicable",
) -> dict[str, Any]:
    identity, provenance = actor_attribution(actor_role)
    return {
        "event_id": event_id,
        "sequence": sequence,
        "occurred_at": {
            "value": f"2026-08-21T13:{sequence:02d}:00Z",
            "evidence_kind": "observed",
        },
        "actor_role": actor_role,
        "actor_identity": identity,
        "actor_provenance": provenance,
        "causal_class": causal_class,
        "intervention_kind": intervention_kind,
        "correction_disposition": correction_disposition,
        "related_guidance_ids": guidance_ids or [],
        "correction_evidence": correction_evidence or [],
        "contribution_kind": contribution_kind,
        "category": category,
        "summary": f"Material version-4 event {event_id}",
        "material_effect": f"Changed version-4 investigation outcome {event_id}",
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


def fixture_v4_events() -> list[dict[str, Any]]:
    return [
        event_v4("V4-1", 1, "executor", "independent-within-scope", "not-applicable", "not-applicable", "finding", "dependency", dependency=True),
        event_v4("V4-2", 2, "alatyr-system", "independent-within-scope", "not-applicable", "not-applicable", "coordination", "other"),
        event_v4("V4-3", 3, "automation", "independent-within-scope", "not-applicable", "not-applicable", "validation", "regression-scenario", validation=True),
        event_v4("V4-4", 4, "human", "intervention", "correction", "new-guidance-candidate", "decision", "review-correction", correction_evidence=["review introduced a reusable constraint"]),
        event_v4("V4-5", 5, "external-maintainer", "intervention", "correction", "known-guidance-routing-failure", "decision", "review-correction", guidance_ids=["GUIDANCE-1"], correction_evidence=["routing receipt omitted GUIDANCE-1"]),
        event_v4("V4-6", 6, "human", "intervention", "correction", "known-guidance-compliance-failure", "decision", "review-correction", guidance_ids=["GUIDANCE-2"], correction_evidence=["delivery receipt included GUIDANCE-2"]),
        event_v4("V4-7", 7, "human", "intervention", "correction", "task-local", "decision", "review-correction", correction_evidence=["correction is bounded to this fixture"]),
        event_v4("V4-8", 8, "human", "intervention", "scope-expansion", "scope-change", "coordination", "other", correction_evidence=["requested scope now includes a second boundary"]),
        event_v4("V4-9", 9, "human", "intervention", "validation-request", "validation-request", "validation", "validation", correction_evidence=["requested one additional validation result"]),
        event_v4("V4-10", 10, "executor", "derived-from-human", "not-applicable", "not-applicable", "implementation", "implementation-revision", causes=["V4-7"]),
        event_v4("V4-11", 11, "executor", "derived-from-human", "not-applicable", "not-applicable", "finding", "dependency", causes=["V4-4"], dependency=True),
        event_v4("V4-12", 12, "executor", "derived-from-external", "not-applicable", "not-applicable", "implementation", "implementation-revision", causes=["V4-5"], post_review=True),
    ]


def v4_ancestor_ids(event_id: str, events: dict[str, dict[str, Any]]) -> set[str]:
    ancestors: set[str] = set()
    pending = list(events.get(event_id, {}).get("caused_by_event_ids", []))
    while pending:
        ancestor_id = pending.pop()
        if ancestor_id in ancestors or ancestor_id not in events:
            continue
        ancestors.add(ancestor_id)
        pending.extend(events[ancestor_id].get("caused_by_event_ids", []))
    return ancestors


def expected_v4_metric_ids(events: list[dict[str, Any]]) -> dict[str, list[str]]:
    event_by_id = {event["event_id"]: event for event in events}

    def correction_ancestor(event: dict[str, Any], role: str | None = None) -> bool:
        for ancestor_id in v4_ancestor_ids(event["event_id"], event_by_id):
            ancestor = event_by_id[ancestor_id]
            if (
                ancestor.get("causal_class") == "intervention"
                and ancestor.get("correction_disposition")
                in IMPLEMENTATION_CORRECTION_DISPOSITIONS
                and (role is None or ancestor.get("actor_role") == role)
            ):
                return True
        return False

    def ids(predicate: Callable[[dict[str, Any]], bool]) -> list[str]:
        return [event["event_id"] for event in events if predicate(event)]

    disposition_metrics = {
        "new_guidance_candidates": "new-guidance-candidate",
        "known_guidance_routing_failures": "known-guidance-routing-failure",
        "known_guidance_compliance_failures": "known-guidance-compliance-failure",
        "task_local_corrections": "task-local",
        "scope_changes": "scope-change",
        "validation_requests": "validation-request",
    }
    expected = {
        "human_interventions": ids(lambda event: event["actor_role"] == "human" and event["causal_class"] == "intervention"),
        "human_architectural_interventions": ids(lambda event: event["actor_role"] == "human" and event["causal_class"] == "intervention" and event["architectural_supervision"]),
        "executor_independent_findings": ids(lambda event: event["actor_role"] == "executor" and event["causal_class"] == "independent-within-scope" and event["contribution_kind"] == "finding"),
        "executor_derived_findings_after_human": ids(lambda event: event["actor_role"] == "executor" and event["causal_class"] == "derived-from-human" and event["contribution_kind"] == "finding"),
        "executor_independent_dependency_checks": ids(lambda event: event["actor_role"] == "executor" and event["causal_class"] == "independent-within-scope" and event["category"] == "dependency"),
        "human_requested_dependency_checks": ids(lambda event: event["actor_role"] == "human" and event["causal_class"] == "intervention" and event["category"] == "dependency"),
        "executor_derived_dependency_expansions_after_human": ids(lambda event: event["actor_role"] == "executor" and event["causal_class"] == "derived-from-human" and event["dependency_expansion"]),
        "hypotheses_tested": ids(lambda event: event["category"] == "hypothesis" and event["hypothesis_outcome"] != "not-applicable"),
        "hypotheses_rejected": ids(lambda event: event["category"] == "hypothesis" and event["hypothesis_outcome"] == "rejected"),
        "implementation_revisions": ids(lambda event: event["contribution_kind"] == "implementation"),
        "implementation_corrections_after_human": ids(lambda event: event["contribution_kind"] == "implementation" and correction_ancestor(event, "human")),
        "validation_expansions": ids(lambda event: event["contribution_kind"] == "validation" and event["validation_expansion"]),
        "regression_scenarios_added": ids(lambda event: event["contribution_kind"] == "validation" and event["category"] == "regression-scenario"),
        "maintainer_corrections": ids(lambda event: event["actor_role"] == "external-maintainer" and event["causal_class"] == "intervention" and event["correction_disposition"] in IMPLEMENTATION_CORRECTION_DISPOSITIONS),
        "post_review_rework": ids(lambda event: event["post_review_rework"] and correction_ancestor(event, "external-maintainer")),
    }
    expected.update(
        {
            metric_name: ids(
                lambda event, disposition=disposition: event.get(
                    "correction_disposition"
                )
                == disposition
            )
            for metric_name, disposition in disposition_metrics.items()
        }
    )
    return expected


def fixture_v4_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    event_ids = expected_v4_metric_ids(events)
    return {
        name: {
            "value": len(event_ids[name]),
            "evidence_kind": "event-derived",
            "event_ids": event_ids[name],
        }
        for name in V4_METRIC_NAMES
    }


def validate_v4_semantics(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors = [
        f"schema:{'.'.join(str(item) for item in error.absolute_path) or 'root'}:{error.message}"
        for error in sorted(
            jsonschema.Draft7Validator(schema).iter_errors(record),
            key=lambda item: list(item.absolute_path),
        )
    ]
    if errors or record.get("schema_version") != 4:
        return errors or ["record is not schema version 4"]

    events = record.get("events", [])
    event_by_id = {
        event.get("event_id"): event
        for event in events
        if isinstance(event, dict) and isinstance(event.get("event_id"), str)
    }
    if len(event_by_id) != len(events):
        errors.append("event IDs must be unique resolved strings")
        return errors

    causal_role = {
        "derived-from-human": "human",
        "derived-from-external": "external-maintainer",
        "derived-from-executor": "executor",
        "derived-from-alatyr-system": "alatyr-system",
        "derived-from-automation": "automation",
    }
    for event in events:
        event_id = event["event_id"]
        ancestors = [event_by_id[item] for item in v4_ancestor_ids(event_id, event_by_id)]
        expected_role = causal_role.get(event["causal_class"])
        if expected_role and not any(item.get("actor_role") == expected_role for item in ancestors):
            errors.append(f"{event_id} lacks a causal {expected_role} ancestor")
        if event["causal_class"] == "independent-within-scope" and any(
            item.get("causal_class") == "intervention" for item in ancestors
        ):
            errors.append(f"{event_id} is not independent because it descends from an intervention")
        if event["architectural_supervision"] and (
            event["actor_role"] not in {"human", "external-maintainer"}
            or event["causal_class"] != "intervention"
            or not event["architectural_impacts"]
        ):
            errors.append(f"{event_id} has invalid architectural-supervision attribution")

    expected_metrics = expected_v4_metric_ids(events)
    metrics = record.get("metrics", {})
    for name in V4_METRIC_NAMES:
        metric = metrics.get(name, {})
        if metric.get("evidence_kind") != "event-derived":
            continue
        expected_ids = expected_metrics[name]
        if metric.get("value") != len(expected_ids) or metric.get("event_ids") != expected_ids:
            errors.append(f"metric {name} does not match its version-4 event predicate")
    return errors


def validate_v4_fixture(schema: dict[str, Any], failures: list[str]) -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    record["schema_version"] = 4
    record["final_result"].pop("lifecycle_coverage")
    record["final_result"].pop("project_knowledge_candidates")
    record["final_result"].pop("repository_lifecycle")
    record["events"] = fixture_v4_events()
    record["metrics"] = fixture_v4_metrics(record["events"])
    errors = validate_v4_semantics(record, schema)
    if errors:
        failures.append("valid schema-version-4 fixture failed: " + "; ".join(errors))

    invalid_cases: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
        (
            "missing actor identity",
            lambda value: value["events"][0].pop("actor_identity"),
            "actor_identity",
        ),
        (
            "known guidance failure without guidance ID",
            lambda value: value["events"][4].update(related_guidance_ids=[]),
            "related_guidance_ids",
        ),
        (
            "non-intervention correction disposition",
            lambda value: value["events"][0].update(correction_disposition="task-local", correction_evidence=["invalid"]),
            "correction_disposition",
        ),
        (
            "validation request mislabeled as correction",
            lambda value: value["events"][8].update(correction_disposition="task-local"),
            "correction_disposition",
        ),
        (
            "derived executor event without human ancestor",
            lambda value: value["events"][9].update(caused_by_event_ids=[]),
            "causal human ancestor",
        ),
        (
            "correction metric drift",
            lambda value: value["metrics"]["known_guidance_routing_failures"].update(value=2),
            "metric known_guidance_routing_failures",
        ),
    ]
    for label, mutate, expected in invalid_cases:
        invalid = copy.deepcopy(record)
        mutate(invalid)
        case_errors = validate_v4_semantics(invalid, schema)
        if not any(expected in error for error in case_errors):
            failures.append(f"version-4 checker did not reject {label}")

    legacy = fixture_record("legacy-base", "legacy-result")
    legacy_errors = list(jsonschema.Draft7Validator(schema).iter_errors(legacy))
    if legacy_errors:
        failures.append("schema-version-3 historical record no longer validates")
    silently_reinterpreted = copy.deepcopy(legacy)
    silently_reinterpreted["events"][0]["actor_role"] = "executor"
    if not list(jsonschema.Draft7Validator(schema).iter_errors(silently_reinterpreted)):
        failures.append("schema-version-3 record silently accepted version-4 attribution fields")


def materiality_evaluation(
    kind: str,
    outcome: str,
    *,
    event_ids: list[str] | None = None,
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "outcome": outcome,
        "event_ids": event_ids or [],
        "evidence": evidence or [],
        "reason": f"Fixture assessment for {kind}",
    }


def fixture_record(base: str, result: str) -> dict[str, Any]:
    return {
        "schema_version": 3,
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
        "continuation": {
            "kind": "initial",
            "previous_debug_id": "not-applicable",
            "reason": "Initial fixture Debug scope.",
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
            "claim_validation": {
                "fidelity": "exact-reproducer",
                "claims": ["The fixture invariant is repaired."],
                "evidence": ["fixture review passed"],
                "limitation": "The fixture proves only its bounded invariant.",
            },
            "engineering_evidence_ids": ["ENG-1"],
            "engineering_evidence_decision": {
                "status": "captured",
                "event_links": [
                    {"event_id": "EVT-1", "role": "finding"},
                    {"event_id": "EVT-2", "role": "decision"},
                    {"event_id": "EVT-2", "role": "correction"},
                    {"event_id": "EVT-2", "role": "direction-change"},
                    {"event_id": "EVT-3", "role": "implementation"},
                    {"event_id": "EVT-4", "role": "finding"},
                    {"event_id": "EVT-4", "role": "rejected-hypothesis"},
                    {"event_id": "EVT-5", "role": "decision"},
                    {"event_id": "EVT-5", "role": "correction"},
                    {"event_id": "EVT-6", "role": "validation"},
                    {"event_id": "EVT-7", "role": "finding"},
                    {"event_id": "EVT-8", "role": "finding"},
                    {"event_id": "EVT-9", "role": "implementation"},
                    {"event_id": "EVT-10", "role": "validation"}
                ],
                "materiality_evaluations": [
                    materiality_evaluation("undocumented-invariant", "applicable", event_ids=["EVT-7"]),
                    materiality_evaluation("rejected-hypothesis", "applicable", event_ids=["EVT-4"]),
                    materiality_evaluation("non-obvious-dependency", "applicable", event_ids=["EVT-1", "EVT-8"]),
                    materiality_evaluation("cross-area-impact", "applicable", event_ids=["EVT-2"]),
                    materiality_evaluation("broad-regression-matrix", "applicable", event_ids=["EVT-6", "EVT-10"]),
                    materiality_evaluation("compatibility-or-public-contract", "not-applicable"),
                    materiality_evaluation("reviewer-correction", "applicable", event_ids=["EVT-2", "EVT-5"]),
                    materiality_evaluation("direction-change", "applicable", event_ids=["EVT-2"]),
                    materiality_evaluation("expensive-to-reconstruct", "applicable", event_ids=["EVT-4"]),
                    materiality_evaluation("unresolved-authority-or-contract", "not-applicable")
                ],
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
    continuation = record.get("continuation", {})
    claim_validation = record["final_result"].get("claim_validation", {})
    return {
        "schema_version": 4,
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
                "continuation_kind": continuation.get("kind", "legacy"),
                "continued_from_debug_id": continuation.get("previous_debug_id", "not-applicable"),
                "claim_validation_fidelity": claim_validation.get("fidelity", "legacy"),
                "result_revision": binding["result_revision"],
                "event_coverage": record["capture_quality"]["event_coverage"],
                "observer_effect": record["capture_quality"]["observer_effect"],
                "elapsed_seconds": elapsed["value"],
                "elapsed_evidence_kind": elapsed["evidence_kind"],
                "metrics": {
                    name: record["metrics"][name]["value"] for name in LEGACY_METRIC_NAMES
                },
                "residual_uncertainty": record["residual_uncertainty"],
            }
        ],
    }


def run_validator(
    repo: Path, *, debug_git_state: bool = False, debug_remote_ref: str | None = None
) -> list[Any]:
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
        debug_git_state=debug_git_state,
        debug_remote_ref=debug_remote_ref,
    )
    validator.check_debug_mode(None)
    return validator.findings


def fixture_v5_record(revision: str) -> dict[str, Any]:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    record.update(
        debug_id="DEBUG-V5-1",
        status="completed",
        owner="engineering",
        residual_uncertainty=["Implementation and validation are outside this phase."],
        limitations=["This fixture covers an analysis-only Debug phase."],
    )
    record["task"] = {
        "summary": "Analyze one reusable invariant",
        "references": ["issue-v5"],
        "scope_kind": "task",
        "scope_id": "analysis-v5",
        "operation_ids": ["logical-integrity-review"],
        "task_class": "defect-analysis",
    }
    record["activation"] = {
        "enabled_by": "explicit-user-request",
        "request_reference": "request-v5",
        "enabled_at": {"value": "2026-08-21T13:00:00Z", "evidence_kind": "observed"},
        "initial_revision": revision,
        "expires_on": "task-completion",
        "ended_by": "task-completion",
    }
    record["continuation"] = {
        "kind": "initial",
        "previous_debug_id": "not-applicable",
        "reason": "Initial analysis scope.",
    }
    record["timing"] = {
        "started_at": {"value": "2026-08-21T13:00:00Z", "evidence_kind": "observed"},
        "completed_at": {"value": "2026-08-21T13:05:00Z", "evidence_kind": "observed"},
        "elapsed_seconds": {"value": 300, "evidence_kind": "observed"},
        "active_work_seconds": {"value": None, "evidence_kind": "unknown"},
    }
    record["capture_quality"] = {
        "event_coverage": "complete",
        "missing_intervals": [],
        "observer_effect": "negligible",
        "estimated_overhead_seconds": {"value": None, "evidence_kind": "unknown"},
    }
    candidate_event = event_v4(
        "V5-1",
        1,
        "executor",
        "independent-within-scope",
        "not-applicable",
        "not-applicable",
        "finding",
        "invariant",
    )
    record["events"] = [candidate_event]
    record["metrics"] = fixture_v4_metrics(record["events"])
    record["metrics"]["new_guidance_candidates"] = {
        "value": 1,
        "evidence_kind": "event-derived",
        "event_ids": ["V5-1"],
    }
    record["final_result"] = {
        "summary": "Analysis identified one reusable invariant candidate.",
        "repository_binding": {
            "kind": "commit",
            "binding_state": "final",
            "base_revision": revision,
            "result_revision": revision,
            "review_reference": "not applicable",
            "selected_paths": [],
            "snapshot_sha256": "not applicable",
            "prior_bindings": [],
        },
        "implementation_surfaces": [],
        "validation": {"results": [], "skipped": ["Implementation validation belongs to the continuation."]},
        "claim_validation": {
            "fidelity": "not-applicable",
            "claims": [],
            "evidence": [],
            "limitation": "No implementation claim is made.",
        },
        "lifecycle_coverage": {
            "completion_scope": "phase-complete",
            "covered_phases": ["analysis", "finalization"],
            "omitted_phases": ["implementation", "validation"],
            "continuation_expected": True,
            "next_phase": "implementation",
            "reason": "The current authorization covered analysis only.",
        },
        "repository_lifecycle": {
            "state": "finalized",
            "completed_transitions": ["analysis", "finalization"],
            "last_verified_revision": revision,
            "last_verified_at": {
                "value": "2026-08-21T13:05:00Z",
                "evidence_kind": "observed",
            },
            "commit_evidence": [],
            "publish_evidence": [],
            "finalization_evidence": ["fixture Debug summary rendered"],
            "next_permitted_action": "Open a separately authorized continuation for implementation.",
        },
        "engineering_evidence_ids": [],
        "engineering_evidence_decision": {
            "status": "blocked",
            "event_links": [{"event_id": "V5-1", "role": "finding"}],
            "materiality_evaluations": [
                materiality_evaluation(
                    kind,
                    "applicable" if kind == "expensive-to-reconstruct" else "not-applicable",
                    event_ids=["V5-1"] if kind == "expensive-to-reconstruct" else [],
                )
                for kind in MATERIALITY_KINDS
            ],
            "knowledge_preserved_by": [],
            "reason": "A reusable candidate needs project-owner review.",
            "next_safe_action": "Open a promotion proposal under current authorization.",
        },
        "project_knowledge_candidates": [
            {
                "candidate_id": "CANDIDATE-V5-1",
                "statement": "The fixture invariant is expensive to reconstruct.",
                "event_ids": ["V5-1"],
                "disposition": "blocked",
                "references": ["project-owner-review-required"],
                "reason": "No promotion write was authorized in this phase.",
            }
        ],
        "upstream_projection": {
            "kind": "same-repository",
            "included_debug_files": False,
            "projected_paths": [],
            "evidence": [revision],
        },
    }
    record["publication"] = {
        "storage_mode": "repository support branch",
        "visibility": "internal",
        "included_in_external_patch": False,
        "policy_evidence": ".ai/project/debug/README.md",
    }
    return record


def fixture_v5_index(record: dict[str, Any]) -> dict[str, Any]:
    binding = record["final_result"]["repository_binding"]
    lifecycle = record["final_result"]["lifecycle_coverage"]
    candidates = record["final_result"]["project_knowledge_candidates"]
    repository_lifecycle = record["final_result"].get("repository_lifecycle", {})
    validation = record["final_result"].get("validation", {})
    validation_results = validation.get("results", []) if isinstance(validation, dict) else []
    validation_classes = sorted(
        {
            item["evidence_class"]
            for item in validation_results
            if isinstance(item, dict) and isinstance(item.get("evidence_class"), str)
        }
    )
    return {
        "schema_version": 6,
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
                "record": f".ai/project/debug/records/{record['debug_id']}.json",
                "task_references": record["task"]["references"],
                "scope_kind": record["task"]["scope_kind"],
                "scope_id": record["task"]["scope_id"],
                "task_class": record["task"]["task_class"],
                "repository_binding_kind": binding["kind"],
                "record_schema_version": record["schema_version"],
                "repository_binding_state": binding["binding_state"],
                "engineering_evidence_status": record["final_result"]["engineering_evidence_decision"]["status"],
                "continuation_kind": record["continuation"]["kind"],
                "continued_from_debug_id": record["continuation"]["previous_debug_id"],
                "claim_validation_fidelity": record["final_result"]["claim_validation"]["fidelity"],
                "lifecycle_completion_scope": lifecycle["completion_scope"],
                "covered_phases": lifecycle["covered_phases"],
                "continuation_expected": lifecycle["continuation_expected"],
                "knowledge_candidate_ids": [item["candidate_id"] for item in candidates],
                "repository_lifecycle_state": repository_lifecycle.get("state", "legacy"),
                "validation_evidence_classes": validation_classes,
                "result_revision": binding["result_revision"],
                "event_coverage": record["capture_quality"]["event_coverage"],
                "observer_effect": record["capture_quality"]["observer_effect"],
                "elapsed_seconds": record["timing"]["elapsed_seconds"]["value"],
                "elapsed_evidence_kind": record["timing"]["elapsed_seconds"]["evidence_kind"],
                "metrics": {name: record["metrics"][name]["value"] for name in V4_METRIC_NAMES},
                "residual_uncertainty": record["residual_uncertainty"],
            }
        ],
    }


def validate_v5_fixture(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="alatyr-debug-v5-") as directory:
        repo = Path(directory)
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "alatyr@example.invalid")
        git(repo, "config", "user.name", "Alatyr Check")
        (repo / "README.md").write_text("fixture\n", encoding="utf-8")
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "fixture")
        revision = git(repo, "rev-parse", "HEAD")
        record = fixture_v5_record(revision)
        record_path = repo / f".ai/project/debug/records/{record['debug_id']}.json"
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
        template_path = repo / ".ai/assistant/templates/debug-session-record.json"
        template_path.parent.mkdir(parents=True)
        template_path.write_text(RECORD.read_text(encoding="utf-8"), encoding="utf-8")
        engineering_index = repo / ".ai/project/engineering-evidence/index.json"
        engineering_index.parent.mkdir(parents=True)
        engineering_index.write_text(
            json.dumps({"schema_version": 4, "index_kind": "target-engineering-evidence-index", "records": []}, indent=2) + "\n",
            encoding="utf-8",
        )

        def write(value: dict[str, Any]) -> None:
            record_path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
            index_path.write_text(json.dumps(fixture_v5_index(value), indent=2) + "\n", encoding="utf-8")

        write(record)
        errors = [item for item in run_validator(repo) if item.level == "error"]
        if errors:
            failures.append(
                "valid schema-version-6 fixture failed: "
                + "; ".join(f"{item.code}: {item.message}" for item in errors)
            )

        historical = copy.deepcopy(record)
        historical["schema_version"] = 4
        historical["debug_id"] = "DEBUG-V4-HISTORICAL"
        historical["final_result"].pop("lifecycle_coverage")
        historical["final_result"].pop("project_knowledge_candidates")
        historical["final_result"].pop("repository_lifecycle")
        historical["metrics"]["new_guidance_candidates"] = {
            "value": 0,
            "evidence_kind": "event-derived",
            "event_ids": [],
        }
        historical_path = (
            repo / ".ai/project/debug/records/DEBUG-V4-HISTORICAL.json"
        )
        historical_path.write_text(
            json.dumps(historical, indent=2) + "\n", encoding="utf-8"
        )
        historical_index = fixture_v5_index(record)
        historical_entry = historical_index["records"][0]
        historical_entry.update(
            debug_id=historical["debug_id"],
            record=".ai/project/debug/records/DEBUG-V4-HISTORICAL.json",
            record_schema_version=4,
            lifecycle_completion_scope="legacy",
            covered_phases=[],
            continuation_expected=False,
            knowledge_candidate_ids=[],
            repository_lifecycle_state="legacy",
            validation_evidence_classes=["legacy"],
            metrics={
                name: historical["metrics"][name]["value"]
                for name in V4_METRIC_NAMES
            },
        )
        index_path.write_text(
            json.dumps(historical_index, indent=2) + "\n", encoding="utf-8"
        )
        historical_errors = [
            item for item in run_validator(repo) if item.level == "error"
        ]
        if historical_errors:
            failures.append(
                "schema-version-6 index rejected a preserved version-4 record: "
                + "; ".join(
                    f"{item.code}: {item.message}" for item in historical_errors
                )
            )

        downlevel_index = fixture_v5_index(record)
        downlevel_index["schema_version"] = 4
        for field in [
            "lifecycle_completion_scope",
            "covered_phases",
            "continuation_expected",
            "knowledge_candidate_ids",
            "repository_lifecycle_state",
            "validation_evidence_classes",
        ]:
            downlevel_index["records"][0].pop(field)
        record_path.write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )
        index_path.write_text(
            json.dumps(downlevel_index, indent=2) + "\n", encoding="utf-8"
        )
        if not any(
            item.level == "error"
            and item.code == "DEBUG_MODE_INDEX_RECORD_VERSION"
            for item in run_validator(repo)
        ):
            failures.append("schema-version-6 Debug record accepted a downlevel index")

        invalid_lifecycle = copy.deepcopy(record)
        invalid_lifecycle["final_result"]["implementation_surfaces"] = ["src/change.php"]
        write(invalid_lifecycle)
        if not any(
            item.level == "error" and item.code == "DEBUG_MODE_LIFECYCLE_IMPLEMENTATION"
            for item in run_validator(repo)
        ):
            failures.append("schema-version-6 lifecycle omitted implementation evidence")

        invalid_candidate_metric = copy.deepcopy(record)
        invalid_candidate_metric["metrics"]["new_guidance_candidates"].update(value=0, event_ids=[])
        write(invalid_candidate_metric)
        if not any(
            item.level == "error" and item.code == "DEBUG_MODE_METRIC_DRIFT"
            for item in run_validator(repo)
        ):
            failures.append("schema-version-6 candidate disposition drift was not rejected")

        invalid_promotion = copy.deepcopy(record)
        invalid_promotion["final_result"]["project_knowledge_candidates"][0][
            "disposition"
        ] = "promotion-proposed"
        write(invalid_promotion)
        if not any(
            item.level == "error"
            and item.code == "DEBUG_MODE_KNOWLEDGE_CANDIDATE_PROMOTION"
            for item in run_validator(repo)
        ):
            failures.append("unindexed Debug knowledge promotion was not rejected")

        schema6_invalid_cases: list[
            tuple[str, Callable[[dict[str, Any]], None], set[str]]
        ] = [
            (
                "completed record retains active repository lifecycle",
                lambda value: value["final_result"]["repository_lifecycle"].update(
                    state="active"
                ),
                {"DEBUG_MODE_REPOSITORY_LIFECYCLE_STATE"},
            ),
            (
                "finalized lifecycle omits finalization evidence",
                lambda value: value["final_result"]["repository_lifecycle"].update(
                    finalization_evidence=[]
                ),
                {"DEBUG_MODE_REPOSITORY_LIFECYCLE_FINALIZATION"},
            ),
            (
                "local validation overclaims CI evidence",
                lambda value: value["final_result"]["validation"].update(
                    results=[
                        {
                            "claim": "Fixture validation passed.",
                            "evidence_class": "ci-verified",
                            "source": "local npm test output",
                            "observed_at": {
                                "value": "2026-08-21T13:04:00Z",
                                "evidence_kind": "observed",
                            },
                            "revision": revision,
                            "limitations": [],
                        }
                    ]
                ),
                {"DEBUG_MODE_VALIDATION_EVIDENCE_CLASS"},
            ),
        ]
        for label, mutate, expected_codes in schema6_invalid_cases:
            invalid = copy.deepcopy(record)
            mutate(invalid)
            write(invalid)
            findings = run_validator(repo)
            if not any(
                finding.level == "error" and finding.code in expected_codes
                for finding in findings
            ):
                failures.append(f"validator did not reject {label}")

        git_state_record = copy.deepcopy(record)
        (repo / "src").mkdir(exist_ok=True)
        (repo / "src/example.txt").write_text("implemented\n", encoding="utf-8")
        git(repo, "add", "src/example.txt")
        git(repo, "commit", "-qm", "implement fixture surface")
        implementation_revision = git(repo, "rev-parse", "HEAD")
        git(repo, "branch", "published-fixture", implementation_revision)
        git_state_record.update(status="active")
        git_state_record["activation"].update(ended_by="active")
        git_state_record["timing"]["completed_at"] = {
            "value": None,
            "evidence_kind": "unknown",
        }
        git_state_record["timing"]["elapsed_seconds"] = {
            "value": None,
            "evidence_kind": "unknown",
        }
        git_state_record["final_result"]["repository_binding"].update(
            binding_state="provisional",
            result_revision=revision,
        )
        git_state_record["final_result"]["implementation_surfaces"] = [
            "src/example.txt"
        ]
        git_state_record["final_result"]["lifecycle_coverage"].update(
            completion_scope="active",
            covered_phases=["analysis", "implementation"],
            omitted_phases=["validation", "finalization"],
            continuation_expected=True,
            next_phase="validation",
        )
        git_state_record["final_result"]["repository_lifecycle"].update(
            state="active",
            completed_transitions=["analysis", "implementation"],
            last_verified_revision=revision,
            finalization_evidence=[],
            next_permitted_action="Finalize or abandon before reporting completion.",
        )
        git_state_record["final_result"]["engineering_evidence_decision"].update(
            status="pending",
            next_safe_action="Finalize the active Debug record.",
        )
        write(git_state_record)
        git_state_findings = run_validator(
            repo,
            debug_git_state=True,
            debug_remote_ref="published-fixture",
        )
        for expected_code in {
            "DEBUG_MODE_ACTIVE_RESULT_DRIFT",
            "DEBUG_MODE_PROVISIONAL_BINDING_AFTER_COMMIT",
            "DEBUG_MODE_PUBLISHED_BUT_UNFINALIZED",
        }:
            if not any(
                item.level == "error" and item.code == expected_code
                for item in git_state_findings
            ):
                failures.append(
                    f"Debug/Git reconciliation did not report {expected_code}"
                )

        chain_records: list[dict[str, Any]] = []
        for debug_id, previous_id, scope_id, covered_phases in [
            (
                "DEBUG-V5-CHAIN-A",
                "not-applicable",
                "analysis-chain-a",
                ["analysis", "finalization"],
            ),
            (
                "DEBUG-V5-CHAIN-B",
                "DEBUG-V5-CHAIN-A",
                "analysis-chain-b",
                ["analysis", "finalization"],
            ),
            (
                "DEBUG-V5-CHAIN-C",
                "DEBUG-V5-CHAIN-B",
                "implementation-chain-c",
                ["implementation", "finalization"],
            ),
        ]:
            chained = copy.deepcopy(record)
            chained["debug_id"] = debug_id
            chained["task"]["scope_id"] = scope_id
            chained["continuation"] = {
                "kind": "initial" if previous_id == "not-applicable" else "continued",
                "previous_debug_id": previous_id,
                "reason": "Fixture continuation lineage.",
            }
            lifecycle = chained["final_result"]["lifecycle_coverage"]
            lifecycle["covered_phases"] = covered_phases
            lifecycle["omitted_phases"] = sorted(
                {"analysis", "implementation", "validation", "finalization"}
                - set(covered_phases)
            )
            lifecycle["continuation_expected"] = (
                "implementation" not in covered_phases
            )
            lifecycle["next_phase"] = (
                "implementation"
                if lifecycle["continuation_expected"]
                else "not-applicable"
            )
            chain_records.append(chained)
            chained_path = repo / f".ai/project/debug/records/{debug_id}.json"
            chained_path.write_text(
                json.dumps(chained, indent=2) + "\n", encoding="utf-8"
            )

        chain_index = fixture_v5_index(chain_records[0])
        chain_index["records"] = [
            fixture_v5_index(chained)["records"][0]
            for chained in chain_records
        ]
        index_path.write_text(
            json.dumps(chain_index, indent=2) + "\n", encoding="utf-8"
        )
        engineering_index.write_text(
            json.dumps(
                {
                    "schema_version": 4,
                    "index_kind": "target-engineering-evidence-index",
                    "records": [
                        {
                            "evidence_id": "ENG-LATER",
                            "task_references": ["issue-v5"],
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        chain_findings = run_validator(repo)
        if any(item.level == "error" for item in chain_findings):
            failures.append(
                "valid multi-hop Debug continuation failed: "
                + "; ".join(
                    f"{item.code}: {item.message}"
                    for item in chain_findings
                    if item.level == "error"
                )
            )
        if any(
            item.code == "DEBUG_MODE_IMPLEMENTATION_CONTINUATION_MISSING"
            for item in chain_findings
        ):
            failures.append(
                "multi-hop implementation continuation was reported as missing"
            )


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
        authoring_template.write_text(
            RECORD.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        canonical_knowledge = repo / "docs/architecture.md"
        canonical_knowledge.parent.mkdir(parents=True)
        canonical_knowledge.write_text(
            "# Architecture\n\nCanonical dependency decision.\n", encoding="utf-8"
        )
        registry = repo / ".ai/project/source-of-truth-registry.md"
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text(
            "# Source Of Truth Registry\n\n"
            "### Fact Type: `architecture decision`\n\n"
            "Fact type: `architecture decision`\n"
            "Canonical owner: `docs/architecture.md`\n"
            "Consistency map node: `not-applicable`\n",
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

        def set_metric(
            value: dict[str, Any], metric_name: str, event_ids: list[str]
        ) -> None:
            value["metrics"][metric_name].update(
                value=len(event_ids), event_ids=event_ids
            )

        def evaluation(value: dict[str, Any], kind: str) -> dict[str, Any]:
            return next(
                item
                for item in value["final_result"]["engineering_evidence_decision"][
                    "materiality_evaluations"
                ]
                if item["kind"] == kind
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
            for name in LEGACY_METRIC_NAMES
        }
        activation_only["final_result"]["implementation_surfaces"] = []
        activation_only["final_result"]["claim_validation"].update(
            fidelity="not-applicable",
            claims=[],
            evidence=[],
            limitation="No implementation claim was made.",
        )
        activation_only["final_result"]["engineering_evidence_decision"][
            "event_links"
        ] = [{"event_id": "EVT-1", "role": "finding"}]
        activation_only["final_result"]["engineering_evidence_decision"][
            "materiality_evaluations"
        ] = [
            materiality_evaluation(
                kind,
                "applicable" if kind == "non-obvious-dependency" else "not-applicable",
                event_ids=["EVT-1"] if kind == "non-obvious-dependency" else [],
            )
            for kind in MATERIALITY_KINDS
        ]
        assert_valid("task activation is not an intervention", activation_only)

        canonical_skip = copy.deepcopy(activation_only)
        canonical_skip["final_result"]["engineering_evidence_ids"] = []
        canonical_skip["final_result"]["engineering_evidence_decision"].update(
            status="skipped",
            knowledge_preserved_by=[
                {
                    "materiality_kind": "non-obvious-dependency",
                    "fact_type": "architecture decision",
                    "canonical_source": "docs/architecture.md",
                    "evidence": "Canonical architecture owner already records the conclusion.",
                }
            ],
            reason="The applicable dependency conclusion is already canonical.",
        )
        assert_valid("canonical materiality preservation permits skip", canonical_skip)

        previous_record = copy.deepcopy(record)
        previous_record["debug_id"] = "DEBUG-0"
        previous_record["task"]["scope_id"] = "task-0"
        previous_record_path = record_path.parent / "DEBUG-0.json"
        previous_record_path.write_text(
            json.dumps(previous_record, indent=2) + "\n", encoding="utf-8"
        )
        continued_record = copy.deepcopy(record)
        continued_record["continuation"].update(
            kind="continued",
            previous_debug_id="DEBUG-0",
            reason="A new explicit task continues the closed investigation.",
        )
        continued_index = fixture_index(continued_record)
        previous_entry = fixture_index(previous_record)["records"][0]
        previous_entry["record"] = ".ai/project/debug/records/DEBUG-0.json"
        continued_index["records"].insert(0, previous_entry)
        record_path.write_text(
            json.dumps(continued_record, indent=2) + "\n", encoding="utf-8"
        )
        index_path.write_text(
            json.dumps(continued_index, indent=2) + "\n", encoding="utf-8"
        )
        continuation_errors = [
            finding for finding in run_validator(repo) if finding.level == "error"
        ]
        if continuation_errors:
            failures.append(
                "valid continuation fixture failed: "
                + "; ".join(
                    f"{item.code}: {item.message}" for item in continuation_errors
                )
            )
        previous_record_path.unlink()

        validation_request = copy.deepcopy(record)
        validation_request["events"][1].update(
            intervention_kind="validation-request",
            contribution_kind="validation",
            category="validation",
            architectural_supervision=False,
            architectural_impacts=[],
            decision_effect="confirms-direction",
        )
        set_metric(validation_request, "human_architectural_interventions", [])
        set_metric(
            validation_request, "implementation_corrections_after_human", []
        )
        validation_links = validation_request["final_result"][
            "engineering_evidence_decision"
        ]["event_links"]
        validation_links[:] = [
            link
            for link in validation_links
            if not (link["event_id"] == "EVT-2" and link["role"] in {"decision", "correction", "direction-change"})
        ]
        validation_links.append({"event_id": "EVT-2", "role": "validation"})
        evaluation(validation_request, "cross-area-impact").update(
            outcome="not-applicable", event_ids=[]
        )
        evaluation(validation_request, "reviewer-correction")["event_ids"] = [
            "EVT-5"
        ]
        evaluation(validation_request, "direction-change").update(
            outcome="not-applicable", event_ids=[]
        )
        assert_valid(
            "human validation request is not an implementation correction",
            validation_request,
        )

        external_validation_request = copy.deepcopy(record)
        external_validation_request["events"][4].update(
            intervention_kind="validation-request",
            contribution_kind="validation",
            category="validation",
        )
        external_validation_request["events"][8]["post_review_rework"] = False
        set_metric(external_validation_request, "maintainer_corrections", [])
        set_metric(external_validation_request, "post_review_rework", [])
        external_links = external_validation_request["final_result"][
            "engineering_evidence_decision"
        ]["event_links"]
        external_links[:] = [
            link
            for link in external_links
            if not (link["event_id"] == "EVT-5" and link["role"] in {"decision", "correction"})
        ]
        external_links.append({"event_id": "EVT-5", "role": "validation"})
        evaluation(external_validation_request, "reviewer-correction")[
            "event_ids"
        ] = ["EVT-2"]
        assert_valid(
            "external validation request is not a maintainer correction",
            external_validation_request,
        )

        compatibility_field_case = copy.deepcopy(record)
        compatibility_field_case["events"] = [
            event("EVT-1", 1, "alatyr", "independent-within-scope", "not-applicable", "finding", "dependency", dependency=True),
            event(
                "EVT-2",
                2,
                "alatyr",
                "independent-within-scope",
                "not-applicable",
                "decision",
                "architecture-area",
                architectural_impacts=["public-contract", "authority-boundary"],
            ),
            event("EVT-3", 3, "alatyr", "independent-within-scope", "not-applicable", "implementation", "implementation-revision"),
            event(
                "EVT-4",
                4,
                "alatyr",
                "independent-within-scope",
                "not-applicable",
                "validation",
                "regression-scenario",
                validation=True,
            ),
        ]
        compatibility_field_case["metrics"] = {
            name: {
                "value": 0,
                "evidence_kind": "event-derived",
                "event_ids": [],
            }
            for name in LEGACY_METRIC_NAMES
        }
        set_metric(compatibility_field_case, "alatyr_independent_findings", ["EVT-1"])
        set_metric(
            compatibility_field_case,
            "alatyr_independent_dependency_checks",
            ["EVT-1"],
        )
        set_metric(compatibility_field_case, "implementation_revisions", ["EVT-3"])
        set_metric(compatibility_field_case, "validation_expansions", ["EVT-4"])
        set_metric(compatibility_field_case, "regression_scenarios_added", ["EVT-4"])
        field_decision = compatibility_field_case["final_result"][
            "engineering_evidence_decision"
        ]
        field_decision["event_links"] = [
            {"event_id": "EVT-1", "role": "finding"},
            {"event_id": "EVT-2", "role": "decision"},
            {"event_id": "EVT-3", "role": "implementation"},
            {"event_id": "EVT-4", "role": "validation"},
        ]
        field_decision["materiality_evaluations"] = [
            materiality_evaluation(
                kind,
                "applicable"
                if kind
                in {
                    "non-obvious-dependency",
                    "broad-regression-matrix",
                    "compatibility-or-public-contract",
                    "expensive-to-reconstruct",
                    "unresolved-authority-or-contract",
                }
                else "not-applicable",
                event_ids={
                    "non-obvious-dependency": ["EVT-1"],
                    "broad-regression-matrix": ["EVT-4"],
                    "compatibility-or-public-contract": ["EVT-2"],
                    "expensive-to-reconstruct": ["EVT-1"],
                    "unresolved-authority-or-contract": ["EVT-2"],
                }.get(kind, []),
                evidence=["external contract remains unresolved"]
                if kind == "unresolved-authority-or-contract"
                else [],
            )
            for kind in MATERIALITY_KINDS
        ]
        compatibility_field_case["final_result"]["claim_validation"].update(
            fidelity="partial",
            claims=["The platform-folding compatibility path is improved."],
            evidence=["representative compatibility regression matrix"],
            limitation="The exact external result-normalization configuration is not reproduced.",
        )
        compatibility_field_case["residual_uncertainty"] = [
            "External contract authority and exact reproducer remain unresolved."
        ]
        assert_valid(
            "independent compatibility investigation requires captured evidence",
            compatibility_field_case,
        )

        def remove_external_correction_claim(value: dict[str, Any]) -> None:
            value["events"][4].update(
                intervention_kind="validation-request",
                contribution_kind="validation",
                category="validation",
            )
            set_metric(value, "maintainer_corrections", [])
            set_metric(value, "post_review_rework", [])
            evaluation(value, "reviewer-correction")["event_ids"] = ["EVT-2"]

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
                "event after completed Debug session",
                lambda value: value["events"][9]["occurred_at"].update(
                    value="2026-08-21T12:11:00Z"
                ),
                {"DEBUG_MODE_EVENT_TIME_WINDOW"},
            ),
            (
                "event before Debug session start",
                lambda value: value["events"][0]["occurred_at"].update(
                    value="2026-08-21T11:59:00Z"
                ),
                {"DEBUG_MODE_EVENT_TIME_WINDOW"},
            ),
            (
                "event sequence contradicts timestamps",
                lambda value: value["events"][8]["occurred_at"].update(
                    value="2026-08-21T12:04:30Z"
                ),
                {"DEBUG_MODE_EVENT_TIME_ORDER", "DEBUG_MODE_EVENT_CAUSAL_TIME"},
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
                "evidence event role does not match referenced event",
                lambda value: value["final_result"]["engineering_evidence_decision"]["event_links"][5].update(role="implementation"),
                {"DEBUG_MODE_EVIDENCE_EVENT_ROLE"},
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
                lambda value: evaluation(value, "rejected-hypothesis").update(event_ids=[]),
                {"DEBUG_MODE_MATERIALITY_TRIGGER"},
            ),
            (
                "materiality evaluation omitted",
                lambda value: value["final_result"]["engineering_evidence_decision"]["materiality_evaluations"].pop(),
                {"DEBUG_MODE_MATERIALITY_SET", "DEBUG_MODE_RECORD_SCHEMA"},
            ),
            (
                "skipped evidence leaves unknown materiality",
                lambda value: (
                    value["final_result"].update(engineering_evidence_ids=[]),
                    value["final_result"]["engineering_evidence_decision"].update(status="skipped"),
                    evaluation(value, "unresolved-authority-or-contract").update(outcome="unknown"),
                ),
                {"DEBUG_MODE_EVIDENCE_SKIP_UNKNOWN"},
            ),
            (
                "partial claim omits residual uncertainty",
                lambda value: (
                    value["final_result"]["claim_validation"].update(fidelity="partial"),
                    value.update(residual_uncertainty=[]),
                ),
                {"DEBUG_MODE_CLAIM_UNCERTAINTY"},
            ),
            (
                "exact reproducer claim omits validation evidence",
                lambda value: value["final_result"]["claim_validation"].update(
                    evidence=[]
                ),
                {"DEBUG_MODE_CLAIM_EVIDENCE"},
            ),
            (
                "implemented result marks claim validation not applicable",
                lambda value: value["final_result"]["claim_validation"].update(
                    fidelity="not-applicable", claims=[], evidence=[]
                ),
                {"DEBUG_MODE_CLAIM_FIDELITY"},
            ),
            (
                "continued record references unknown prior record",
                lambda value: value["continuation"].update(
                    kind="continued", previous_debug_id="DEBUG-UNKNOWN"
                ),
                {"DEBUG_MODE_CONTINUATION_REFERENCE"},
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

        version_two = copy.deepcopy(record)
        version_two["schema_version"] = 2
        version_two.pop("continuation")
        version_two["final_result"].pop("claim_validation")
        version_two["final_result"]["engineering_evidence_decision"] = {
            "status": "captured",
            "trigger_event_ids": ["EVT-2", "EVT-4", "EVT-5"],
            "trigger_kinds": [
                "direction-change",
                "rejected-hypothesis",
                "correction",
            ],
            "knowledge_preserved_by": [],
            "reason": "Legacy version-2 evidence was captured.",
            "next_safe_action": "Migrate when the record is next maintained.",
        }
        write(version_two)
        version_two_findings = run_validator(repo)
        version_two_errors = [
            item for item in version_two_findings if item.level == "error"
        ]
        if version_two_errors:
            failures.append(
                "schema-version-2 compatibility failed: "
                + "; ".join(
                    f"{item.code}: {item.message}" for item in version_two_errors
                )
            )
        if not any(
            item.code == "DEBUG_MODE_V2_CONTRACT" for item in version_two_findings
        ):
            failures.append("schema-version-2 records did not report migration warning")

        version_two_with_continuation = copy.deepcopy(version_two)
        version_two_with_continuation["continuation"] = {
            "kind": "continued",
            "previous_debug_id": "DEBUG-0",
            "reason": "invalid backport",
        }
        write(version_two_with_continuation)
        if not any(
            item.level == "error" and item.code == "DEBUG_MODE_RECORD_SCHEMA"
            for item in run_validator(repo)
        ):
            failures.append(
                "schema-version-2 record accepted version-3 continuation fields"
            )

        version_two_late_event = copy.deepcopy(version_two)
        version_two_late_event["events"][9]["occurred_at"]["value"] = (
            "2026-08-21T12:11:00Z"
        )
        write(version_two_late_event)
        version_two_late_findings = run_validator(repo)
        if any(
            item.level == "error" and item.code == "DEBUG_MODE_EVENT_TIME_WINDOW"
            for item in version_two_late_findings
        ):
            failures.append("schema-version-2 post-completion event was rejected instead of warned")
        if not any(
            item.level == "warning" and item.code == "DEBUG_MODE_EVENT_TIME_WINDOW"
            for item in version_two_late_findings
        ):
            failures.append("schema-version-2 post-completion event lacked migration warning")

        legacy = copy.deepcopy(record)
        legacy["schema_version"] = 1
        legacy.pop("continuation")
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
            for name in LEGACY_METRIC_NAMES
        }
        legacy["final_result"].pop("engineering_evidence_decision")
        legacy["final_result"].pop("claim_validation")
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
            "immutable task evidence",
            "`actor_role`",
            "`actor_identity`",
            "`actor_provenance`",
            "`known-guidance-routing-failure`",
            "Schema versions 1 through 4 remain readable",
            "`materiality_evaluations`",
            "`exact-reproducer`",
            "`phase-complete`",
            "Schema-version-6 records",
            "validation result is a structured claim",
            "project-knowledge candidate",
        ],
        failures,
    )
    require_text(FLOW, ["## Modes", "explicit current user request", "actor role", "correction disposition", "known-guidance-routing-failure", "derived-from-human", "contribution kind", "rejected-hypothesis", "prior_bindings", "continued investigation", "materiality", "exact reproducer", "Debug/Git reconciliation", "evidence class"], failures)
    require_text(GATE, ["non-canonical observability evidence", "logical scope", "actor role", "correction", "known-guidance", "Engineering Evidence decision", "direction-changing correction", "continued work", "materiality", "validation fidelity", "repository lifecycle state", "Debug/Git reconciliation"], failures)
    require_text(SUMMARY, ["# Alatyr Debug Summary", "Record schema and attribution model", "Human architectural interventions", "Final result binding", "Durable engineering evidence", "External projection", "Claim-validation fidelity", "Continuation lineage", "Repository lifecycle", "Validation evidence classes"], failures)
    require_text(
        POLICY,
        ["Owner:", "Storage mode:", "Visibility:", "Retention policy:", "Redaction policy:", "External patch policy:"],
        failures,
    )
    require_text(
        RECORD_POLICY,
        ["actor_role", "actor_identity", "actor_provenance", "correction_disposition", "migration-limited", "schema version 6", "continuation", "validation fidelity", "phase completion"],
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
        if index.get("schema_version") != 6 or "redaction_policy" not in index:
            failures.append("source Debug Mode index must use lifecycle-projection schema 6")
        if record.get("record_kind") != "alatyr-debug-session":
            failures.append("debug record template kind is invalid")
        if record.get("evidence_classification") != "non-canonical-observability":
            failures.append("debug record template must be non-canonical")
        if record.get("schema_version") != 6:
            failures.append("debug record template must use lifecycle and knowledge-closure schema 6")
        template_schema_errors = list(
            jsonschema.Draft7Validator(schema).iter_errors(record)
        )
        if template_schema_errors:
            failures.append(
                "debug record template does not match schema version 6: "
                + "; ".join(error.message for error in template_schema_errors)
            )
        if "continuation" not in record:
            failures.append("debug record template must expose continuation lineage")
        if "engineering_evidence_decision" not in record.get("final_result", {}):
            failures.append("debug record template must expose durable evidence closure")
        if "claim_validation" not in record.get("final_result", {}):
            failures.append("debug record template must expose claim-validation fidelity")
        if "lifecycle_coverage" not in record.get("final_result", {}):
            failures.append("debug record template must expose lifecycle coverage")
        if "project_knowledge_candidates" not in record.get("final_result", {}):
            failures.append("debug record template must expose project-knowledge candidate closure")
        if "repository_lifecycle" not in record.get("final_result", {}):
            failures.append("debug record template must expose repository lifecycle evidence")
        if overlay.get("overlay") != "debug-mode":
            failures.append("Debug Mode overlay identity is invalid")
        modes = {
            item.get("expected_mode")
            for item in scenarios.get("scenarios", [])
            if isinstance(item, dict)
        }
        if modes != {"enabled", "inactive", "checkpointed", "redacted", "finalized", "compared", "rejected", "excluded"}:
            failures.append("conformance scenarios do not cover the required Debug Mode lifecycle")
        validate_v4_fixture(schema, failures)

    validate_fixture(failures)
    validate_v5_fixture(failures)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: checked Debug Mode contracts, privacy, attribution, metrics, and validator enforcement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
