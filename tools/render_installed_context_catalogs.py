#!/usr/bin/env python3
"""Check or regenerate recursive context catalogs in one installed adapter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from context_catalog import ContextCatalogError, load_codebook, validate_context_catalog
from render_context_catalogs import (
    INDEX_NAME,
    build_directory_catalog_contents,
    build_framework_catalog_contents,
    framework_base_files,
)


def expected_outputs(target: Path) -> dict[Path, str]:
    framework = target / ".ai" / "framework"
    project = target / ".ai" / "project"
    assistant = target / ".ai" / "assistant"
    for required in [framework, project, assistant]:
        if not required.is_dir():
            raise ValueError(f"installed contour is missing: {required}")
    outputs = {
        framework / relpath: text
        for relpath, text in build_framework_catalog_contents(
            selected_files=framework_base_files(framework), root=framework
        ).items()
    }
    for root, contour in [(project, "project"), (assistant, "assistant")]:
        outputs.update(
            {
                root / relpath: text
                for relpath, text in build_directory_catalog_contents(
                    root, contour
                ).items()
            }
        )
    return outputs


def generated_paths(target: Path) -> set[Path]:
    framework = target / ".ai" / "framework"
    return {
        framework / INDEX_NAME,
        *framework.glob(f"catalog/**/{INDEX_NAME}"),
        *(target / ".ai" / "project").glob(f"**/{INDEX_NAME}"),
        *(target / ".ai" / "assistant").glob(f"**/{INDEX_NAME}"),
    }


def validate_written(target: Path) -> None:
    for contour in ["framework", "project", "assistant"]:
        root = target / ".ai" / contour
        validate_context_catalog(root / INDEX_NAME, catalog_root=root)
    codebook = target / ".ai" / "framework" / "semantics" / "index.json"
    load_codebook(codebook, root=codebook.parent)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate adapter-owned catalog files; otherwise check only.",
    )
    args = parser.parse_args()
    target = args.target.resolve()
    try:
        expected = expected_outputs(target)
    except (OSError, UnicodeError, ValueError, ContextCatalogError) as exc:
        print(f"FAIL: cannot derive installed context catalogs: {exc}", file=sys.stderr)
        return 1

    stale = sorted(generated_paths(target) - set(expected))
    mismatched = [
        path
        for path, text in sorted(expected.items())
        if not path.is_file() or path.read_text(encoding="utf-8") != text
    ]
    if args.write:
        for path in stale:
            path.unlink()
        for path, text in expected.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))
        try:
            validate_written(target)
        except (OSError, UnicodeError, ValueError, ContextCatalogError) as exc:
            print(f"FAIL: generated catalogs are invalid: {exc}", file=sys.stderr)
            return 1
        print(
            f"Wrote {len(expected)} installed context indexes; removed {len(stale)} stale indexes"
        )
        return 0

    if mismatched or stale:
        for path in mismatched:
            print(f"FAIL: missing or stale {path.relative_to(target)}", file=sys.stderr)
        for path in stale:
            print(f"FAIL: unexpected {path.relative_to(target)}", file=sys.stderr)
        print(
            "Repair with explicit adapter-write authorization: "
            f"render_installed_context_catalogs.py --target {target} --write",
            file=sys.stderr,
        )
        return 1
    try:
        validate_written(target)
    except (OSError, UnicodeError, ValueError, ContextCatalogError) as exc:
        print(f"FAIL: installed catalogs are invalid: {exc}", file=sys.stderr)
        return 1
    print(f"OK: checked {len(expected)} installed context indexes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
