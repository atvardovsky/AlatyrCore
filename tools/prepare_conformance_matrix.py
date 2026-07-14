#!/usr/bin/env python3
"""Prepare conformance workspaces for multiple assistant surfaces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from materialize_conformance_fixtures import fixture_dirs, load_json
from prepare_conformance_run import (
    SURFACES,
    default_source_commit,
    prepare_run,
    resolve_assistant_surface,
    safe_name,
)


def canonical_surface_ids() -> list[str]:
    data = load_json(SURFACES)
    surfaces = data.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        raise ValueError(f"{SURFACES} must contain non-empty surfaces")
    result: list[str] = []
    for item in surfaces:
        if not isinstance(item, dict):
            raise ValueError(f"{SURFACES} surface entries must be objects")
        surface_id = item.get("id")
        if not isinstance(surface_id, str) or not surface_id:
            raise ValueError(f"{SURFACES} surface missing id")
        result.append(surface_id)
    if len(result) != len(set(result)):
        raise ValueError(f"{SURFACES} contains duplicate surface ids")
    return result


def select_surfaces(values: list[str]) -> list[str]:
    selected = values or canonical_surface_ids()
    resolved = [
        resolve_assistant_surface(value, allow_custom=False) for value in selected
    ]
    if len(resolved) != len(set(resolved)):
        raise ValueError("assistant surfaces resolve to duplicate canonical ids")
    return resolved


def write_matrix_readme(output: Path, matrix: dict[str, Any]) -> None:
    text = f"""# Alatyr Assistant Conformance Matrix

Matrix id: `{matrix['matrix_id']}`
Source commit: `{matrix['source_commit']}`
Status: `prepared-not-executed`

This workspace contains {len(matrix['surfaces'])} assistant surface runs across
{len(matrix['fixtures'])} fixtures. Preparation does not run an assistant and
does not prove installation, target validation, or runtime cost.

Each surface workspace contains prompts, seed targets, a `run.json` plan, and
a reports directory. After external assistant execution, validate the matrix:

```sh
python3 tools/check_conformance_matrix.py --matrix {output / 'matrix.json'} --require-reports
```
"""
    (output / "README.md").write_text(text, encoding="utf-8")


def prepare_matrix(args: argparse.Namespace) -> Path:
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.overwrite:
        raise ValueError(f"matrix output is not empty: {output}; use --overwrite")
    output.mkdir(parents=True, exist_ok=True)

    surfaces = select_surfaces(args.assistant_surface)
    fixtures = [path.name for path in fixture_dirs(args.fixture)]
    source_commit = args.source_commit or default_source_commit()
    matrix_id = args.matrix_id or f"matrix-{source_commit}"
    runs: list[dict[str, Any]] = []
    failures: list[str] = []

    for surface in surfaces:
        workspace = output / "surfaces" / surface
        run_id = f"{safe_name(matrix_id)}-{safe_name(surface)}"
        run_args = argparse.Namespace(
            output=workspace,
            assistant_surface=surface,
            allow_custom_surface=False,
            run_id=run_id,
            source_commit=source_commit,
            fixture=fixtures,
            overwrite=args.overwrite,
        )
        run_failures = prepare_run(run_args)
        failures.extend(f"{surface}: {failure}" for failure in run_failures)
        runs.append(
            {
                "assistant_surface": surface,
                "run_id": run_id,
                "workspace": f"surfaces/{surface}",
                "reports_directory": f"surfaces/{surface}/reports",
                "expected_fixtures": fixtures,
                "expected_report_count": len(fixtures),
            }
        )

    if failures:
        raise ValueError("; ".join(failures))

    matrix = {
        "schema_version": 1,
        "matrix_kind": "assistant-conformance-matrix-plan",
        "status": "prepared-not-executed",
        "matrix_id": matrix_id,
        "source_commit": source_commit,
        "surfaces": surfaces,
        "fixtures": fixtures,
        "expected_report_count": len(surfaces) * len(fixtures),
        "execution_claimed": False,
        "runs": runs,
    }
    matrix_path = output / "matrix.json"
    matrix_path.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    write_matrix_readme(output, matrix)
    return matrix_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare an assistant conformance matrix without running assistants."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--assistant-surface",
        action="append",
        default=[],
        help="Canonical or aliased assistant surface. Defaults to every supported surface.",
    )
    parser.add_argument(
        "--fixture",
        action="append",
        default=[],
        help="Fixture to prepare. Defaults to every fixture.",
    )
    parser.add_argument("--matrix-id")
    parser.add_argument("--source-commit")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    try:
        matrix_path = prepare_matrix(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"OK: prepared conformance matrix at {matrix_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
