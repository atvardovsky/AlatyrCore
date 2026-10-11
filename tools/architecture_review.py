"""Source-bound review freshness, independent of support hashes and decisions."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from target_validation_support import is_target_relative_path
from target_adapter_validation.values import is_resolved_string

MAX_REVIEW_FILE_BYTES = 1024 * 1024
MAX_REVIEW_TOTAL_BYTES = 8 * MAX_REVIEW_FILE_BYTES
MAX_REVIEW_UNIQUE_FILES = 256


class BoundedReviewDigests:
    """Hash selected inputs once, without unbounded reads or catalog fan-out."""

    def __init__(self, filesystem: Any) -> None:
        self.filesystem = filesystem
        self.total_bytes = 0
        self.digests: dict[str, str | None] = {}

    def __call__(self, path: str) -> str | None:
        if path in self.digests:
            return self.digests[path]
        if len(self.digests) >= MAX_REVIEW_UNIQUE_FILES:
            return None
        remaining = MAX_REVIEW_TOTAL_BYTES - self.total_bytes
        try:
            read = self.filesystem.read_bytes_result(Path(path), max_bytes=min(MAX_REVIEW_FILE_BYTES, remaining))
        except (OSError, ValueError):
            self.digests[path] = None
            return None
        digest = read.digest if read.value is not None else None
        if read.value is not None:
            self.total_bytes += len(read.value)
        self.digests[path] = digest
        return digest


def review_failures(review: Any, digest: Callable[[str], str | None]) -> list[str]:
    if not isinstance(review, dict):
        return ["source_review requires an explicit review disposition"]
    required = {"state", "reason", "reviewer", "reviewed_at", "changed_fact_ids", "inputs"}
    failures = []
    if set(review) != required:
        failures.append("source_review fields must be: " + ", ".join(sorted(required)))
    state = review.get("state")
    if not isinstance(state, str) or state not in {"reviewed", "not-required", "revalidation-required"}:
        failures.append("source_review.state is invalid")
    for field in ("reason", "reviewer"):
        if not is_resolved_string(review.get(field)):
            failures.append(f"source_review.{field} must be concrete")
    facts = review.get("changed_fact_ids")
    if not isinstance(facts, list) or not all(is_resolved_string(item) for item in facts):
        failures.append("source_review.changed_fact_ids must be resolved strings")
    timestamp = review.get("reviewed_at")
    try:
        if not isinstance(timestamp, str):
            raise ValueError("timestamp must be a string")
        time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if time.tzinfo is None or time > datetime.now(timezone.utc):
            raise ValueError("timestamp must be timezone-aware and not in the future")
    except (ValueError, OverflowError):
        failures.append("source_review.reviewed_at must be a valid, non-future timestamp")
    inputs = review.get("inputs")
    if not isinstance(inputs, list) or len(inputs) > 128:
        failures.append("source_review.inputs must contain at most 128 exact file bindings")
        return failures
    if state == "reviewed" and not inputs:
        failures.append("reviewed requires input evidence, not only a status declaration")
    seen = set()
    for item in inputs:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            failures.append("review input requires path and SHA-256")
            continue
        path, expected = item["path"], item["sha256"]
        if not is_resolved_string(path) or not is_target_relative_path(path) or path in seen:
            failures.append("review input path must be unique and target-relative")
            continue
        seen.add(path)
        if not isinstance(expected, str) or len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            failures.append(f"review input {path} requires a lowercase SHA-256")
            continue
        actual = digest(path)
        if actual is None or actual != expected:
            failures.append(f"review input changed or is unavailable: {path}; revalidation required")
    return failures
