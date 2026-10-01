"""Shared contracts for Alatyr change-package records and compact indexes."""

from __future__ import annotations

from typing import Any


CHANGE_PACKAGE_STATUSES = frozenset(
    {
        "proposed",
        "approved",
        "implementing",
        "validated",
        "complete",
        "blocked",
    }
)

KNOWLEDGE_CANDIDATE_STATUSES = frozenset({"validated", "complete"})
ACTIVE_CHANGE_PACKAGE_STATUSES = frozenset(
    {"proposed", "approved", "implementing", "validated", "blocked"}
)
CHANGE_PACKAGE_STATUS_PLACEHOLDER = (
    "{PROPOSED_APPROVED_IMPLEMENTING_VALIDATED_COMPLETE_OR_BLOCKED}"
)
INDEX_PROJECTION_FIELDS = (
    "package_id",
    "status",
    "changed_fact_ids",
    "canonical_owners",
    "project_areas",
    "evidence_quality",
    "approval_records",
    "active_workstream",
)
INCIDENT_INDEX_PROJECTION_FIELDS = (
    "incident_family_id",
    "corrective_iteration",
    "latest_failed_gate_state",
)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(
        dict.fromkeys(item for item in value if isinstance(item, str) and item)
    )


def package_index_projection(record: dict[str, Any]) -> dict[str, Any]:
    """Project one package record into the fields owned by its compact index."""

    changed_facts = record.get("changed_facts")
    facts = changed_facts if isinstance(changed_facts, list) else []
    fact_ids: list[str] = []
    owners: list[str] = []
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        fact_id = fact.get("id")
        if isinstance(fact_id, str) and fact_id and fact_id not in fact_ids:
            fact_ids.append(fact_id)
        owner = fact.get("canonical_owner")
        if isinstance(owner, str) and owner and owner not in owners:
            owners.append(owner)

    routing = _mapping(record.get("routing"))
    provenance = _mapping(record.get("provenance"))
    approved_scope = _mapping(record.get("approved_scope"))
    operation = _mapping(record.get("operation"))
    incident = _mapping(record.get("incident_continuity"))
    failed_gate = _mapping(incident.get("latest_failed_gate"))
    return {
        "package_id": record.get("package_id"),
        "status": record.get("status"),
        "changed_fact_ids": fact_ids,
        "canonical_owners": owners,
        "project_areas": _string_list(routing.get("project_areas")),
        "evidence_quality": provenance.get("evidence_quality"),
        "approval_records": _string_list(approved_scope.get("approval_records")),
        "active_workstream": operation.get("active_workstream"),
        "incident_family_id": incident.get("family_id"),
        "corrective_iteration": incident.get("corrective_iteration"),
        "latest_failed_gate_state": failed_gate.get("state"),
    }


def package_index_projection_mismatches(
    entry: dict[str, Any],
    record: dict[str, Any],
    *,
    include_incident: bool | None = None,
) -> tuple[str, ...]:
    projection = package_index_projection(record)
    if include_incident is None:
        include_incident = (
            record.get("status") in ACTIVE_CHANGE_PACKAGE_STATUSES
            or any(field in entry for field in INCIDENT_INDEX_PROJECTION_FIELDS)
        )
    fields = INDEX_PROJECTION_FIELDS + (
        INCIDENT_INDEX_PROJECTION_FIELDS if include_incident else ()
    )
    return tuple(
        field for field in fields if entry.get(field) != projection[field]
    )


def incident_continuity_failures(record: dict[str, Any]) -> tuple[str, ...]:
    """Validate the deterministic incident-lineage portion of an active package."""

    incident = record.get("incident_continuity")
    if not isinstance(incident, dict):
        return ("active change package requires incident_continuity",)
    failures: list[str] = []
    required_fields = {
        "mode",
        "family_id",
        "trigger",
        "corrective_iteration",
        "predecessors",
        "problem_model",
        "latest_failed_gate",
        "lifecycle_model_required",
    }
    missing = sorted(required_fields - incident.keys())
    if missing:
        failures.append("incident_continuity is missing: " + ", ".join(missing))

    mode = incident.get("mode")
    family_id = incident.get("family_id")
    trigger = incident.get("trigger")
    iteration = incident.get("corrective_iteration")
    predecessors = incident.get("predecessors")
    if mode not in {"none", "new", "continuation", "systemic-repair"}:
        failures.append(f"unsupported incident mode: {mode!r}")
    if trigger not in {
        "none",
        "reported-defect",
        "escaped-defect",
        "failed-required-gate",
        "recurring-correction",
        "manual",
    }:
        failures.append(f"unsupported incident trigger: {trigger!r}")
    if not isinstance(iteration, int) or isinstance(iteration, bool) or iteration < 0:
        failures.append("corrective_iteration must be a non-negative integer")
    if not isinstance(predecessors, list):
        failures.append("incident predecessors must be a list")
        predecessors = []
    if mode == "none":
        if family_id != "none" or trigger != "none" or iteration != 0 or predecessors:
            failures.append(
                "non-incident package requires family_id=none, trigger=none, iteration=0, and no predecessors"
            )
    else:
        if not isinstance(family_id, str) or family_id in {"", "none"}:
            failures.append("incident package requires a stable family_id")
        if trigger == "none":
            failures.append("incident package requires a concrete trigger")
    if mode in {"continuation", "systemic-repair"}:
        if not isinstance(iteration, int) or isinstance(iteration, bool) or iteration < 1:
            failures.append("continued incident package requires corrective_iteration >= 1")
        if not predecessors:
            failures.append("continued incident package requires predecessor bindings")
    if isinstance(iteration, int) and not isinstance(iteration, bool) and iteration >= 2:
        if mode != "systemic-repair" or trigger != "recurring-correction":
            failures.append(
                "the second corrective iteration and later require systemic-repair and recurring-correction"
            )
    if trigger == "recurring-correction" and mode != "systemic-repair":
        failures.append("recurring-correction requires systemic-repair mode")

    model = incident.get("problem_model")
    if not isinstance(model, dict) or set(model) != {"path", "sha256"}:
        failures.append("incident problem_model requires path and sha256")
    gate = incident.get("latest_failed_gate")
    if not isinstance(gate, dict) or set(gate) != {"state", "id", "evidence_refs"}:
        failures.append("incident latest_failed_gate has an invalid shape")
    else:
        state = gate.get("state")
        evidence = gate.get("evidence_refs")
        if state not in {"none", "open", "resolved"}:
            failures.append(f"unsupported latest failed gate state: {state!r}")
        elif state == "none" and (gate.get("id") != "none" or evidence):
            failures.append("failed gate state none cannot carry identity or evidence")
        elif state in {"open", "resolved"} and (
            gate.get("id") in {None, "", "none"}
            or not isinstance(evidence, list)
            or not evidence
        ):
            failures.append("open or resolved failed gate requires identity and evidence")
    if (
        mode == "systemic-repair"
        or trigger
        in {"escaped-defect", "failed-required-gate", "recurring-correction"}
    ) and incident.get("lifecycle_model_required") is not True:
        failures.append("systemic or escaped failure requires lifecycle_model_required=true")
    return tuple(failures)
