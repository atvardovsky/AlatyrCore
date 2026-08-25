#!/usr/bin/env python3
"""Validate Alatyr rule category ownership metadata.

This validates the AlatyrCore source repository only. It is not a portable
framework requirement for target projects.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "framework" / "rule-registry.json"
REGISTRY_DOC = ROOT / "framework" / "rule-registry.md"
OWNERSHIP_DOC = ROOT / "framework" / "rule-ownership.md"


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssertionError(f"missing {path}") from exc
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return data


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise AssertionError(f"{field} must be a non-empty string")
    return value


def require_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise AssertionError(f"{field} must be a non-empty list")
    strings: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            raise AssertionError(f"{field}[{index}] must be a non-empty string")
        strings.append(item)
    return strings


def validate() -> list[str]:
    failures: list[str] = []
    try:
        data = load_json(REGISTRY)
        registry_text = REGISTRY_DOC.read_text(encoding="utf-8")
        ownership_text = OWNERSHIP_DOC.read_text(encoding="utf-8")
    except (OSError, AssertionError) as exc:
        return [str(exc)]

    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        return ["framework/rule-registry.json must contain rules"]

    rule_categories: dict[str, str] = {}
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            failures.append(f"rules[{index}] must be an object")
            continue
        try:
            rule_id = require_string(rule.get("id"), f"rules[{index}].id")
            category = require_string(rule.get("category"), f"{rule_id}.category")
            canonical_source = require_string(
                rule.get("canonical_source"), f"{rule_id}.canonical_source"
            )
        except AssertionError as exc:
            failures.append(str(exc))
            continue
        if rule_id in rule_categories:
            failures.append(f"duplicate rule id: {rule_id}")
        rule_categories[rule_id] = category
        if not (ROOT / canonical_source).is_file():
            failures.append(
                f"{rule_id} canonical source does not exist: {canonical_source}"
            )
        registry_mapping = (
            f"Rule ID: `{rule_id}`\n"
            f"Source owner: `{canonical_source}`\n"
            f"Installed owner: `.ai/{canonical_source}`"
        )
        if registry_mapping not in registry_text:
            failures.append(
                "framework/rule-registry.md missing source/installed owner mapping "
                f"for {rule_id}: {canonical_source} -> .ai/{canonical_source}"
            )
        ownership_mapping = (
            f"Rule: `{rule_id}`\n"
            f"Source canonical owner: `{canonical_source}`\n"
            f"Installed canonical owner: `.ai/{canonical_source}`"
        )
        if ownership_mapping not in ownership_text:
            failures.append(
                "framework/rule-ownership.md missing source/installed canonical "
                f"owner mapping for {rule_id}: {canonical_source} -> "
                f".ai/{canonical_source}"
            )

    category_owners = data.get("category_owners")
    if not isinstance(category_owners, list) or not category_owners:
        return ["framework/rule-registry.json must contain category_owners"]

    seen_categories: set[str] = set()
    owned_rule_ids: set[str] = set()
    for index, owner in enumerate(category_owners):
        if not isinstance(owner, dict):
            failures.append(f"category_owners[{index}] must be an object")
            continue
        try:
            category = require_string(owner.get("category"), f"category_owners[{index}].category")
            owner_path = require_string(owner.get("owner"), f"{category}.owner")
            rule_ids = require_string_list(owner.get("rule_ids"), f"{category}.rule_ids")
            require_string_list(owner.get("derived_surfaces"), f"{category}.derived_surfaces")
        except AssertionError as exc:
            failures.append(str(exc))
            continue

        if category in seen_categories:
            failures.append(f"duplicate category owner: {category}")
        seen_categories.add(category)

        if not (ROOT / owner_path).is_file():
            failures.append(f"{category} owner path does not exist: {owner_path}")

        if f"Category: `{category}`" not in ownership_text:
            failures.append(f"framework/rule-ownership.md missing category {category}")
        routing_mapping = (
            f"Category: `{category}`\n"
            f"Source routing owner: `{owner_path}`\n"
            f"Installed routing owner: `.ai/{owner_path}`"
        )
        if routing_mapping not in ownership_text:
            failures.append(
                "framework/rule-ownership.md missing source/installed category "
                f"routing owner for {category}: {owner_path} -> .ai/{owner_path}"
            )

        for rule_id in rule_ids:
            if rule_id not in rule_categories:
                failures.append(f"{category} references unknown rule id {rule_id}")
                continue
            if rule_categories[rule_id] != category:
                failures.append(
                    f"{category} references {rule_id}, but registry category is "
                    f"{rule_categories[rule_id]}"
                )
            if rule_id in owned_rule_ids:
                failures.append(f"rule id owned more than once: {rule_id}")
            owned_rule_ids.add(rule_id)
            if rule_id not in ownership_text:
                failures.append(f"framework/rule-ownership.md missing {rule_id}")

    missing_categories = sorted(set(rule_categories.values()) - seen_categories)
    if missing_categories:
        failures.append(f"category_owners missing categories: {missing_categories}")

    missing_rules = sorted(set(rule_categories) - owned_rule_ids)
    if missing_rules:
        failures.append(f"category_owners missing rule ids: {missing_rules}")

    return failures


def main() -> int:
    failures = validate()
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: checked category routing and canonical rule ownership")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
