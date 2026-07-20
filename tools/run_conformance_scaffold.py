#!/usr/bin/env python3
"""Run scaffold conformance against generated fixture repositories.

This source-repository helper materializes temporary fixture repositories from
`conformance/fixtures/*/fixture.json` and checks that the AlatyrCore
scaffolder preserves existing files while creating placeholder adapter
structure.

It is not an assistant installation test and not a portable target validation
requirement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from scaffold_target_structure import plan as scaffold_plan


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "conformance" / "fixtures"
SNAPSHOTS = ROOT / "conformance" / "golden" / "scaffolded-adapters"
PLACEHOLDER_PATTERN = re.compile(r"\{[A-Z0-9_]+(?:_[A-Z0-9_]+)*\}")

REQUIRED_SCAFFOLD_FILES = [
    ".ai/alatyr.yaml",
    ".ai/framework/README.md",
    ".ai/framework/rule-registry.json",
    ".ai/assistant/context-profiles.md",
    ".ai/assistant/module-profile.md",
    ".ai/assistant/help.md",
    ".ai/assistant/operation-catalog.json",
    ".ai/assistant/flows/adapter-health.flow.md",
    ".ai/assistant/templates/pre-change-preview.md",
    ".ai/project/source-of-truth-registry.md",
]

PLACEHOLDER_FILES = [
    ".ai/alatyr.yaml",
    ".ai/assistant/context-profiles.md",
    ".ai/assistant/module-profile.md",
    ".ai/assistant/help.md",
    ".ai/assistant/operation-catalog.json",
    ".ai/project/source-of-truth-registry.md",
]


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def write_seed_files(repo: Path, fixture: dict[str, Any]) -> dict[Path, str]:
    seed_hashes: dict[Path, str] = {}
    for seed in fixture["seed_files"]:
        relpath = Path(seed["path"])
        if relpath.is_absolute() or ".." in relpath.parts:
            raise ValueError(f"unsafe seed path: {relpath}")
        path = repo / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(seed["content"], encoding="utf-8")
        seed_hashes[path] = digest(path)
    return seed_hashes


def assert_seed_files_preserved(seed_hashes: dict[Path, str]) -> list[str]:
    failures: list[str] = []
    for path, expected_hash in seed_hashes.items():
        if not path.is_file():
            failures.append(f"seed file removed: {path}")
        elif digest(path) != expected_hash:
            failures.append(f"seed file changed: {path}")
    return failures


def assert_required_scaffold(repo: Path) -> list[str]:
    failures: list[str] = []
    for relpath in REQUIRED_SCAFFOLD_FILES:
        if not (repo / relpath).is_file():
            failures.append(f"missing scaffold output: {repo / relpath}")
    for relpath in PLACEHOLDER_FILES:
        path = repo / relpath
        if path.is_file() and "{" not in path.read_text(encoding="utf-8"):
            failures.append(f"scaffold placeholder was resolved unexpectedly: {path}")
    return failures


def skipped_existing_paths(repo: Path, blocked: list[str]) -> list[str]:
    prefix = "exists, would not overwrite: "
    paths: list[str] = []
    for item in blocked:
        if not item.startswith(prefix):
            continue
        path = Path(item[len(prefix) :])
        try:
            paths.append(relative_path(path, repo))
        except ValueError:
            paths.append(path.as_posix())
    return sorted(paths)


def build_snapshot(
    fixture: dict[str, Any],
    repo: Path,
    actions: list[str],
    blocked: list[str],
) -> dict[str, Any]:
    seed_paths = sorted(seed["path"] for seed in fixture["seed_files"])
    all_paths = sorted(
        relative_path(path, repo) for path in repo.rglob("*") if path.is_file()
    )
    created_paths = sorted(path for path in all_paths if path not in seed_paths)
    placeholder_paths = sorted(
        path
        for path in created_paths
        if PLACEHOLDER_PATTERN.search((repo / path).read_text(encoding="utf-8"))
    )

    return {
        "schema_version": 1,
        "fixture": fixture["fixture"],
        "snapshot_kind": "scaffolded-adapter",
        "conformance_scope": (
            "Source scaffold output snapshot; not an assistant installation "
            "test and not a completed target adapter."
        ),
        "claims_installation_complete": False,
        "action_count": len(actions),
        "blocked_count": len(blocked),
        "created_paths": created_paths,
        "preserved_seed_paths": seed_paths,
        "skipped_existing_paths": skipped_existing_paths(repo, blocked),
        "placeholder_paths": placeholder_paths,
        "target_validation_claimed": False,
    }


def check_or_write_snapshot(
    snapshot: dict[str, Any],
    *,
    write_golden: bool,
) -> list[str]:
    fixture_name = snapshot["fixture"]
    path = SNAPSHOTS / f"{fixture_name}.json"
    if write_golden:
        SNAPSHOTS.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
        return []

    if not path.is_file():
        return [f"missing scaffold snapshot: {path}"]

    try:
        expected = load_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"invalid scaffold snapshot {path}: {exc}"]

    if expected != snapshot:
        return [
            f"scaffold snapshot drift for {fixture_name}: "
            f"run with --write-golden-snapshots after reviewing the change"
        ]
    return []


def run_fixture(
    fixture_dir: Path, work_root: Path
) -> tuple[str, int, int, list[str], dict[str, Any]]:
    fixture = load_json(fixture_dir / "fixture.json")
    fixture_name = fixture["fixture"]
    repo = work_root / fixture_name
    repo.mkdir(parents=True, exist_ok=False)

    seed_hashes = write_seed_files(repo, fixture)

    dry_actions, dry_blocked = scaffold_plan(
        SimpleNamespace(target=repo, write=False, overwrite_existing=False)
    )
    if not dry_actions:
        return fixture_name, 0, len(dry_blocked), ["dry-run produced no actions"], {}

    write_actions, write_blocked = scaffold_plan(
        SimpleNamespace(target=repo, write=True, overwrite_existing=False)
    )

    failures = []
    if not write_actions:
        failures.append("write mode produced no actions")
    failures.extend(assert_seed_files_preserved(seed_hashes))
    failures.extend(assert_required_scaffold(repo))

    expected_existing = {
        seed["path"]
        for seed in fixture["seed_files"]
        if seed["path"] in {"AGENTS.md", ".github/copilot-instructions.md"}
    }
    actual_existing = set(skipped_existing_paths(repo, write_blocked))
    for relpath in expected_existing:
        if relpath not in actual_existing:
            failures.append(f"expected existing protected surface to be skipped: {relpath}")

    snapshot = build_snapshot(fixture, repo, write_actions, write_blocked)
    return fixture_name, len(write_actions), len(write_blocked), failures, snapshot


def fixture_dirs(selected: list[str]) -> list[Path]:
    dirs = sorted(path for path in FIXTURES.iterdir() if path.is_dir())
    if not selected:
        return dirs
    selected_set = set(selected)
    result = [path for path in dirs if path.name in selected_set]
    missing = sorted(selected_set - {path.name for path in result})
    if missing:
        raise ValueError(f"unknown fixture(s): {', '.join(missing)}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run source scaffold conformance against generated fixtures."
    )
    parser.add_argument(
        "--fixture",
        action="append",
        default=[],
        help="Fixture name to run. May be provided more than once.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep the temporary generated fixture repositories.",
    )
    parser.add_argument(
        "--write-golden-snapshots",
        action="store_true",
        help="Refresh golden scaffolded-adapter snapshots after review.",
    )
    args = parser.parse_args()

    work_root = Path(tempfile.mkdtemp(prefix="alatyr-conformance-")).resolve()
    failures: list[str] = []

    try:
        for fixture_dir in fixture_dirs(args.fixture):
            name, actions, blocked, fixture_failures, snapshot = run_fixture(
                fixture_dir, work_root
            )
            if not fixture_failures:
                fixture_failures.extend(
                    check_or_write_snapshot(
                        snapshot, write_golden=args.write_golden_snapshots
                    )
                )
            if fixture_failures:
                failures.extend(f"{name}: {failure}" for failure in fixture_failures)
            else:
                snapshot_note = (
                    "snapshot refreshed"
                    if args.write_golden_snapshots
                    else "snapshot matched"
                )
                print(
                    f"OK: {name} scaffolded with {actions} actions and "
                    f"{blocked} preserved/skipped files; {snapshot_note}"
                )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))
    finally:
        if args.keep_temp:
            print(f"Kept temporary fixtures: {work_root}")
        else:
            shutil.rmtree(work_root, ignore_errors=True)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("OK: scaffold conformance fixtures passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
