#!/usr/bin/env python3
"""Validate Alatyr conformance fixture metadata.

This checks fixture contracts in the source repository. It does not run
assistant installations or validate target projects.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE = ROOT / "conformance"
FIXTURES = CONFORMANCE / "fixtures"
SHARED = CONFORMANCE / "golden" / "shared-expectations.json"


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


def require_list(data: dict[str, Any], key: str, path: Path) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise AssertionError(f"{path} must contain non-empty list {key}")
    if not all(isinstance(item, str) and item for item in value):
        raise AssertionError(f"{path} list {key} must contain strings")
    return value


def require_string_list(
    data: dict[str, Any], key: str, path: Path, *, allow_empty: bool = False
) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or (not value and not allow_empty):
        requirement = "list" if allow_empty else "non-empty list"
        raise AssertionError(f"{path} must contain {requirement} {key}")
    if not all(isinstance(item, str) and item for item in value):
        raise AssertionError(f"{path} list {key} must contain strings")
    return value


def require_seed_files(data: dict[str, Any], path: Path) -> list[dict[str, str]]:
    value = data.get("seed_files")
    if not isinstance(value, list) or not value:
        raise AssertionError(f"{path} must contain non-empty list seed_files")

    seen_paths: set[str] = set()
    seed_files: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise AssertionError(f"{path} seed_files item {index} must be an object")
        seed_path = item.get("path")
        content = item.get("content")
        if not isinstance(seed_path, str) or not seed_path:
            raise AssertionError(f"{path} seed_files item {index} missing path")
        if seed_path.startswith("/") or ".." in Path(seed_path).parts:
            raise AssertionError(f"{path} seed file path is unsafe: {seed_path}")
        if seed_path in seen_paths:
            raise AssertionError(f"{path} duplicate seed file path: {seed_path}")
        seen_paths.add(seed_path)
        if not isinstance(content, str) or not content:
            raise AssertionError(f"{path} seed file {seed_path} missing content")
        seed_files.append({"path": seed_path, "content": content})
    return seed_files


def main() -> int:
    failures: list[str] = []
    try:
        shared = load_json(SHARED)
        shared_required = set(require_list(shared, "required_evidence", SHARED))
        require_list(shared, "forbidden_claims", SHARED)
    except AssertionError as exc:
        failures.append(str(exc))
        shared_required = set()

    for fixture_dir in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        readme = fixture_dir / "README.md"
        fixture_path = fixture_dir / "fixture.json"
        expected_path = fixture_dir / "expected.json"
        if not readme.is_file():
            failures.append(f"missing fixture README: {readme}")
            continue
        try:
            fixture = load_json(fixture_path)
            if fixture.get("schema_version") != 1:
                raise AssertionError(f"{fixture_path} schema_version must be 1")
            if fixture.get("fixture") != fixture_dir.name:
                raise AssertionError(
                    f"{fixture_path} fixture must be {fixture_dir.name}"
                )
            for fixture_key in [
                "source_surfaces",
                "missing_surfaces",
                "protected_surfaces",
                "expected_profiles",
                "expected_module_states",
            ]:
                require_string_list(fixture, fixture_key, fixture_path)
            require_string_list(
                fixture, "existing_ai_surfaces", fixture_path, allow_empty=True
            )
            require_seed_files(fixture, fixture_path)

            data = load_json(expected_path)
            if data.get("schema_version") != 1:
                raise AssertionError(f"{expected_path} schema_version must be 1")
            if data.get("fixture") != fixture_dir.name:
                raise AssertionError(
                    f"{expected_path} fixture must be {fixture_dir.name}"
                )
            require_list(data, "target_shape", expected_path)
            require_list(data, "expected_behaviors", expected_path)
            evidence = set(require_list(data, "required_evidence", expected_path))
            missing_shared = sorted(shared_required - evidence)
            allowed_missing = {
                "files_created_preserved_or_skipped",
                "manifest_version_handling",
                "approval_needs",
                "bridge_capability_status",
            }
            unexpected_missing = [
                item for item in missing_shared if item not in allowed_missing
            ]
            if unexpected_missing:
                raise AssertionError(
                    f"{expected_path} missing required evidence: {unexpected_missing}"
                )
        except AssertionError as exc:
            failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: checked conformance fixture metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
