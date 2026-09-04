#!/usr/bin/env python3
"""Compare two AlatyrCore source-check reports without rerunning checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_report(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    if data.get("schema_version") not in {2, 3}:
        raise ValueError(
            f"{path} uses report schema {data.get('schema_version')}; "
            "only schema 2 or 3 reports are comparable"
        )
    if data.get("report_kind") != "alatyr-source-check-run":
        raise ValueError(f"{path} is not an Alatyr source-check report")
    return data


def status_counts(report: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for check in report.get("checks", []):
        if isinstance(check, dict):
            status = str(check.get("status", "unknown"))
            counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def timing(report: dict[str, Any], key: str) -> float:
    timing_data = report.get("timing")
    value = timing_data.get(key) if isinstance(timing_data, dict) else None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return 0.0


def source_label(report: dict[str, Any]) -> str:
    source = report.get("source")
    if not isinstance(source, dict):
        return "unknown-source"
    commit = source.get("source_commit") or "unknown-commit"
    manifest = source.get("manifest_sha256") or "unknown-manifest"
    dirty = source.get("source_tree_dirty")
    return f"{commit}@{str(manifest)[:12]} dirty={dirty}"


def render_comparison(base: dict[str, Any], candidate: dict[str, Any]) -> str:
    base_checks = len(base.get("checks", []))
    candidate_checks = len(candidate.get("checks", []))
    base_wall = timing(base, "wall_seconds")
    candidate_wall = timing(candidate, "wall_seconds")
    base_sum = timing(base, "sum_check_duration_seconds")
    candidate_sum = timing(candidate, "sum_check_duration_seconds")
    lines = [
        "Alatyr source-check report comparison",
        f"Base source: {source_label(base)}",
        f"Candidate source: {source_label(candidate)}",
        f"Profiles: {base.get('profile')} -> {candidate.get('profile')}",
        f"Selected checks: {base_checks} -> {candidate_checks}",
        f"Status counts: {status_counts(base)} -> {status_counts(candidate)}",
        (
            f"Wall seconds: {base_wall:.3f} -> {candidate_wall:.3f} "
            f"({candidate_wall - base_wall:+.3f})"
        ),
        (
            f"Sum check seconds: {base_sum:.3f} -> {candidate_sum:.3f} "
            f"({candidate_sum - base_sum:+.3f})"
        ),
    ]
    if source_label(base) == source_label(candidate):
        lines.append("Comparability: same source identity")
    else:
        lines.append("Comparability: different source identity; timing deltas are advisory")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    try:
        print(render_comparison(load_report(args.base), load_report(args.candidate)), end="")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
