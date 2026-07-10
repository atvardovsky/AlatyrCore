#!/usr/bin/env python3
"""Validate golden assistant-result conformance reports.

This source-repository helper checks fixture report contracts under
`conformance/golden/fixture-reports`. It is not an assistant installation test,
does not run an assistant, and does not validate real target repositories.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "conformance" / "fixtures"
SHARED = ROOT / "conformance" / "golden" / "shared-expectations.json"
REPORTS = ROOT / "conformance" / "golden" / "fixture-reports"


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


def require_string_list(data: dict[str, Any], key: str, path: Path) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise AssertionError(f"{path} must contain non-empty list {key}")
    if not all(isinstance(item, str) and item for item in value):
        raise AssertionError(f"{path} list {key} must contain strings")
    return value


def require_non_empty(data: dict[str, Any], key: str, path: Path) -> Any:
    value = data.get(key)
    if value in (None, "", [], {}):
        raise AssertionError(f"{path} missing non-empty evidence field {key}")
    return value


def require_contains(
    actual: list[str], expected: list[str], *, field: str, path: Path
) -> None:
    missing = sorted(set(expected) - set(actual))
    if missing:
        raise AssertionError(f"{path} {field} missing {missing}")


def validate_files_evidence(report: dict[str, Any], path: Path) -> None:
    value = require_non_empty(report, "files_created_preserved_or_skipped", path)
    if not isinstance(value, dict):
        raise AssertionError(f"{path} files_created_preserved_or_skipped must be object")
    for key in ["created", "preserved", "skipped"]:
        items = value.get(key)
        if not isinstance(items, list):
            raise AssertionError(
                f"{path} files_created_preserved_or_skipped.{key} must be a list"
            )


def validate_validation_status(report: dict[str, Any], path: Path) -> None:
    value = require_non_empty(report, "validation_status", path)
    if not isinstance(value, dict):
        raise AssertionError(f"{path} validation_status must be object")
    if value.get("target_validation_claimed") is not False:
        raise AssertionError(
            f"{path} must not claim target validation for source fixtures"
        )
    unresolved = value.get("unresolved")
    if not isinstance(unresolved, list) or not unresolved:
        raise AssertionError(f"{path} validation_status.unresolved must be non-empty")


def validate_report(
    fixture_dir: Path,
    shared: dict[str, Any],
    report_path: Path,
    *,
    expected_report_kind: str,
    actual_run: bool = False,
) -> None:
    fixture = load_json(fixture_dir / "fixture.json")
    expected = load_json(fixture_dir / "expected.json")
    report = load_json(report_path)

    if report.get("schema_version") != 1:
        raise AssertionError(f"{report_path} schema_version must be 1")
    if report.get("fixture") != fixture_dir.name:
        raise AssertionError(f"{report_path} fixture must be {fixture_dir.name}")
    if report.get("report_kind") != expected_report_kind:
        raise AssertionError(
            f"{report_path} report_kind must be {expected_report_kind}"
        )
    scope = report.get("conformance_scope")
    if not isinstance(scope, str) or "not target validation" not in scope:
        raise AssertionError(
            f"{report_path} must state it is not target validation"
        )
    if (
        not actual_run
        and "not an assistant installation test" not in scope
    ):
        raise AssertionError(
            f"{report_path} must state it is not an assistant installation test"
        )
    if report.get("claims_installation_complete") is not False:
        raise AssertionError(f"{report_path} must not claim installation is complete")
    if actual_run:
        for required_actual_key in ["run_id", "assistant_surface", "source_commit"]:
            require_non_empty(report, required_actual_key, report_path)

    shared_required = require_string_list(shared, "required_evidence", SHARED)
    fixture_required = require_string_list(expected, "required_evidence", fixture_dir / "expected.json")
    for evidence_key in sorted(set(shared_required) | set(fixture_required)):
        require_non_empty(report, evidence_key, report_path)

    validate_files_evidence(report, report_path)
    validate_validation_status(report, report_path)

    target_shape = require_string_list(expected, "target_shape", fixture_dir / "expected.json")
    target_shape_confirmed = require_string_list(
        report, "target_shape_confirmed", report_path
    )
    require_contains(
        target_shape_confirmed,
        target_shape,
        field="target_shape_confirmed",
        path=report_path,
    )

    source_surfaces = require_string_list(fixture, "source_surfaces", fixture_dir / "fixture.json")
    inspected = require_string_list(report, "target_facts_inspected", report_path)
    require_contains(
        inspected,
        source_surfaces,
        field="target_facts_inspected",
        path=report_path,
    )

    expected_behaviors = require_string_list(
        expected, "expected_behaviors", fixture_dir / "expected.json"
    )
    behaviors = require_string_list(report, "behaviors_satisfied", report_path)
    require_contains(
        behaviors,
        expected_behaviors,
        field="behaviors_satisfied",
        path=report_path,
    )

    expected_profiles = require_string_list(fixture, "expected_profiles", fixture_dir / "fixture.json")
    profiles = require_string_list(report, "context_profiles_considered", report_path)
    require_contains(
        profiles,
        expected_profiles,
        field="context_profiles_considered",
        path=report_path,
    )

    expected_module_states = require_string_list(
        fixture, "expected_module_states", fixture_dir / "fixture.json"
    )
    module_states = require_string_list(report, "module_profile_status", report_path)
    require_contains(
        module_states,
        expected_module_states,
        field="module_profile_status",
        path=report_path,
    )

    missing_surfaces = require_string_list(fixture, "missing_surfaces", fixture_dir / "fixture.json")
    residual_risk = require_string_list(report, "residual_risk", report_path)
    require_contains(
        residual_risk,
        missing_surfaces,
        field="residual_risk",
        path=report_path,
    )

    forbidden_claims = require_string_list(shared, "forbidden_claims", SHARED)
    forbidden_absent = require_string_list(
        report, "forbidden_claims_absent", report_path
    )
    require_contains(
        forbidden_absent,
        forbidden_claims,
        field="forbidden_claims_absent",
        path=report_path,
    )


def validate_golden_reports(shared: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    fixture_dirs = sorted(path for path in FIXTURES.iterdir() if path.is_dir())
    for fixture_dir in fixture_dirs:
        report_path = REPORTS / f"{fixture_dir.name}.json"
        try:
            validate_report(
                fixture_dir,
                shared,
                report_path,
                expected_report_kind="assistant-result-conformance",
            )
        except AssertionError as exc:
            failures.append(str(exc))

    report_names = {path.stem for path in REPORTS.glob("*.json")}
    fixture_names = {path.name for path in fixture_dirs}
    extra_reports = sorted(report_names - fixture_names)
    if extra_reports:
        failures.append(f"unexpected fixture report(s): {extra_reports}")
    return failures


def validate_actual_reports(
    actual_dir: Path,
    shared: dict[str, Any],
    *,
    require_reports: bool,
    require_all_fixtures: bool,
) -> list[str]:
    failures: list[str] = []
    if not actual_dir.is_dir():
        return [f"actual report directory does not exist: {actual_dir}"]

    report_paths = sorted(path for path in actual_dir.glob("*.json") if path.is_file())
    if not report_paths:
        if require_reports:
            return [f"actual report directory has no JSON reports: {actual_dir}"]
        return []

    fixture_dirs = {path.name: path for path in FIXTURES.iterdir() if path.is_dir()}
    seen_fixtures: set[str] = set()
    for report_path in report_paths:
        try:
            report = load_json(report_path)
            fixture_name = report.get("fixture")
            if not isinstance(fixture_name, str) or fixture_name not in fixture_dirs:
                raise AssertionError(
                    f"{report_path} fixture must match a known fixture"
                )
            validate_report(
                fixture_dirs[fixture_name],
                shared,
                report_path,
                expected_report_kind="assistant-run-result",
                actual_run=True,
            )
            seen_fixtures.add(fixture_name)
        except AssertionError as exc:
            failures.append(str(exc))

    if require_all_fixtures:
        missing = sorted(set(fixture_dirs) - seen_fixtures)
        if missing:
            failures.append(f"actual reports missing fixture(s): {missing}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate golden conformance reports and optional actual "
            "assistant-run reports."
        )
    )
    parser.add_argument(
        "--actual-dir",
        type=Path,
        help=(
            "Directory containing actual assistant-run JSON reports to compare "
            "with fixture contracts."
        ),
    )
    parser.add_argument(
        "--require-actual-reports",
        action="store_true",
        help="Fail when --actual-dir has no JSON reports.",
    )
    parser.add_argument(
        "--require-all-fixtures",
        action="store_true",
        help="Fail when --actual-dir does not contain a valid report for every fixture.",
    )
    args = parser.parse_args()

    failures: list[str] = []
    try:
        shared = load_json(SHARED)
        failures.extend(validate_golden_reports(shared))
        if args.require_all_fixtures and args.actual_dir is None:
            failures.append("--require-all-fixtures requires --actual-dir")
        if args.actual_dir is not None:
            failures.extend(
                validate_actual_reports(
                    args.actual_dir,
                    shared,
                    require_reports=args.require_actual_reports,
                    require_all_fixtures=args.require_all_fixtures,
                )
            )
    except (OSError, AssertionError) as exc:
        failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    if args.actual_dir is None:
        print("OK: checked golden conformance reports")
    else:
        print("OK: checked golden conformance reports and actual assistant-run reports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
