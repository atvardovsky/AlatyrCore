#!/usr/bin/env python3
"""Validate large-task orchestration source and target-template contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK = ROOT / "framework" / "large-task-orchestration.md"
TARGET = ROOT / "templates" / "target"
FLOW = TARGET / ".ai" / "assistant" / "flows" / "large-task-orchestration.flow.md"
PACKET = (
    TARGET
    / ".ai"
    / "assistant"
    / "templates"
    / "large-task-operation-packet.md"
)
ROUTER = TARGET / ".ai" / "assistant" / "context-router.json"
MANIFEST = TARGET / ".ai" / "alatyr.yaml"

FRAMEWORK_REQUIRED = [
    "## Activation",
    "## Operation Packet",
    "## Workstream Contract",
    "## Resume Protocol",
    "## Final Convergence",
    "not a canonical owner",
]

FLOW_REQUIRED = [
    "## Activation Gate",
    "large-or-resumable",
    ".ai/assistant/templates/large-task-operation-packet.md",
    "global logical integrity review",
]

PACKET_REQUIRED = [
    "Operation ID:",
    "Allowed actions:",
    "Activation reason:",
    "Selected task profile:",
    "Task-scale overlay: `large-or-resumable`",
    "Loaded files and reasons:",
    "Canonical owner:",
    "Selected relationship edges:",
    "Skipped or missing edges:",
    "### Workstream `{WORKSTREAM_ID}`",
    "Dependencies:",
    "Required context:",
    "Allowed surfaces:",
    "Validation:",
    "### Checkpoint `{CHECKPOINT_ID}`",
    "Next ready action:",
    "## Final Convergence",
    "Approval scope versus applied changes:",
    "Global logical integrity review:",
    "Relationship impact closure:",
    "Final residual risk:",
    "## Resume Rule",
]


def require_text(path: Path, expected: list[str], failures: list[str]) -> None:
    if not path.is_file():
        failures.append(f"missing {path.relative_to(ROOT)}")
        return
    text = path.read_text(encoding="utf-8")
    for value in expected:
        if value not in text:
            failures.append(f"{path.relative_to(ROOT)} missing {value}")


def main() -> int:
    failures: list[str] = []
    require_text(FRAMEWORK, FRAMEWORK_REQUIRED, failures)
    require_text(FLOW, FLOW_REQUIRED, failures)
    require_text(PACKET, PACKET_REQUIRED, failures)

    try:
        router = json.loads(ROUTER.read_text(encoding="utf-8"))
        scale = router["task_scale_overlays"]["large-or-resumable"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        failures.append(f"invalid large task router overlay: {exc}")
    else:
        required_context = scale.get("required_context", [])
        for value in [
            ".ai/framework/large-task-orchestration.md",
            ".ai/assistant/flows/large-task-orchestration.flow.md",
            ".ai/assistant/templates/large-task-operation-packet.md",
        ]:
            if value not in required_context:
                failures.append(f"large task router overlay missing {value}")

    manifest_text = MANIFEST.read_text(encoding="utf-8")
    required_manifest = (
        "large_task_packet: "
        '".ai/assistant/templates/large-task-operation-packet.md"'
    )
    if required_manifest not in manifest_text:
        failures.append(f"{MANIFEST.relative_to(ROOT)} missing large_task_packet")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("OK: checked large-task orchestration flow, packet, router, and manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
