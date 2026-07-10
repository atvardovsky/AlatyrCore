#!/usr/bin/env python3
"""Prepare fixture targets and prompts for an assistant conformance run.

This source-repository helper creates seed-only fixture repositories plus
per-fixture prompt files. It does not run an assistant, scaffold Alatyr,
install an adapter, or validate a target project.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from materialize_conformance_fixtures import (
    FIXTURES,
    fixture_dirs,
    load_json,
    materialize_fixture,
)


ROOT = Path(__file__).resolve().parents[1]
SURFACES = ROOT / "conformance" / "runs" / "assistant-surfaces.json"


def default_source_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    commit = result.stdout.strip()
    return commit or "unknown"


def safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value)


def assistant_surface_ids() -> dict[str, str]:
    data = load_json(SURFACES)
    surfaces = data.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        raise ValueError(f"{SURFACES} must contain non-empty surfaces")

    result: dict[str, str] = {}
    for surface in surfaces:
        if not isinstance(surface, dict):
            raise ValueError(f"{SURFACES} surface entries must be objects")
        surface_id = surface.get("id")
        aliases = surface.get("aliases", [])
        if not isinstance(surface_id, str) or not surface_id:
            raise ValueError(f"{SURFACES} surface missing id")
        if not isinstance(aliases, list):
            raise ValueError(f"{SURFACES} aliases for {surface_id} must be list")
        result[surface_id] = surface_id
        for alias in aliases:
            if not isinstance(alias, str) or not alias:
                raise ValueError(f"{SURFACES} alias for {surface_id} must be string")
            result[alias] = surface_id
    return result


def resolve_assistant_surface(value: str, *, allow_custom: bool) -> str:
    surfaces = assistant_surface_ids()
    if value in surfaces:
        return surfaces[value]
    if allow_custom:
        return value
    allowed = ", ".join(sorted(set(surfaces.values())))
    raise ValueError(
        f"unknown assistant surface: {value}; expected one of {allowed}, "
        "or use --allow-custom-surface"
    )


def render_list(items: list[str]) -> str:
    return "\n".join(f"- `{item}`" for item in items)


def render_prompt(
    *,
    fixture: dict[str, Any],
    expected: dict[str, Any],
    target_path: Path,
    report_path: Path,
    run_id: str,
    assistant_surface: str,
    source_commit: str,
) -> str:
    fixture_name = fixture["fixture"]
    return f"""# Alatyr Conformance Run: {fixture_name}

You are running a conformance fixture for Alatyr Core.

This is a controlled fixture run, not a real target installation and not
target validation. Do not copy facts from the fixture name into the target
adapter. Do not invent validation commands.

## Inputs

- Alatyr Core source repository: `{ROOT}`
- Fixture target repository: `{target_path}`
- Report path to write: `{report_path}`
- Run id: `{run_id}`
- Assistant surface: `{assistant_surface}`
- Source commit: `{source_commit}`

## Task

Use the Alatyr Core source repository as installation guidance and inspect the
fixture target repository. Produce an assistant-run conformance report at the
report path above.

You may create or update files inside the fixture target repository if your
assistant-run procedure is meant to test installation behavior, but the final
report must not claim that a real target adapter is complete. Treat unresolved
fixture facts as unresolved.

## Expected Target Shape

{render_list(expected["target_shape"])}

## Source Surfaces To Inspect

{render_list(fixture["source_surfaces"])}

## Missing Surfaces To Preserve As Gaps

{render_list(fixture["missing_surfaces"])}

## Expected Profiles To Consider

{render_list(fixture["expected_profiles"])}

## Expected Module States

{render_list(fixture["expected_module_states"])}

## Expected Behaviors

{render_list(expected["expected_behaviors"])}

## Required Evidence Keys

{render_list(expected["required_evidence"])}

## Report Requirements

Write valid JSON to `{report_path}` with:

- `schema_version`: `1`
- `fixture`: `{fixture_name}`
- `report_kind`: `assistant-run-result`
- `run_id`: `{run_id}`
- `assistant_surface`: `{assistant_surface}`
- `source_commit`: `{source_commit}`
- `conformance_scope`: include `not target validation`
- `claims_installation_complete`: `false`
- `validation_status.target_validation_claimed`: `false`
- all expected behavior IDs in `behaviors_satisfied`
- all forbidden claim IDs in `forbidden_claims_absent`

Use `conformance/runs/assistant-run-report-template.json` as the field shape.
After writing the report, it should pass:

```sh
python3 tools/check_conformance_reports.py --actual-dir {report_path.parent} --require-actual-reports
```
"""


def write_run_readme(
    output: Path,
    *,
    run_id: str,
    assistant_surface: str,
    source_commit: str,
) -> None:
    readme = f"""# Alatyr Assistant Conformance Run

Run id: `{run_id}`
Assistant surface: `{assistant_surface}`
Source commit: `{source_commit}`

## Layout

- `targets/`: seed-only fixture repositories.
- `prompts/`: per-fixture prompts to give an assistant.
- `reports/`: assistant-run JSON reports to validate.

## Workflow

1. Give each prompt under `prompts/` to the selected assistant.
2. Let the assistant inspect the matching fixture under `targets/`.
3. Require the assistant to write JSON into `reports/`.
4. Validate captured reports from the Alatyr Core source repository:

```sh
python3 tools/check_conformance_reports.py --actual-dir {output / "reports"} --require-actual-reports
```

These files are conformance-run inputs. They are not completed target
installations and do not prove real target validation.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")


def prepare_run(args: argparse.Namespace) -> list[str]:
    failures: list[str] = []
    output = args.output.resolve()
    targets = output / "targets"
    prompts = output / "prompts"
    reports = output / "reports"

    output.mkdir(parents=True, exist_ok=True)
    targets.mkdir(parents=True, exist_ok=True)
    prompts.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    assistant_surface = resolve_assistant_surface(
        args.assistant_surface,
        allow_custom=args.allow_custom_surface,
    )
    source_commit = args.source_commit or default_source_commit()
    run_id = args.run_id or f"manual-{safe_name(assistant_surface)}-{source_commit}"

    write_run_readme(
        output,
        run_id=run_id,
        assistant_surface=assistant_surface,
        source_commit=source_commit,
    )
    (reports / "README.md").write_text(
        "# Assistant Reports\n\nWrite assistant-run JSON reports here.\n",
        encoding="utf-8",
    )

    for fixture_dir in fixture_dirs(args.fixture):
        try:
            fixture = load_json(fixture_dir / "fixture.json")
            expected = load_json(fixture_dir / "expected.json")
            fixture_name, seed_files = materialize_fixture(
                fixture_dir,
                targets,
                overwrite=args.overwrite,
            )
            prompt_path = prompts / f"{fixture_name}.md"
            if prompt_path.exists() and not args.overwrite:
                raise ValueError(
                    f"prompt already exists: {prompt_path}; use --overwrite"
                )
            prompt_path.write_text(
                render_prompt(
                    fixture=fixture,
                    expected=expected,
                    target_path=targets / fixture_name,
                    report_path=reports / f"{fixture_name}.json",
                    run_id=run_id,
                    assistant_surface=assistant_surface,
                    source_commit=source_commit,
                ),
                encoding="utf-8",
            )
            print(
                f"OK: prepared {fixture_name} with {len(seed_files)} seed files "
                f"and prompt {prompt_path}"
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failures.append(str(exc))

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare fixture targets and prompts for assistant conformance."
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory where run targets, prompts, and reports will be created.",
    )
    parser.add_argument(
        "--assistant-surface",
        required=True,
        help=(
            "Assistant surface id from conformance/runs/assistant-surfaces.json, "
            "such as codex, claude, cursor, or github-copilot."
        ),
    )
    parser.add_argument(
        "--allow-custom-surface",
        action="store_true",
        help="Allow an assistant surface not listed in assistant-surfaces.json.",
    )
    parser.add_argument(
        "--run-id",
        help="Stable run identifier. Defaults to assistant surface plus source commit.",
    )
    parser.add_argument(
        "--source-commit",
        help="Source commit or baseline identifier. Defaults to current git HEAD.",
    )
    parser.add_argument(
        "--fixture",
        action="append",
        default=[],
        help="Fixture name to prepare. May be provided more than once.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing fixture target directories and prompt files.",
    )
    args = parser.parse_args()

    try:
        failures = prepare_run(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures = [str(exc)]
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(f"OK: conformance run prepared under {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
