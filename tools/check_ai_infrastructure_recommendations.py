#!/usr/bin/env python3
"""Validate AI infrastructure recommendation source and target contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
FRAMEWORK = ROOT / "framework" / "ai-infrastructure-recommendations.md"
ROUTER = TARGET / ".ai" / "assistant" / "ai-infrastructure-router.json"
FLOW = (
    TARGET
    / ".ai"
    / "assistant"
    / "flows"
    / "ai-infrastructure-recommendation.flow.md"
)
TEMPLATE = (
    TARGET
    / ".ai"
    / "assistant"
    / "templates"
    / "ai-infrastructure-recommendation.md"
)
CAPTURE_FLOW = (
    TARGET
    / ".ai"
    / "assistant"
    / "flows"
    / "development-evidence-capture.flow.md"
)
DEVELOPMENT_EVIDENCE = TARGET / ".ai" / "project" / "development-evidence.json"
PROJECT_CONTOUR = TARGET / ".ai" / "project" / "contour.md"
ASSISTANT_CONTOUR = TARGET / ".ai" / "assistant" / "contour.md"
HELP = TARGET / ".ai" / "assistant" / "help.md"
HELP_REFERENCE = TARGET / ".ai" / "assistant" / "help-reference.md"
MANIFEST = TARGET / ".ai" / "alatyr.yaml"

FRAMEWORK_TEXT = [
    "# AI Infrastructure Recommendations",
    "Recommendations are read-only decision evidence by default.",
    "Project evidence describes the need, constraints, and expected outcome.",
    "## Target Optimization Boundary",
    "Target evidence must not directly recommend or edit the installed",
    "## Development Pattern Evidence",
    "Never store secrets, credentials, personal data, or complete conversation",
    "Review existing items before recommending `add-new`.",
    "## Cost And Quality Gate",
    "Do not invent",
    "percentages or token savings without measurements.",
    "## Existing-Item Review",
    "## Recommendation Process",
    "## Rejection Criteria",
]

FLOW_TEXT = [
    "# AI Infrastructure Recommendation Flow",
    ".ai/framework/ai-infrastructure-recommendations.md",
    ".ai/assistant/templates/ai-infrastructure-recommendation.md",
    ".ai/project/contour.md",
    ".ai/project/source-of-truth-registry.md",
    ".ai/project/development-evidence.json",
    "Select the `recommend` route",
    "Evaluate existing-item changes",
    "before `add-new`.",
    "Label estimates",
    "Do not change project contour facts.",
    "Do not fetch, install, execute, edit, remove,",
    "activate, or change permissions during this flow.",
    "Do not recommend changes to `.ai/framework`, AlatyrCore source, or portable",
]

CAPTURE_FLOW_TEXT = [
    "# Development Evidence Capture Flow",
    ".ai/project/development-evidence.json",
    "Do not assume prior assistant conversations are available.",
    "## Capture Gate",
    "Do not record routine successful one-off work",
    "Under `read-only`, report a capture candidate",
    "Do not copy raw request,",
    "Do not recommend an AI item during capture.",
    "Do not modify `.ai/framework`, AlatyrCore source, portable rules",
    "## Pattern Contract",
]

TEMPLATE_TEXT = [
    "# AI Infrastructure Recommendation",
    "## Recommendation Scope",
    "## Candidate Record",
    "## Existing Item Review Summary",
    "## Decision Summary",
    "Project area and canonical owner:",
    "Recommendation record path:",
    "Project-contour evidence:",
    "Selected development pattern IDs:",
    "Pattern occurrence and evidence references:",
    "Evidence quality:",
    "Recommendation ID:",
    "Recommendation kind:",
    "Existing item IDs:",
    "Existing coverage and why keep is insufficient:",
    "Expected quality or consistency effect:",
    "Acceptance criteria:",
    "Expected context-load effect:",
    "Implementation cost:",
    "Ongoing maintenance cost and owner:",
    "Permission, safety, dependency, and compatibility impact:",
    "Next route and operation:",
    "Actions explicitly not taken:",
    "Residual risk:",
]

PLACEHOLDER_FIELDS = [
    "- Operation ID:",
    "- Recommendation record path:",
    "- Recommendation date:",
    "- Allowed actions:",
    "- Recommendation scope:",
    "- Project area and canonical owner:",
    "- Project-contour evidence:",
    "- Selected development pattern IDs:",
    "- Evidence quality:",
    "- Recommendation ID:",
    "- Recommendation kind:",
    "- Existing item IDs:",
    "- Observed problem:",
    "- Expected quality or consistency effect:",
    "- Acceptance criteria:",
    "- Expected context-load effect:",
    "- Implementation cost:",
    "- Next route and operation:",
    "- Residual risk:",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def field_line(text: str, field: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(field):
            following = lines[index + 1] if index + 1 < len(lines) else ""
            return f"{line} {following}"
    return ""


def string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item for item in value)
    )


def main() -> int:
    failures: list[str] = []
    paths = [
        FRAMEWORK,
        ROUTER,
        FLOW,
        TEMPLATE,
        CAPTURE_FLOW,
        DEVELOPMENT_EVIDENCE,
        PROJECT_CONTOUR,
        ASSISTANT_CONTOUR,
        HELP,
        HELP_REFERENCE,
        MANIFEST,
    ]
    missing = [path.relative_to(ROOT) for path in paths if not path.is_file()]
    if missing:
        for path in missing:
            print(f"FAIL: missing {path}", file=sys.stderr)
        return 1

    framework_text = read(FRAMEWORK)
    flow_text = read(FLOW)
    template_text = read(TEMPLATE)
    capture_flow_text = read(CAPTURE_FLOW)
    for label, text, required_values in [
        (FRAMEWORK.relative_to(ROOT), framework_text, FRAMEWORK_TEXT),
        (FLOW.relative_to(ROOT), flow_text, FLOW_TEXT),
        (TEMPLATE.relative_to(ROOT), template_text, TEMPLATE_TEXT),
        (CAPTURE_FLOW.relative_to(ROOT), capture_flow_text, CAPTURE_FLOW_TEXT),
    ]:
        for required in required_values:
            if required not in text:
                failures.append(f"{label} missing {required}")

    for field in PLACEHOLDER_FIELDS:
        line = field_line(template_text, field)
        if not line:
            failures.append(f"{TEMPLATE.relative_to(ROOT)} missing field {field}")
        elif "{" not in line:
            failures.append(
                f"{TEMPLATE.relative_to(ROOT)} field {field} must use a placeholder"
            )

    try:
        router = json.loads(read(ROUTER))
    except json.JSONDecodeError as exc:
        failures.append(f"invalid {ROUTER.relative_to(ROOT)}: {exc}")
        router = {}

    try:
        development_evidence = json.loads(read(DEVELOPMENT_EVIDENCE))
    except json.JSONDecodeError as exc:
        failures.append(f"invalid {DEVELOPMENT_EVIDENCE.relative_to(ROOT)}: {exc}")
        development_evidence = {}
    if development_evidence.get("schema_version") != 1:
        failures.append("development evidence schema_version must be 1")
    if development_evidence.get("register_kind") != "target-development-evidence":
        failures.append("development evidence register_kind is incorrect")
    for field in ["project", "owner", "retention_policy", "last_reviewed"]:
        value = development_evidence.get(field)
        if not isinstance(value, str) or "{" not in value:
            failures.append(f"development evidence {field} must use a placeholder")
    content_policy = development_evidence.get("content_policy", "")
    for required in ["no raw chat", "secrets", "credentials", "personal data"]:
        if required not in content_policy:
            failures.append(f"development evidence content_policy missing {required}")
    if development_evidence.get("patterns") != []:
        failures.append("development evidence target template patterns must start empty")

    if router.get("schema_version") != 2:
        failures.append("AI infrastructure router schema_version must be 2")
    if router.get("recommendation_template") != (
        ".ai/assistant/templates/ai-infrastructure-recommendation.md"
    ):
        failures.append("AI infrastructure router recommendation_template is incorrect")
    order = router.get("routing_order")
    if not isinstance(order, list) or "recommend" not in order:
        failures.append("AI infrastructure router must include recommend routing")
    elif order.index("recommend") != order.index("inventory") + 1:
        failures.append("recommend route must follow inventory in routing_order")

    route = router.get("routes", {}).get("recommend")
    if not isinstance(route, dict):
        failures.append("AI infrastructure router missing recommend route")
        route = {}
    for field in [
        "use_when",
        "required_context",
        "expand_when",
        "allowed_actions",
        "approval_gates",
        "validation",
        "final_evidence",
    ]:
        if not string_list(route.get(field)):
            failures.append(f"recommend route {field} must be a non-empty string list")
    allowed = route.get("allowed_actions", [])
    if "read-only" not in allowed:
        failures.append("recommend route must allow read-only")
    if any(action in allowed for action in ["code-and-tests", "full-with-approval"]):
        failures.append("recommend route must not allow implementation actions")
    for required in [
        ".ai/framework/ai-infrastructure-recommendations.md",
        ".ai/assistant/flows/ai-infrastructure-recommendation.flow.md",
        ".ai/assistant/templates/ai-infrastructure-recommendation.md",
        ".ai/project/contour.md",
        ".ai/project/source-of-truth-registry.md",
        ".ai/project/development-evidence.json",
    ]:
        if required not in route.get("required_context", []):
            failures.append(f"recommend route required_context missing {required}")

    project_text = read(PROJECT_CONTOUR)
    assistant_text = read(ASSISTANT_CONTOUR)
    for required in [
        "## AI Infrastructure Evidence Boundary",
        "assistant contour owns",
        ".ai/project/development-evidence.json",
    ]:
        if required not in project_text:
            failures.append(f"project contour missing ownership boundary: {required}")
    for required in [
        "project-evidenced recommendation",
        "lazy development-evidence capture mechanics",
    ]:
        if required not in assistant_text:
            failures.append(f"assistant contour missing ownership boundary: {required}")

    for path in [HELP, HELP_REFERENCE]:
        text = read(path)
        for alias in [
            "alatyr-suggest-ai {RECOMMENDATION_SCOPE}",
            "alatyr-improve-ai {AI_INFRASTRUCTURE_ITEM_ID}",
        ]:
            if alias not in text:
                failures.append(f"{path.relative_to(ROOT)} missing {alias}")
    if "Operation: `ai-infrastructure-recommendation`" not in read(HELP_REFERENCE):
        failures.append("help reference missing recommendation operation")

    manifest_text = read(MANIFEST)
    for required in [
        'recommendation: ".ai/assistant/templates/ai-infrastructure-recommendation.md"',
        'ai_infrastructure_recommendation: ".ai/assistant/templates/ai-infrastructure-recommendation.md"',
        'development_evidence: ".ai/project/development-evidence.json"',
        'development_evidence_capture: ".ai/assistant/flows/development-evidence-capture.flow.md"',
    ]:
        if required not in manifest_text:
            failures.append(f"target manifest missing {required}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("OK: checked AI infrastructure recommendation contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
