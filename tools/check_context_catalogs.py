#!/usr/bin/env python3
"""Validate recursive context catalogs and semantic-codebook coverage."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from context_catalog import ContextCatalogError, load_codebook, validate_context_catalog
from render_context_catalogs import INDEX_NAME, framework_base_files


ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK = ROOT / "framework"
TARGET = ROOT / "templates" / "target"
CODEBOOK = FRAMEWORK / "semantics" / "index.json"
CONTEXT_OWNER = FRAMEWORK / "context-profiles.md"
REQUIRED_PRELOAD_TERMS = {
    "alatyr:current-scope-authorization@1",
    "alatyr:canonical-owner@1",
    "alatyr:protected-change@1",
    "alatyr:logical-integrity@1",
    "alatyr:bounded-context-expansion@1",
}


def _target_files(root: Path, *, exclude: set[str] | None = None) -> set[str]:
    excluded = exclude or set()
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.name not in {INDEX_NAME, ".gitignore"}
        and path.relative_to(root).as_posix() not in excluded
    }


def main() -> int:
    failures: list[str] = []
    resolutions = {}
    catalogs = {
        "framework": (FRAMEWORK / INDEX_NAME, FRAMEWORK, framework_base_files()),
        "project": (
            TARGET / ".ai" / "project" / INDEX_NAME,
            TARGET / ".ai" / "project",
            _target_files(TARGET / ".ai" / "project"),
        ),
        "assistant": (
            TARGET / ".ai" / "assistant" / INDEX_NAME,
            TARGET / ".ai" / "assistant",
            _target_files(
                TARGET / ".ai" / "assistant",
                exclude={"bootstrap-index.json"},
            ),
        ),
    }
    for contour, (index, root, expected_paths) in catalogs.items():
        try:
            resolution = validate_context_catalog(index, catalog_root=root)
            resolutions[contour] = resolution
        except ContextCatalogError as exc:
            failures.append(f"{contour} context catalog: {exc}")
            continue
        indexed_paths = {item.path for item in resolution.items}
        missing = sorted(expected_paths - indexed_paths)
        extra = sorted(indexed_paths - expected_paths)
        if missing:
            failures.append(f"{contour} context catalog misses files: {missing}")
        if extra:
            failures.append(f"{contour} context catalog has extra files: {extra}")

    framework_resolution = resolutions.get("framework")
    if framework_resolution is not None and any(
        item.path == "file-inventory.json" for item in framework_resolution.items
    ):
        failures.append(
            "framework file inventory must stay outside its recursive digest catalog"
        )
    try:
        context_owner = CONTEXT_OWNER.read_text(encoding="utf-8")
    except OSError as exc:
        failures.append(f"framework inventory context exception: {exc}")
    else:
        for marker in [
            "`framework/file-inventory.json`",
            "circular digest dependency",
            "packaging and upgrade",
        ]:
            if marker not in context_owner:
                failures.append(
                    "framework context owner does not explain the file-inventory "
                    f"routing exception: {marker}"
                )

    requested_terms = {
        term_id
        for resolution in resolutions.values()
        for item in resolution.items
        for term_id in item.semantic_refs
    }
    try:
        resolved_terms = load_codebook(
            CODEBOOK,
            root=CODEBOOK.parent,
            required_terms=requested_terms,
        )
    except ContextCatalogError as exc:
        failures.append(f"semantic codebook: {exc}")
        resolved_terms = {}
    missing_preload = sorted(REQUIRED_PRELOAD_TERMS - set(resolved_terms))
    if missing_preload:
        failures.append(f"semantic codebook misses required preload terms: {missing_preload}")

    try:
        index = json.loads(CODEBOOK.read_text(encoding="utf-8"))
        preload_ids = {
            term_id
            for shard in index.get("shards", [])
            if isinstance(shard, dict) and shard.get("preload") is True
            for term_id in shard.get("term_ids", [])
        }
        if preload_ids != REQUIRED_PRELOAD_TERMS:
            failures.append(
                "semantic codebook preload set must contain only the required core terms"
            )
        preload_words = sum(
            len(resolved_terms[term_id]["definition"].split())
            for term_id in preload_ids
            if term_id in resolved_terms
        )
        if preload_words > 300:
            failures.append(
                f"semantic codebook preload uses {preload_words} words and exceeds 300"
            )
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        failures.append(f"semantic codebook preload: {exc}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: recursive context catalogs and semantic codebook agree; "
        + " ".join(
            f"{contour}={len(resolution.items)}"
            for contour, resolution in resolutions.items()
        )
        + f" terms={len(resolved_terms)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
