"""Change-package index traversal over the caller's shared evidence snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from change_package_contract import (
    ACTIVE_CHANGE_PACKAGE_STATUSES, CHANGE_PACKAGE_STATUSES,
    INCIDENT_INDEX_PROJECTION_FIELDS, package_index_projection_mismatches,
)
from target_validation_support import GitEvidenceView, is_placeholder, is_target_relative_path
from target_adapter_validation.context import TargetRepositoryView


@dataclass(frozen=True)
class ChangePackageIndexValidator:
    """Own index traversal without owning acceptance policy or another cache."""

    context: TargetRepositoryView
    git: GitEvidenceView
    target_path: Callable[[str], Path]
    is_target_file: Callable[[str | Path], bool]
    target_exists: Callable[[str | Path], bool]
    error: Callable[[str, str, str | None], None]
    active_change_package_paths: set[str]
    validation_scope: str
    diff_ref: str | None
    validate_entries: Callable[..., set[str]]

    def check_change_package_index_entries(
        self,
        records: list[Any],
        *,
        source: str,
        changed_paths: set[str] | None,
        source_changed: bool,
        seen: set[str],
        record_filter: set[str] | None = None,
    ) -> set[str]:
        matched_records: set[str] = set()
        for index, entry in enumerate(records):
            if record_filter is not None and (
                not isinstance(entry, dict)
                or not isinstance(entry.get("record"), str)
                or entry.get("record") not in record_filter
            ):
                continue
            if not isinstance(entry, dict):
                self.error(
                    "PACKAGE_INDEX_ENTRY",
                    f"records[{index}] must be an object",
                    source,
                )
                continue
            required_fields = [
                "package_id",
                "status",
                "record",
                "changed_fact_ids",
                "canonical_owners",
                "project_areas",
                "evidence_quality",
                "approval_records",
                "active_workstream",
                "residual_risk",
            ]
            if isinstance(entry.get("status"), str) and entry["status"] in ACTIVE_CHANGE_PACKAGE_STATUSES:
                required_fields.extend(INCIDENT_INDEX_PROJECTION_FIELDS)
                record_value = entry.get("record")
                if isinstance(record_value, str):
                    self.active_change_package_paths.add(record_value)
            for field in required_fields:
                if field not in entry:
                    self.error(
                        "PACKAGE_INDEX_FIELD",
                        f"records[{index}] missing {field}",
                        source,
                    )
            status = entry.get("status")
            if "status" in entry and (
                not isinstance(status, str) or status not in CHANGE_PACKAGE_STATUSES
            ):
                self.error(
                    "PACKAGE_INDEX_STATUS",
                    f"records[{index}].status is not a canonical package status: {status!r}",
                    source,
                )
            package_id = entry.get("package_id")
            if isinstance(package_id, str):
                if package_id in seen:
                    self.error(
                        "PACKAGE_INDEX_DUPLICATE",
                        f"duplicate package_id: {package_id}",
                        source,
                    )
                seen.add(package_id)
            record = entry.get("record")
            if not isinstance(record, str) or is_placeholder(record):
                continue
            if changed_paths is not None and record in changed_paths:
                matched_records.add(record)
            if not is_target_relative_path(record) or not self.is_target_file(record):
                self.error(
                    "PACKAGE_INDEX_RECORD_PATH",
                    f"records[{index}].record does not resolve inside target: {record}",
                    source,
                )
                continue
            validate_projection = (
                changed_paths is None
                or source_changed
                or record in changed_paths
                or isinstance(status, str) and status in ACTIVE_CHANGE_PACKAGE_STATUSES
            )
            if not validate_projection:
                continue
            package, package_error = self.context.read_json(self.target_path(record))
            if package_error is not None:
                self.error(
                    "PACKAGE_INDEX_RECORD_LOAD",
                    f"records[{index}].record cannot be loaded: {package_error}",
                    record,
                )
                continue
            if not isinstance(package, dict):
                self.error(
                    "PACKAGE_INDEX_RECORD_ROOT",
                    f"records[{index}].record must contain an object",
                    record,
                )
                continue
            mismatches = package_index_projection_mismatches(entry, package)
            if mismatches:
                self.error(
                    "PACKAGE_INDEX_PROJECTION",
                    "records[{}] differs from its package record for: {}".format(
                        index, ", ".join(mismatches)
                    ),
                    source,
                )
        return matched_records


    def check_change_package_index(self) -> None:
        relpath = ".ai/assistant/change-packages/index.json"
        path = self.target_path(relpath)
        if not self.target_exists(path):
            return
        data, data_error = self.context.read_json(path)
        if data_error is not None:
            self.error(
                "PACKAGE_INDEX_JSON",
                f"invalid change-package index: {data_error}",
                relpath,
            )
            return
        if not isinstance(data, dict):
            self.error("PACKAGE_INDEX_ROOT", "change-package index must be an object", relpath)
            return
        if data.get("schema_version") != 1:
            self.error("PACKAGE_INDEX_SCHEMA", "schema_version must be 1", relpath)
        if data.get("index_kind") != "target-change-package-index":
            self.error(
                "PACKAGE_INDEX_KIND",
                "index_kind must be target-change-package-index",
                relpath,
            )
        records = data.get("records")
        if not isinstance(records, list):
            self.error("PACKAGE_INDEX_RECORDS", "records must be a list", relpath)
            return
        changed_paths: set[str] | None = None
        index_changed = True
        if self.validation_scope == "changed":
            changed = self.git.changed_files(self.diff_ref)
            if changed is not None:
                changed_paths = set(changed)
                index_changed = relpath in changed_paths
        changed_record_candidates: set[str] = set()
        if changed_paths is not None:
            package_prefix = ".ai/assistant/change-packages/"
            changed_record_candidates = {
                changed_path
                for changed_path in changed_paths
                if changed_path.startswith(package_prefix)
                and changed_path.endswith(".json")
                and changed_path != relpath
            }
        seen: set[str] = set()
        matched_records = self.validate_entries(
            records,
            source=relpath,
            changed_paths=changed_paths,
            source_changed=index_changed,
            seen=seen,
        )

        shards = data.get("shards", [])
        if not isinstance(shards, list):
            self.error("PACKAGE_INDEX_SHARDS", "shards must be a list", relpath)
            return
        declared_shard_paths = {
            descriptor.get("path")
            for descriptor in shards
            if isinstance(descriptor, dict)
            and isinstance(descriptor.get("path"), str)
        }
        pending_changed_records = (
            changed_record_candidates - declared_shard_paths - matched_records
        )
        seen_shard_ids: set[str] = set()
        seen_shard_paths: set[str] = set()
        for index, descriptor in enumerate(shards):
            if not isinstance(descriptor, dict):
                self.error(
                    "PACKAGE_INDEX_SHARD",
                    f"shards[{index}] must be an object",
                    relpath,
                )
                continue
            missing = {
                "shard_id",
                "path",
                "sha256",
                "record_count",
            } - descriptor.keys()
            if missing:
                self.error(
                    "PACKAGE_INDEX_SHARD_FIELD",
                    f"shards[{index}] missing fields: {', '.join(sorted(missing))}",
                    relpath,
                )
                continue
            shard_id = descriptor.get("shard_id")
            shard_relpath = descriptor.get("path")
            expected_sha = descriptor.get("sha256")
            expected_count = descriptor.get("record_count")
            if not isinstance(shard_id, str) or not shard_id:
                self.error(
                    "PACKAGE_INDEX_SHARD_ID",
                    f"shards[{index}].shard_id must be a non-empty string",
                    relpath,
                )
                continue
            if shard_id in seen_shard_ids:
                self.error(
                    "PACKAGE_INDEX_SHARD_DUPLICATE",
                    f"duplicate shard_id: {shard_id}",
                    relpath,
                )
                continue
            seen_shard_ids.add(shard_id)
            if (
                not isinstance(shard_relpath, str)
                or shard_relpath in seen_shard_paths
                or not is_target_relative_path(shard_relpath)
                or self.target_path(shard_relpath).is_symlink()
                or not self.is_target_file(shard_relpath)
            ):
                self.error(
                    "PACKAGE_INDEX_SHARD_PATH",
                    f"shards[{index}].path is invalid or unavailable: {shard_relpath!r}",
                    relpath,
                )
                continue
            seen_shard_paths.add(shard_relpath)
            shard_changed = (
                changed_paths is None
                or index_changed
                or shard_relpath in changed_paths
            )
            if not shard_changed and not pending_changed_records:
                continue
            shard_path = self.target_path(shard_relpath)
            content = self.context.read_bytes_result(shard_path)
            if content.value is None:
                self.error(
                    "PACKAGE_INDEX_SHARD_LOAD",
                    f"shards[{index}] cannot be read: {content.error}",
                    shard_relpath,
                )
                continue
            actual_sha = content.digest
            if expected_sha != actual_sha:
                self.error(
                    "PACKAGE_INDEX_SHARD_DIGEST",
                    f"shards[{index}].sha256 differs from its file",
                    relpath,
                )
            shard, shard_error = self.context.read_json(shard_path)
            if shard_error is not None or not isinstance(shard, dict):
                self.error(
                    "PACKAGE_INDEX_SHARD_LOAD",
                    f"shards[{index}] is not a valid JSON object: {shard_error}",
                    shard_relpath,
                )
                continue
            if (
                shard.get("schema_version") != 1
                or shard.get("index_kind") != "target-change-package-index-shard"
                or shard.get("shard_id") != shard_id
            ):
                self.error(
                    "PACKAGE_INDEX_SHARD_IDENTITY",
                    f"shards[{index}] identity differs from its descriptor",
                    shard_relpath,
                )
            shard_records = shard.get("records")
            if not isinstance(shard_records, list):
                self.error(
                    "PACKAGE_INDEX_SHARD_RECORDS",
                    f"shards[{index}].records must be a list",
                    shard_relpath,
                )
                continue
            if expected_count != len(shard_records):
                self.error(
                    "PACKAGE_INDEX_SHARD_COUNT",
                    f"shards[{index}].record_count differs from its file",
                    relpath,
                )
            for record_index, entry in enumerate(shard_records):
                if (
                    isinstance(entry, dict)
                    and isinstance(entry.get("status"), str) and entry["status"] in ACTIVE_CHANGE_PACKAGE_STATUSES
                ):
                    self.error(
                        "PACKAGE_INDEX_ACTIVE_SHARDED",
                        f"shards[{index}].records[{record_index}] is active and must remain in the root index",
                        shard_relpath,
                    )
            matched_records = self.validate_entries(
                shard_records,
                source=shard_relpath,
                changed_paths=changed_paths,
                source_changed=shard_changed,
                seen=seen,
                record_filter=None if shard_changed else pending_changed_records,
            )
            pending_changed_records -= matched_records
