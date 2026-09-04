#!/usr/bin/env python3
"""Validate framework pack inheritance, dependency closure, and projections."""

from __future__ import annotations

import hashlib
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


EXPECTED_PACKS = ["kernel", "core", "standard", "complete"]
REQUIRED_PROJECTED = {
    "README.md",
    "context-index.json",
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
            path.relative_to(FRAMEWORK_ROOT).as_posix()
            for path in FRAMEWORK_ROOT.rglob("*")
            if path.is_file() and path.suffix in {".md", ".json"}
        }
        selections = {name: resolve_framework_files(name) for name in EXPECTED_PACKS}
        if not selections["kernel"] < selections["core"]:
            failures.append("kernel framework pack must be a strict subset of core")
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
        for path in FRAMEWORK_ROOT.rglob("*.md"):
            metadata = parse_front_matter(path)
            if not metadata:
                continue
            for rule_id in metadata.get("owns_rules", []):
                dependencies[rule_id] = set(metadata.get("depends_on", []))
        for name in ["kernel", "core", "standard"]:
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
                str(entry["path"])[len("framework/"):]
                for entry in inventory.get("files", [])
                if isinstance(entry, dict) and isinstance(entry.get("path"), str)
            }
            if inventory_names != selections[name] - {"file-inventory.json"}:
                failures.append(f"framework pack {name} inventory projection drifted")
            if inventory.get("framework_pack") != name:
                failures.append(f"framework pack {name} inventory does not identify its pack")
            semantic_index = json.loads(contents["semantics/index.json"] or "{}")
            semantic_terms: dict[str, dict[str, object]] = {}
            for descriptor in semantic_index.get("shards", []):
                if not isinstance(descriptor, dict) or not isinstance(
                    descriptor.get("path"), str
                ):
                    failures.append(f"framework pack {name} has an invalid semantic shard")
                    continue
                shard_name = f"semantics/{descriptor['path']}"
                if shard_name not in selections[name]:
                    failures.append(
                        f"framework pack {name} semantic index references absent {shard_name}"
                    )
                    continue
                shard_text = contents.get(shard_name)
                if shard_text is None:
                    shard_text = (FRAMEWORK_ROOT / shard_name).read_text(encoding="utf-8")
                expected_digest = "sha256:" + hashlib.sha256(
                    shard_text.encode("utf-8")
                ).hexdigest()
                if descriptor.get("content_digest") != expected_digest:
                    failures.append(
                        f"framework pack {name} semantic shard digest drifted for {shard_name}"
                    )
                shard = json.loads(shard_text)
                terms = shard.get("terms", [])
                actual_ids = [term.get("id") for term in terms if isinstance(term, dict)]
                if descriptor.get("term_ids") != actual_ids:
                    failures.append(
                        f"framework pack {name} semantic term IDs drifted for {shard_name}"
                    )
                for term in terms:
                    if isinstance(term, dict) and isinstance(term.get("id"), str):
                        semantic_terms[term["id"]] = term
            for term_id, term in semantic_terms.items():
                owner = term.get("canonical_owner")
                owner_rule = term.get("owner_rule_id")
                if owner not in selections[name]:
                    failures.append(
                        f"framework pack {name} semantic term {term_id} misses owner {owner}"
                    )
                if owner_rule not in rule_ids:
                    failures.append(
                        f"framework pack {name} semantic term {term_id} misses rule {owner_rule}"
                    )
                missing_terms = sorted(
                    dependency
                    for dependency in term.get("depends_on", [])
                    if dependency not in semantic_terms
                )
                if missing_terms:
                    failures.append(
                        f"framework pack {name} semantic term {term_id} misses terms {missing_terms}"
                    )
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
