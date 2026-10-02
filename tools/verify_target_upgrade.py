#!/usr/bin/env python3
"""Verify that an installed Alatyr update reached strict acceptance."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def acceptance_failures(payload: dict[str, Any]) -> list[str]:
    """Return contract failures that prevent a completed-update claim."""

    failures: list[str] = []
    if payload.get("tool") != "validate_target_adapter":
        failures.append("report was not produced by validate_target_adapter")
    if payload.get("status") != "passed":
        failures.append("validator status is not passed")
    if payload.get("validation_phase") != "acceptance":
        failures.append("validation phase is not acceptance")
    if payload.get("validation_scope") != "full":
        failures.append("validation scope is not full")
    if payload.get("installation_state") != "accepted":
        failures.append("installation state is not accepted")

    placeholder = payload.get("placeholder_validation")
    if not isinstance(placeholder, dict) or placeholder.get("acceptance_eligible") is not True:
        failures.append("validator report is not acceptance eligible")
    elif placeholder.get("unresolved_active") != 0:
        failures.append("active target placeholders remain")

    layers = payload.get("health_layers")
    current_change = layers.get("current_change") if isinstance(layers, dict) else None
    if not isinstance(current_change, dict) or current_change.get("state") != "structurally-checked":
        failures.append("upgrade change scope was not structurally checked")
    elif not (
        current_change.get("approval_scope_enforced") is True
        and current_change.get("approval_records_selected", 0) > 0
    ):
        failures.append("upgrade approval scope was not enforced")
    elif current_change.get("change_package_required") is True and not (
        current_change.get("change_package_enforced") is True
        and current_change.get("change_packages_selected", 0) > 0
    ):
        failures.append("required upgrade change-package scope was not enforced")
    else:
        change_set = current_change.get("change_set")
        if not isinstance(change_set, dict):
            failures.append("upgrade change-set binding is missing")
        else:
            digest = change_set.get("content_sha256")
            if not isinstance(digest, str) or len(digest) != 64:
                failures.append("upgrade change-set digest is invalid")
            if change_set.get("hash_contract") != "canonical-git-change-set-v1":
                failures.append("upgrade change-set hash contract is invalid")
            if not isinstance(change_set.get("changed_path_count"), int):
                failures.append("upgrade changed-path count is missing")

    archive = payload.get("approval_archive")
    if not isinstance(archive, dict) or archive.get("mode") != "full":
        failures.append("approval archive was not fully validated")

    counts = payload.get("counts")
    if not isinstance(counts, dict):
        failures.append("validator finding counts are missing")
    else:
        if counts.get("errors") != 0:
            failures.append("validator report contains errors")
        if counts.get("blocking_warnings") != 0:
            failures.append("validator report contains blocking warnings")

    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        failures.append("repository binding evidence is missing")
    else:
        for field in ("observed_revision", "observed_branch"):
            value = evidence.get(field)
            if not isinstance(value, str) or not value or value == "not available":
                failures.append(f"repository {field.removeprefix('observed_')} is unavailable")
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the portable target validator with the final update-acceptance "
            "contract. This command verifies an already applied update and never "
            "changes target files."
        )
    )
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--framework-source", default=ROOT, type=Path)
    parser.add_argument("--migration-diff", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--diff-ref", required=True)
    parser.add_argument(
        "--approval-record", action="append", required=True, type=Path
    )
    parser.add_argument("--change-package", action="append", default=[], type=Path)
    parser.add_argument("--strict-warnings", action="store_true")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing verification report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = args.target.resolve()
    source = args.framework_source.resolve()
    migration_diff = args.migration_diff.resolve()
    output = args.output.resolve()

    if not target.is_dir():
        print(f"Target repository does not exist: {target}", file=sys.stderr)
        return 2
    if not (source / "tools" / "validate_target_adapter.py").is_file():
        print(f"Framework source is incomplete: {source}", file=sys.stderr)
        return 2
    if not migration_diff.is_file():
        print(f"Migration diff does not exist: {migration_diff}", file=sys.stderr)
        return 2
    if output.exists() and not args.overwrite:
        print(f"Verification output already exists: {output}; pass --overwrite", file=sys.stderr)
        return 2

    command = [
        sys.executable,
        str(source / "tools" / "validate_target_adapter.py"),
        "--target",
        str(target),
        "--framework-source",
        str(source),
        "--migration-diff",
        str(migration_diff),
        "--validation-phase",
        "acceptance",
        "--validation-scope",
        "full",
        "--approval-archive-mode",
        "full",
        "--enforce-approval-scope",
        "--output",
        str(output),
    ]
    if args.diff_ref:
        command.extend(["--diff-ref", args.diff_ref])
    for record in args.approval_record:
        command.extend(["--approval-record", str(record)])
    for package in args.change_package:
        command.extend(["--change-package", str(package)])
    if args.change_package:
        command.append("--enforce-change-package")
    if args.strict_warnings:
        command.append("--strict-warnings")

    result = subprocess.run(
        command,
        cwd=source,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if not output.is_file():
        diagnostic = result.stderr.strip() or result.stdout.strip() or "no validator report"
        print(f"Upgrade verification failed: {diagnostic}", file=sys.stderr)
        return result.returncode or 1
    try:
        payload = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Upgrade verification report is invalid: {exc}", file=sys.stderr)
        return 1

    failures = acceptance_failures(payload)
    if result.returncode != 0 and not failures:
        failures.append(f"validator exited with status {result.returncode}")
    if failures:
        print("Alatyr update is not accepted:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        print(f"Verification evidence: {output}", file=sys.stderr)
        return 1

    evidence = payload["evidence"]
    print(
        "Alatyr update accepted for "
        f"{evidence['observed_branch']}@{evidence['observed_revision']}"
    )
    print(f"Verification evidence: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
