#!/usr/bin/env python3
"""Prepare or write a reviewed source release checkpoint."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from check_release_drift import (
    RELEASE_BASELINE_DIR,
    ROOT,
    contract_digest_at,
    file_sha256,
    git,
    nearest_release_baseline,
    read_at,
    require_git_text,
    unreleased_section_is_empty,
    validate_committed_report,
)


def checkpoint_record(version: str, source_commit: str) -> dict[str, object]:
    commit = require_git_text("rev-parse", "--verify", f"{source_commit}^{{commit}}")
    if not re.fullmatch(r"[0-9a-f]{40,64}", commit):
        raise RuntimeError("source commit must resolve to a full Git object ID")
    if git("merge-base", "--is-ancestor", commit, "HEAD").returncode != 0:
        raise RuntimeError("source commit must be an ancestor of HEAD")

    committed_version = read_at(commit, "VERSION")
    if committed_version != version:
        raise RuntimeError(
            f"source commit VERSION={committed_version} does not match {version}"
        )
    if not unreleased_section_is_empty(read_at(commit, "CHANGELOG.md")):
        raise RuntimeError("source commit must have an empty Unreleased section")

    adapter = read_at(commit, "ADAPTER_SCHEMA_VERSION")
    template = read_at(commit, "TEMPLATE_VERSION")
    digest = contract_digest_at(commit)
    report_path = ROOT / "docs" / "releases" / f"{version}-migration.md"
    if not report_path.is_file():
        raise RuntimeError(f"missing migration report: {report_path.relative_to(ROOT)}")

    previous, _intervening = nearest_release_baseline(version)
    previous_digest = previous.expected_digest or contract_digest_at(previous.ref)
    failures = validate_committed_report(
        baseline=previous.label,
        from_version=read_at(previous.ref, "VERSION"),
        to_version=version,
        from_adapter=read_at(previous.ref, "ADAPTER_SCHEMA_VERSION"),
        to_adapter=adapter,
        from_template=read_at(previous.ref, "TEMPLATE_VERSION"),
        to_template=template,
        from_digest=previous_digest,
        to_digest=digest,
    )
    if failures:
        raise RuntimeError("migration report is not checkpoint-ready: " + "; ".join(failures))

    return {
        "schema_version": 2,
        "baseline_kind": "source-release-checkpoint",
        "framework_version": version,
        "adapter_schema_version": adapter,
        "template_version": template,
        "source_commit": commit,
        "contract_sha256": digest,
        "migration_report": f"docs/releases/{version}-migration.md",
        "migration_report_sha256": file_sha256(report_path),
        "previous_baseline": previous.label,
        "publication_status": "untagged-release-checkpoint",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write docs/releases/baselines/<version>.json; otherwise print it.",
    )
    args = parser.parse_args()
    try:
        record = checkpoint_record(args.version, args.source_commit)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(record, indent=2) + "\n"
    if not args.write:
        print(rendered, end="")
        return 0
    output = RELEASE_BASELINE_DIR / f"{args.version}.json"
    if output.exists():
        print(f"FAIL: checkpoint already exists: {output.relative_to(ROOT)}", file=sys.stderr)
        return 1
    output.write_text(rendered, encoding="utf-8")
    print(f"Wrote {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
