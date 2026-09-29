#!/usr/bin/env python3
"""Suggest bounded project-knowledge candidates from validated package summaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

if __package__:
    from .change_package_contract import (
        KNOWLEDGE_CANDIDATE_STATUSES,
        package_index_projection_mismatches,
    )
else:
    from change_package_contract import (
        KNOWLEDGE_CANDIDATE_STATUSES,
        package_index_projection_mismatches,
    )


PACKAGE_INDEX = Path(".ai/assistant/change-packages/index.json")
KNOWLEDGE_INDEX = Path(".ai/project/knowledge/index.json")
MAX_EVIDENCE_IDS = 8


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def string_values(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        dict.fromkeys(item for item in value if isinstance(item, str) and item)
    )


def candidate_keys(entry: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    areas = string_values(entry.get("project_areas"))
    owners = string_values(entry.get("canonical_owners"))
    return tuple((area, owner) for area in areas for owner in owners)


@dataclass
class CandidateEvidence:
    occurrences: int = 0
    package_ids: list[str] = field(default_factory=list)
    changed_fact_ids: list[str] = field(default_factory=list)
    verification_entries: list[dict[str, Any]] = field(default_factory=list, repr=False)
    _digest: Any = field(default_factory=hashlib.sha256, repr=False)

    def add(self, entry: dict[str, Any]) -> None:
        self.occurrences += 1
        package_id = entry["package_id"]
        self._digest.update(package_id.encode("utf-8"))
        self._digest.update(b"\0")
        if len(self.package_ids) < MAX_EVIDENCE_IDS:
            self.package_ids.append(package_id)
            self.verification_entries.append(entry)
        for fact_id in string_values(entry.get("changed_fact_ids")):
            self._digest.update(fact_id.encode("utf-8"))
            self._digest.update(b"\0")
            if fact_id not in self.changed_fact_ids:
                if len(self.changed_fact_ids) >= MAX_EVIDENCE_IDS:
                    break
                self.changed_fact_ids.append(fact_id)

    @property
    def evidence_sha256(self) -> str:
        return self._digest.hexdigest()


def candidate_id(key: tuple[str, str], evidence: CandidateEvidence) -> str:
    identity = {
        "contract": 1,
        "kind": "project-area-canonical-owner",
        "project_area": key[0],
        "canonical_owner": key[1],
        "occurrences": evidence.occurrences,
        "package_ids": evidence.package_ids,
        "changed_fact_ids": evidence.changed_fact_ids,
        "evidence_sha256": evidence.evidence_sha256,
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"knowledge-candidate-{digest[:24]}"


def safe_target_path(target: Path, relpath: Any) -> Path | None:
    if not isinstance(relpath, str) or not relpath:
        return None
    relative = Path(relpath)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    unresolved = target / relative
    if unresolved.is_symlink():
        return None
    candidate = unresolved.resolve()
    try:
        candidate.relative_to(target)
    except ValueError:
        return None
    if candidate.is_symlink() or not candidate.is_file():
        return None
    return candidate


def package_records(
    target: Path,
    root_index: dict[str, Any],
    source_bindings: list[dict[str, Any]],
) -> Iterator[Any]:
    records = root_index.get("records")
    if not isinstance(records, list):
        raise ValueError(f"{PACKAGE_INDEX} records must be a list")
    yield from records

    shards = root_index.get("shards", [])
    if not isinstance(shards, list):
        raise ValueError(f"{PACKAGE_INDEX} shards must be a list")
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for index, descriptor in enumerate(shards):
        if not isinstance(descriptor, dict):
            raise ValueError(f"{PACKAGE_INDEX} shards[{index}] must be an object")
        shard_id = descriptor.get("shard_id")
        relpath = descriptor.get("path")
        expected_sha = descriptor.get("sha256")
        expected_count = descriptor.get("record_count")
        if not isinstance(shard_id, str) or not shard_id or shard_id in seen_ids:
            raise ValueError(f"{PACKAGE_INDEX} shards[{index}] has an invalid shard_id")
        if not isinstance(relpath, str) or relpath in seen_paths:
            raise ValueError(f"{PACKAGE_INDEX} shards[{index}] has an invalid path")
        shard_path = safe_target_path(target, relpath)
        if shard_path is None:
            raise ValueError(f"{PACKAGE_INDEX} shards[{index}] path is unavailable")
        actual_sha = sha256(shard_path)
        if expected_sha != actual_sha:
            raise ValueError(f"{PACKAGE_INDEX} shards[{index}] SHA-256 differs")
        shard = load_object(shard_path)
        if (
            shard.get("schema_version") != 1
            or shard.get("index_kind") != "target-change-package-index-shard"
            or shard.get("shard_id") != shard_id
        ):
            raise ValueError(f"{PACKAGE_INDEX} shards[{index}] identity differs")
        shard_records = shard.get("records")
        if not isinstance(shard_records, list) or expected_count != len(shard_records):
            raise ValueError(f"{PACKAGE_INDEX} shards[{index}] record count differs")
        seen_ids.add(shard_id)
        seen_paths.add(relpath)
        source_bindings.append(
            {"path": relpath, "sha256": actual_sha, "record_count": len(shard_records)}
        )
        yield from shard_records


def aggregate_source_sha256(source_bindings: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for binding in source_bindings:
        digest.update(
            json.dumps(binding, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        digest.update(b"\0")
    return digest.hexdigest()


def verified_entry(target: Path, entry: dict[str, Any]) -> bool:
    record_path = safe_target_path(target, entry.get("record"))
    if record_path is None:
        return False
    try:
        record = load_object(record_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return False
    return not package_index_projection_mismatches(entry, record)


def promoted_candidate_ids(
    target: Path, knowledge_index: dict[str, Any]
) -> tuple[set[str], int]:
    candidate_ids: set[str] = set()
    invalid_records = 0
    descriptors = knowledge_index.get("promotion_records")
    if not isinstance(descriptors, list):
        return candidate_ids, invalid_records
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            invalid_records += 1
            continue
        path = safe_target_path(target, descriptor.get("path"))
        if path is None:
            invalid_records += 1
            continue
        try:
            promotion = load_object(path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            invalid_records += 1
            continue
        candidate = promotion.get("candidate")
        value = candidate.get("candidate_id") if isinstance(candidate, dict) else None
        if isinstance(value, str) and value:
            candidate_ids.add(value)
        else:
            invalid_records += 1
    return candidate_ids, invalid_records


def suggestions(target: Path, *, minimum_occurrences: int = 2) -> dict[str, Any]:
    target = target.resolve()
    package_path = target / PACKAGE_INDEX
    knowledge_path = target / KNOWLEDGE_INDEX
    package_index = load_object(package_path)
    knowledge_index = load_object(knowledge_path)
    if (
        package_index.get("schema_version") != 1
        or package_index.get("index_kind") != "target-change-package-index"
    ):
        raise ValueError(f"{PACKAGE_INDEX} identity is invalid")
    root_sha = sha256(package_path)
    source_bindings = [
        {
            "path": PACKAGE_INDEX.as_posix(),
            "sha256": root_sha,
            "record_count": len(package_index.get("records", []))
            if isinstance(package_index.get("records"), list)
            else -1,
        }
    ]

    grouped_evidence: dict[tuple[str, str], CandidateEvidence] = {}
    terminal_records = 0
    duplicate_package_ids = 0
    seen_package_ids: set[str] = set()
    for record in package_records(target, package_index, source_bindings):
        if not isinstance(record, dict):
            continue
        if record.get("status") not in KNOWLEDGE_CANDIDATE_STATUSES:
            continue
        package_id = record.get("package_id")
        if not isinstance(package_id, str) or not package_id:
            continue
        if package_id in seen_package_ids:
            duplicate_package_ids += 1
            continue
        seen_package_ids.add(package_id)
        terminal_records += 1
        for key in candidate_keys(record):
            grouped_evidence.setdefault(key, CandidateEvidence()).add(record)

    existing_candidate_ids, invalid_promotions = promoted_candidate_ids(
        target, knowledge_index
    )
    candidates: list[dict[str, Any]] = []
    suppressed_candidate_ids: list[str] = []
    projection_cache: dict[str, bool] = {}
    verified_package_ids: set[str] = set()
    rejected_package_ids: set[str] = set()
    for key, evidence in sorted(grouped_evidence.items()):
        if evidence.occurrences < minimum_occurrences:
            continue
        verified_samples = 0
        for entry in evidence.verification_entries:
            package_id = entry["package_id"]
            if package_id not in projection_cache:
                projection_cache[package_id] = verified_entry(target, entry)
            if projection_cache[package_id]:
                verified_samples += 1
                verified_package_ids.add(package_id)
            else:
                rejected_package_ids.add(package_id)
        if verified_samples < minimum_occurrences:
            continue
        identity = candidate_id(key, evidence)
        if identity in existing_candidate_ids:
            if len(suppressed_candidate_ids) < MAX_EVIDENCE_IDS:
                suppressed_candidate_ids.append(identity)
            continue
        candidates.append(
            {
                "candidate_id": identity,
                "candidate_kind": "project-area-canonical-owner",
                "selector": {
                    "project_area": key[0],
                    "canonical_owner": key[1],
                },
                "occurrences": evidence.occurrences,
                "verified_evidence_samples": verified_samples,
                "package_ids": evidence.package_ids,
                "changed_fact_ids": evidence.changed_fact_ids,
                "evidence_sha256": evidence.evidence_sha256,
                "evidence_truncated": evidence.occurrences > len(evidence.package_ids),
                "next_action": "review-for-promotion",
            }
        )

    existing_promotions = knowledge_index.get("promotion_records")
    existing_count = len(existing_promotions) if isinstance(existing_promotions, list) else 0
    return {
        "schema_version": 2,
        "report_kind": "project-knowledge-candidate-suggestions",
        "source": PACKAGE_INDEX.as_posix(),
        "source_sha256": aggregate_source_sha256(source_bindings),
        "source_files": source_bindings,
        "knowledge_index_sha256": sha256(knowledge_path),
        "minimum_occurrences": minimum_occurrences,
        "validated_or_completed_packages_considered": terminal_records,
        "candidate_projection_verified_packages": len(verified_package_ids),
        "candidate_projection_rejected_packages": len(rejected_package_ids),
        "duplicate_package_ids_ignored": duplicate_package_ids,
        "existing_promotions": existing_count,
        "invalid_promotion_records_ignored": invalid_promotions,
        "suppressed_existing_candidates": len(suppressed_candidate_ids),
        "suppressed_candidate_ids": suppressed_candidate_ids,
        "candidates": candidates,
        "automatic_promotion_performed": False,
        "reasoning_boundary": (
            "Repeated validated projections are discovery evidence only. A project owner "
            "must review meaning, freshness, conflicts, and canonical ownership before "
            "promotion. Input digests support external cache decisions but are not trusted "
            "as semantic proof."
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
