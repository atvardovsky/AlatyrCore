#!/usr/bin/env python3
"""Validate structured metadata on framework rule-owner documents.

This validates AlatyrCore source documentation only. It is not a portable
framework requirement for target projects.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK = ROOT / "framework"
REGISTRY = FRAMEWORK / "rule-registry.json"
CONTEXT_PROFILES = FRAMEWORK / "context-profiles.md"

Metadata = Dict[str, Any]


def load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssertionError(f"missing {path}") from exc
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return data


def canonical_profiles() -> set[str]:
    text = CONTEXT_PROFILES.read_text(encoding="utf-8")
    profiles = set(re.findall(r"^- `([^`]+)`", text, flags=re.MULTILINE))
    profiles.add("all")
    return profiles


def parse_front_matter(path: Path) -> Metadata | None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return None

    try:
        end = lines[1:].index("---") + 1
    except ValueError:
        raise AssertionError(f"{path.relative_to(ROOT)} has unterminated front matter")

    current_section: str | None = None
    metadata: Metadata = {}
    in_alatyr_doc = False
    for line_number, line in enumerate(lines[1:end], start=2):
        if not line.strip():
            continue
        if line == "alatyr_doc:":
            in_alatyr_doc = True
            continue
        if not in_alatyr_doc:
            raise AssertionError(
                f"{path.relative_to(ROOT)}:{line_number} unexpected front matter key"
            )
        if line.startswith("  ") and not line.startswith("    "):
            current_section = None
            content = line.strip()
            if ":" not in content:
                raise AssertionError(
                    f"{path.relative_to(ROOT)}:{line_number} expected key/value"
                )
            key, value = content.split(":", 1)
            value = value.strip()
            if value == "[]":
                metadata[key] = []
            elif value:
                metadata[key] = strip_quotes(value)
            else:
                metadata[key] = []
                current_section = key
            continue
        if line.startswith("    - "):
            if current_section is None:
                raise AssertionError(
                    f"{path.relative_to(ROOT)}:{line_number} list item without key"
                )
            metadata[current_section].append(strip_quotes(line[6:].strip()))
            continue
        raise AssertionError(
            f"{path.relative_to(ROOT)}:{line_number} unsupported front matter shape"
        )

    return metadata


def strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def require_string(metadata: Metadata, key: str, relpath: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value:
        raise AssertionError(f"{relpath} metadata {key} must be a non-empty string")
    return value


def require_string_list(metadata: Metadata, key: str, relpath: str) -> List[str]:
    value = metadata.get(key)
    if not isinstance(value, list):
        raise AssertionError(f"{relpath} metadata {key} must be a list")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            raise AssertionError(
                f"{relpath} metadata {key}[{index}] must be a non-empty string"
            )
    return value


def registry_facts() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[str]], set[str]]:
    data = load_json(REGISTRY)
    rules = data.get("rules")
    if not isinstance(rules, list):
        raise AssertionError("framework/rule-registry.json must contain rules")

    rules_by_id: Dict[str, Dict[str, Any]] = {}
    rules_by_source: Dict[str, List[str]] = {}
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise AssertionError(f"rules[{index}] must be an object")
        rule_id = rule.get("id")
        source = rule.get("canonical_source")
        if not isinstance(rule_id, str) or not rule_id:
            raise AssertionError(f"rules[{index}] missing id")
        if not isinstance(source, str) or not source:
            raise AssertionError(f"{rule_id} missing canonical_source")
        rules_by_id[rule_id] = rule
        rules_by_source.setdefault(source, []).append(rule_id)

    category_owners = data.get("category_owners")
    if not isinstance(category_owners, list):
        raise AssertionError("framework/rule-registry.json must contain category_owners")
    category_owner_paths: set[str] = set()
    for index, owner in enumerate(category_owners):
        if not isinstance(owner, dict):
            raise AssertionError(f"category_owners[{index}] must be an object")
        owner_path = owner.get("owner")
        if not isinstance(owner_path, str) or not owner_path:
            raise AssertionError(f"category_owners[{index}] missing owner")
        category_owner_paths.add(owner_path)

    return rules_by_id, rules_by_source, category_owner_paths


def validate() -> List[str]:
    failures: List[str] = []
    try:
        rules_by_id, rules_by_source, category_owner_paths = registry_facts()
        profiles = canonical_profiles()
    except (OSError, AssertionError) as exc:
        return [str(exc)]

    required_metadata_paths = set(rules_by_source) | category_owner_paths
    seen_ids: Dict[str, str] = {}

    for path in sorted(FRAMEWORK.glob("*.md")):
        relpath = path.relative_to(ROOT).as_posix()
        try:
            metadata = parse_front_matter(path)
            if metadata is None:
                if relpath in required_metadata_paths:
                    failures.append(f"{relpath} missing alatyr_doc front matter")
                continue

            doc_id = require_string(metadata, "id", relpath)
            doc_type = require_string(metadata, "type", relpath)
            owns_rules = require_string_list(metadata, "owns_rules", relpath)
            depends_on = require_string_list(metadata, "depends_on", relpath)
            applies_to = require_string_list(metadata, "applies_to", relpath)
        except AssertionError as exc:
            failures.append(str(exc))
            continue

        if doc_id in seen_ids:
            failures.append(
                f"duplicate framework metadata id {doc_id}: {seen_ids[doc_id]} and {relpath}"
            )
        seen_ids[doc_id] = relpath

        if doc_type != "framework-rule-owner":
            failures.append(f"{relpath} unsupported metadata type: {doc_type}")

        expected_owned = sorted(rules_by_source.get(relpath, []))
        if sorted(owns_rules) != expected_owned:
            failures.append(
                f"{relpath} owns_rules {sorted(owns_rules)} must match "
                f"registry canonical_source rules {expected_owned}"
            )

        for rule_id in owns_rules:
            if rule_id not in rules_by_id:
                failures.append(f"{relpath} owns unknown rule {rule_id}")
        for rule_id in depends_on:
            if rule_id not in rules_by_id:
                failures.append(f"{relpath} depends on unknown rule {rule_id}")
        for profile in applies_to:
            if profile not in profiles:
                failures.append(f"{relpath} applies_to unknown profile {profile}")

    missing_ids = sorted(path for path in required_metadata_paths if path not in seen_ids.values())
    for relpath in missing_ids:
        failures.append(f"{relpath} required metadata was not loaded")

    return failures


def main() -> int:
    failures = validate()
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: checked framework metadata for rule-owner documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
