#!/usr/bin/env python3
"""Validate deterministic core, standard, and full scaffold profiles."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from scaffold_target_structure import (
    PROFILE_MANIFEST,
    TEMPLATE_ROOT,
    profile_names,
    resolve_profile_paths,
)


EXPECTED_PROFILES = ["core", "standard", "full"]
CORE_REQUIRED = {
    Path(".ai/README.md"),
    Path(".ai/alatyr.yaml"),
    Path(".ai/assistant/context-router.json"),
    Path(".ai/assistant/context-profiles.md"),
    Path(".ai/assistant/module-profile.md"),
    Path(".ai/project/source-of-truth-registry.md"),
    Path("AGENTS.md"),
}
FULL_ONLY_BRIDGES = {
    Path("CLAUDE.md"),
    Path("GEMINI.md"),
    Path(".github/copilot-instructions.md"),
    Path(".cursor/rules/alatyr-core.mdc"),
    Path(".devin/rules/alatyr-core.md"),
    Path(".windsurf/rules/alatyr-core.md"),
}


def main() -> int:
    failures: list[str] = []
    try:
        manifest = json.loads(PROFILE_MANIFEST.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != 1:
            failures.append("scaffold profile schema_version must be 1")
        names = profile_names()
        if names != EXPECTED_PROFILES:
            failures.append(f"scaffold profiles must be {EXPECTED_PROFILES}, got {names}")

        all_templates = {
            path.relative_to(TEMPLATE_ROOT)
            for path in TEMPLATE_ROOT.rglob("*")
            if path.is_file()
        }
        core = resolve_profile_paths("core")
        standard = resolve_profile_paths("standard")
        full = resolve_profile_paths("full")

        missing_core = sorted(CORE_REQUIRED - core)
        if missing_core:
            failures.append(f"core profile missing required paths: {missing_core}")
        if not core < standard:
            failures.append("core profile must be a strict subset of standard")
        if not standard < full:
            failures.append("standard profile must be a strict subset of full")
        if full != all_templates:
            failures.append("full profile must include every target template")
        unknown = sorted(full - all_templates)
        if unknown:
            failures.append(f"scaffold profiles reference missing templates: {unknown}")
        leaked_bridges = sorted(FULL_ONLY_BRIDGES & standard)
        if leaked_bridges:
            failures.append(f"assistant-specific bridges leaked into standard: {leaked_bridges}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked scaffold profiles "
        f"core={len(core)} standard={len(standard)} full={len(full)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
