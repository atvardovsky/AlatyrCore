"""Shared status vocabulary for Alatyr change-package records and indexes."""

from __future__ import annotations


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
