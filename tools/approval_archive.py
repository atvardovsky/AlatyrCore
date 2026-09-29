"""Build and validate immutable monthly approval archive shard indexes."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from evidence_contract import canonical_worktree_entries, digest_entries


ARCHIVE_ROOT = Path(".ai/assistant/approvals/archive")
INDEX_PATH = Path(".ai/assistant/approvals/archive-index.json")
RECORD_SUFFIXES = {".json", ".md"}


def _shard_records(target: Path, directory: Path) -> list[str]:
    root = target.resolve()
    return sorted(
        path.relative_to(root).as_posix()
        for path in directory.rglob("*")
        if path.is_file()
        and path.suffix.lower() in RECORD_SUFFIXES
        and path.name != "context-index.json"
    )


def build_archive_index(target: Path) -> dict[str, Any]:
    target = target.resolve()
    archive_root = target / ARCHIVE_ROOT
    shards: list[dict[str, Any]] = []
    if archive_root.is_dir():
        for directory in sorted(path for path in archive_root.iterdir() if path.is_dir()):
            records = _shard_records(target, directory)
            if not records:
                continue
            content_digest = digest_entries(canonical_worktree_entries(target, records))
            digest = hashlib.sha256(
                b"alatyr-approval-archive-v1\0" + content_digest.encode("ascii")
            ).hexdigest()
            shards.append(
                {
                    "id": directory.name,
                    "directory": directory.relative_to(target).as_posix(),
                    "record_count": len(records),
                    "digest": f"sha256:{digest}",
                }
            )
    return {
        "schema_version": 1,
        "index_kind": "target-approval-archive-index",
        "shards": shards,
    }


__all__ = ["ARCHIVE_ROOT", "INDEX_PATH", "build_archive_index"]
