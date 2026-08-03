#!/usr/bin/env python3
"""Measure deterministic target-template context routing costs."""

from __future__ import annotations

import argparse
import math
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
    texts = [path.read_text(encoding="utf-8") for _, path in resolved]
    characters = sum(len(value) for value in texts)
    return {
        "declared_files": len(unique),
        "resolved_files": len(resolved),
        "words": sum(len(re.findall(r"\S+", value)) for value in texts),
        "characters": characters,
        "bytes": sum(len(value.encode("utf-8")) for value in texts),
        "estimated_tokens_4_chars": math.ceil(characters / 4),
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
    def descriptor(entry: Any) -> tuple[str | None, dict[str, Any]]:
        reference = entry.get("descriptor") if isinstance(entry, dict) else None
        path = source_path(reference) if isinstance(reference, str) else None
        if path is None or not path.is_file():
            return reference, {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return reference, data if isinstance(data, dict) else {}

    profiles: dict[str, dict[str, Any]] = {}
    for name, entry in router.get("profile_index", {}).items():
        reference, profile = descriptor(entry)
        profiles[name] = measure(
            [value for value in [reference, *profile.get("required_context", [])] if value]
        )

    intent_overlays: dict[str, dict[str, Any]] = {}
    intent_contracts: dict[str, tuple[str | None, dict[str, Any]]] = {}
    capability_index = json.loads(
        (TARGET / ".ai/assistant/assistant-capabilities.json").read_text(
            encoding="utf-8"
        )
    )
    default_surface = capability_index.get("default_surface")
    default_capability = capability_index.get("surfaces", {}).get(default_surface)
    for name, overlay in router.get("intent_overlays", {}).items():
        reference, contract = descriptor(overlay)
        intent_contracts[name] = (reference, contract)
        surface_context = [default_capability] if name == "diagram-request" else []
        intent_overlays[name] = measure(
            [
                value
                for value in [
                    reference,
                    *contract.get("required_context", []),
                    *surface_context,
                ]
                if value
            ]
        )

    operation_routing = router.get("operation_routing", {})
    diagram_reference, diagram_overlay = intent_contracts.get(
        "diagram-request", (None, {})
    )
    diagram_compact_refs = [
        operation_routing.get("index", ""),
        diagram_reference,
        *diagram_overlay.get("required_context", []),
        default_capability,
    ]
    diagram_full_reference_refs = [
        operation_routing.get("catalog", ""),
        ".ai/assistant/help.md",
        ".ai/assistant/flows/operation-routing.flow.md",
        ".ai/assistant/module-profile.md",
        ".ai/assistant/bridge-capability-matrix.md",
        diagram_reference,
        *diagram_overlay.get("required_context", []),
        default_capability,
    ]
    diagram_compact = measure([value for value in diagram_compact_refs if value])
    diagram_full_reference = measure(
        [value for value in diagram_full_reference_refs if value]
    )

    architecture_reference, architecture_overlay = intent_contracts.get(
        "architecture-request", (None, {})
    )
    architecture_conditional_refs = [
        entry.get("path")
        for entry in architecture_overlay.get("conditional_context", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    ]
    architecture_compact_refs = [
        operation_routing.get("index", ""),
        architecture_reference,
        *architecture_overlay.get("required_context", []),
    ]
    architecture_full_reference_refs = [
        operation_routing.get("catalog", ""),
        ".ai/assistant/help.md",
        ".ai/assistant/flows/operation-routing.flow.md",
        ".ai/assistant/module-profile.md",
        architecture_reference,
        *architecture_overlay.get("required_context", []),
        *architecture_conditional_refs,
    ]
    architecture_compact = measure(
        [value for value in architecture_compact_refs if value]
    )
    architecture_full_reference = measure(
        [value for value in architecture_full_reference_refs if value]
    )

    migration_reference, migration = descriptor(router.get("migration_routing", {}))
    migration_initial_refs = [
        value
        for value in [migration_reference, *migration.get("required_context", [])]
        if value
    ]
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
        "intent_overlays": intent_overlays,
        "operation_routes": {
            "diagram-discussion": {
                "compact": diagram_compact,
                "full_reference_union": diagram_full_reference,
                "word_reduction_percent": reduction_percent(
                    diagram_compact["words"], diagram_full_reference["words"]
                ),
            },
            "architecture-assistance": {
                "compact": architecture_compact,
                "full_reference_union": architecture_full_reference,
                "word_reduction_percent": reduction_percent(
                    architecture_compact["words"],
                    architecture_full_reference["words"],
                ),
            }
        },
        "migration_routing": {
            "initial": migration_initial,
            "full_candidate_union": migration_full,
            "initial_word_reduction_percent": reduction_percent(
                migration_initial["words"], migration_full["words"]
            ),
        },
        "limitations": [
            "token count uses a four-characters-per-token estimate, not model billing",
            "runtime clients may preload hidden context not represented by repository paths",
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
