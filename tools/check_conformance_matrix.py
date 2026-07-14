#!/usr/bin/env python3
"""Validate prepared or externally executed assistant conformance matrices."""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

from check_conformance_reports import REPORTS, SHARED, load_json, validate_actual_reports
from materialize_conformance_fixtures import fixture_dirs
from prepare_conformance_matrix import canonical_surface_ids, prepare_matrix


def safe_relative_path(base: Path, value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise AssertionError(f"matrix {field} must be a non-empty relative path")
    relpath = Path(value)
    if relpath.is_absolute() or ".." in relpath.parts:
        raise AssertionError(f"matrix {field} is unsafe: {value}")
    return base / relpath


def string_list(data: dict[str, Any], field: str) -> list[str]:
    value = data.get(field)
    if not isinstance(value, list) or not value:
        raise AssertionError(f"matrix {field} must be a non-empty list")
    if not all(isinstance(item, str) and item for item in value):
        raise AssertionError(f"matrix {field} must contain strings")
    if len(value) != len(set(value)):
        raise AssertionError(f"matrix {field} must not contain duplicates")
    return value


def validate_matrix(matrix_path: Path, *, require_reports: bool) -> list[str]:
    failures: list[str] = []
    try:
        matrix = load_json(matrix_path)
        base = matrix_path.resolve().parent
        if matrix.get("schema_version") != 1:
            raise AssertionError("matrix schema_version must be 1")
        if matrix.get("matrix_kind") != "assistant-conformance-matrix-plan":
            raise AssertionError("matrix_kind must be assistant-conformance-matrix-plan")
        if matrix.get("status") != "prepared-not-executed":
            raise AssertionError("matrix status must preserve prepared-not-executed")
        if matrix.get("execution_claimed") is not False:
            raise AssertionError("prepared matrix must not claim assistant execution")

        surfaces = string_list(matrix, "surfaces")
        fixtures = string_list(matrix, "fixtures")
        unknown_surfaces = sorted(set(surfaces) - set(canonical_surface_ids()))
        if unknown_surfaces:
            raise AssertionError(f"matrix has unsupported surfaces: {unknown_surfaces}")
        known_fixtures = {path.name for path in fixture_dirs([])}
        unknown_fixtures = sorted(set(fixtures) - known_fixtures)
        if unknown_fixtures:
            raise AssertionError(f"matrix has unknown fixtures: {unknown_fixtures}")

        expected_count = len(surfaces) * len(fixtures)
        if matrix.get("expected_report_count") != expected_count:
            raise AssertionError("matrix expected_report_count does not match its dimensions")
        source_commit = matrix.get("source_commit")
        if not isinstance(source_commit, str) or not source_commit:
            raise AssertionError("matrix source_commit must be non-empty")

        runs = matrix.get("runs")
        if not isinstance(runs, list) or len(runs) != len(surfaces):
            raise AssertionError("matrix must contain one run per assistant surface")
        seen_surfaces: set[str] = set()
        shared = load_json(SHARED)
        captured_pairs: set[tuple[str, str]] = set()
        for index, run in enumerate(runs):
            if not isinstance(run, dict):
                raise AssertionError(f"matrix run {index} must be an object")
            surface = run.get("assistant_surface")
            if surface not in surfaces or surface in seen_surfaces:
                raise AssertionError(f"matrix run {index} has invalid assistant surface")
            seen_surfaces.add(surface)
            expected_run_fixtures = run.get("expected_fixtures")
            if expected_run_fixtures != fixtures:
                raise AssertionError(f"matrix run {surface} fixture scope drifted")
            if run.get("expected_report_count") != len(fixtures):
                raise AssertionError(f"matrix run {surface} report count drifted")

            workspace = safe_relative_path(base, run.get("workspace"), "workspace")
            reports_dir = safe_relative_path(
                base, run.get("reports_directory"), "reports_directory"
            )
            run_manifest = load_json(workspace / "run.json")
            for field, expected_value in [
                ("run_kind", "assistant-conformance-run-plan"),
                ("status", "prepared-not-executed"),
                ("assistant_surface", surface),
                ("run_id", run.get("run_id")),
                ("source_commit", source_commit),
                ("fixtures", fixtures),
                ("expected_report_count", len(fixtures)),
                ("execution_claimed", False),
            ]:
                if run_manifest.get(field) != expected_value:
                    raise AssertionError(
                        f"matrix run {surface} manifest field {field} drifted"
                    )
            for fixture in fixtures:
                if not (workspace / "prompts" / f"{fixture}.md").is_file():
                    raise AssertionError(
                        f"matrix run {surface} is missing prompt for {fixture}"
                    )
                if not (workspace / "targets" / fixture).is_dir():
                    raise AssertionError(
                        f"matrix run {surface} is missing target for {fixture}"
                    )

            if require_reports:
                failures.extend(
                    validate_actual_reports(
                        reports_dir,
                        shared,
                        require_reports=True,
                        require_all_fixtures=True,
                        expected_fixtures=set(fixtures),
                    )
                )
                for report_path in reports_dir.glob("*.json"):
                    report = load_json(report_path)
                    pair = (str(report.get("assistant_surface")), str(report.get("fixture")))
                    if report.get("assistant_surface") != surface:
                        failures.append(
                            f"{report_path} assistant_surface does not match matrix run"
                        )
                    if report.get("run_id") != run.get("run_id"):
                        failures.append(f"{report_path} run_id does not match matrix run")
                    if report.get("source_commit") != source_commit:
                        failures.append(
                            f"{report_path} source_commit does not match matrix"
                        )
                    if pair in captured_pairs:
                        failures.append(f"duplicate matrix report pair: {pair}")
                    captured_pairs.add(pair)

        if seen_surfaces != set(surfaces):
            raise AssertionError("matrix runs do not cover every selected surface")
        if require_reports and len(captured_pairs) != expected_count:
            failures.append(
                f"matrix captured {len(captured_pairs)} of {expected_count} expected reports"
            )
    except (OSError, ValueError, json.JSONDecodeError, AssertionError) as exc:
        failures.append(str(exc))
    return failures


def source_self_check() -> list[str]:
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "matrix"
        args = argparse.Namespace(
            output=output,
            assistant_surface=[],
            fixture=[],
            matrix_id="source-contract-matrix",
            source_commit="source-contract",
            overwrite=False,
        )
        with redirect_stdout(io.StringIO()):
            matrix_path = prepare_matrix(args)
        failures = validate_matrix(matrix_path, require_reports=False)
        matrix = load_json(matrix_path)
        expected = len(canonical_surface_ids()) * len(fixture_dirs([]))
        if matrix.get("expected_report_count") != expected:
            failures.append("source matrix does not cover every surface/fixture pair")
        for run in matrix.get("runs", []):
            surface = run["assistant_surface"]
            reports_dir = safe_relative_path(
                matrix_path.parent,
                run["reports_directory"],
                "reports_directory",
            )
            for fixture in matrix["fixtures"]:
                report = load_json(REPORTS / f"{fixture}.json")
                report.update(
                    {
                        "report_kind": "assistant-run-result",
                        "run_id": run["run_id"],
                        "assistant_surface": surface,
                        "source_commit": matrix["source_commit"],
                        "run_provenance": {
                            "provider": "synthetic",
                            "product": "matrix-source-check",
                            "model": "unknown",
                            "version_or_date": "unknown",
                            "execution_mode": "manual",
                            "started_at": "unknown",
                            "completed_at": "unknown",
                            "operator": "source-check",
                            "report_origin": "synthetic-source-contract",
                        },
                        "conformance_scope": (
                            "Synthetic matrix contract; not target validation."
                        ),
                        "bridge_behavior_evidence": {
                            "entry_files_used": ["AGENTS.md"],
                            "auto_load_observed": "unknown; synthetic source contract",
                            "help_found": "yes; required by source contract",
                            "context_router_found": "yes; required by source contract",
                            "known_surface_limitations": [
                                "vendor behavior is not exercised"
                            ],
                        },
                        "context_cost_evidence": {
                            "measurement_kind": "synthetic-source-contract",
                            "loaded_files": ["AGENTS.md"],
                            "loaded_file_count": 1,
                            "approximate_words": 1,
                            "budget_exceeded": False,
                            "expansion_reasons": ["none; synthetic source contract"],
                            "receipt_reused": False,
                        },
                    }
                )
                (reports_dir / f"{fixture}.json").write_text(
                    json.dumps(report, indent=2) + "\n",
                    encoding="utf-8",
                )
        failures.extend(validate_matrix(matrix_path, require_reports=True))

        first_run = matrix["runs"][0]
        missing_report = safe_relative_path(
            matrix_path.parent,
            first_run["reports_directory"],
            "reports_directory",
        ) / f"{matrix['fixtures'][0]}.json"
        missing_report.unlink()
        if not validate_matrix(matrix_path, require_reports=True):
            failures.append("matrix completeness must fail when one report is missing")
        return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a prepared or externally executed conformance matrix."
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        help="Path to matrix.json. Omit to run the source-tool self-check.",
    )
    parser.add_argument(
        "--require-reports",
        action="store_true",
        help="Require valid actual reports for every matrix pair.",
    )
    args = parser.parse_args()
    if args.require_reports and args.matrix is None:
        print("FAIL: --require-reports requires --matrix", file=sys.stderr)
        return 1

    failures = (
        validate_matrix(args.matrix, require_reports=args.require_reports)
        if args.matrix
        else source_self_check()
    )
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    scope = "captured reports" if args.require_reports else "prepared matrix contracts"
    print(f"OK: checked conformance {scope}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
