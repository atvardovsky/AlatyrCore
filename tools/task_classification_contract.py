"""Shared task-classification constants for AlatyrCore source checks.

The source router and target adapter router remain separate contracts. This
module only centralizes the stable literals that multiple validators must
check in the same way.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


TASK_CLASSIFICATION_SCHEMA_VERSION = 1
TASK_CLASSES = [
    "protected-or-sensitive",
    "large-or-resumable",
    "small-task",
    "standard-task",
]
DEFAULT_TASK_CLASS = "standard-task"
AMBIGUITY_READ_ONLY_MARKER = "read-only"
SMALL_TASK_CLASS = "small-task"
LARGE_TASK_CLASS = "large-or-resumable"

TARGET_REQUIRED_EXPANSION_TRIGGERS = [
    "semantic or logical fact changes",
    "source-of-truth owner is missing disputed or contradicted",
    "approval safety security data architecture public contract or live-external boundary appears",
    "focused validation fails or cannot prove the changed contract",
]

TARGET_REQUIRED_SMALL_TASK_EXPANSION_TRIGGERS = [
    "semantic or logical fact changes",
    "source-of-truth owner is missing disputed or contradicted",
    "focused validation fails or cannot prove the changed contract",
]

SOURCE_REQUIRED_EXPANSION_TRIGGERS = [
    "framework rule or lifecycle behavior changes",
    "adapter schema or target template contract changes",
    "source-of-truth conflict or ownership ambiguity",
    "approval, authorization, safety, security, release, or assistant-infrastructure boundary appears",
    "focused validation fails or selected check coverage is ambiguous",
    "explicit repository audit, release readiness review, or full corpus comparison",
]

SOURCE_SMALL_TASK_FOCUSED_CHECKS_MARKER = "focused source checks"


def missing_required_values(value: Any, required: Sequence[str]) -> list[str]:
    if not isinstance(value, list):
        return list(required)
    return [item for item in required if item not in value]
