#!/usr/bin/env python3
"""Render the deterministic Alatyr framework file inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK = ROOT / "framework"
OUTPUT = FRAMEWORK / "file-inventory.json"
REGISTRY = FRAMEWORK / "rule-registry.json"


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return data


def build_inventory() -> dict[str, Any]:
    registry = load_object(REGISTRY)
    rules_by_source: dict[str, list[str]] = {}
    for rule in registry.get("rules", []):
        if not isinstance(rule, dict):
            continue
        source = rule.get("canonical_source")
        rule_id = rule.get("id")
        if isinstance(source, str) and isinstance(rule_id, str):
            rules_by_source.setdefault(source, []).append(rule_id)

    files: list[dict[str, Any]] = []
    for path in sorted(FRAMEWORK.rglob("*")):
        if not path.is_file() or path == OUTPUT or path.suffix not in {".md", ".json"}:
            continue
        relpath = path.relative_to(ROOT).as_posix()
        files.append(
            {
                "path": relpath,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "rule_ids": sorted(rules_by_source.get(relpath, [])),
            }
        )
    return {
        "schema_version": 1,
        "inventory_kind": "alatyr-framework-files",
        "framework_version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "adapter_schema_version": int(
            (ROOT / "ADAPTER_SCHEMA_VERSION").read_text(encoding="utf-8").strip()
        ),
        "template_version": int(
            (ROOT / "TEMPLATE_VERSION").read_text(encoding="utf-8").strip()
        ),
        "files": files,
    }


def render() -> str:
    return json.dumps(build_inventory(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    expected = render()
    output = args.output.resolve()
    if args.check:
        try:
            actual = output.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        if actual != expected:
            print(
                f"FAIL: {output.relative_to(ROOT)} is stale; rerun renderer",
                file=sys.stderr,
            )
            return 1
        print(f"OK: checked {output.relative_to(ROOT)}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(expected, encoding="utf-8")
    print(f"WROTE: {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
