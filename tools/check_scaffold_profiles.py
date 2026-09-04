#!/usr/bin/env python3
"""Validate deterministic kernel, core, standard, and full scaffold profiles."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from scaffold_target_structure import (
    PROJECTED_MARKDOWN_PATHS,
    PROFILE_MANIFEST,
    TEMPLATE_ROOT,
    build_target_context_catalogs,
    project_assistant_bridges,
    profile_names,
    resolve_assistant_surfaces,
    resolve_profile_paths,
    resolved_framework_pack,
)
from framework_packaging import resolve_framework_files
from scaffold_projection import path_available, project_markdown_fragments


EXPECTED_PROFILES = ["kernel", "core", "standard", "full"]
KERNEL_REQUIRED = {
    Path(".ai/README.md"),
    Path(".ai/alatyr.yaml"),
    Path(".ai/assistant/bootstrap-index.json"),
    Path(".ai/assistant/entry-packet.json"),
    Path(".ai/assistant/context-router.json"),
    Path(".ai/assistant/context-profiles.md"),
    Path(".ai/assistant/context/task-scales/small-task.json"),
    Path(".ai/assistant/installation-state.json"),
    Path(".ai/assistant/module-profile.md"),
    Path(".ai/assistant/task-decomposition.json"),
    Path(".ai/assistant/gates/index.json"),
    Path(".ai/assistant/gates/core.md"),
    Path(".ai/assistant/gates/final-evidence.md"),
    Path(".ai/assistant/flows/logical-integrity-review.flow.md"),
    Path(".ai/assistant/templates/small-task-evidence.md"),
    Path(".ai/assistant/templates/task-decomposition.md"),
    Path(".ai/project/source-of-truth-registry.md"),
    Path("AGENTS.md"),
}
CORE_REQUIRED = {
    Path(".ai/assistant/context/project-knowledge-routing.json"),
    Path(".ai/assistant/context/cost-scenarios.json"),
    Path(".ai/assistant/context/migration-routing.json"),
    Path(".ai/assistant/flows/engineering-evidence-capture.flow.md"),
    Path(".ai/assistant/flows/project-knowledge.flow.md"),
    Path(".ai/assistant/gates/engineering-evidence.md"),
    Path(".ai/assistant/gates/project-knowledge.md"),
    Path(".ai/assistant/templates/engineering-evidence-record.json"),
    Path(".ai/assistant/templates/project-knowledge-promotion.json"),
    Path(".ai/project/engineering-evidence/index.json"),
    Path(".ai/project/knowledge/index.json"),
}
STANDARD_REQUIRED = {
    Path(".ai/assistant/operation-index.json"),
    Path(".ai/assistant/operation-catalog.json"),
    Path(".ai/assistant/flows/operation-routing.flow.md"),
    Path(".ai/assistant/flows/adapter-health.flow.md"),
    Path(".ai/assistant/templates/pre-change-preview.md"),
}
FULL_ONLY_BRIDGES = {
    Path("CLAUDE.md"),
    Path("GEMINI.md"),
    Path(".github/copilot-instructions.md"),
    Path(".github/prompts/gate-review.prompt.md"),
    Path(".agents/skills/README.md"),
    Path(".cursor/rules/alatyr-core.mdc"),
    Path(".cursorrules"),
    Path(".roo/rules/alatyr-core.md"),
    Path(".rules"),
    Path(".devin/rules/alatyr-core.md"),
    Path(".windsurf/rules/alatyr-core.md"),
    Path(".windsurfrules"),
}
MARKDOWN_PATH_CLAIM_RE = re.compile(r"`(?P<path>\.ai/[A-Za-z0-9_./-]+)`")


def check_projected_markdown_claims(
    profile: str,
    selected_templates: set[Path],
    framework_pack: str,
) -> list[str]:
    """Return unsupported concrete path claims in projected Markdown."""

    generated_indexes = set(build_target_context_catalogs(selected_templates))
    selected = selected_templates | generated_indexes | {
        Path(".ai/framework") / path
        for path in resolve_framework_files(framework_pack)
    }
    failures: list[str] = []
    for relpath in sorted(PROJECTED_MARKDOWN_PATHS & selected_templates):
        rendered = project_markdown_fragments(
            (TEMPLATE_ROOT / relpath).read_text(encoding="utf-8"),
            selected,
        )
        if "alatyr:scaffold-fragment" in rendered:
            failures.append(f"{profile} {relpath} retained scaffold fragment markers")
        for match in MARKDOWN_PATH_CLAIM_RE.finditer(rendered):
            claim = match.group("path")
            if not path_available(claim, selected):
                failures.append(
                    f"{profile} {relpath} claims absent scaffold path: {claim}"
                )
    return failures


def main() -> int:
    failures: list[str] = []
    try:
        manifest = json.loads(PROFILE_MANIFEST.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != 2:
            failures.append("scaffold profile schema_version must be 2")
        names = profile_names()
        if names != EXPECTED_PROFILES:
            failures.append(f"scaffold profiles must be {EXPECTED_PROFILES}, got {names}")

        all_templates = {
            path.relative_to(TEMPLATE_ROOT)
            for path in TEMPLATE_ROOT.rglob("*")
            if path.is_file()
        }
        kernel = resolve_profile_paths("kernel")
        core = resolve_profile_paths("core")
        standard = resolve_profile_paths("standard")
        full = resolve_profile_paths("full")

        missing_kernel = sorted(KERNEL_REQUIRED - kernel)
        if missing_kernel:
            failures.append(f"kernel profile missing required paths: {missing_kernel}")
        missing_core = sorted(CORE_REQUIRED - core)
        if missing_core:
            failures.append(f"core profile missing required paths: {missing_core}")
        missing_standard = sorted(STANDARD_REQUIRED - standard)
        if missing_standard:
            failures.append(
                f"standard profile missing operation surfaces: {missing_standard}"
            )
        if not kernel < core:
            failures.append("kernel profile must be a strict subset of core")
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
        default_bridges = sorted(
            FULL_ONLY_BRIDGES & project_assistant_bridges(full, set())
        )
        if default_bridges:
            failures.append(
                "assistant-specific bridges leaked into default full scaffold: "
                f"{default_bridges}"
            )
        selected_zed_bridges = FULL_ONLY_BRIDGES & project_assistant_bridges(
            full, resolve_assistant_surfaces(["zed"])
        )
        if selected_zed_bridges != {Path(".rules")}:
            failures.append(
                "Zed alias selection must add only the .rules native bridge"
            )
        selected_agents_bridges = FULL_ONLY_BRIDGES & project_assistant_bridges(
            full, resolve_assistant_surfaces(["agents"])
        )
        if selected_agents_bridges != {Path(".agents/skills/README.md")}:
            failures.append(
                "AGENTS-aware surface selection must add only .agents/skills/README.md"
            )
        try:
            project_assistant_bridges(
                standard, resolve_assistant_surfaces(["claude"])
            )
        except ValueError:
            pass
        else:
            failures.append(
                "standard profile must reject an unavailable Claude native bridge"
            )
        matched_packs = {
            profile: resolved_framework_pack(profile, "matched")
            for profile in EXPECTED_PROFILES
        }
        if matched_packs != {
            "kernel": "kernel",
            "core": "core",
            "standard": "standard",
            "full": "complete",
        }:
            failures.append(f"support-profile framework pack mapping drifted: {matched_packs}")
        if not resolve_framework_files("kernel") < resolve_framework_files("core"):
            failures.append("kernel framework pack must be smaller than core")
        if not resolve_framework_files("core") < resolve_framework_files("standard"):
            failures.append("core framework pack must be smaller than standard")
        ai_infrastructure = resolve_profile_paths("core", {"ai-infrastructure"})
        if not core < ai_infrastructure:
            failures.append("enabled ai-infrastructure capability must expand core")
        if Path(".ai/assistant/ai-infrastructure-router.json") not in ai_infrastructure:
            failures.append("ai-infrastructure capability misses its router")
        architecture = resolve_profile_paths("core", {"architecture-knowledge"})
        if Path(".ai/project/architecture/catalog.json") not in architecture:
            failures.append("architecture capability misses its compact catalog")
        if (
            resolved_framework_pack("core", "matched", {"architecture-knowledge"})
            != "complete"
        ):
            failures.append("architecture capability must raise the matched framework pack")
        for profile, selected_templates in [
            ("kernel", kernel),
            ("core", core),
            ("standard", standard),
            ("full", full),
        ]:
            failures.extend(
                check_projected_markdown_claims(
                    profile,
                    selected_templates,
                    resolved_framework_pack(profile, "matched"),
                )
            )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked scaffold profiles "
        f"kernel={len(kernel)} core={len(core)} standard={len(standard)} "
        f"full={len(full)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
