#!/usr/bin/env python3
"""Converge installed generated support and run canonical target validation."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from target_tool_compat import assert_write_compatible


TOOLS = Path(__file__).resolve().parent
SOURCE_ROOT = TOOLS.parent
FIXED_GENERATED_PATHS = {
    Path(".ai/assistant/approvals/archive-index.json"),
    Path(".ai/assistant/change-packages/index.json"),
    Path(".ai/assistant/entry-packet.json"),
    Path(".ai/assistant/bootstrap-index.json"),
    Path(".ai/assistant/bootstrap-integrity.json"),
    Path(".ai/support-state.json"),
}


@dataclass(frozen=True)
class Step:
    step_id: str
    script: str
    arguments: tuple[str, ...]


def _tool_step(step_id: str, script: str, target: Path, *arguments: str) -> Step:
    return Step(step_id, script, ("--target", str(target), *arguments))


def build_steps(
    *,
    target: Path,
    write: bool,
    migration_staging: bool,
    diff_ref: str | None,
    approval_records: Iterable[Path],
    change_packages: Iterable[Path],
    require_current_change: bool = False,
) -> list[Step]:
    approval_records = tuple(approval_records)
    packages = tuple(change_packages)
    mode = ("--write",) if write else ()
    staging = ("--migration-staging",) if migration_staging else ()
    steps = [
        _tool_step("approval-archive", "render_approval_archive_index.py", target, *mode, *staging),
    ]
    if (
        target / ".ai/assistant/change-packages/index.json"
    ).is_file() or packages:
        steps.append(
            _tool_step(
                "package-index",
                "render_change_package_index.py",
                target,
                *mode,
                *staging,
            )
        )
    steps.append(
        _tool_step("entry-packet", "render_target_entry_packet.py", target, *mode, *staging)
    )
    if write:
        # Bootstrap and context catalogs form a bounded two-pass projection cycle:
        # the sidecar binds catalog roots and the assistant catalog binds the sidecar.
        steps.extend(
            [
                _tool_step("bootstrap-pass-1", "render_target_bootstrap_index.py", target, *mode, *staging),
                _tool_step("context-pass-1", "render_installed_context_catalogs.py", target, *mode, *staging),
                _tool_step("bootstrap-pass-2", "render_target_bootstrap_index.py", target, *mode, *staging),
                _tool_step("context-pass-2", "render_installed_context_catalogs.py", target, *mode, *staging),
            ]
        )
    else:
        steps.extend(
            [
                _tool_step("context-catalogs", "render_installed_context_catalogs.py", target),
                _tool_step("bootstrap", "render_target_bootstrap_index.py", target, "--check"),
            ]
        )
    steps.append(
        _tool_step("support-state", "snapshot_target_support.py", target, *mode, *staging)
    )

    validator_arguments = [
        "--target",
        str(target),
        "--framework-source",
        str(SOURCE_ROOT),
        "--validation-phase",
        "migration-staging" if migration_staging else "acceptance",
        "--validation-scope",
        "full",
        "--approval-archive-mode",
        "full",
    ]
    if diff_ref:
        validator_arguments.extend(["--diff-ref", diff_ref])
    for record in approval_records:
        validator_arguments.extend(["--approval-record", str(record)])
    for package in packages:
        validator_arguments.extend(["--change-package", str(package)])
    if packages:
        validator_arguments.append("--enforce-change-package")
    if require_current_change:
        validator_arguments.append("--enforce-approval-scope")
    steps.append(
        Step("canonical-validation", "validate_target_adapter.py", tuple(validator_arguments))
    )
    return steps


def generated_paths(target: Path) -> set[Path]:
    paths = {target / path for path in FIXED_GENERATED_PATHS}
    for contour in ("framework", "project", "assistant"):
        root = target / ".ai" / contour
        if root.is_dir():
            paths.update(root.glob("**/context-index.json"))
    package_index = target / ".ai/assistant/change-packages/index.json"
    if package_index.is_file():
        try:
            from render_change_package_index import expected_outputs

            paths.update(expected_outputs(target))
        except (OSError, UnicodeError, ValueError):
            pass
    return paths


def snapshot(paths: Iterable[Path]) -> dict[Path, bytes | None]:
    return {path: path.read_bytes() if path.is_file() else None for path in paths}


def restore(target: Path, before: dict[Path, bytes | None]) -> None:
    all_paths = set(before) | generated_paths(target)
    for path in sorted(all_paths):
        original = before.get(path)
        if original is None:
            if path.is_file():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(original)


def execute_steps(
    steps: Iterable[Step],
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[int, str | None]:
    for step in steps:
        result = runner(
            [sys.executable, str(TOOLS / step.script), *step.arguments],
            check=False,
            text=True,
        )
        if result.returncode:
            return result.returncode, step.step_id
    return 0, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--migration-staging", action="store_true")
    parser.add_argument("--diff-ref")
    parser.add_argument("--approval-record", action="append", type=Path, default=[])
    parser.add_argument("--change-package", action="append", type=Path, default=[])
    parser.add_argument("--require-current-change", action="store_true")
    args = parser.parse_args()
    if args.require_current_change and not (
        args.diff_ref and args.approval_record and args.change_package
    ):
        parser.error(
            "--require-current-change requires --diff-ref, --approval-record, and --change-package"
        )

    target = args.target.resolve()
    if args.write:
        try:
            assert_write_compatible(
                target,
                tool_name="finalize_target_support.py",
                migration_staging=args.migration_staging,
            )
        except (OSError, ValueError) as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 2
    steps = build_steps(
        target=target,
        write=args.write,
        migration_staging=args.migration_staging,
        diff_ref=args.diff_ref,
        approval_records=args.approval_record,
        change_packages=args.change_package,
        require_current_change=args.require_current_change,
    )
    before = snapshot(generated_paths(target)) if args.write else {}
    result, failed_step = execute_steps(steps)
    if result:
        if args.write:
            restore(target, before)
            print(
                f"FAIL: {failed_step} failed; restored generated support files",
                file=sys.stderr,
            )
        else:
            print(f"FAIL: {failed_step} failed", file=sys.stderr)
        return result
    action = "converged" if args.write else "checked"
    print(f"OK: {action} generated support and canonical validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
