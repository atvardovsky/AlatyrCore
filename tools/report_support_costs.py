#!/usr/bin/env python3
"""Measure standing Alatyr support-surface cost.

This source helper measures repository files that Alatyr installs or manages.
It does not judge semantic correctness, model billing, or project value.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

from capability_catalog import dependency_closure, load_modules, minimum_pack
from framework_packaging import projected_framework_contents, resolve_framework_files
from scaffold_target_structure import (
    FRAMEWORK_ROOT,
    TEMPLATE_ROOT,
    build_target_context_catalogs,
    build_projection_context,
    load_assistant_surfaces,
    project_assistant_bridges,
    projected_template_content,
    resolve_assistant_surfaces,
    resolve_profile_paths,
    resolved_framework_pack,
)
from render_context_catalogs import INDEX_NAME
from support_state import (
    POLICY_PATH,
    STATE_PATH,
    build_support_state_from_contents,
    render_state,
)
from target_tool_compat import generation_provenance_from_manifest_text


WORD_RE = re.compile(r"\S+")
BRIDGE_ROOTS = {
    ".cursor",
    ".devin",
    ".github",
    ".roo",
    ".windsurf",
}
ROOT_ENTRYPOINTS = {
    "AGENTS.md",
    "AI_ASSISTANTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".cursorrules",
    ".rules",
    ".windsurfrules",
    "CODEOWNERS",
}
TEXT_CACHE: dict[Path, str] = {}


def read_text(path: Path) -> str:
    resolved = path.resolve()
    cached = TEXT_CACHE.get(resolved)
    if cached is None:
        cached = resolved.read_text(encoding="utf-8", errors="replace")
        TEXT_CACHE[resolved] = cached
    return cached


def group_key(label: str) -> str:
    parts = label.split("/")
    if label.startswith(".ai/framework/"):
        return ".ai/framework"
    if label.startswith(".ai/assistant/"):
        return ".ai/assistant"
    if label.startswith(".ai/project/"):
        return ".ai/project"
    if label.startswith(".ai/"):
        return "/".join(parts[:2])
    if label in ROOT_ENTRYPOINTS:
        return "root-entrypoints"
    if parts and parts[0] in BRIDGE_ROOTS:
        return "assistant-bridges"
    return parts[0] if parts else "unknown"


def measure_text_entries(entries: Iterable[tuple[str, str]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    groups: dict[str, dict[str, int]] = {}
    for label, text in sorted(entries):
        lines = len(text.splitlines())
        words = len(WORD_RE.findall(text))
        characters = len(text)
        encoded = len(text.encode("utf-8"))
        records.append(
            {
                "path": label,
                "lines": lines,
                "words": words,
                "characters": characters,
                "bytes": encoded,
            }
        )
        group = groups.setdefault(
            group_key(label),
            {"files": 0, "lines": 0, "words": 0, "characters": 0, "bytes": 0},
        )
        group["files"] += 1
        group["lines"] += lines
        group["words"] += words
        group["characters"] += characters
        group["bytes"] += encoded

    totals = {
        "files": len(records),
        "lines": sum(record["lines"] for record in records),
        "words": sum(record["words"] for record in records),
        "characters": sum(record["characters"] for record in records),
        "bytes": sum(record["bytes"] for record in records),
        "estimated_tokens_4_chars": math.ceil(
            sum(record["characters"] for record in records) / 4
        ),
    }
    return {
        **totals,
        "groups": [
            {"group": group, **values}
            for group, values in sorted(
                groups.items(), key=lambda item: (-item[1]["words"], item[0])
            )
        ],
        "largest_files": sorted(records, key=lambda item: item["words"], reverse=True)[
            :15
        ],
        "missing_paths": [],
    }


def measure_files(files: Iterable[tuple[str, Path]]) -> dict[str, Any]:
    entries: list[tuple[str, str]] = []
    missing: list[str] = []
    for label, path in sorted(files):
        if not path.is_file():
            missing.append(label)
            continue
        entries.append((label, read_text(path)))
    measured = measure_text_entries(entries)
    measured["missing_paths"] = missing
    return measured


def combine_measurements(*measurements: dict[str, Any]) -> dict[str, Any]:
    groups: dict[str, dict[str, int]] = {}
    largest_files: list[dict[str, Any]] = []
    missing_paths: list[str] = []
    totals = {"files": 0, "lines": 0, "words": 0, "characters": 0, "bytes": 0}
    for measurement in measurements:
        for key in totals:
            totals[key] += int(measurement.get(key, 0))
        missing_paths.extend(measurement.get("missing_paths", []))
        largest_files.extend(measurement.get("largest_files", []))
        for group in measurement.get("groups", []):
            if not isinstance(group, dict) or not isinstance(group.get("group"), str):
                continue
            merged = groups.setdefault(
                group["group"],
                {"files": 0, "lines": 0, "words": 0, "characters": 0, "bytes": 0},
            )
            for key in merged:
                merged[key] += int(group.get(key, 0))
    return {
        **totals,
        "estimated_tokens_4_chars": math.ceil(totals["characters"] / 4),
        "groups": [
            {"group": group, **values}
            for group, values in sorted(
                groups.items(), key=lambda item: (-item[1]["words"], item[0])
            )
        ],
        "largest_files": sorted(
            largest_files, key=lambda item: item["words"], reverse=True
        )[:15],
        "missing_paths": sorted(missing_paths),
    }


def target_template_pairs(paths: Iterable[Path]) -> list[tuple[str, Path]]:
    return [
        (path.as_posix(), TEMPLATE_ROOT / path)
        for path in sorted(paths, key=lambda item: item.as_posix())
    ]


def framework_pairs(paths: Iterable[str]) -> list[tuple[str, Path]]:
    return [
        (f".ai/framework/{path}", FRAMEWORK_ROOT / path)
        for path in sorted(paths)
    ]


def assistant_surface_summary() -> dict[str, Any]:
    surfaces = load_assistant_surfaces()
    bridge_paths = sorted(
        {
            path
            for surface in surfaces
            for path in surface.get("bridge_paths", [])
            if isinstance(path, str)
        }
    )
    capability_dir = TEMPLATE_ROOT / ".ai" / "assistant" / "assistant-capabilities"
    unique_payloads: set[str] = set()
    capability_files = sorted(capability_dir.glob("*.json"))
    for path in capability_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.pop("assistant_surface", None)
            data.pop("surface_id", None)
        unique_payloads.add(json.dumps(data, sort_keys=True))
    return {
        "known_surfaces": len(surfaces),
        "declared_bridge_paths": len(bridge_paths),
        "capability_template_files": len(capability_files),
        "unique_capability_payloads_without_identity": len(unique_payloads),
    }


def module_costs() -> list[dict[str, Any]]:
    modules = load_modules()
    costs: list[dict[str, Any]] = []
    for module_id, module in modules.items():
        closure = dependency_closure({module_id}, modules)
        paths: set[Path] = set()
        for selected in closure:
            target_files = modules[selected].get("target_files", [])
            if isinstance(target_files, list):
                paths.update(Path(value) for value in target_files if isinstance(value, str))
        measured = measure_files(target_template_pairs(paths))
        costs.append(
            {
                "module": module_id,
                "min_framework_pack": module.get("min_framework_pack"),
                "dependency_closure": sorted(closure),
                "target_files": measured["files"],
                "target_words": measured["words"],
                "target_bytes": measured["bytes"],
                "required_pack_with_dependencies": minimum_pack({module_id}),
            }
        )
    return sorted(costs, key=lambda item: (-item["target_words"], item["module"]))


def support_state_inventory_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "source": path.name,
            "present": False,
            "managed_files": 0,
            "managed_groups": 0,
            "words": 0,
            "bytes": 0,
        }
    text = read_text(path)
    data = json.loads(text)
    files = data.get("files") if isinstance(data, dict) else None
    groups = data.get("groups") if isinstance(data, dict) else None
    return {
        "source": path.as_posix(),
        "present": True,
        "managed_files": len(files) if isinstance(files, list) else 0,
        "managed_groups": len(groups) if isinstance(groups, list) else 0,
        "words": len(WORD_RE.findall(text)),
        "bytes": len(text.encode("utf-8")),
    }


def projected_support_state_text(
    *,
    framework_pack: str,
    target_contents: dict[str, str],
    framework_contents: dict[str, str | None],
) -> str:
    policy_text = target_contents.get(POLICY_PATH)
    if policy_text is None:
        policy_text = read_text(TEMPLATE_ROOT / POLICY_PATH)
    policy = json.loads(policy_text)
    manifest_text = target_contents.get(".ai/alatyr.yaml")
    if manifest_text is None:
        manifest_text = read_text(TEMPLATE_ROOT / ".ai" / "alatyr.yaml")
    contents = {
        label: text.encode("utf-8")
        for label, text in target_contents.items()
        if label != STATE_PATH
    }
    for relpath in resolve_framework_files(framework_pack):
        label = f".ai/framework/{relpath}"
        content = framework_contents.get(relpath)
        if content is None:
            content = read_text(FRAMEWORK_ROOT / relpath)
        contents[label] = content.encode("utf-8")
    state = build_support_state_from_contents(
        contents,
        policy=policy,
        generated_by=generation_provenance_from_manifest_text(
            TEMPLATE_ROOT,
            tool_name="scaffold_target_structure.py",
            manifest_text=manifest_text,
        ),
        source_revision="source-template",
    )
    return render_state(state)


def projected_scaffold_measurements(
    *,
    profile: str,
    enabled_modules: set[str],
    framework_pack: str,
    selected_surfaces: set[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Any, dict[str, Any]]:
    selected_template_paths = resolve_profile_paths(profile, enabled_modules)
    selected_template_paths = project_assistant_bridges(
        selected_template_paths, selected_surfaces
    )
    selected_template_paths.update(build_target_context_catalogs(selected_template_paths))
    selected_framework_paths = resolve_framework_files(framework_pack)
    selected = selected_template_paths | {
        Path(".ai") / "framework" / name for name in selected_framework_paths
    }
    initial_context = build_projection_context(selected_template_paths, enabled_modules)
    preliminary_contents: dict[Path, str] = {}
    for rel in selected_template_paths:
        if rel.name == INDEX_NAME or rel.as_posix() == STATE_PATH:
            continue
        content = projected_template_content(
            rel,
            profile,
            framework_pack,
            selected,
            initial_context,
            TEMPLATE_ROOT,
        )
        if content is not None:
            preliminary_contents[rel] = content
    context_catalogs = build_target_context_catalogs(
        selected_template_paths, preliminary_contents
    )
    projection_context = build_projection_context(
        selected, enabled_modules, context_catalogs
    )
    target_contents: dict[str, str] = {}
    for rel in selected_template_paths:
        if rel.as_posix() == STATE_PATH:
            continue
        content = projected_template_content(
            rel,
            profile,
            framework_pack,
            selected,
            projection_context,
            TEMPLATE_ROOT,
        )
        if content is None:
            content = read_text(TEMPLATE_ROOT / rel)
        target_contents[rel.as_posix()] = content
    framework_contents = projected_framework_contents(framework_pack)
    support_state_measure = measure_text_entries([])
    if STATE_PATH in {path.as_posix() for path in selected_template_paths}:
        support_state_text = projected_support_state_text(
            framework_pack=framework_pack,
            target_contents=target_contents,
            framework_contents=framework_contents,
        )
        support_state_measure = measure_text_entries([(STATE_PATH, support_state_text)])
        target_contents[STATE_PATH] = support_state_text
    framework_texts = []
    for relpath in selected_framework_paths:
        content = framework_contents.get(relpath)
        if content is None:
            content = read_text(FRAMEWORK_ROOT / relpath)
        framework_texts.append((f".ai/framework/{relpath}", content))
    target_measure = measure_text_entries(target_contents.items())
    framework_measure = measure_text_entries(framework_texts)
    return (
        target_measure,
        framework_measure,
        combine_measurements(target_measure, framework_measure),
        projection_context,
        support_state_measure,
    )


def build_scaffold_report(
    profile: str = "kernel",
    enabled_modules: Iterable[str] | None = None,
    framework_pack: str = "matched",
    assistant_surfaces: Iterable[str] | None = None,
    assistant_surface_report: dict[str, Any] | None = None,
    optional_module_cost_report: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    enabled = set(enabled_modules or [])
    selected_surfaces = resolve_assistant_surfaces(list(assistant_surfaces or []))
    selected_pack = resolved_framework_pack(profile, framework_pack, enabled)
    target_measure, framework_measure, combined_measure, projection, state_measure = (
        projected_scaffold_measurements(
            profile=profile,
            enabled_modules=enabled,
            framework_pack=selected_pack,
            selected_surfaces=selected_surfaces,
        )
    )
    return {
        "schema_version": 1,
        "report_kind": "alatyr-standing-support-cost",
        "measurement": "whitespace-delimited words in projected installed support files",
        "profile": profile,
        "profile_recommendation": {
            "default": "kernel",
            "escalation_order": ["kernel", "core", "standard", "full"],
            "policy": (
                "start from the cheapest sufficient profile and escalate only "
                "for target evidence, a named module dependency, an assistant "
                "surface requirement, or failed validation"
            ),
        },
        "enabled_modules": sorted(enabled),
        "selected_assistant_surfaces": sorted(selected_surfaces),
        "framework_pack": selected_pack,
        "target_templates": target_measure,
        "framework_pack_files": framework_measure,
        "combined_support": combined_measure,
        "cost_scopes": {
            "selected_support_projection": {
                "description": "Files selected by the scaffold profile, enabled modules, assistant surfaces, and framework pack.",
                "files": combined_measure["files"],
                "words": combined_measure["words"],
                "estimated_tokens_4_chars": combined_measure["estimated_tokens_4_chars"],
            },
            "profile_generated_support_state": {
                "description": "Generated .ai/support-state.json projected for the selected profile, not the complete source template inventory.",
                "present": state_measure["files"] == 1,
                "files": state_measure["files"],
                "words": state_measure["words"],
                "bytes": state_measure["bytes"],
                "estimated_tokens_4_chars": state_measure["estimated_tokens_4_chars"],
            },
            "complete_managed_inventory": support_state_inventory_summary(
                TEMPLATE_ROOT / ".ai" / "support-state.json"
            ),
            "runtime_context": {
                "description": "Task-time context is selected through bootstrap/router/catalogs and measured by report_context_costs.py.",
                "standing_support_cost_is_not_runtime_context": True,
            },
        },
        "operation_surface": {
            "operation_catalog_installed": projection.catalog is not None,
            "projected_operation_count": len(projection.operation_ids),
        },
        "assistant_surfaces": (
            assistant_surface_report
            if assistant_surface_report is not None
            else assistant_surface_summary()
        ),
        "optional_module_costs": (
            optional_module_cost_report
            if optional_module_cost_report is not None
            else module_costs()
        ),
        "limitations": [
            "standing support cost is not runtime context cost",
            "word counts are deterministic source measurements, not provider billing",
            "assistant comprehension and logical integrity still require reasoning",
            "target usefulness depends on selected modules and project-specific facts",
        ],
    }


def load_support_policy(target: Path) -> dict[str, Any] | None:
    path = target / ".ai" / "project" / "support-policy.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def classify_path(relpath: str, policy: dict[str, Any] | None) -> str:
    if not policy:
        return "unclassified"
    for exclusion in policy.get("exclusions", []):
        if isinstance(exclusion, dict) and fnmatch.fnmatch(relpath, exclusion.get("pattern", "")):
            return "excluded"
    for entry in policy.get("classifications", []):
        if not isinstance(entry, dict):
            continue
        classification = entry.get("classification")
        patterns = entry.get("patterns")
        if isinstance(classification, str) and isinstance(patterns, list):
            if any(isinstance(pattern, str) and fnmatch.fnmatch(relpath, pattern) for pattern in patterns):
                return classification
    return "unclassified"


def build_installed_report(target: Path) -> dict[str, Any]:
    target = target.resolve()
    policy = load_support_policy(target)
    bridge_paths = {
        path
        for surface in load_assistant_surfaces()
        for path in surface.get("bridge_paths", [])
        if isinstance(path, str)
    }
    paths = {
        path.relative_to(target)
        for path in (target / ".ai").rglob("*")
        if path.is_file()
    } if (target / ".ai").is_dir() else set()
    paths.update(Path(path) for path in bridge_paths if (target / path).is_file())
    paths.update(Path(path) for path in ROOT_ENTRYPOINTS if (target / path).is_file())
    pairs = [(path.as_posix(), target / path) for path in sorted(paths)]
    measured = measure_files(pairs)
    classifications: dict[str, int] = {}
    for label, path in pairs:
        if path.is_file():
            classification = classify_path(label, policy)
            classifications[classification] = classifications.get(classification, 0) + 1
    return {
        "schema_version": 1,
        "report_kind": "installed-alatyr-standing-support-cost",
        "target": str(target),
        "review_recommendation": {
            "entry_point": ".ai/assistant/entry-packet.json",
            "policy": (
                "route through the generated entry packet when present, then "
                "use support-delta for changed support surfaces before loading "
                "large human reference files"
            ),
        },
        "support_policy_present": policy is not None,
        "support_surfaces": measured,
        "cost_scopes": {
            "installed_support_files": {
                "description": "Support files present in the target filesystem and measured by this report.",
                "files": measured["files"],
                "words": measured["words"],
                "estimated_tokens_4_chars": measured["estimated_tokens_4_chars"],
            },
            "managed_inventory": support_state_inventory_summary(
                target / ".ai" / "support-state.json"
            ),
            "runtime_context": {
                "description": "Task-time context depends on the target router, selected profiles, and context receipts.",
                "standing_support_cost_is_not_runtime_context": True,
            },
        },
        "classifications": dict(sorted(classifications.items())),
        "limitations": [
            "installed support cost is a filesystem measurement, not semantic correctness",
            "ignored local state is not filtered unless the target support policy excludes it",
            "runtime context depends on the selected task route",
        ],
    }


def render_text(report: dict[str, Any]) -> str:
    if report["report_kind"] == "installed-alatyr-standing-support-cost":
        support = report["support_surfaces"]
        inventory = report["cost_scopes"]["managed_inventory"]
        lines = [
            "Alatyr installed support cost",
            f"Target: {report['target']}",
            f"Recommended entry point: {report['review_recommendation']['entry_point']}",
            f"Files: {support['files']}",
            f"Words: {support['words']}",
            f"Estimated tokens at 4 chars/token: {support['estimated_tokens_4_chars']}",
            (
                "Managed inventory records: "
                f"{inventory['managed_files']} files"
                if inventory["present"]
                else "Managed inventory records: unavailable"
            ),
            "Classifications:",
        ]
        for name, count in report["classifications"].items():
            lines.append(f"- {name}: {count}")
    else:
        support = report["combined_support"]
        inventory = report["cost_scopes"]["complete_managed_inventory"]
        state = report["cost_scopes"]["profile_generated_support_state"]
        lines = [
            "Alatyr scaffold support cost",
            f"Profile: {report['profile']}",
            f"Recommended default: {report['profile_recommendation']['default']}",
            f"Framework pack: {report['framework_pack']}",
            f"Files: {support['files']}",
            f"Words: {support['words']}",
            f"Estimated tokens at 4 chars/token: {support['estimated_tokens_4_chars']}",
            (
                "Complete managed inventory records: "
                f"{inventory['managed_files']} files"
                if inventory["present"]
                else "Complete managed inventory records: unavailable"
            ),
            (
                "Profile generated support-state: "
                f"{state['words']} words"
                if state["present"]
                else "Profile generated support-state: unavailable"
            ),
            f"Projected operations: {report['operation_surface']['projected_operation_count']}",
            "Largest groups:",
        ]
        for group in support["groups"][:6]:
            lines.append(
                f"- {group['group']}: {group['files']} files, {group['words']} words"
            )
        lines.append("Most expensive optional modules:")
        for module in report["optional_module_costs"][:6]:
            lines.append(
                f"- {module['module']}: {module['target_files']} files, "
                f"{module['target_words']} words"
            )
    lines.append("Limitations:")
    for item in report["limitations"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--format", choices=["json", "text"], default="json")
    parser.add_argument(
        "--profile",
        choices=["kernel", "core", "standard", "full"],
        default="kernel",
    )
    parser.add_argument(
        "--enable-module",
        action="append",
        default=[],
        help="Include an optional capability and its dependency closure.",
    )
    parser.add_argument(
        "--framework-pack",
        choices=["matched", "core", "standard", "complete"],
        default="matched",
    )
    parser.add_argument(
        "--assistant-surface",
        action="append",
        default=[],
        help="Include native bridge files for one selected assistant surface.",
    )
    args = parser.parse_args()

    report = (
        build_installed_report(args.target)
        if args.target
        else build_scaffold_report(
            args.profile,
            args.enable_module,
            args.framework_pack,
            args.assistant_surface,
        )
    )
    rendered = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_text(report)
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
