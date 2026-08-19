#!/usr/bin/env python3
"""Validate framework pack inheritance, dependency closure, and projections."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from check_framework_metadata import parse_front_matter
from framework_packaging import (
    FRAMEWORK_ROOT,
    PACK_CATALOG,
    pack_names,
    project_registry,
    projected_framework_contents,
    resolve_framework_files,
)


EXPECTED_PACKS = ["core", "standard", "complete"]
REQUIRED_PROJECTED = {
    "README.md",
    "file-inventory.json",
    "rule-ownership.md",
    "rule-registry.json",
    "rule-registry.md",
}


def main() -> int:
    failures: list[str] = []
    try:
        catalog = json.loads(PACK_CATALOG.read_text(encoding="utf-8"))
        if catalog.get("schema_version") != 1:
            failures.append("framework pack schema_version must be 1")
        if catalog.get("pack_kind") != "alatyr-framework-pack-catalog":
            failures.append("framework pack catalog kind is invalid")
        if set(catalog.get("projected_files", [])) != REQUIRED_PROJECTED:
            failures.append("framework pack projected_files contract drifted")
        names = pack_names()
        if names != EXPECTED_PACKS:
            failures.append(f"framework packs must be {EXPECTED_PACKS}, got {names}")

        all_files = {
            path.name
            for path in FRAMEWORK_ROOT.iterdir()
            if path.is_file() and path.suffix in {".md", ".json"}
        }
        selections = {name: resolve_framework_files(name) for name in EXPECTED_PACKS}
        if not selections["core"] < selections["standard"]:
            failures.append("core framework pack must be a strict subset of standard")
        if not selections["standard"] < selections["complete"]:
            failures.append("standard framework pack must be a strict subset of complete")
        if selections["complete"] != all_files:
            failures.append("complete framework pack must contain every framework file")
        for name, files in selections.items():
            missing_projected = REQUIRED_PROJECTED - files
            if missing_projected:
                failures.append(f"framework pack {name} misses projected files {sorted(missing_projected)}")
            missing_files = sorted(file for file in files if not (FRAMEWORK_ROOT / file).is_file())
            if missing_files:
                failures.append(f"framework pack {name} references missing files {missing_files}")

        dependencies: dict[str, set[str]] = {}
        for path in FRAMEWORK_ROOT.glob("*.md"):
            metadata = parse_front_matter(path)
            if not metadata:
                continue
            for rule_id in metadata.get("owns_rules", []):
                dependencies[rule_id] = set(metadata.get("depends_on", []))
        for name in ["core", "standard"]:
            registry = project_registry(name)
            rule_ids = {rule["id"] for rule in registry["rules"]}
            for rule_id in sorted(rule_ids):
                missing = dependencies.get(rule_id, set()) - rule_ids
                if missing:
                    failures.append(
                        f"framework pack {name} rule {rule_id} misses dependencies {sorted(missing)}"
                    )
            contents = projected_framework_contents(name)
            inventory = json.loads(contents["file-inventory.json"] or "{}")
            inventory_names = {
                Path(entry["path"]).name
                for entry in inventory.get("files", [])
                if isinstance(entry, dict) and isinstance(entry.get("path"), str)
            }
            if inventory_names != selections[name] - {"file-inventory.json"}:
                failures.append(f"framework pack {name} inventory projection drifted")
            if inventory.get("framework_pack") != name:
                failures.append(f"framework pack {name} inventory does not identify its pack")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: checked framework packs "
        + " ".join(f"{name}={len(selections[name])}" for name in EXPECTED_PACKS)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
