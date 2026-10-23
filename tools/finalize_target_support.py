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
from task_acceptance_binding import add_task_arguments, task_arguments
from support_write_transaction import SupportTransaction, read_output, support_writer_lock
from target_support_outputs import step_outputs
from target_adapter_validation.current_change import change_packages_enabled


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
    task_id: str | None = None,
    task_class: str | None = None,
    problem_models: Iterable[Path] = (),
    require_task_acceptance: bool = False,
    historical_evidence_index: Path | None = None,
) -> list[Step]:
    approval_records = tuple(approval_records)
    packages = tuple(change_packages)
    package_required = False
    if require_current_change:
        if not (diff_ref and approval_records):
            raise ValueError("--require-current-change requires --diff-ref and --approval-record")
        package_required = change_packages_enabled(target)
        if package_required and not packages:
            raise ValueError("--require-current-change requires --change-package when change-packages is enabled")
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
    if historical_evidence_index is not None:
        validator_arguments.extend(["--historical-evidence-index", str(historical_evidence_index)])
    for package in packages:
        validator_arguments.extend(["--change-package", str(package)])
    if packages or package_required:
        validator_arguments.append("--enforce-change-package")
    if require_current_change:
        validator_arguments.append("--enforce-approval-scope")
    validator_arguments.extend(task_arguments(task_id=task_id, task_class=task_class,
        problem_models=problem_models, required=require_task_acceptance))
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


def snapshot(paths: Iterable[Path], *, target: Path) -> dict[Path, bytes | None]:
    return {path: read_output(target, path) for path in paths}


def restore(target: Path, before: dict[Path, bytes | None], *, owned: dict[Path, bytes | None]) -> list[str]:
    transaction = SupportTransaction(target)
    transaction.before, transaction.owned = before, owned
    return transaction.rollback()


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


def execute_write_steps(target: Path, steps: Iterable[Step], *, runner=subprocess.run) -> tuple[int, str | None, list[str]]:
    """Derive owned postimages in-process; never infer ownership from a later read."""
    transaction = SupportTransaction(target)
    failed_step = None
    with support_writer_lock(target):
        try:
            expected = snapshot(generated_paths(target), target=target)
            for step in steps:
                failed_step = step.step_id
                if step.step_id == "canonical-validation":
                    result, failed = execute_steps([step], runner=runner)
                    if result:
                        return result, failed, transaction.rollback()
                else:
                    outputs = step_outputs(step.step_id, target)
                    transaction.apply(outputs, expected_inputs={path: expected.get(path) for path in outputs})
                    expected.update(outputs)
        except Exception as exc:
            print(f"FAIL: {failed_step}: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2, failed_step, transaction.rollback()
    return 0, None, []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--migration-staging", action="store_true")
    parser.add_argument("--diff-ref")
    parser.add_argument("--approval-record", action="append", type=Path, default=[])
    parser.add_argument("--change-package", action="append", type=Path, default=[])
    parser.add_argument("--historical-evidence-index", type=Path)
    parser.add_argument("--require-current-change", action="store_true")
    add_task_arguments(parser)
    args = parser.parse_args()
    try:
        task_arguments(task_id=args.task_id, task_class=args.task_class, required=args.require_task_acceptance)
    except ValueError as exc:
        parser.error(str(exc))
    if args.require_current_change and not (
        args.diff_ref and args.approval_record
    ):
        parser.error(
            "--require-current-change requires --diff-ref and --approval-record"
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
    try:
        steps = build_steps(
            target=target,
            write=args.write,
            migration_staging=args.migration_staging,
            diff_ref=args.diff_ref,
            approval_records=args.approval_record,
            change_packages=args.change_package,
            require_current_change=args.require_current_change,
            task_id=args.task_id,
            task_class=args.task_class,
            problem_models=args.problem_model,
            require_task_acceptance=args.require_task_acceptance,
            historical_evidence_index=args.historical_evidence_index,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    try:
        if args.write:
            result, failed_step, conflicts = execute_write_steps(target, steps)
        else:
            result, failed_step = execute_steps(steps)
            conflicts = []
    except (OSError, ValueError) as exc:
        print(f"FAIL: support writer unavailable: {exc}", file=sys.stderr)
        return 2
    if result:
        if args.write:
            print(
                f"FAIL: {failed_step} failed; restored only unchanged transaction-owned outputs; rollback conflicts preserved: {conflicts}",
                file=sys.stderr,
            )
        else:
            print(f"FAIL: {failed_step} failed", file=sys.stderr)
        return result
    action = "converged" if args.write else "checked"
    print(f"OK: {action} generated support and canonical validation")
    if not args.require_task_acceptance:
        print("Current-task acceptance was not requested; this result is not task-completion evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
