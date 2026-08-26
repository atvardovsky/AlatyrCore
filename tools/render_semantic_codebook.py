#!/usr/bin/env python3
"""Render or check the portable Alatyr semantic-codebook index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from context_catalog import file_digest, load_codebook, load_object


ROOT = Path(__file__).resolve().parents[1]
SEMANTICS = ROOT / "framework" / "semantics"
OUTPUT = SEMANTICS / "index.json"


def build() -> dict[str, Any]:
    shards: list[dict[str, Any]] = []
    seen_terms: set[str] = set()
    for path in sorted(SEMANTICS.glob("*.json")):
        if path == OUTPUT:
            continue
        data = load_object(path)
        terms = data.get("terms")
        if not isinstance(terms, list):
            raise ValueError(f"{path.relative_to(ROOT)} has no terms list")
        term_ids = [term.get("id") for term in terms if isinstance(term, dict)]
        if len(term_ids) != len(terms) or not all(isinstance(term_id, str) for term_id in term_ids):
            raise ValueError(f"{path.relative_to(ROOT)} has invalid term IDs")
        duplicates = sorted(set(term_ids) & seen_terms)
        if duplicates:
            raise ValueError(f"duplicate semantic terms: {duplicates}")
        seen_terms.update(term_ids)
        shards.append(
            {
                "id": data.get("shard_id"),
                "path": path.name,
                "preload": data.get("preload"),
                "selectors": data.get("selectors"),
                "term_ids": term_ids,
                "content_digest": file_digest(path),
            }
        )
    return {
        "schema_version": 1,
        "index_kind": "alatyr-semantic-codebook-index",
        "codebook_id": "alatyr-core",
        "namespace_policy": {
            "framework": "alatyr:*",
            "target": "project:*",
            "override": "project terms must not redefine framework term IDs"
        },
        "fallback": "load the referenced canonical owner and do not infer an unresolved compact term",
        "shards": shards,
    }


def render() -> str:
    return json.dumps(build(), indent=2, ensure_ascii=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.check:
        try:
            actual = OUTPUT.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        if actual != expected:
            print("FAIL: framework/semantics/index.json is stale", file=sys.stderr)
            return 1
        try:
            load_codebook(OUTPUT, root=SEMANTICS)
        except ValueError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        print("OK: checked semantic codebook index and preload closure")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
