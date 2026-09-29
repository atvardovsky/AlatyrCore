#!/usr/bin/env python3
"""Suggest bounded project-knowledge candidates from validated package summaries."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


PACKAGE_INDEX = Path(".ai/assistant/change-packages/index.json")
KNOWLEDGE_INDEX = Path(".ai/project/knowledge/index.json")
COMPLETED_STATUS_TERMS = ("validated", "complete", "published", "deployed")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def suggestions(target: Path, *, minimum_occurrences: int = 2) -> dict[str, Any]:
    target = target.resolve()
    package_index = load_object(target / PACKAGE_INDEX)
    knowledge_index = load_object(target / KNOWLEDGE_INDEX)
    records = package_index.get("records")
    if not isinstance(records, list):
        raise ValueError(f"{PACKAGE_INDEX} records must be a list")
    accepted_records = [
        record
        for record in records
        if isinstance(record, dict)
        and isinstance(record.get("status"), str)
        and any(term in record["status"].casefold() for term in COMPLETED_STATUS_TERMS)
    ]
    by_area: dict[str, list[str]] = defaultdict(list)
    by_owner: dict[str, list[str]] = defaultdict(list)
    for record in accepted_records:
        package_id = record.get("package_id")
        if not isinstance(package_id, str) or not package_id:
            continue
        for area in record.get("project_areas", []):
            if isinstance(area, str) and area:
                by_area[area].append(package_id)
        for owner in record.get("canonical_owners", []):
            if isinstance(owner, str) and owner:
                by_owner[owner].append(package_id)

    candidates: list[dict[str, Any]] = []
    for kind, groups in (("project-area", by_area), ("canonical-owner", by_owner)):
        for selector, package_ids in sorted(groups.items()):
            unique_ids = list(dict.fromkeys(package_ids))
            if len(unique_ids) < minimum_occurrences:
                continue
            candidates.append(
                {
                    "candidate_kind": kind,
                    "selector": selector,
                    "occurrences": len(unique_ids),
                    "package_ids": unique_ids[:8],
                    "next_action": "review-for-promotion",
                }
            )

    existing_promotions = knowledge_index.get("promotion_records")
    existing_count = len(existing_promotions) if isinstance(existing_promotions, list) else 0
    return {
        "schema_version": 1,
        "report_kind": "project-knowledge-candidate-suggestions",
        "source": PACKAGE_INDEX.as_posix(),
        "validated_or_completed_packages_considered": len(accepted_records),
        "existing_promotions": existing_count,
        "candidates": candidates,
        "automatic_promotion_performed": False,
        "reasoning_boundary": (
            "Repeated summaries are discovery evidence only. A project owner must review "
            "meaning, freshness, conflicts, and canonical ownership before promotion."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--minimum-occurrences", type=int, default=2)
    args = parser.parse_args()
    if args.minimum_occurrences < 2:
        parser.error("--minimum-occurrences must be at least 2")
    try:
        report = suggestions(
            args.target, minimum_occurrences=args.minimum_occurrences
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
