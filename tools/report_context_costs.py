#!/usr/bin/env python3
"""Measure deterministic target-template context routing costs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
ROUTER = TARGET / ".ai" / "assistant" / "context-router.json"


def source_path(reference: str) -> Path | None:
    if reference.startswith("{"):
        return None
    if reference.startswith(".ai/framework/"):
        return ROOT / "framework" / reference[len(".ai/framework/") :]
    if reference.startswith(".ai/"):
        return TARGET / reference
    if reference in {"AGENTS.md", "AI_ASSISTANTS.md"}:
        return TARGET / reference
    return None


def word_count(path: Path) -> int:
    return len(re.findall(r"\S+", path.read_text(encoding="utf-8")))


def measure(references: list[str]) -> dict[str, Any]:
    unique = list(dict.fromkeys(references))
    resolved: list[tuple[str, Path]] = []
    unresolved: list[str] = []
    missing: list[str] = []
    for reference in unique:
        path = source_path(reference)
        if path is None:
            unresolved.append(reference)
        elif not path.is_file():
            missing.append(reference)
        else:
            resolved.append((reference, path))
    return {
        "declared_files": len(unique),
        "resolved_files": len(resolved),
        "words": sum(word_count(path) for _, path in resolved),
        "resolved_paths": [reference for reference, _ in resolved],
        "unresolved_references": unresolved,
        "missing_paths": missing,
    }


def reduction_percent(initial: int, full: int) -> float | str:
    if full <= 0:
        return "unknown"
    return round((1 - initial / full) * 100, 1)


def build_report() -> dict[str, Any]:
    router = json.loads(ROUTER.read_text(encoding="utf-8"))
    bootstrap_refs = [
        *router.get("preloaded_context", []),
        *router.get("bootstrap_context", []),
    ]
    bootstrap = measure(bootstrap_refs)
    profiles: dict[str, dict[str, Any]] = {}
    for name, profile in router.get("profiles", {}).items():
        profiles[name] = measure(profile.get("required_context", []))

    migration = router.get("migration_routing", {})
    migration_initial_refs = migration.get("required_context", [])
    migration_full_refs = list(
        dict.fromkeys(
            [
                *migration_initial_refs,
                *migration.get("candidate_context", []),
            ]
        )
    )
    migration_initial = measure(migration_initial_refs)
    migration_full = measure(migration_full_refs)

    return {
        "schema_version": 1,
        "report_kind": "static-target-context-cost",
        "source": "templates/target/.ai/assistant/context-router.json",
        "measurement": "whitespace-delimited words in resolved source templates",
        "budgets": router.get("context_budgets", {}),
        "bootstrap": bootstrap,
        "profiles": profiles,
        "migration_routing": {
            "initial": migration_initial,
            "full_candidate_union": migration_full,
            "initial_word_reduction_percent": reduction_percent(
                migration_initial["words"], migration_full["words"]
            ),
        },
        "limitations": [
            "static template measurement is not model token usage",
            "placeholder target-owned context is unresolved",
            "runtime expansion depends on task evidence",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure deterministic context costs from the target router template."
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(build_report(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
