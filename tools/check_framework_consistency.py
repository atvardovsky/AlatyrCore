#!/usr/bin/env python3
"""Source-repository consistency checks for Alatyr Core.

This validates the AlatyrCore repository itself. It is not a portable framework
requirement for target projects.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relpath: str) -> str:
    return (ROOT / relpath).read_text(encoding="utf-8")


def line_count(relpath: str) -> int:
    return len(read_text(relpath).splitlines())


def framework_files() -> list[str]:
    return sorted(
        str(path.relative_to(ROOT))
        for path in (ROOT / "framework").glob("*.md")
        if path.is_file()
    )


def git_check_ignore_no_index(relpath: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", relpath],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    failures: list[str] = []
    fw_files = framework_files()

    explicit_source_lists = [
        "README.md",
        "AGENTS.md",
        "INSTALL.md",
        "installer/assistant-installation.flow.md",
    ]
    for doc in explicit_source_lists:
        text = read_text(doc)
        for relpath in fw_files:
            if relpath not in text:
                failures.append(f"{doc} does not list {relpath}")

    framework_index = read_text("framework/README.md")
    for relpath in fw_files:
        target_path = f".ai/{relpath}"
        if target_path not in framework_index:
            failures.append(f"framework/README.md does not index {target_path}")

    target_agents = read_text("templates/target/AGENTS.md")
    for relpath in fw_files:
        target_path = f".ai/{relpath}"
        if target_path not in target_agents:
            failures.append(f"templates/target/AGENTS.md does not list {target_path}")

    ai_assistants = read_text("AI_ASSISTANTS.md")
    if "all files under `framework/`" not in ai_assistants:
        failures.append("AI_ASSISTANTS.md must tell assistants to read all framework files")

    required_target_templates = [
        "templates/target/.ai/assistant/flows/blueprint-driven-change.flow.md",
        "templates/target/.ai/assistant/flows/documentation-sync.flow.md",
        "templates/target/.ai/assistant/flows/logical-integrity-review.flow.md",
        "templates/target/.ai/assistant/flows/skill-adaptation.flow.md",
        "templates/target/.ai/assistant/skills/example/SKILL.md",
    ]
    for relpath in required_target_templates:
        if not (ROOT / relpath).is_file():
            failures.append(f"missing target template: {relpath}")

    placeholder_templates = [
        "templates/target/AGENTS.md",
        "templates/target/.ai/README.md",
        "templates/target/.ai/project/contour.md",
        "templates/target/.ai/assistant/contour.md",
        "templates/target/.ai/assistant/gates/checklist.md",
        "templates/target/.ai/assistant/flows/blueprint-driven-change.flow.md",
        "templates/target/.ai/assistant/flows/documentation-sync.flow.md",
        "templates/target/.ai/assistant/flows/logical-integrity-review.flow.md",
        "templates/target/.ai/assistant/flows/skill-adaptation.flow.md",
        "templates/target/.ai/assistant/skills/example/SKILL.md",
        "templates/target/.ai/assistant/templates/installation-note.md",
    ]
    for relpath in placeholder_templates:
        if "{" not in read_text(relpath):
            failures.append(f"{relpath} should remain placeholder-based")

    bridge_files = [
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
    for relpath in bridge_files:
        if line_count(relpath) > 25:
            failures.append(f"{relpath} is too long for a bridge/template wrapper")

    for path in (ROOT / "templates" / "target").rglob("*"):
        if not path.is_file():
            continue
        relpath = str(path.relative_to(ROOT))
        if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
            if git_check_ignore_no_index(relpath):
                failures.append(f"{relpath} is hidden by .gitignore")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(f"OK: checked {len(fw_files)} framework docs and target templates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
