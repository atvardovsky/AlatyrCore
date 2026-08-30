#!/usr/bin/env python3
"""Check one operation diff against explicitly selected approval scope."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from validate_target_adapter import AdapterValidatorConfig, Finding, Validator


def _counts(findings: list[Finding]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for finding in findings:
        counts[finding.level] = counts.get(finding.level, 0) + 1
    return counts


def _finding_to_dict(finding: Finding) -> dict[str, str | None]:
    return {
        "level": finding.level,
        "code": finding.code,
        "message": finding.message,
        "path": finding.path,
    }


def _render_text(
    *,
    target: Path,
    diff_ref: str,
    approval_records: list[Path],
    change_packages: list[Path],
    findings: list[Finding],
) -> str:
    counts = _counts(findings)
    state = "failed" if counts["error"] else "passed"
    lines = [
        f"Approval scope check: {state}",
        f"Target: {target}",
        f"Diff ref: {diff_ref}",
        f"Approval records: {len(approval_records)} explicit",
        f"Change packages: {len(change_packages)} explicit",
        "Scope source: selected machine-readable approval records only",
        "Files changed by this command: none",
        (
            f"Findings: errors={counts['error']} "
            f"warnings={counts['warning']} info={counts['info']}"
        ),
    ]
    for finding in findings:
        suffix = f" [{finding.path}]" if finding.path else ""
        lines.append(
            f"{finding.level.upper()} {finding.code}: {finding.message}{suffix}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        type=Path,
        default=Path("."),
        help="Target repository directory. Defaults to the current directory.",
    )
    parser.add_argument(
        "--diff-ref",
        required=True,
        help="Git ref used as the approved diff base.",
    )
    parser.add_argument(
        "--approval-record",
        type=Path,
        action="append",
        required=True,
        help=(
            "Explicit target-relative machine-readable approval record. "
            "May be supplied multiple times."
        ),
    )
    parser.add_argument(
        "--change-package",
        type=Path,
        action="append",
        default=[],
        help=(
            "Optional explicit target-relative change-package JSON record to "
            "enforce with the same operation check."
        ),
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Write the read-only check result to stdout.",
    )
    args = parser.parse_args()

    target = args.target.resolve()
    validator = Validator(
        target,
        framework_source=None,
        diff_ref=args.diff_ref,
        approval_records=args.approval_record,
        enforce_approval_scope=True,
        change_packages=args.change_package,
        enforce_change_package=bool(args.change_package),
        migration_diff=None,
        allow_placeholders=True,
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
        validation_phase="migration-staging",
    )
    validator.check_approval_scope()
    if args.change_package:
        validator.check_change_package_index()
        validator.check_change_packages()

    findings = validator.findings
    counts = _counts(findings)
    if args.format == "json":
        payload = {
            "status": "failed" if counts["error"] else "passed",
            "target": str(target),
            "diff_ref": args.diff_ref,
            "approval_records": [str(path) for path in args.approval_record],
            "change_packages": [str(path) for path in args.change_package],
            "scope_source": "selected machine-readable approval records only",
            "files_changed_by_command": [],
            "counts": counts,
            "findings": [_finding_to_dict(finding) for finding in findings],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print(
            _render_text(
                target=target,
                diff_ref=args.diff_ref,
                approval_records=args.approval_record,
                change_packages=args.change_package,
                findings=findings,
            ),
            end="",
        )
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
