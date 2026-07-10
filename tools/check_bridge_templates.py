#!/usr/bin/env python3
"""Validate Alatyr target bridge templates.

This checks bridge templates in the AlatyrCore source repository. It is not a
portable framework requirement for target projects.
"""

from __future__ import annotations

import sys
from pathlib import Path

from render_bridge_templates import (
    BridgeTemplateError,
    MANIFEST_PATH,
    load_manifest,
    render_templates,
)


ROOT = Path(__file__).resolve().parents[1]
MAX_BRIDGE_LINES = 25

BRIDGE_FILES = [
    "templates/target/AI_ASSISTANTS.md",
    "templates/target/CLAUDE.md",
    "templates/target/GEMINI.md",
    "templates/target/.cursor/rules/alatyr-core.mdc",
    "templates/target/.cursorrules",
    "templates/target/.devin/rules/alatyr-core.md",
    "templates/target/.github/copilot-instructions.md",
    "templates/target/.github/prompts/gate-review.prompt.md",
    "templates/target/.windsurf/rules/alatyr-core.md",
    "templates/target/.windsurfrules",
]

REQUIRED_BRIDGE_REFS = [
    ".ai/assistant/help.md",
    ".ai/assistant/flows/operation-routing.flow.md",
    "alatyr-ai-inventory",
    "alatyr-adaptation",
    "alatyr-add-ai",
]

REQUIRED_CANONICAL_REFS = [
    "AGENTS.md",
    ".ai/README.md",
]


def read_text(relpath: str) -> str:
    return (ROOT / relpath).read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    rendered: dict[str, str] = {}

    try:
        manifest = load_manifest(MANIFEST_PATH)
        rendered = render_templates(manifest)
        manifest_paths = sorted(rendered)
        bridge_paths = sorted(BRIDGE_FILES)
        if manifest_paths != bridge_paths:
            failures.append(
                "tools/bridge_template_manifest.json paths do not match "
                "check_bridge_templates.py bridge list"
            )
    except BridgeTemplateError as exc:
        failures.append(str(exc))

    for relpath in BRIDGE_FILES:
        path = ROOT / relpath
        if not path.is_file():
            failures.append(f"missing bridge template: {relpath}")
            continue

        text = read_text(relpath)
        expected = rendered.get(relpath)
        if expected is not None and text != expected:
            failures.append(
                f"{relpath} differs from tools/bridge_template_manifest.json"
            )

        line_count = len(text.splitlines())
        if line_count > MAX_BRIDGE_LINES:
            failures.append(
                f"{relpath} has {line_count} lines; bridge templates must stay "
                f"at or below {MAX_BRIDGE_LINES}"
            )

        for required_ref in REQUIRED_BRIDGE_REFS:
            if required_ref not in text:
                failures.append(f"{relpath} does not route {required_ref}")

        for required_ref in REQUIRED_CANONICAL_REFS:
            if required_ref not in text:
                failures.append(f"{relpath} does not point to {required_ref}")

        if relpath != "templates/target/AI_ASSISTANTS.md":
            lower_text = text.lower()
            if "bridge" not in lower_text:
                failures.append(f"{relpath} does not identify itself as a bridge")

    matrix = read_text("templates/target/.ai/assistant/bridge-capability-matrix.md")
    for required_matrix_ref in [
        "Routes `alatyr-ai-inventory`:",
        "Routes `alatyr-adaptation`:",
        "Routes `alatyr-add-ai`:",
        ".ai/assistant/help.md",
        ".ai/assistant/flows/operation-routing.flow.md",
        "Conformance check:",
    ]:
        if required_matrix_ref not in matrix:
            failures.append(
                "templates/target/.ai/assistant/bridge-capability-matrix.md "
                f"missing {required_matrix_ref}"
            )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(f"OK: checked {len(BRIDGE_FILES)} bridge templates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
