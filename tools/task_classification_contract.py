"""Shared task-classification constants for AlatyrCore source checks.

The source router and target adapter router remain separate contracts. This
module only centralizes the stable literals that multiple validators must
check in the same way.
"""

from __future__ import annotations

from collections.abc import Sequence
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "framework" / "task-classes.json"
TASK_CLASS_REGISTRY = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

TASK_CLASSIFICATION_SCHEMA_VERSION = TASK_CLASS_REGISTRY["schema_version"]
TASK_CLASSES = TASK_CLASS_REGISTRY["classification_order"]
DEFAULT_TASK_CLASS = TASK_CLASS_REGISTRY["default_class"]
TASK_CLASS_DEFINITIONS = TASK_CLASS_REGISTRY["classes"]
TARGET_REQUIRED_EXPANSION_TRIGGERS = TASK_CLASS_REGISTRY["expansion_triggers"]
AMBIGUITY_READ_ONLY_MARKER = "read-only"
SMALL_TASK_CLASS = "small-task"
LARGE_TASK_CLASS = "large-or-resumable"

TARGET_REQUIRED_SMALL_TASK_EXPANSION_TRIGGERS = [
    "semantic or logical fact changes",
    "source-of-truth owner is missing disputed or contradicted",
    "focused validation fails or cannot prove the changed contract",
    "validator checker schema gate or generated-projection behavior changes",
    "repair repeats escapes or invalidates a previously passed gate",
]

SOURCE_REQUIRED_EXPANSION_TRIGGERS = [
    "framework rule or lifecycle behavior changes",
    "adapter schema or target template contract changes",
    "source-of-truth conflict or ownership ambiguity",
    "approval, authorization, safety, security, release, or assistant-infrastructure boundary appears",
    "focused validation fails or selected check coverage is ambiguous",
    "validator checker schema gate or generated-projection behavior changes",
    "explicit repository audit, release readiness review, or full corpus comparison",
]

SOURCE_SMALL_TASK_FOCUSED_CHECKS_MARKER = "focused source checks"


def missing_required_values(value: Any, required: Sequence[str]) -> list[str]:
    if not isinstance(value, list):
        return list(required)
    return [item for item in required if item not in value]
