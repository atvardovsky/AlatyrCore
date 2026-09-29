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
    return {
        "package_id": record.get("package_id"),
        "status": record.get("status"),
        "changed_fact_ids": fact_ids,
        "canonical_owners": owners,
        "project_areas": _string_list(routing.get("project_areas")),
        "evidence_quality": provenance.get("evidence_quality"),
        "approval_records": _string_list(approved_scope.get("approval_records")),
        "active_workstream": operation.get("active_workstream"),
    }


def package_index_projection_mismatches(
    entry: dict[str, Any], record: dict[str, Any]
) -> tuple[str, ...]:
    projection = package_index_projection(record)
    return tuple(
        field for field in INDEX_PROJECTION_FIELDS if entry.get(field) != projection[field]
    )
