#!/usr/bin/env python3
"""Render or check the portable Alatyr semantic-codebook index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from context_catalog import file_digest, load_codebook, load_object, preload_term_ids


ROOT = Path(__file__).resolve().parents[1]
SEMANTICS = ROOT / "framework" / "semantics"
OUTPUT = SEMANTICS / "index.json"
ROUTER_PROJECTIONS = (
    ROOT / "tools" / "source_context_router.json",
    ROOT / "templates" / "target" / ".ai" / "assistant" / "context-router.json",
)


def build(semantics: Path = SEMANTICS) -> dict[str, Any]:
    output = semantics / "index.json"
    shards: list[dict[str, Any]] = []
    seen_terms: set[str] = set()
    for path in sorted(semantics.glob("*.json")):
        if path == output:
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
        owner_digests: dict[str, str] = {}
        for term in terms:
            owner = term.get("canonical_owner")
            if not isinstance(owner, str) or not owner:
                raise ValueError(f"{path.relative_to(ROOT)} has an invalid canonical owner")
            owner_path = (semantics.parent / owner).resolve()
            if owner_path.parent != semantics.parent.resolve() or not owner_path.is_file():
                raise ValueError(
                    f"{path.relative_to(ROOT)} has a missing or escaping canonical owner: {owner}"
                )
            owner_digests[term["id"]] = file_digest(owner_path)
        shards.append(
            {
                "id": data.get("shard_id"),
                "path": path.name,
                "preload": data.get("preload"),
                "selectors": data.get("selectors"),
                "term_ids": term_ids,
                "canonical_owner_digests": owner_digests,
                "content_digest": file_digest(path),
            }
        )
    return {
        "schema_version": 2,
        "index_kind": "alatyr-semantic-codebook-index",
        "codebook_id": "alatyr-core",
        "selection_mode": "explicit-references",
        "namespace_policy": {
            "framework": "alatyr:*",
            "target": "project:*",
            "override": "project terms must not redefine framework term IDs"
        },
        "fallback": "load the referenced canonical owner and do not infer an unresolved compact term",
        "shards": shards,
    }


def render(semantics: Path = SEMANTICS) -> str:
    return json.dumps(build(semantics), indent=2, ensure_ascii=True) + "\n"


def sync_router_preloads() -> int:
    preload = preload_term_ids(OUTPUT)
    changed = 0
    for path in ROUTER_PROJECTIONS:
        router = load_object(path)
        semantic = router.get("semantic_codebook")
        if not isinstance(semantic, dict):
            raise ValueError(f"{path.relative_to(ROOT)} has no semantic_codebook")
        if semantic.get("preload_terms") == preload:
            continue
        semantic["preload_terms"] = preload
        path.write_text(
            json.dumps(router, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        changed += 1
    return changed


def stale_router_preloads() -> list[Path]:
    preload = preload_term_ids(OUTPUT)
    stale: list[Path] = []
    for path in ROUTER_PROJECTIONS:
        router = load_object(path)
        semantic = router.get("semantic_codebook")
        if not isinstance(semantic, dict) or semantic.get("preload_terms") != preload:
            stale.append(path)
    return stale


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
        stale = stale_router_preloads()
        if stale:
            print(
                "FAIL: semantic preload projections are stale: "
                + ", ".join(path.relative_to(ROOT).as_posix() for path in stale),
                file=sys.stderr,
            )
            return 1
        print("OK: checked semantic codebook index and preload closure")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8")
    synced = sync_router_preloads()
    print(f"Wrote {OUTPUT.relative_to(ROOT)}; router_preloads_updated={synced}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
