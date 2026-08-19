"""Resolve and project portable framework packs for target scaffolds."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from render_rule_registry_docs import render_ownership, render_registry
from target_adapter_validation.framework_baseline import render_pack_readme


ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK_ROOT = ROOT / "framework"
PACK_CATALOG = FRAMEWORK_ROOT / "framework-packs.json"
REGISTRY = FRAMEWORK_ROOT / "rule-registry.json"
PROJECTED_FILES = {
    "README.md",
    "file-inventory.json",
    "rule-ownership.md",
    "rule-registry.json",
    "rule-registry.md",
}

def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    return data


def pack_names() -> list[str]:
    packs = load_object(PACK_CATALOG).get("packs")
    if not isinstance(packs, dict):
        raise ValueError("framework pack catalog must define packs")
    return list(packs)


def _resolve_pack_contract(pack: str) -> tuple[set[str], set[str], bool]:
    catalog = load_object(PACK_CATALOG)
    packs = catalog.get("packs")
    if not isinstance(packs, dict) or pack not in packs:
        raise ValueError(f"unknown framework pack: {pack}")
    resolving: set[str] = set()

    def resolve(name: str) -> tuple[set[str], set[str], bool]:
        if name in resolving:
            raise ValueError(f"cyclic framework pack inheritance: {name}")
        entry = packs.get(name)
        if not isinstance(entry, dict):
            raise ValueError(f"invalid framework pack: {name}")
        resolving.add(name)
        rule_ids: set[str] = set()
        files: set[str] = set()
        include_remaining = False
        parent = entry.get("extends")
        if parent is not None:
            if not isinstance(parent, str) or parent not in packs:
                raise ValueError(f"invalid parent for framework pack: {name}")
            parent_rules, parent_files, parent_remaining = resolve(parent)
            rule_ids.update(parent_rules)
            files.update(parent_files)
            include_remaining = parent_remaining
        for field, destination in [("rule_ids", rule_ids), ("additional_files", files)]:
            values = entry.get(field, [])
            if not isinstance(values, list) or not all(
                isinstance(value, str) and value for value in values
            ):
                raise ValueError(f"framework pack {name} has invalid {field}")
            destination.update(values)
        include_remaining = include_remaining or entry.get(
            "include_remaining_framework_files"
        ) is True
        resolving.remove(name)
        return rule_ids, files, include_remaining

    return resolve(pack)


def resolve_framework_files(pack: str) -> set[str]:
    rule_ids, files, include_remaining = _resolve_pack_contract(pack)
    registry = load_object(REGISTRY)
    sources = {
        rule["id"]: Path(rule["canonical_source"]).name
        for rule in registry.get("rules", [])
        if isinstance(rule, dict)
        and isinstance(rule.get("id"), str)
        and isinstance(rule.get("canonical_source"), str)
    }
    unknown = sorted(rule_ids - set(sources))
    if unknown:
        raise ValueError(f"framework pack {pack} has unknown rule IDs: {unknown}")
    files.update(sources[rule_id] for rule_id in rule_ids)
    files.update(PROJECTED_FILES)
    if include_remaining:
        files.update(
            path.name
            for path in FRAMEWORK_ROOT.iterdir()
            if path.is_file() and path.suffix in {".md", ".json"}
        )
    return files


def project_registry(pack: str) -> dict[str, Any]:
    selected_files = resolve_framework_files(pack)
    data = load_object(REGISTRY)
    selected_rules = [
        rule
        for rule in data.get("rules", [])
        if isinstance(rule, dict)
        and Path(str(rule.get("canonical_source", ""))).name in selected_files
    ]
    selected_ids = {rule["id"] for rule in selected_rules}
    owners: list[dict[str, Any]] = []
    for owner in data.get("category_owners", []):
        if not isinstance(owner, dict):
            continue
        rule_ids = [rule_id for rule_id in owner.get("rule_ids", []) if rule_id in selected_ids]
        if not rule_ids:
            continue
        projected = dict(owner)
        projected["rule_ids"] = rule_ids
        owners.append(projected)
    return {
        "schema_version": data.get("schema_version"),
        "category_owners": owners,
        "rules": selected_rules,
    }


def projected_framework_contents(pack: str) -> dict[str, str | None]:
    selected_files = resolve_framework_files(pack)
    if pack == "complete":
        return {name: None for name in selected_files}
    projected_registry = project_registry(pack)
    contents: dict[str, str | None] = {name: None for name in selected_files}
    contents["README.md"] = render_pack_readme(pack, selected_files)
    contents["rule-registry.json"] = json.dumps(projected_registry, indent=2) + "\n"
    contents["rule-registry.md"] = render_registry(projected_registry)
    contents["rule-ownership.md"] = render_ownership(projected_registry)

    inventory_files: list[dict[str, Any]] = []
    rules_by_source: dict[str, list[str]] = {}
    for rule in projected_registry["rules"]:
        rules_by_source.setdefault(rule["canonical_source"], []).append(rule["id"])
    for name in sorted(selected_files - {"file-inventory.json"}):
        content = contents.get(name)
        payload = (
            content.encode("utf-8")
            if content is not None
            else (FRAMEWORK_ROOT / name).read_bytes()
        )
        relpath = f"framework/{name}"
        inventory_files.append(
            {
                "path": relpath,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "rule_ids": sorted(rules_by_source.get(relpath, [])),
                "projected": name in PROJECTED_FILES,
            }
        )
    inventory = {
        "schema_version": 1,
        "inventory_kind": "alatyr-framework-files",
        "framework_pack": pack,
        "framework_version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "adapter_schema_version": int(
            (ROOT / "ADAPTER_SCHEMA_VERSION").read_text(encoding="utf-8").strip()
        ),
        "template_version": int(
            (ROOT / "TEMPLATE_VERSION").read_text(encoding="utf-8").strip()
        ),
        "files": inventory_files,
    }
    contents["file-inventory.json"] = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    return contents
