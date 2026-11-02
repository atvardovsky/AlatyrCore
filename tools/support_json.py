#!/usr/bin/env python3
"""Inspect or verify bounded JSON support views without changing their sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from itertools import islice
from pathlib import Path
from typing import Any, Iterable

from context_input_snapshot import read_regular_context_bytes
from repair_qualification import MISSING, pointer_value
from source_context_selection import contained_source_path, source_json


MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_VIEW_BYTES = 256 * 1024
DEFAULT_VIEW_BYTES = 32 * 1024
MAX_SELECTORS = 32
MAX_DEPTH = 64
COLLECTION_LIMIT = 64
BYTE_REVIEW_LIMIT = 64 * 1024
INDEX_KINDS = {
    "target-project-knowledge-routing-index", "target-change-package-index",
    "target-approval-archive-index", "target-consistency-map",
}


def encoded(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def read_bytes(root: Path, relpath: str, limit: int) -> bytes:
    path = contained_source_path(root.resolve(), relpath)
    if not path.is_file():
        raise ValueError(f"JSON source must be a regular file: {relpath}")
    raw = read_regular_context_bytes(path, max_bytes=limit)
    contained_source_path(root.resolve(), relpath)
    return raw


def _pointer(key: str) -> str:
    return "/" + key.replace("~", "~0").replace("/", "~1")


def _check_depth(document: dict) -> None:
    stack = [iter(document.values())]
    while stack:
        try:
            value = next(stack[-1])
        except StopIteration:
            stack.pop()
            continue
        if isinstance(value, (dict, list)):
            if len(stack) >= MAX_DEPTH:
                raise ValueError(f"JSON support nesting exceeds {MAX_DEPTH} containers")
            stack.append(iter(value.values()) if isinstance(value, dict) else iter(value))


def _select(document: dict, pointer: str) -> Any:
    value = document if pointer == "" else pointer_value(document, pointer)
    if value is MISSING:
        raise ValueError(f"JSON selector is invalid or unavailable: {pointer!r}")
    return value


def _report_pointers(document: dict, requested: list[str], max_bytes: int) -> list[str]:
    common = [_pointer(key) for key in ("status", "errors", "warnings", "findings",
                                       "acceptance_evidence", "acceptance_eligible",
                                       "exit_code", "coverage", "limitations") if key in document]
    if document.get("tool") == "validate_target_adapter":
        if type(document.get("schema_version")) is not int or document["schema_version"] != 3:
            raise ValueError("unsupported target-validation report version; use its full report")
        return [*common, "/schema_version", "/tool", "/status", "/exit_code", "/counts",
                "/validation_phase", "/validation_scope", "/installation_state",
                "/task_acceptance", "/placeholder_validation", "/evidence",
                "/adapter_health", "/health_layers", "/approval_archive", "/findings"]
    if document.get("report_kind") == "alatyr-source-check-run":
        if type(document.get("schema_version")) is not int or document["schema_version"] != 3:
            raise ValueError("unsupported source-check report version; use its full report")
        pointers = [*common, "/schema_version", "/report_kind", "/profile", "/source", "/selection",
                    "/reuse_contract", "/acceptance_evidence", "/source_write_scope"]
        checks = document.get("checks")
        if not isinstance(checks, list):
            raise ValueError("source-check report checks must be a list")
        if "" in requested or "/checks" in requested:
            return [*pointers, "/checks"]
        diagnostic_count = 0
        for index, row in enumerate(checks):
            # Only explicit successful rows may leave diagnostic delivery.
            if (not isinstance(row, dict) or not isinstance(row.get("status"), str)
                    or row["status"] not in {"passed", "reused-pass"}
                    or type(row.get("exit_code")) is not int or row["exit_code"] != 0
                    or row.get("timed_out") is not False):
                pointers.append(f"/checks/{index}")
                diagnostic_count += 1
                # Each required sibling entry costs more than 24 bytes even
                # before its value. Stop before constructing an oversized view.
                if diagnostic_count > max_bytes // 24:
                    raise ValueError(f"required report diagnostics exceed the {max_bytes}-byte view budget; select /checks as a whole if it fits, or review the full source; diagnostics were not truncated")
        return pointers
    # Unknown formats have no inferred acceptance semantics. Retain any explicit
    # top-level diagnostic/status surfaces, not just the requested detail.
    return common


def _minimal_pointers(pointers: list[str]) -> list[str]:
    ordered = sorted(set(pointers), key=lambda value: (value.count("/"), value))
    result: set[str] = set()
    for pointer in ordered:
        ancestors = (pointer[:index] for index, char in enumerate(pointer) if char == "/" and index > 0)
        if "" not in result and not any(parent in result for parent in ancestors):
            result.add(pointer)
    return sorted(result)


def build_view(raw: bytes, *, path: str, selectors: Iterable[str] = (),
               max_bytes: int = DEFAULT_VIEW_BYTES) -> dict:
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_VIEW_BYTES:
        raise ValueError(f"view budget must be an integer from 1 to {MAX_VIEW_BYTES} bytes")
    if not isinstance(raw, bytes) or len(raw) > MAX_SOURCE_BYTES:
        raise ValueError(f"source must contain at most {MAX_SOURCE_BYTES} bytes")
    document = source_json(raw.decode("utf-8"), lossless_numbers=True)
    _check_depth(document)
    requested = list(islice(selectors, MAX_SELECTORS + 1))
    if len(requested) > MAX_SELECTORS or any(not isinstance(value, str) for value in requested):
        raise ValueError(f"select at most {MAX_SELECTORS} JSON pointers")
    if len(set(requested)) != len(requested):
        raise ValueError("JSON selectors must be unique")
    for pointer in requested:
        _select(document, pointer)
    required = sorted(set(_report_pointers(document, requested, max_bytes)))
    selected = _minimal_pointers([*requested, *required])
    values = [{"pointer": pointer, "value": _select(document, pointer)} for pointer in selected]
    fields = [{"pointer": _pointer(key), "kind": type(value).__name__,
               "items": len(value) if isinstance(value, (list, dict)) else None}
              for key, value in sorted(document.items())]
    if len(fields) > COLLECTION_LIMIT:
        raise ValueError(f"source has more than {COLLECTION_LIMIT} root fields; select a smaller canonical artifact")
    kind = document.get("index_kind", document.get("map_kind", document.get("state_kind")))
    disposition = (
        "use-existing-index" if isinstance(kind, str) and kind in INDEX_KINDS else
        "project-machine-inventory" if kind == "target-support-state" else
        "project-report-details" if isinstance(document.get("report_kind"), str)
        or document.get("tool") == "validate_target_adapter" else
        "keep-record-whole" if isinstance(document.get("record_kind"), str) else
        "review-collection-boundaries" if len(raw) > BYTE_REVIEW_LIMIT
        or any(isinstance(value, list) and len(value) > COLLECTION_LIMIT for value in document.values()) else
        "keep-cohesive"
    )
    result = {
        "schema_version": 1, "view_kind": "alatyr-support-json-view", "read_only": True,
        "source": {"path": path, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
        "requested_pointers": sorted(requested), "required_pointers": required,
        "selected": values, "root_fields": fields,
        "coverage": {"whole_source_selected": "" in selected, "unselected_content": "reference-only",
                     "report_check_count": len(document["checks"]) if document.get("report_kind") == "alatyr-source-check-run" else None},
        "layout": {"disposition": disposition, "automatic_migration_performed": False,
                   "review_limits": {"collection_items": COLLECTION_LIMIT, "source_bytes": BYTE_REVIEW_LIMIT}},
        "max_output_bytes": max_bytes,
        "authorization_granted": False, "acceptance_granted": False,
        "consistency_scope": "Exact selected values and source identity only; run existing full adapter checks for schemas, references, shards and projections.",
        "detail_recovery": "Read the bound source or select exact pointers; no related files were opened.",
        "limitation": "Navigation only, not an executable packet or complete semantic context. Resolve required owners and dependencies before acting; no token, latency or billing saving is established.",
    }
    # Byte-count digit growth is monotonic. Do not embed a rounded percentage:
    # its variable width can oscillate at a rounding boundary.
    result["delivery"] = {"bytes": 0}
    for _ in range(4):
        size = len(encoded(result))
        measurement = {"bytes": size}
        if result["delivery"] == measurement:
            break
        result["delivery"] = measurement
    else:
        raise ValueError("view measurement did not converge")
    if size > max_bytes:
        raise ValueError(f"complete JSON view requires {size} bytes; limit is {max_bytes}; narrow selection or review the full source; diagnostics were not truncated")
    return result


def verify_view(raw: bytes, view: dict, *, path: str) -> None:
    if not isinstance(view, dict) or not isinstance(view.get("requested_pointers"), list):
        raise ValueError("invalid JSON support view")
    expected = build_view(raw, path=path, selectors=view["requested_pointers"],
                          max_bytes=view.get("max_output_bytes"))
    if encoded(view) != encoded(expected):
        raise ValueError("JSON support view is stale or inconsistent with its source, selection or delivery contract")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--path", required=True, help="Exact repository-relative JSON object path.")
    parser.add_argument("--select", action="append", default=[], help="Exact JSON Pointer; repeat for needed values. Empty pointer selects the whole source.")
    parser.add_argument("--max-output-bytes", type=int, default=DEFAULT_VIEW_BYTES)
    parser.add_argument("--check", help="Repository-relative saved view to verify; never writes.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.check is not None and (args.select or args.max_output_bytes != DEFAULT_VIEW_BYTES):
        parser.error("--check uses the saved selection and budget; do not override them")
    try:
        raw = read_bytes(args.target, args.path, MAX_SOURCE_BYTES)
        if args.check is not None:
            view = source_json(read_bytes(args.target, args.check, MAX_VIEW_BYTES).decode("utf-8"), lossless_numbers=True)
            verify_view(raw, view, path=args.path)
            print("OK: JSON support view matches current source and delivery contract; no adapter acceptance established")
        else:
            view = build_view(raw, path=args.path, selectors=args.select, max_bytes=args.max_output_bytes)
            sys.stdout.buffer.write(encoded(view))
    except (OSError, ValueError, RecursionError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
