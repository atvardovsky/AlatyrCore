#!/usr/bin/env python3
"""Scaffold Alatyr target adapter structure from source templates.

This is a source-repository helper, not the Alatyr installation mechanism.
It copies placeholder files only. It does not inspect target facts, accept an
installation, overwrite existing files by default, or make protected decisions.

The implementation uses only Python standard-library APIs so it can run on
Linux, macOS, and Windows with Python 3.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scaffold_projection import (
    build_operation_index,
    load_object,
    project_agent_rule_ids,
    project_ai_infrastructure_router,
    project_catalog,
    project_context_descriptor,
    project_manifest,
    project_router,
    render_json,
)
from framework_packaging import (
    pack_names,
    project_registry,
    projected_framework_contents,
    resolve_framework_files,
)


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / "templates" / "target"
FRAMEWORK_ROOT = ROOT / "framework"
PROFILE_MANIFEST = ROOT / "tools" / "scaffold_profiles.json"


def load_profile_manifest() -> dict[str, Any]:
    data = json.loads(PROFILE_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("scaffold profile manifest must be a JSON object")
    return data


def profile_names() -> list[str]:
    profiles = load_profile_manifest().get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("scaffold profile manifest must define profiles")
    return list(profiles)


def resolve_profile_paths(profile: str) -> set[Path]:
    manifest = load_profile_manifest()
    profiles = manifest.get("profiles")
    if not isinstance(profiles, dict) or profile not in profiles:
        raise ValueError(f"unknown scaffold profile: {profile}")

    resolving: set[str] = set()

    def resolve(name: str) -> set[Path]:
        if name in resolving:
            raise ValueError(f"cyclic scaffold profile inheritance: {name}")
        entry = profiles.get(name)
        if not isinstance(entry, dict):
            raise ValueError(f"invalid scaffold profile: {name}")
        resolving.add(name)
        paths: set[Path] = set()
        parent = entry.get("extends")
        if parent is not None:
            if not isinstance(parent, str) or parent not in profiles:
                raise ValueError(f"invalid parent for scaffold profile: {name}")
            paths.update(resolve(parent))
        items = entry.get("template_files", [])
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise ValueError(f"invalid template_files for scaffold profile: {name}")
        paths.update(Path(item) for item in items)
        if entry.get("include_remaining_template_files") is True:
            paths.update(
                path.relative_to(TEMPLATE_ROOT)
                for path in TEMPLATE_ROOT.rglob("*")
                if path.is_file()
            )
        resolving.remove(name)
        return paths

    return resolve(profile)


def iter_template_files(profile: str = "full") -> list[Path]:
    return sorted(TEMPLATE_ROOT / relpath for relpath in resolve_profile_paths(profile))


def resolved_framework_pack(profile: str, requested: str) -> str:
    if requested == "matched":
        return {"core": "core", "standard": "standard", "full": "complete"}[profile]
    minimum = {"core": 0, "standard": 1, "full": 2}[profile]
    rank = {"core": 0, "standard": 1, "complete": 2}[requested]
    if rank < minimum:
        raise ValueError(
            f"framework pack {requested} is too small for support profile {profile}"
        )
    return requested


def iter_framework_files(pack: str = "complete") -> list[Path]:
    return sorted(FRAMEWORK_ROOT / name for name in resolve_framework_files(pack))


def copy_file(src: Path, dst: Path, *, write: bool, content: str | None = None) -> None:
    if write:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            shutil.copyfile(src, dst)
        else:
            # Projected framework hashes are defined over canonical UTF-8 bytes.
            # Text-mode writes translate LF to CRLF on Windows and invalidate
            # the generated file inventory.
            dst.write_bytes(content.encode("utf-8"))


@dataclass(frozen=True)
class ProjectionContext:
    catalog: dict[str, Any] | None
    operation_ids: frozenset[str]


def build_projection_context(selected: set[Path]) -> ProjectionContext:
    catalog_rel = Path(".ai/assistant/operation-catalog.json")
    catalog = None
    if catalog_rel in selected:
        catalog = project_catalog(load_object(TEMPLATE_ROOT / catalog_rel), selected)
    operation_ids = frozenset(
        operation["id"]
        for operation in (catalog or {}).get("operations", [])
        if isinstance(operation, dict) and isinstance(operation.get("id"), str)
    )
    return ProjectionContext(catalog=catalog, operation_ids=operation_ids)


def projected_template_content(
    rel: Path,
    profile: str,
    framework_pack: str,
    selected: set[Path],
    context: ProjectionContext,
) -> str | None:
    src = TEMPLATE_ROOT / rel
    if rel == Path("AGENTS.md") and framework_pack != "complete":
        rule_ids = [rule["id"] for rule in project_registry(framework_pack)["rules"]]
        return project_agent_rule_ids(src.read_text(encoding="utf-8"), rule_ids)
    if rel == Path(".ai/alatyr.yaml"):
        return project_manifest(
            src.read_text(encoding="utf-8"), profile, framework_pack, selected
        )

    catalog_rel = Path(".ai/assistant/operation-catalog.json")
    index_rel = Path(".ai/assistant/operation-index.json")
    router_rel = Path(".ai/assistant/context-router.json")
    catalog = context.catalog
    if rel == catalog_rel and catalog is not None:
        return render_json(catalog)
    if rel == index_rel and catalog is not None:
        return render_json(build_operation_index(catalog))
    if rel == router_rel:
        return render_json(
            project_router(load_object(src), selected, set(context.operation_ids))
        )
    if rel == Path(".ai/assistant/ai-infrastructure-router.json"):
        return render_json(project_ai_infrastructure_router(load_object(src), selected))
    if rel.parts[:4] == (".ai", "assistant", "context", "profiles") or rel in {
        Path(".ai/assistant/context/migration-routing.json"),
        Path(".ai/assistant/context/cost-scenarios.json"),
        Path(".ai/assistant/context/consistency-routing.json"),
        Path(".ai/assistant/context/intents/diagram-request.json"),
        Path(".ai/assistant/context/intents/architecture-request.json"),
        Path(".ai/assistant/context/intents/code-documentation.json"),
        Path(".ai/assistant/context/intents/vocabulary-request.json"),
        Path(".ai/assistant/context/intents/test-first-request.json"),
        Path(".ai/assistant/context/intents/extension-request.json"),
        Path(".ai/assistant/context/task-scales/large-or-resumable.json"),
        Path(".ai/assistant/context/task-scales/change-package.json"),
    }:
        return render_json(
            project_context_descriptor(
                load_object(src), selected, set(context.operation_ids)
            )
        )
    return None


def plan(args: argparse.Namespace) -> tuple[list[str], list[str]]:
    target = args.target.resolve()
    profile = getattr(args, "profile", "full")
    requested_pack = getattr(args, "framework_pack", "matched")
    framework_pack = resolved_framework_pack(profile, requested_pack)
    selected_templates = resolve_profile_paths(profile)
    framework_files = resolve_framework_files(framework_pack)
    selected = selected_templates | {
        Path(".ai") / "framework" / name for name in framework_files
    }
    projection_context = build_projection_context(selected)
    framework_contents = projected_framework_contents(framework_pack)
    actions: list[str] = []
    blocked: list[str] = []

    if not target.exists():
        blocked.append(f"target does not exist: {target}")
        return actions, blocked
    if not target.is_dir():
        blocked.append(f"target is not a directory: {target}")
        return actions, blocked

    for src in iter_template_files(profile):
        rel = src.relative_to(TEMPLATE_ROOT)
        dst = target / rel
        if dst.exists() and not args.overwrite_existing:
            blocked.append(f"exists, would not overwrite: {dst}")
            continue
        copy_file(
            src,
            dst,
            write=args.write,
            content=projected_template_content(
                rel, profile, framework_pack, selected, projection_context
            ),
        )
        actions.append(f"template: {rel} -> {dst}")

    for src in iter_framework_files(framework_pack):
        rel = Path(".ai") / "framework" / src.name
        dst = target / rel
        if dst.exists() and not args.overwrite_existing:
            blocked.append(f"exists, would not overwrite: {dst}")
            continue
        copy_file(src, dst, write=args.write, content=framework_contents[src.name])
        actions.append(f"framework: {src.name} -> {dst}")

    return actions, blocked


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scaffold placeholder Alatyr adapter files. Default mode is dry-run."
        ),
        epilog=(
            "Examples:\n"
            "  Linux/macOS: python3 tools/scaffold_target_structure.py "
            "--target /path/to/repo\n"
            "  Windows: py -3 tools\\scaffold_target_structure.py "
            "--target C:\\path\\repo\n"
            "  Windows cmd wrapper: tools\\scaffold_target_structure.cmd "
            "--target C:\\path\\repo"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target",
        required=True,
        type=Path,
        help="Existing target repository directory.",
    )
    parser.add_argument(
        "--framework-pack",
        choices=["matched", *pack_names()],
        default="matched",
        help=(
            "Portable framework pack. matched selects core, standard, or "
            "complete from the target support profile; a broader pack is allowed."
        ),
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write files. Without this flag the helper prints the plan only.",
    )
    parser.add_argument(
        "--profile",
        choices=profile_names(),
        default="full",
        help=(
            "Target adapter support profile. core installs required adapter "
            "surfaces, standard adds common lifecycle/product operations, and "
            "full preserves the historical all-template behavior."
        ),
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help=(
            "Overwrite existing files. Use only after explicit human approval "
            "for the exact target path and protected surfaces."
        ),
    )
    args = parser.parse_args()

    try:
        actions, blocked = plan(args)
        framework_pack = resolved_framework_pack(args.profile, args.framework_pack)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    mode = "WRITE" if args.write else "DRY-RUN"
    print(f"Alatyr scaffold mode: {mode}")
    print(f"Alatyr scaffold profile: {args.profile}")
    print(f"Alatyr framework pack: {framework_pack}")
    print("This helper does not complete installation or fill target facts.")
    print("Supported platforms: Linux, macOS, Windows.")

    if actions:
        print("\nActions:")
        for action in actions:
            print(f"- {action}")

    if blocked:
        print("\nBlocked or skipped:")
        for item in blocked:
            print(f"- {item}")

    if args.write and blocked and not args.overwrite_existing:
        print(
            "\nSome files were skipped because they already exist. "
            "Review target facts and approvals before overwriting.",
            file=sys.stderr,
        )

    return 1 if blocked and not actions else 0


if __name__ == "__main__":
    raise SystemExit(main())
