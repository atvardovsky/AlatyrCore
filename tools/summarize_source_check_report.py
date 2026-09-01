#!/usr/bin/env python3
"""Render a compact Markdown summary for an Alatyr source-check report."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def _duration(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}s"
    return "n/a"


def _short_text(value: object, *, limit: int = 240) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def status_counts(checks: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for check in checks:
        status = check.get("status")
        if isinstance(status, str):
            counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def selected_failure_checks(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        check
        for check in checks
        if check.get("status") == "failed" or check.get("timed_out") is True
    ]


def selected_blocked_checks(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [check for check in checks if check.get("status") == "blocked"]


def render_summary(report: dict[str, Any], *, source_label: str) -> str:
    checks = report.get("checks")
    if not isinstance(checks, list):
        checks = []
    typed_checks = [check for check in checks if isinstance(check, dict)]
    counts = status_counts(typed_checks)
    timing = report.get("timing") if isinstance(report.get("timing"), dict) else {}
    source = report.get("source") if isinstance(report.get("source"), dict) else {}
    selection = report.get("selection") if isinstance(report.get("selection"), dict) else {}

    lines = [
        "### Alatyr Source Checks",
        "",
        f"- Report: `{source_label}`",
        f"- Profile: `{report.get('profile', 'unknown')}`",
        f"- Source commit: `{source.get('source_commit') or 'unknown'}`",
        f"- Source tree dirty: `{source.get('source_tree_dirty')}`",
        f"- Wall time: {_duration(timing.get('wall_seconds'))}",
        f"- Selected checks: `{len(typed_checks)}`",
    ]
    if counts:
        lines.append(
            "- Status counts: "
            + ", ".join(f"{status}={count}" for status, count in counts.items())
        )
    if selection.get("fell_back_to_full") is True:
        lines.append("- Focused selection fell back to the full profile.")
    unmatched = selection.get("unmatched_changed_paths")
    if isinstance(unmatched, list) and unmatched:
        lines.append("- Unmatched changed paths:")
        for path in unmatched[:10]:
            lines.append(f"  - `{path}`")
        if len(unmatched) > 10:
            lines.append(f"  - ... {len(unmatched) - 10} more")

    failures = selected_failure_checks(typed_checks)
    if failures:
        lines.extend(["", "Failed Checks:"])
        for check in failures[:12]:
            check_id = check.get("id", "unknown")
            exit_code = check.get("exit_code", "n/a")
            timed_out = check.get("timed_out") is True
            diagnostic = _short_text(check.get("stderr") or check.get("stdout"))
            suffix = f"; {diagnostic}" if diagnostic else ""
            timeout = "; timed out" if timed_out else ""
            lines.append(f"- `{check_id}` exit={exit_code}{timeout}{suffix}")
        if len(failures) > 12:
            lines.append(f"- ... {len(failures) - 12} more failed checks")

    blocked = selected_blocked_checks(typed_checks)
    if blocked:
        lines.extend(["", "Blocked Checks:"])
        for check in blocked[:12]:
            dependencies = check.get("blocked_by")
            blocked_by = (
                ", ".join(str(item) for item in dependencies)
                if isinstance(dependencies, list)
                else "unknown"
            )
            lines.append(f"- `{check.get('id', 'unknown')}` blocked by {blocked_by}")
        if len(blocked) > 12:
            lines.append(f"- ... {len(blocked) - 12} more blocked checks")

    slowest = timing.get("slowest_checks")
    if isinstance(slowest, list) and slowest:
        lines.extend(["", "Slowest Checks:"])
        for item in slowest[:5]:
            if isinstance(item, dict):
                lines.append(
                    f"- `{item.get('id', 'unknown')}` "
                    f"{_duration(item.get('duration_seconds'))}"
                )

    lines.append("")
    return "\n".join(lines)


def emit(text: str, *, github_step_summary: bool) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_step_summary and summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as stream:
            stream.write(text)
            if not text.endswith("\n"):
                stream.write("\n")
        return
    print(text, end="" if text.endswith("\n") else "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Render a non-failing diagnostic when the report was not produced.",
    )
    parser.add_argument(
        "--github-step-summary",
        action="store_true",
        help="Append output to GITHUB_STEP_SUMMARY when that environment variable is set.",
    )
    args = parser.parse_args()

    if not args.report.is_file():
        if not args.allow_missing:
            print(f"FAIL: source-check report is missing: {args.report}", file=sys.stderr)
            return 1
        emit(
            (
                "### Alatyr Source Checks\n\n"
                f"- Report was not generated: `{args.report}`\n"
            ),
            github_step_summary=args.github_step_summary,
        )
        return 0

    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read source-check report: {exc}", file=sys.stderr)
        return 1
    if not isinstance(report, dict):
        print("FAIL: source-check report must be a JSON object", file=sys.stderr)
        return 1
    emit(
        render_summary(report, source_label=args.report.as_posix()),
        github_step_summary=args.github_step_summary,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
