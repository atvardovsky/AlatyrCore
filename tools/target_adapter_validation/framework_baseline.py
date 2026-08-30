"""Resolve source-owned framework pack expectations for baseline checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from render_context_catalogs import build_framework_catalog_contents
from render_rule_registry_docs import render_ownership, render_registry


def render_pack_readme(pack: str, selected_files: set[str]) -> str:
    lines = [
        "# Alatyr Framework Pack",
        "",
        f"Installed framework pack: `{pack}`.",
        "",
        "This is a projected portable framework index. The complete source catalog",
        "is `framework/framework-packs.json`; absent optional owners are unavailable",
        "until a reviewed pack expansion installs them and updates the manifest, rule",
        "registry, ownership map, and inventory.",
        "",
        "## Installed Files",
        "",
    ]
    lines.extend(f"- `.ai/framework/{name}`" for name in sorted(selected_files))
    lines.extend(
        [
            "",
            "Use `.ai/framework/rule-registry.json` for installed rule IDs and",
            "`.ai/framework/file-inventory.json` for exact file evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    return data


def project_semantic_index(source_framework: Path, selected_files: set[str]) -> str:
    """Render a semantic-codebook index that references only installed shards."""

    semantic_index_path = source_framework / "semantics" / "index.json"
    index = load_object(semantic_index_path)
    shards = index.get("shards")
    if not isinstance(shards, list):
        raise ValueError("source semantic codebook index has invalid shards")
    selected_shards: list[dict[str, Any]] = []
    for shard in shards:
        if not isinstance(shard, dict):
            raise ValueError("source semantic codebook index has invalid shard entry")
        path = shard.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError("source semantic codebook shard path is invalid")
        if f"semantics/{path}" in selected_files:
            selected_shards.append(dict(shard))
    if not selected_shards:
        raise ValueError("projected semantic codebook index would be empty")
    projected = dict(index)
    projected["shards"] = selected_shards
    return json.dumps(projected, indent=2, ensure_ascii=True) + "\n"


def source_pack_projection(
    source_framework: Path, pack: str
) -> tuple[set[str], dict[str, Any], dict[str, bytes]]:
    catalog = load_object(source_framework / "framework-packs.json")
    registry = load_object(source_framework / "rule-registry.json")
    packs = catalog.get("packs")
    if not isinstance(packs, dict) or pack not in packs:
        raise ValueError(f"source framework has no pack {pack}")

    resolving: set[str] = set()

    def resolve(name: str) -> tuple[set[str], set[str], bool]:
        if name in resolving:
            raise ValueError(f"cyclic source framework pack inheritance: {name}")
        entry = packs.get(name)
        if not isinstance(entry, dict):
            raise ValueError(f"invalid source framework pack: {name}")
        resolving.add(name)
        rules: set[str] = set()
        files: set[str] = set()
        include_remaining = False
        parent = entry.get("extends")
        if parent is not None:
            if not isinstance(parent, str):
                raise ValueError(f"invalid source framework pack parent: {name}")
            parent_rules, parent_files, parent_remaining = resolve(parent)
            rules.update(parent_rules)
            files.update(parent_files)
            include_remaining = parent_remaining
        for field, destination in [("rule_ids", rules), ("additional_files", files)]:
            values = entry.get(field, [])
            if not isinstance(values, list) or not all(
                isinstance(value, str) and value for value in values
            ):
                raise ValueError(f"invalid source framework pack {name}.{field}")
            destination.update(values)
        include_remaining = include_remaining or entry.get(
            "include_remaining_framework_files"
        ) is True
        resolving.remove(name)
        return rules, files, include_remaining

    rule_ids, files, include_remaining = resolve(pack)
    rules_by_id = {
        rule["id"]: rule
        for rule in registry.get("rules", [])
        if isinstance(rule, dict) and isinstance(rule.get("id"), str)
    }
    unknown = rule_ids - set(rules_by_id)
    if unknown:
        raise ValueError(f"source framework pack has unknown rules: {sorted(unknown)}")
    files.update(
        str(rules_by_id[rule_id]["canonical_source"])[len("framework/"):]
        for rule_id in rule_ids
    )
    projected_files = catalog.get("projected_files")
    if not isinstance(projected_files, list) or not all(
        isinstance(value, str) and value for value in projected_files
    ):
        raise ValueError("source framework pack projected_files is invalid")
    files.update(projected_files)
    if include_remaining:
        files.update(
            path.relative_to(source_framework).as_posix()
            for path in source_framework.rglob("*")
            if path.is_file()
            and path.suffix in {".md", ".json"}
            and not path.relative_to(source_framework).as_posix().startswith("catalog/")
            and path.name != "context-index.json"
        )
    files.update(build_framework_catalog_contents(files, root=source_framework))

    selected_rules = [
        rule
        for rule in registry.get("rules", [])
        if isinstance(rule, dict)
        and str(rule.get("canonical_source", "")).startswith("framework/")
        and str(rule.get("canonical_source", ""))[len("framework/"):] in files
    ]
    selected_ids = {rule["id"] for rule in selected_rules}
    owners: list[dict[str, Any]] = []
    for owner in registry.get("category_owners", []):
        if not isinstance(owner, dict):
            continue
        owner_rule_ids = [
            rule_id for rule_id in owner.get("rule_ids", []) if rule_id in selected_ids
        ]
        if owner_rule_ids:
            projected_owner = dict(owner)
            projected_owner["rule_ids"] = owner_rule_ids
            owners.append(projected_owner)
    projected_registry = {
        "schema_version": registry.get("schema_version"),
        "category_owners": owners,
        "rules": selected_rules,
    }

    if include_remaining:
        contents = {
            name: (source_framework / name).read_bytes()
            for name in files
        }
        return files, projected_registry, contents

    contents: dict[str, bytes] = {}
    projected_content = {
        "README.md": render_pack_readme(pack, files).encode("utf-8"),
        "rule-registry.json": (
            json.dumps(projected_registry, indent=2) + "\n"
        ).encode("utf-8"),
        "rule-registry.md": render_registry(projected_registry).encode("utf-8"),
        "rule-ownership.md": render_ownership(projected_registry).encode("utf-8"),
    }
    if "semantics/index.json" in files:
        projected_content["semantics/index.json"] = project_semantic_index(
            source_framework, files
        ).encode("utf-8")
    projected_content.update(
        {
            name: content.encode("utf-8")
            for name, content in build_framework_catalog_contents(
                files,
                root=source_framework,
                content_overrides={
                    name: content.decode("utf-8")
                    for name, content in projected_content.items()
                    if name != "file-inventory.json"
                },
            ).items()
        }
    )
    for name in files - {"file-inventory.json"}:
        contents[name] = projected_content.get(name, (source_framework / name).read_bytes())

    rules_by_source: dict[str, list[str]] = {}
    for rule in projected_registry["rules"]:
        rules_by_source.setdefault(rule["canonical_source"], []).append(rule["id"])
    inventory = {
        "schema_version": 1,
        "inventory_kind": "alatyr-framework-files",
        "framework_pack": pack,
        "framework_version": (source_framework.parent / "VERSION")
        .read_text(encoding="utf-8")
        .strip(),
        "adapter_schema_version": int(
            (source_framework.parent / "ADAPTER_SCHEMA_VERSION")
            .read_text(encoding="utf-8")
            .strip()
        ),
        "template_version": int(
            (source_framework.parent / "TEMPLATE_VERSION")
            .read_text(encoding="utf-8")
            .strip()
        ),
        "files": [
            {
                "path": f"framework/{name}",
                "sha256": hashlib.sha256(contents[name]).hexdigest(),
                "rule_ids": sorted(rules_by_source.get(f"framework/{name}", [])),
                "projected": name in projected_files,
            }
            for name in sorted(contents)
        ],
    }
    contents["file-inventory.json"] = (
        json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return files, projected_registry, contents


def source_pack_expectation(
    source_framework: Path, pack: str
) -> tuple[set[str], dict[str, Any], dict[str, str]]:
    files, projected_registry, contents = source_pack_projection(
        source_framework, pack
    )
    expected_hashes = {
        name: hashlib.sha256(payload).hexdigest() for name, payload in contents.items()
    }
    return files, projected_registry, expected_hashes
