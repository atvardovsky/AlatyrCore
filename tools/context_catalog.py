"""Resolve recursive Alatyr context indexes and semantic codebooks."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


CONTEXT_INDEX_SCHEMA_VERSION = 1
CODEBOOK_SCHEMA_VERSION = 1
PACKET_SCHEMA_VERSION = 1
CONTEXT_INDEX_KIND = "alatyr-context-index"
CODEBOOK_INDEX_KIND = "alatyr-semantic-codebook-index"
CODEBOOK_SHARD_KIND = "alatyr-semantic-codebook-shard"
PACKET_KIND = "alatyr-context-packet"
SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}")
TERM_ID_RE = re.compile(r"(?:alatyr|project):[a-z0-9][a-z0-9-]*(?:@[1-9][0-9]*)?")
INDEX_ENTRY_KINDS = {"index", "content"}
CONTOURS = {"framework", "project", "assistant"}


class ContextCatalogError(ValueError):
    """Raised when a context catalog or semantic codebook is invalid."""


@dataclass(frozen=True)
class CatalogItem:
    item_id: str
    kind: str
    path: str
    summary: str
    selectors: dict[str, tuple[str, ...]]
    load_when: tuple[str, ...]
    semantic_refs: tuple[str, ...]
    owner_refs: tuple[str, ...]
    estimated_words: int
    content_digest: str


@dataclass(frozen=True)
class CatalogResolution:
    indexes: tuple[str, ...]
    items: tuple[CatalogItem, ...]


def load_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContextCatalogError(f"cannot load {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ContextCatalogError(f"{path} must contain a JSON object")
    return data


def file_digest(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def word_count(path: Path) -> int:
    return len(re.findall(r"\S+", path.read_text(encoding="utf-8")))


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContextCatalogError(f"{label} must be a non-empty string")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ContextCatalogError(f"{label} must be a normalized relative path")
    return value


def _string_list(value: Any, label: str, *, non_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (non_empty and not value):
        suffix = " non-empty" if non_empty else ""
        raise ContextCatalogError(f"{label} must be a{suffix} list")
    if not all(isinstance(item, str) and item for item in value):
        raise ContextCatalogError(f"{label} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise ContextCatalogError(f"{label} contains duplicates")
    return tuple(value)


def _validate_selectors(value: Any, label: str) -> dict[str, tuple[str, ...]]:
    if not isinstance(value, dict):
        raise ContextCatalogError(f"{label} must be an object")
    selectors: dict[str, tuple[str, ...]] = {}
    for key, entries in value.items():
        if not isinstance(key, str) or not key:
            raise ContextCatalogError(f"{label} keys must be non-empty strings")
        selectors[key] = _string_list(entries, f"{label}.{key}")
    return selectors


def _resolve_under(root: Path, relpath: str, label: str) -> Path:
    candidate = (root / relpath).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise ContextCatalogError(f"{label} escapes its catalog root")
    return candidate


def validate_context_catalog(
    root_index: Path,
    *,
    catalog_root: Path | None = None,
    verify_content: bool = True,
) -> CatalogResolution:
    """Validate and flatten one recursive context-index tree."""

    root_index = root_index.resolve()
    catalog_root = (catalog_root or root_index.parent).resolve()
    seen_indexes: set[Path] = set()
    active_indexes: set[Path] = set()
    seen_ids: set[str] = set()
    seen_content_paths: set[str] = set()
    indexes: list[str] = []
    items: list[CatalogItem] = []
    root_max_depth: int | None = None
    root_contour: str | None = None

    def visit(index_path: Path, depth: int) -> None:
        nonlocal root_max_depth, root_contour
        if index_path in active_indexes:
            raise ContextCatalogError(f"context index cycle reaches {index_path}")
        if index_path in seen_indexes:
            raise ContextCatalogError(f"context index has multiple parents: {index_path}")
        data = load_object(index_path)
        if data.get("schema_version") != CONTEXT_INDEX_SCHEMA_VERSION:
            raise ContextCatalogError(f"{index_path} has unsupported schema_version")
        if data.get("index_kind") != CONTEXT_INDEX_KIND:
            raise ContextCatalogError(f"{index_path} has invalid index_kind")
        index_id = data.get("index_id")
        if not isinstance(index_id, str) or not index_id:
            raise ContextCatalogError(f"{index_path}.index_id must be non-empty")
        if index_id in seen_ids:
            raise ContextCatalogError(f"duplicate context ID: {index_id}")
        seen_ids.add(index_id)
        contour = data.get("contour")
        if contour not in CONTOURS:
            raise ContextCatalogError(f"{index_path}.contour is invalid")
        max_depth = data.get("max_depth")
        if not isinstance(max_depth, int) or isinstance(max_depth, bool) or max_depth < 1:
            raise ContextCatalogError(f"{index_path}.max_depth must be a positive integer")
        if root_max_depth is None:
            root_max_depth = max_depth
            root_contour = contour
        elif max_depth != root_max_depth or contour != root_contour:
            raise ContextCatalogError(
                f"{index_path} must retain root contour and max_depth"
            )
        if depth > max_depth:
            raise ContextCatalogError(
                f"context index depth {depth} exceeds max_depth {max_depth}: {index_path}"
            )
        for field in ("title", "summary"):
            if not isinstance(data.get(field), str) or not data[field]:
                raise ContextCatalogError(f"{index_path}.{field} must be non-empty")
        entries = data.get("entries")
        if not isinstance(entries, list):
            raise ContextCatalogError(f"{index_path}.entries must be a list")

        active_indexes.add(index_path)
        seen_indexes.add(index_path)
        indexes.append(index_path.relative_to(catalog_root).as_posix())
        for position, entry in enumerate(entries):
            label = f"{index_path}.entries[{position}]"
            if not isinstance(entry, dict):
                raise ContextCatalogError(f"{label} must be an object")
            required = {
                "id",
                "kind",
                "path",
                "summary",
                "selectors",
                "load_when",
                "semantic_refs",
                "owner_refs",
                "estimated_words",
                "content_digest",
            }
            if set(entry) != required:
                raise ContextCatalogError(
                    f"{label} must contain exactly {sorted(required)}"
                )
            item_id = entry.get("id")
            if not isinstance(item_id, str) or not item_id:
                raise ContextCatalogError(f"{label}.id must be non-empty")
            if item_id in seen_ids:
                raise ContextCatalogError(f"duplicate context ID: {item_id}")
            seen_ids.add(item_id)
            kind = entry.get("kind")
            if kind not in INDEX_ENTRY_KINDS:
                raise ContextCatalogError(f"{label}.kind is invalid")
            relpath = _safe_relative(entry.get("path"), f"{label}.path")
            target = _resolve_under(catalog_root, relpath, f"{label}.path")
            summary = entry.get("summary")
            if not isinstance(summary, str) or not summary:
                raise ContextCatalogError(f"{label}.summary must be non-empty")
            selectors = _validate_selectors(entry.get("selectors"), f"{label}.selectors")
            load_when = _string_list(entry.get("load_when"), f"{label}.load_when", non_empty=True)
            semantic_refs = _string_list(entry.get("semantic_refs"), f"{label}.semantic_refs")
            for term_id in semantic_refs:
                if not TERM_ID_RE.fullmatch(term_id):
                    raise ContextCatalogError(f"{label} has invalid semantic term {term_id}")
            owner_refs = _string_list(entry.get("owner_refs"), f"{label}.owner_refs")
            estimated_words = entry.get("estimated_words")
            if (
                not isinstance(estimated_words, int)
                or isinstance(estimated_words, bool)
                or estimated_words < 1
            ):
                raise ContextCatalogError(f"{label}.estimated_words must be positive")
            digest = entry.get("content_digest")
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                raise ContextCatalogError(f"{label}.content_digest must be sha256:<hex>")
            if not target.is_file():
                raise ContextCatalogError(f"{label}.path does not exist: {relpath}")
            if verify_content:
                if word_count(target) != estimated_words:
                    raise ContextCatalogError(f"{label}.estimated_words is stale")
                if file_digest(target) != digest:
                    raise ContextCatalogError(f"{label}.content_digest is stale")
            if kind == "index":
                visit(target, depth + 1)
                continue
            if relpath in seen_content_paths:
                raise ContextCatalogError(f"content path is indexed more than once: {relpath}")
            seen_content_paths.add(relpath)
            items.append(
                CatalogItem(
                    item_id=item_id,
                    kind=kind,
                    path=relpath,
                    summary=summary,
                    selectors=selectors,
                    load_when=load_when,
                    semantic_refs=semantic_refs,
                    owner_refs=owner_refs,
                    estimated_words=estimated_words,
                    content_digest=digest,
                )
            )
        active_indexes.remove(index_path)

    visit(root_index, 1)
    return CatalogResolution(indexes=tuple(indexes), items=tuple(items))


def load_codebook(
    index_path: Path,
    *,
    root: Path | None = None,
    required_terms: Iterable[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Load a semantic codebook and return the bounded required closure."""

    index_path = index_path.resolve()
    root = (root or index_path.parent).resolve()
    index = load_object(index_path)
    if index.get("schema_version") != CODEBOOK_SCHEMA_VERSION:
        raise ContextCatalogError("semantic codebook index schema_version is invalid")
    if index.get("index_kind") != CODEBOOK_INDEX_KIND:
        raise ContextCatalogError("semantic codebook index kind is invalid")
    shards = index.get("shards")
    if not isinstance(shards, list) or not shards:
        raise ContextCatalogError("semantic codebook index shards must be non-empty")

    terms: dict[str, dict[str, Any]] = {}
    shard_ids: set[str] = set()
    for position, descriptor in enumerate(shards):
        label = f"semantic codebook shards[{position}]"
        if not isinstance(descriptor, dict) or set(descriptor) != {
            "id",
            "path",
            "preload",
            "selectors",
            "term_ids",
            "content_digest",
        }:
            raise ContextCatalogError(f"{label} has invalid fields")
        shard_id = descriptor.get("id")
        if not isinstance(shard_id, str) or not shard_id or shard_id in shard_ids:
            raise ContextCatalogError(f"{label}.id is invalid or duplicated")
        shard_ids.add(shard_id)
        relpath = _safe_relative(descriptor.get("path"), f"{label}.path")
        shard_path = _resolve_under(root, relpath, f"{label}.path")
        if not shard_path.is_file() or file_digest(shard_path) != descriptor.get("content_digest"):
            raise ContextCatalogError(f"{label} is missing or has stale digest")
        _validate_selectors(descriptor.get("selectors"), f"{label}.selectors")
        declared_ids = _string_list(descriptor.get("term_ids"), f"{label}.term_ids", non_empty=True)
        if not isinstance(descriptor.get("preload"), bool):
            raise ContextCatalogError(f"{label}.preload must be boolean")
        shard = load_object(shard_path)
        if shard.get("schema_version") != CODEBOOK_SCHEMA_VERSION:
            raise ContextCatalogError(f"{shard_path} schema_version is invalid")
        if shard.get("record_kind") != CODEBOOK_SHARD_KIND:
            raise ContextCatalogError(f"{shard_path} record_kind is invalid")
        if shard.get("shard_id") != shard_id:
            raise ContextCatalogError(f"{shard_path}.shard_id differs from its index")
        if shard.get("preload") is not descriptor.get("preload"):
            raise ContextCatalogError(f"{shard_path}.preload differs from its index")
        shard_selectors = _validate_selectors(
            shard.get("selectors"), f"{shard_path}.selectors"
        )
        if shard_selectors != _validate_selectors(
            descriptor.get("selectors"), f"{label}.selectors"
        ):
            raise ContextCatalogError(f"{shard_path}.selectors differ from its index")
        entries = shard.get("terms")
        if not isinstance(entries, list) or not entries:
            raise ContextCatalogError(f"{shard_path}.terms must be non-empty")
        actual_ids: list[str] = []
        for term in entries:
            if not isinstance(term, dict):
                raise ContextCatalogError(f"{shard_path} contains a non-object term")
            required = {
                "id",
                "version",
                "definition",
                "owner_rule_id",
                "canonical_owner",
                "scope",
                "non_meanings",
                "depends_on",
                "replaced_by",
            }
            if set(term) != required:
                raise ContextCatalogError(f"{shard_path} term fields are invalid")
            term_id = term.get("id")
            if not isinstance(term_id, str) or not TERM_ID_RE.fullmatch(term_id):
                raise ContextCatalogError(f"{shard_path} has invalid term ID {term_id}")
            if term_id in terms:
                raise ContextCatalogError(f"duplicate semantic term: {term_id}")
            for field in ("definition", "owner_rule_id", "canonical_owner", "scope"):
                if not isinstance(term.get(field), str) or not term[field]:
                    raise ContextCatalogError(f"{term_id}.{field} must be non-empty")
            if not isinstance(term.get("version"), int) or term["version"] < 1:
                raise ContextCatalogError(f"{term_id}.version must be positive")
            _safe_relative(term["canonical_owner"], f"{term_id}.canonical_owner")
            _string_list(term.get("non_meanings"), f"{term_id}.non_meanings")
            dependencies = _string_list(term.get("depends_on"), f"{term_id}.depends_on")
            if any(not TERM_ID_RE.fullmatch(item) for item in dependencies):
                raise ContextCatalogError(f"{term_id} has invalid dependency IDs")
            replacement = term.get("replaced_by")
            if replacement is not None and (
                not isinstance(replacement, str) or not TERM_ID_RE.fullmatch(replacement)
            ):
                raise ContextCatalogError(f"{term_id}.replaced_by is invalid")
            actual_ids.append(term_id)
            terms[term_id] = term
        if list(declared_ids) != actual_ids:
            raise ContextCatalogError(f"{label}.term_ids differ from shard order")

    requested = set(required_terms or ())
    requested.update(
        term_id
        for descriptor in shards
        if descriptor.get("preload") is True
        for term_id in descriptor["term_ids"]
    )
    unknown = sorted(requested - set(terms))
    if unknown:
        raise ContextCatalogError(f"unknown semantic terms: {unknown}")

    resolved: dict[str, dict[str, Any]] = {}
    active: set[str] = set()

    def include(term_id: str) -> None:
        if term_id in active:
            raise ContextCatalogError(f"semantic term dependency cycle reaches {term_id}")
        if term_id in resolved:
            return
        active.add(term_id)
        for dependency in terms[term_id]["depends_on"]:
            if dependency not in terms:
                raise ContextCatalogError(f"{term_id} depends on unknown term {dependency}")
            include(dependency)
        active.remove(term_id)
        resolved[term_id] = terms[term_id]

    for term_id in sorted(requested):
        include(term_id)
    return resolved


def build_context_packet(
    *,
    profile: str,
    operation: str,
    selected_items: Iterable[CatalogItem],
    semantic_terms: dict[str, dict[str, Any]],
    max_words: int,
) -> dict[str, Any]:
    """Build a deterministic packet projection from selected catalog items."""

    items = sorted(selected_items, key=lambda item: item.item_id)
    required_refs = sorted({term for item in items for term in item.semantic_refs})
    missing = sorted(set(required_refs) - set(semantic_terms))
    if missing:
        raise ContextCatalogError(f"context packet has unresolved semantic terms: {missing}")
    selected_words = sum(item.estimated_words for item in items)
    semantic_words = sum(
        len(re.findall(r"\S+", semantic_terms[term_id]["definition"]))
        for term_id in semantic_terms
    )
    total_words = selected_words + semantic_words
    if total_words > max_words:
        raise ContextCatalogError(
            f"context packet uses {total_words} words and exceeds budget {max_words}"
        )
    payload = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "packet_kind": PACKET_KIND,
        "profile": profile,
        "operation": operation,
        "selected_items": [
            {
                "id": item.item_id,
                "path": item.path,
                "content_digest": item.content_digest,
                "reason": list(item.load_when),
            }
            for item in items
        ],
        "semantic_terms": [
            {
                "id": term_id,
                "version": semantic_terms[term_id]["version"],
                "definition": semantic_terms[term_id]["definition"],
                "canonical_owner": semantic_terms[term_id]["canonical_owner"],
            }
            for term_id in semantic_terms
        ],
        "budget": {
            "max_words": max_words,
            "selected_content_words": selected_words,
            "semantic_definition_words": semantic_words,
            "total_words": total_words,
        },
    }
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    payload["packet_digest"] = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
    return payload
