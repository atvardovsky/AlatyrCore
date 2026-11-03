"""Source-bound review freshness, independent of support hashes and decisions."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from target_validation_support import is_target_relative_path
from target_adapter_validation.values import is_resolved_string

MAX_REVIEW_FILE_BYTES = 1024 * 1024
MAX_REVIEW_TOTAL_BYTES = 8 * MAX_REVIEW_FILE_BYTES
MAX_REVIEW_UNIQUE_FILES = 256


def review_routes(items: list[dict], owners: list[str], facts: list[str]) -> dict[str, dict]:
    """Preserve fact OR whole-owner routing and explain every selected item."""
    normalize = lambda path: PurePosixPath(path.replace("\\", "/")).as_posix()
    owner_set, fact_set = {normalize(path) for path in owners}, set(facts)
    result = {}
    for item in items:
        review = item.get("source_review")
        if not isinstance(review, dict):
            continue
        paths = {normalize(row["path"]) for row in review.get("inputs", [])
                 if isinstance(row, dict) and isinstance(row.get("path"), str)} if isinstance(review.get("inputs"), list) else set()
        reviewed = {fact for fact in review.get("changed_fact_ids", []) if isinstance(fact, str)} if isinstance(review.get("changed_fact_ids"), list) else set()
        owner_matches, fact_matches = sorted(owner_set & paths), sorted(fact_set & reviewed)
        if owner_matches or fact_matches:
            previous = result.setdefault(item["id"], {"owner_paths": [], "fact_ids": []})
            previous["owner_paths"] = sorted(set(previous["owner_paths"]) | set(owner_matches))
            previous["fact_ids"] = sorted(set(previous["fact_ids"]) | set(fact_matches))
    return result


def review_frontier(validator: Any, owners: list[str], facts: list[str]) -> dict:
    """Bounded early routing; unchanged coverage, no review or acceptance grant."""
    path = ".ai/project/architecture/catalog.json"
    result = {"state": "not-configured", "routes": {}, "input_groups": [], "failures": [], "authority": "none"}
    if not validator.is_target_file(path):
        return result
    raw = validator.context.read_bytes_result(validator.target_path(path), max_bytes=512 * 1024)
    catalog = validator.load_json_object(validator.target_path(path), "TASK_ARCHITECTURE_CATALOG") if raw.value is not None else None
    if not isinstance(catalog, dict) or catalog.get("schema_version") != 2 or any(not isinstance(catalog.get(key), list) for key in ("areas", "patterns")):
        return {**result, "state": "unavailable", "failures": ["architecture routing requires a bounded schema-2 catalog"]}
    items = [*catalog["areas"], *catalog["patterns"]]
    if len(items) > 256 or any(not isinstance(item, dict) or not is_resolved_string(item.get("id")) for item in items):
        return {**result, "state": "unavailable", "failures": ["architecture routing requires at most 256 identified items"]}
    ids = [item["id"] for item in items]
    if len(ids) != len(set(ids)):
        return {**result, "state": "unavailable", "failures": ["architecture routing contains duplicate identities"]}
    malformed = [item["id"] + ": " + message for item in items
                 for message in review_failures(item.get("source_review"), None)]
    if malformed:
        return {**result, "state": "unavailable", "failures": malformed[:32],
                "omitted_failure_count": max(0, len(malformed) - 32)}
    routes = review_routes(items, owners, facts)
    digests, groups, failures = BoundedReviewDigests(validator.context), {}, []
    for item in items:
        if item["id"] not in routes:
            continue
        review = item.get("source_review")
        problems = review_failures(review, digests)
        if isinstance(review, dict) and review.get("state") == "revalidation-required":
            problems.append("review explicitly requires revalidation")
        failures.extend(item["id"] + ": " + problem for problem in problems)
        for binding in review.get("inputs", []) if isinstance(review, dict) and isinstance(review.get("inputs"), list) else []:
            if not isinstance(binding, dict) or not isinstance(binding.get("path"), str):
                continue
            actual = digests(binding["path"]) if is_target_relative_path(binding["path"]) else None
            if actual is None or actual != binding.get("sha256"):
                key = (binding["path"], binding["sha256"])
                group = groups.setdefault(key, {"path": key[0], "expected_sha256": key[1], "actual_sha256": actual, "item_ids": []})
                group["item_ids"].append(item["id"])
    if len(groups) > MAX_REVIEW_UNIQUE_FILES:
        return {**result, "state": "unavailable", "failures": ["review frontier exceeds its bound; use explicit decomposition"]}
    return {**result, "state": "revalidation-required" if failures else "inputs-current-not-review-acceptance",
            "routes": routes, "input_groups": list(groups.values()), "failures": failures[:32],
            "omitted_failure_count": max(0, len(failures) - 32)}


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


def review_failures(review: Any, digest: Callable[[str], str | None] | None) -> list[str]:
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
        if digest is None:
            continue
        actual = digest(path)
        if actual is None or actual != expected:
            failures.append(f"review input changed or is unavailable: {path}; revalidation required")
    return failures
