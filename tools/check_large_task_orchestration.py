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
RECEIPT_SCHEMA = ROOT / "schemas" / "alatyr-context-receipt.schema.json"

FRAMEWORK_REQUIRED = [
    "## Activation",
    "## Operation Packet",
    "## Workstream Contract",
    "## Resume Protocol",
    "## Semantic Guidance Revalidation",
    "## Final Convergence",
    "protected implementation begins or resumes",
    "material decision",
    "final target validation begins",
    "final evidence is accepted",
    "not proof that an assistant read",
    "not a canonical owner",
]

FLOW_REQUIRED = [
    "## Activation Gate",
    "large-or-resumable",
    ".ai/assistant/templates/large-task-operation-packet.md",
    "global logical integrity review",
    "planned, resolved, and observed ordered semantic",
    "before protected implementation",
    "material decision",
    "final validation",
    "final evidence",
    "It does not prove",
    "model read, understood, remembered, or followed",
]

PACKET_REQUIRED = [
    "Operation ID:",
    "Allowed actions:",
    "Activation reason:",
    "Selected task profile:",
    "Task-scale overlay: `large-or-resumable`",
    "Loaded files and reasons:",
    "### Semantic Guidance Receipt",
    "Planned ordered identities:",
    "Resolved ordered identities:",
    "Observed ordered identities:",
    "Claim boundary: bundle identity does not prove model comprehension",
    "Canonical owner:",
    "Selected relationship edges:",
    "Skipped or missing edges:",
    "### Workstream `{WORKSTREAM_ID}`",
    "Dependencies:",
    "Required context:",
    "Allowed surfaces:",
    "Validation:",
    "### Checkpoint `{CHECKPOINT_ID}`",
    "Revalidation gate:",
    "Previously accepted resolved bundle digest:",
    "Current resolved bundle digest:",
    "Guidance identity delta:",
    "Changed guidance owners loaded:",
    "Revalidation result:",
    "Next ready action:",
    "## Final Convergence",
    "Approval scope versus applied changes:",
    "Final semantic-guidance revalidation:",
    "Final accepted resolved bundle digest:",
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
        scale_route = router["task_scale_overlays"]["large-or-resumable"]
        descriptor = scale_route["descriptor"]
        scale = json.loads((TARGET / descriptor).read_text(encoding="utf-8"))
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
        revalidation = scale.get("semantic_guidance_revalidation")
        if not isinstance(revalidation, dict):
            failures.append("large task router overlay missing semantic revalidation contract")
        else:
            expected_gates = [
                "protected implementation",
                "material decisions",
                "final validation",
                "final evidence",
            ]
            if revalidation.get("required_before") != expected_gates:
                failures.append("large task router overlay has invalid revalidation gates")
            if "only changed owners" not in str(revalidation.get("on_difference")):
                failures.append("large task router overlay must reload only changed owners")

    try:
        receipt_schema = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))
        semantic_reference = receipt_schema["properties"]["semantic_guidance"]["$ref"]
        definitions = receipt_schema["$defs"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        failures.append(f"invalid semantic guidance receipt schema: {exc}")
    else:
        if semantic_reference != "#/$defs/semanticGuidanceReceipt":
            failures.append("receipt schema has invalid semantic_guidance reference")
        for definition in [
            "semanticGuidanceReceipt",
            "semanticGuidanceStage",
            "resolvedSemanticGuidanceStage",
            "observedSemanticGuidanceStage",
            "semanticGuidanceIdentity",
            "resolvedSemanticGuidanceIdentity",
            "semanticGuidanceBundleDigest",
        ]:
            if definition not in definitions:
                failures.append(f"receipt schema missing {definition}")
        digest = definitions.get("semanticGuidanceBundleDigest", {}).get("properties", {})
        if digest.get("schema_version", {}).get("const") != 1:
            failures.append("semantic guidance bundle digest schema version must be 1")
        if digest.get("algorithm", {}).get("const") != "sha256":
            failures.append("semantic guidance bundle digest algorithm must be sha256")

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
