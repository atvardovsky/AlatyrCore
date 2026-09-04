"""Build deterministic, read-only context plans for installed Alatyr targets."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable

from context_catalog import (
    CatalogItem,
    ContextCatalogError,
    build_context_packet,
    catalog_content_stats,
    file_digest,
    load_codebook,
    validate_context_catalog,
)
from impact_graph import (
    ImpactGraph,
    ImpactGraphError,
    build_reverse_index,
    load_impact_graph,
    matching_node_ids,
    traverse_impact,
    validate_graph,
)


PLAN_SCHEMA_VERSION = 1
PLAN_KIND = "target-context-plan"
PLACEHOLDER_RE = re.compile(r"\{[A-Z][A-Z0-9_]*\}")
REQUIRED_CONTOURS = ("framework", "project", "assistant")


@dataclass(frozen=True)
class ContextPlanRequest:
    target: Path
    profile: str
    operation: str
    changed_paths: tuple[str, ...] = ()
    fact_ids: tuple[str, ...] = ()
    assistant_surface: str | None = None
    max_words: int | None = None


class ContextPlanningError(ValueError):
    """A structured, expected reason why a context plan cannot be used."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: str = "unavailable",
        upgrade_required: bool = False,
        details: dict[str, Any] | None = None,
        actions: Iterable[str] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.upgrade_required = upgrade_required
        self.details = details or {}
        self.actions = tuple(actions)


@dataclass(frozen=True)
class _Catalogs:
    items: tuple[CatalogItem, ...]
    by_id: dict[str, CatalogItem]
    by_path: dict[str, CatalogItem]
    evidence: tuple[dict[str, Any], ...]


def _canonical_digest(value: Any) -> str:
    content = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _normalize_relative(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContextPlanningError(
            "INVALID_RELATIVE_PATH", f"{label} must be a non-empty relative path",
            status="invalid-request",
        )
    normalized = value.strip().replace("\\", "/")
    posix = PurePosixPath(normalized)
    windows = PureWindowsPath(value.strip())
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or not posix.parts
        or any(part in {"", ".", ".."} for part in posix.parts)
    ):
        raise ContextPlanningError(
            "INVALID_RELATIVE_PATH",
            f"{label} must be normalized and target-relative: {value}",
            status="invalid-request",
        )
    return posix.as_posix()


def _target_path(target: Path, relpath: str, label: str) -> Path:
    normalized = _normalize_relative(relpath, label)
    candidate = (target / normalized).resolve()
    if candidate != target and target not in candidate.parents:
        raise ContextPlanningError(
            "TARGET_PATH_ESCAPE",
            f"{label} escapes the target repository: {relpath}",
            status="blocked",
        )
    return candidate


def _load_json(target: Path, relpath: str, label: str) -> dict[str, Any]:
    path = _target_path(target, relpath, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContextPlanningError(
            "ADAPTER_ARTIFACT_UNAVAILABLE",
            f"cannot load {relpath}: {exc}",
            upgrade_required=True,
            details={"path": relpath},
            actions=("install or update the target adapter artifact",),
        ) from exc
    if not isinstance(value, dict):
        raise ContextPlanningError(
            "ADAPTER_ARTIFACT_INVALID",
            f"{relpath} must contain a JSON object",
            upgrade_required=True,
            details={"path": relpath},
        )
    return value


def _placeholder_locations(value: Any, prefix: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, str) and PLACEHOLDER_RE.search(value):
        found.append(prefix)
    elif isinstance(value, dict):
        for key in sorted(value):
            found.extend(_placeholder_locations(value[key], f"{prefix}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_placeholder_locations(item, f"{prefix}[{index}]"))
    return found


def _require_concrete(value: Any, label: str) -> None:
    locations = _placeholder_locations(value)
    if locations:
        raise ContextPlanningError(
            "ADAPTER_PLACEHOLDERS_UNRESOLVED",
            f"{label} contains unresolved target placeholders",
            upgrade_required=True,
            details={"artifact": label, "locations": locations},
            actions=("complete the selected adapter records from target evidence",),
        )


def _load_router(target: Path) -> dict[str, Any]:
    router = _load_json(
        target, ".ai/assistant/context-router.json", "context router"
    )
    if router.get("schema_version") != 10 or router.get("router_kind") != "target-context-router":
        raise ContextPlanningError(
            "CONTEXT_ROUTER_UNSUPPORTED",
            "target context router must use schema 10 and target-context-router",
            upgrade_required=True,
            actions=("run the Alatyr framework-update assessment",),
        )
    return router


def _resolve_profile(
    target: Path, router: dict[str, Any], profile: str
) -> tuple[dict[str, Any], str]:
    profile_index = router.get("profile_index")
    if not isinstance(profile_index, dict) or profile not in profile_index:
        raise ContextPlanningError(
            "UNKNOWN_CONTEXT_PROFILE",
            f"unknown target context profile: {profile}",
            status="invalid-request",
            details={"available_profiles": sorted(profile_index or {})},
        )
    entry = profile_index[profile]
    if not isinstance(entry, dict) or not isinstance(entry.get("descriptor"), str):
        raise ContextPlanningError(
            "CONTEXT_PROFILE_INDEX_INVALID",
            f"target profile index entry is invalid: {profile}",
            upgrade_required=True,
        )
    _require_concrete(entry, f"profile index entry {profile}")
    descriptor_path = _normalize_relative(entry["descriptor"], "profile descriptor")
    descriptor = _load_json(target, descriptor_path, "profile descriptor")
    if (
        descriptor.get("schema_version") != 1
        or descriptor.get("descriptor_kind") != "target-context-profile"
        or descriptor.get("profile") != profile
    ):
        raise ContextPlanningError(
            "CONTEXT_PROFILE_INVALID",
            f"profile descriptor does not describe {profile}",
            upgrade_required=True,
            details={"path": descriptor_path},
        )
    _require_concrete(descriptor, descriptor_path)
    return descriptor, descriptor_path


def _resolve_operation(
    target: Path, router: dict[str, Any], requested: str
) -> tuple[dict[str, Any], str, str, str]:
    routing = router.get("operation_routing")
    if not isinstance(routing, dict):
        raise ContextPlanningError(
            "OPERATION_ROUTING_UNAVAILABLE",
            "target context router has no operation routing contract",
            upgrade_required=True,
        )
    index_path = _normalize_relative(str(routing.get("index", "")), "operation index")
    catalog_path = _normalize_relative(str(routing.get("catalog", "")), "operation catalog")
    index = _load_json(target, index_path, "operation index")
    catalog = _load_json(target, catalog_path, "operation catalog")
    if index.get("schema_version") != 1 or index.get("index_kind") != "target-operation-index":
        raise ContextPlanningError(
            "OPERATION_INDEX_INVALID", "target operation index is invalid",
            upgrade_required=True,
        )
    if (
        catalog.get("schema_version") != 1
        or catalog.get("catalog_kind") != "target-operation-catalog"
    ):
        raise ContextPlanningError(
            "OPERATION_CATALOG_INVALID", "target operation catalog is invalid",
            upgrade_required=True,
        )
    if index.get("catalog") != catalog_path:
        raise ContextPlanningError(
            "OPERATION_INDEX_STALE",
            "operation index does not point to the active operation catalog",
            upgrade_required=True,
        )
    aliases = index.get("aliases")
    indexed_operations = index.get("operations")
    if not isinstance(aliases, dict) or not isinstance(indexed_operations, dict):
        raise ContextPlanningError(
            "OPERATION_INDEX_INVALID", "target operation index entries are invalid",
            upgrade_required=True,
        )
    operation_id = aliases.get(requested, requested)
    operations = catalog.get("operations")
    if not isinstance(operations, list):
        operations = []
    by_id = {
        operation.get("id"): operation
        for operation in operations
        if isinstance(operation, dict) and isinstance(operation.get("id"), str)
    }
    operation = by_id.get(operation_id)
    if operation is None:
        raise ContextPlanningError(
            "UNKNOWN_OPERATION",
            f"unknown target operation or alias: {requested}",
            status="invalid-request",
            details={"available_operations": sorted(by_id)},
        )
    _require_concrete(operation, f"operation {operation_id}")
    expected_index = [
        operation.get("required_module"),
        operation.get("flow"),
        *operation.get("allowed_actions", []),
    ]
    if indexed_operations.get(operation_id) != expected_index:
        raise ContextPlanningError(
            "OPERATION_INDEX_STALE",
            f"compact operation route is stale: {operation_id}",
            upgrade_required=True,
        )
    return operation, operation_id, index_path, catalog_path


def _load_catalogs(target: Path, router: dict[str, Any]) -> _Catalogs:
    recursive = router.get("recursive_context")
    indexes = recursive.get("contour_indexes") if isinstance(recursive, dict) else None
    if not isinstance(indexes, dict) or set(indexes) != set(REQUIRED_CONTOURS):
        raise ContextPlanningError(
            "RECURSIVE_CONTEXT_UNAVAILABLE",
            "target router must define framework, project, and assistant context indexes",
            upgrade_required=True,
        )
    items: list[CatalogItem] = []
    evidence: list[dict[str, Any]] = []
    try:
        for contour in REQUIRED_CONTOURS:
            relpath = _normalize_relative(str(indexes[contour]), f"{contour} context index")
            root_index = _target_path(target, relpath, f"{contour} context index")
            catalog_root = root_index.parent
            resolution = validate_context_catalog(
                root_index, catalog_root=catalog_root, verify_content=False
            )
            prefix = root_index.parent.relative_to(target).as_posix()
            items.extend(
                replace(item, path=f"{prefix}/{item.path}")
                for item in resolution.items
            )
            evidence.append(
                {
                    "contour": contour,
                    "root_index": relpath,
                    "root_index_digest": file_digest(root_index),
                    "index_count": len(resolution.indexes),
                    "item_count": len(resolution.items),
                }
            )
    except (ContextCatalogError, OSError, ValueError) as exc:
        raise ContextPlanningError(
            "CONTEXT_CATALOG_STALE",
            f"recursive target context catalog is unavailable or stale: {exc}",
            upgrade_required=True,
            actions=("regenerate and validate installed recursive context catalogs",),
        ) from exc
    by_id: dict[str, CatalogItem] = {}
    by_path: dict[str, CatalogItem] = {}
    for item in items:
        if item.item_id in by_id or item.path in by_path:
            raise ContextPlanningError(
                "CONTEXT_CATALOG_COLLISION",
                f"duplicate context identity or path: {item.item_id} / {item.path}",
                upgrade_required=True,
            )
        by_id[item.item_id] = item
        by_path[item.path] = item
    return _Catalogs(tuple(items), by_id, by_path, tuple(evidence))


def _select_path(
    relpath: str,
    reason: str,
    catalogs: _Catalogs,
    selected: dict[str, CatalogItem],
    reasons: dict[str, set[str]],
) -> None:
    normalized = _normalize_relative(relpath, "selected context path")
    if PLACEHOLDER_RE.search(normalized):
        _require_concrete(normalized, normalized)
    item = catalogs.by_path.get(normalized)
    if item is None:
        raise ContextPlanningError(
            "REQUIRED_CONTEXT_UNINDEXED",
            f"required context is absent from recursive catalogs: {normalized}",
            upgrade_required=True,
            details={"path": normalized, "reason": reason},
            actions=("regenerate context indexes after repairing the canonical adapter source",),
        )
    selected[item.item_id] = item
    reasons.setdefault(item.item_id, set()).add(reason)


def _synthetic_file_item(
    target: Path, relpath: str, item_id: str, reason: str
) -> CatalogItem:
    path = _target_path(target, relpath, "graph-selected context")
    if not path.is_file():
        raise ContextPlanningError(
            "CANONICAL_OWNER_UNAVAILABLE",
            f"graph-selected canonical context is not a file: {relpath}",
            status="blocked",
            details={"path": relpath},
        )
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise ContextPlanningError(
            "CANONICAL_OWNER_UNREADABLE",
            f"graph-selected canonical context cannot be read as UTF-8: {relpath}",
            status="blocked",
        ) from exc
    return CatalogItem(
        item_id=item_id,
        kind="content",
        path=relpath,
        summary="graph-selected canonical target context",
        selectors={},
        load_when=(reason,),
        semantic_refs=(),
        owner_refs=(),
        estimated_words=len(re.findall(r"\S+", text)),
        content_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
    )


def _select_synthetic(
    item: CatalogItem,
    reason: str,
    selected: dict[str, CatalogItem],
    reasons: dict[str, set[str]],
) -> None:
    existing = selected.get(item.item_id)
    if existing is not None and existing != item:
        raise ContextPlanningError(
            "CONTEXT_ID_COLLISION", f"context item ID collision: {item.item_id}",
            status="blocked",
        )
    selected[item.item_id] = item
    reasons.setdefault(item.item_id, set()).add(reason)


def _load_reverse_index(target: Path, graph: ImpactGraph) -> tuple[dict[str, Any], str]:
    relpath = graph.root.get("reverse_index")
    if not isinstance(relpath, str) or not relpath:
        relpath = ".ai/assistant/consistency-reverse-index.json"
    relpath = _normalize_relative(relpath, "consistency reverse index")
    reverse = _load_json(target, relpath, "consistency reverse index")
    expected = build_reverse_index(graph)
    if reverse != expected:
        raise ContextPlanningError(
            "CONSISTENCY_REVERSE_INDEX_STALE",
            "installed consistency reverse index differs from the active graph",
            upgrade_required=True,
            details={"path": relpath, "graph_digest": graph.graph_digest},
            actions=("regenerate the consistency reverse index",),
        )
    return reverse, relpath


def _impact_selection(
    request: ContextPlanRequest,
    target: Path,
    router: dict[str, Any],
    catalogs: _Catalogs,
    selected: dict[str, CatalogItem],
    reasons: dict[str, set[str]],
) -> dict[str, Any]:
    if not request.changed_paths and not request.fact_ids:
        return {
            "used": False,
            "graph_digest": None,
            "changed_path_matches": {},
            "selected_node_ids": [],
            "selected_edges": [],
            "skipped_edges": [],
            "canonical_owners": [],
            "impacted_surfaces": [],
            "unresolved_relationships": [],
        }
    routing_ref = router.get("consistency_routing")
    descriptor_path = routing_ref.get("descriptor") if isinstance(routing_ref, dict) else None
    if not isinstance(descriptor_path, str):
        raise ContextPlanningError(
            "CONSISTENCY_ROUTING_UNAVAILABLE",
            "changed facts or paths require installed consistency routing",
            upgrade_required=True,
        )
    descriptor_path = _normalize_relative(descriptor_path, "consistency routing descriptor")
    descriptor = _load_json(target, descriptor_path, "consistency routing descriptor")
    _require_concrete(descriptor, descriptor_path)
    _select_path(descriptor_path, "consistency-routing-descriptor", catalogs, selected, reasons)
    required = descriptor.get("required_context")
    if not isinstance(required, list) or not required:
        raise ContextPlanningError(
            "CONSISTENCY_ROUTING_INVALID",
            "consistency routing must declare required context",
            upgrade_required=True,
        )
    for relpath in required:
        if not isinstance(relpath, str):
            raise ContextPlanningError(
                "CONSISTENCY_ROUTING_INVALID",
                "consistency routing required context must contain paths",
                upgrade_required=True,
            )
        _select_path(relpath, "consistency-routing-required", catalogs, selected, reasons)
    try:
        graph = load_impact_graph(target)
        graph_failures = validate_graph(graph)
    except ImpactGraphError as exc:
        raise ContextPlanningError(
            "CONSISTENCY_GRAPH_UNAVAILABLE",
            f"cannot load target consistency graph: {exc}",
            upgrade_required=True,
        ) from exc
    if graph_failures:
        raise ContextPlanningError(
            "CONSISTENCY_GRAPH_INVALID",
            "target consistency graph failed structural validation",
            upgrade_required=True,
            details={"failures": graph_failures},
        )
    reverse, reverse_path = _load_reverse_index(target, graph)
    for graph_path in graph.source_paths:
        _select_path(graph_path, "active-consistency-graph", catalogs, selected, reasons)
    _select_path(reverse_path, "active-consistency-reverse-index", catalogs, selected, reasons)

    changed_path_matches = {
        path: sorted(matching_node_ids(reverse, path)) for path in request.changed_paths
    }
    direct_catalog_paths = {
        path for path in request.changed_paths if path in catalogs.by_path
    }
    for path in sorted(direct_catalog_paths):
        _select_path(path, "explicit-changed-support-path", catalogs, selected, reasons)
    unmapped = sorted(
        path
        for path, matches in changed_path_matches.items()
        if not matches and path not in direct_catalog_paths
    )
    if unmapped:
        raise ContextPlanningError(
            "CHANGED_PATH_UNMAPPED",
            "changed paths are not covered by recursive context or the consistency graph",
            status="blocked",
            upgrade_required=True,
            details={
                "unmapped_paths": unmapped,
                "relationship_candidate_policy": "review and map; never promote automatically",
            },
            actions=(
                "review the changed paths for new or missing project relationships",
                "update accepted target consistency evidence before using a bounded plan",
            ),
        )
    start_ids = set(request.fact_ids)
    for matches in changed_path_matches.values():
        start_ids.update(matches)
    unknown_facts = sorted(start_ids - graph.nodes.keys())
    if unknown_facts:
        raise ContextPlanningError(
            "UNKNOWN_FACT_ID",
            "requested fact IDs are absent from the target consistency graph",
            status="blocked",
            upgrade_required=True,
            details={"fact_ids": unknown_facts},
        )
    policy = graph.root.get("impact_policy")
    policy = policy if isinstance(policy, dict) else {}
    max_depth = policy.get("max_depth", 4)
    max_nodes = policy.get("max_nodes", 100)
    if not isinstance(max_depth, int) or not isinstance(max_nodes, int):
        raise ContextPlanningError(
            "CONSISTENCY_IMPACT_POLICY_INVALID",
            "consistency impact limits must be integers",
            upgrade_required=True,
        )
    try:
        node_ids, selected_edges, skipped_edges = traverse_impact(
            graph, start_ids, max_depth=max_depth, max_nodes=max_nodes
        )
    except ImpactGraphError as exc:
        raise ContextPlanningError(
            "IMPACT_TRAVERSAL_BLOCKED", str(exc), status="blocked"
        ) from exc
    depth_limited = [
        edge for edge in skipped_edges if edge.get("reason") == "depth-limit"
    ]
    if depth_limited:
        raise ContextPlanningError(
            "IMPACT_DEPTH_EXCEEDED",
            "accepted impact relationships exceed the configured traversal depth",
            status="blocked",
            details={"skipped_edges": depth_limited, "max_depth": max_depth},
        )

    canonical_owners: list[dict[str, Any]] = []
    impacted_surfaces: list[dict[str, Any]] = []
    for node_id in node_ids:
        node = graph.nodes[node_id]
        owner = node.get("canonical_owner")
        if isinstance(owner, str) and owner:
            owner = _normalize_relative(owner, f"canonical owner for {node_id}")
            if PLACEHOLDER_RE.search(owner):
                _require_concrete(owner, f"canonical owner for {node_id}")
            owner_path = _target_path(target, owner, f"canonical owner for {node_id}")
            owner_record: dict[str, Any] = {"node_id": node_id, "path": owner}
            if owner in catalogs.by_path:
                _select_path(owner, f"canonical-owner:{node_id}", catalogs, selected, reasons)
                owner_record.update(
                    {"kind": "indexed-file", "context_id": catalogs.by_path[owner].item_id}
                )
            elif owner_path.is_file():
                synthetic = _synthetic_file_item(
                    target, owner, f"impact.owner.{node_id}", f"canonical-owner:{node_id}"
                )
                _select_synthetic(
                    synthetic, f"canonical-owner:{node_id}", selected, reasons
                )
                owner_record.update(
                    {"kind": "target-file", "context_id": synthetic.item_id}
                )
            elif owner_path.is_dir():
                owner_record["kind"] = "target-directory"
            else:
                raise ContextPlanningError(
                    "CANONICAL_OWNER_UNAVAILABLE",
                    f"canonical owner is missing for {node_id}: {owner}",
                    status="blocked",
                )
            canonical_owners.append(owner_record)
        for binding in node.get("bindings", []):
            if not isinstance(binding, dict):
                continue
            impacted_surfaces.append(
                {
                    "node_id": node_id,
                    "binding_id": binding.get("id"),
                    "path": binding.get("path"),
                    "selector_kind": binding.get("selector_kind"),
                    "surface_kind": binding.get("surface_kind"),
                    "authority": binding.get("authority"),
                }
            )
            for context_id in binding.get("context_ids", []):
                if not isinstance(context_id, str) or PLACEHOLDER_RE.search(context_id):
                    raise ContextPlanningError(
                        "IMPACT_CONTEXT_ID_INVALID",
                        f"impact binding has an invalid context ID: {context_id!r}",
                        upgrade_required=True,
                    )
                item = catalogs.by_id.get(context_id)
                if item is None:
                    raise ContextPlanningError(
                        "IMPACT_CONTEXT_ID_UNRESOLVED",
                        f"impact context ID is absent from recursive catalogs: {context_id}",
                        upgrade_required=True,
                    )
                selected[item.item_id] = item
                reasons.setdefault(item.item_id, set()).add(
                    f"impact-context:{node_id}"
                )
    for path in request.changed_paths:
        source = _target_path(target, path, "changed path")
        if source.is_file() and path not in catalogs.by_path:
            item = _synthetic_file_item(
                target,
                path,
                "task.path." + hashlib.sha256(path.encode("utf-8")).hexdigest()[:16],
                "explicit-changed-path",
            )
            _select_synthetic(item, "explicit-changed-path", selected, reasons)
    return {
        "used": True,
        "graph_digest": graph.graph_digest,
        "changed_path_matches": changed_path_matches,
        "selected_node_ids": node_ids,
        "selected_edges": selected_edges,
        "skipped_edges": skipped_edges,
        "canonical_owners": canonical_owners,
        "impacted_surfaces": impacted_surfaces,
        "unresolved_relationships": [],
        "limits": {"max_depth": max_depth, "max_nodes": max_nodes},
    }


def _add_owner_closure(
    catalogs: _Catalogs,
    selected: dict[str, CatalogItem],
    reasons: dict[str, set[str]],
) -> None:
    by_rule: dict[str, list[CatalogItem]] = {}
    for item in catalogs.items:
        for rule_id in item.selectors.get("rule_ids", ()):
            by_rule.setdefault(rule_id, []).append(item)
    pending = list(selected.values())
    visited: set[str] = set()
    while pending:
        item = pending.pop()
        if item.item_id in visited:
            continue
        visited.add(item.item_id)
        for owner_ref in item.owner_refs:
            candidates = by_rule.get(owner_ref, [])
            if len(candidates) != 1:
                raise ContextPlanningError(
                    "OWNER_REFERENCE_UNRESOLVED",
                    f"owner reference {owner_ref} resolves to {len(candidates)} context items",
                    upgrade_required=True,
                    details={"source_context_id": item.item_id},
                )
            owner = candidates[0]
            if owner.item_id not in selected:
                selected[owner.item_id] = owner
                pending.append(owner)
            reasons.setdefault(owner.item_id, set()).add(
                f"owner-reference:{owner_ref}"
            )


def _verify_selected_content(
    target: Path, selected: Iterable[CatalogItem]
) -> None:
    """Verify only the content leaves selected by the bounded routing plan."""

    try:
        for item in selected:
            stats = catalog_content_stats(target / item.path)
            if stats.words != item.estimated_words:
                raise ContextCatalogError(
                    f"{item.path}.estimated_words is stale"
                )
            if stats.digest != item.content_digest:
                raise ContextCatalogError(
                    f"{item.path}.content_digest is stale"
                )
    except (ContextCatalogError, OSError, UnicodeError) as exc:
        raise ContextPlanningError(
            "CONTEXT_CATALOG_STALE",
            f"selected context content is unavailable or stale: {exc}",
            upgrade_required=True,
            actions=("regenerate the selected context catalog branch",),
        ) from exc


def _resolve_surface(
    target: Path, router: dict[str, Any], requested: str | None
) -> tuple[str, dict[str, str]]:
    delivery = router.get("cache_aware_delivery")
    index_path = delivery.get("provider_capability_index") if isinstance(delivery, dict) else None
    if not isinstance(index_path, str):
        raise ContextPlanningError(
            "ASSISTANT_CAPABILITY_INDEX_UNAVAILABLE",
            "router does not identify the assistant capability index",
            upgrade_required=True,
        )
    index_path = _normalize_relative(index_path, "assistant capability index")
    index = _load_json(target, index_path, "assistant capability index")
    surfaces = index.get("surfaces")
    if not isinstance(surfaces, dict):
        raise ContextPlanningError(
            "ASSISTANT_CAPABILITY_INDEX_INVALID",
            "assistant capability index has no surfaces",
            upgrade_required=True,
        )
    surface = requested or index.get("default_surface")
    if not isinstance(surface, str) or surface not in surfaces:
        raise ContextPlanningError(
            "UNKNOWN_ASSISTANT_SURFACE",
            f"unknown assistant surface: {surface}",
            status="invalid-request",
            details={"available_surfaces": sorted(surfaces)},
        )
    record_path = surfaces[surface]
    if not isinstance(record_path, str):
        raise ContextPlanningError(
            "ASSISTANT_CAPABILITY_INDEX_INVALID",
            f"assistant surface path is invalid: {surface}",
            upgrade_required=True,
        )
    record = _load_json(target, record_path, "assistant capability record")
    if record.get("assistant_surface") != surface:
        raise ContextPlanningError(
            "ASSISTANT_CAPABILITY_RECORD_INVALID",
            f"assistant capability record differs from selected surface: {surface}",
            upgrade_required=True,
        )
    _require_concrete(record, record_path)
    return surface, {
        "index": index_path,
        "index_digest": file_digest(
            _target_path(target, index_path, "assistant capability index")
        ),
        "record": record_path,
        "record_digest": file_digest(
            _target_path(target, record_path, "assistant capability record")
        ),
    }


def _packet_projection(packet: dict[str, Any]) -> dict[str, Any]:
    semantic_identities = [
        {
            "id": term["id"],
            "version": term["version"],
            "canonical_owner": term["canonical_owner"],
            "definition_digest": _canonical_digest(term["definition"]),
        }
        for term in packet["semantic_terms"]
    ]
    projection = {
        "schema_version": 1,
        "projection_kind": "target-context-packet-projection",
        "source_packet": {
            "schema_version": packet["schema_version"],
            "packet_kind": packet["packet_kind"],
            "content_bound_digest": packet["packet_digest"],
        },
        "cache_delivery": packet["cache_delivery"],
        "semantic_term_identities": semantic_identities,
        "profile": packet["profile"],
        "operation": packet["operation"],
        "task_classification": packet["task_classification"],
        "selected_items": packet["selected_items"],
        "routing": packet["routing"],
        "budget": packet["budget"],
        "receipt": packet["receipt"],
    }
    projection["projection_digest"] = _canonical_digest(projection)
    return projection


def _semantic_terms(
    target: Path,
    router: dict[str, Any],
    selected: Iterable[CatalogItem],
    profile: str,
    operation: str,
) -> tuple[dict[str, dict[str, Any]], str]:
    config = router.get("semantic_codebook")
    if not isinstance(config, dict) or not isinstance(config.get("index"), str):
        raise ContextPlanningError(
            "SEMANTIC_CODEBOOK_UNAVAILABLE",
            "target router does not identify an installed semantic codebook",
            upgrade_required=True,
        )
    index_path = _normalize_relative(config["index"], "semantic codebook index")
    codebook_index = _load_json(target, index_path, "semantic codebook index")
    required = {term for item in selected for term in item.semantic_refs}
    try:
        terms = load_codebook(
            _target_path(target, index_path, "semantic codebook index"),
            root=_target_path(target, index_path, "semantic codebook index").parent,
            required_terms=required,
            selectors={"task_profiles": profile, "operations": operation},
        )
    except (ContextCatalogError, OSError) as exc:
        raise ContextPlanningError(
            "SEMANTIC_CODEBOOK_STALE",
            f"installed semantic codebook is unavailable or stale: {exc}",
            upgrade_required=True,
            actions=("regenerate and validate the installed semantic codebook",),
        ) from exc
    configured_preload = config.get("preload_terms")
    shards = codebook_index.get("shards")
    declared_preload: list[str] = []
    if isinstance(shards, list):
        for shard in shards:
            if isinstance(shard, dict) and shard.get("preload") is True:
                declared_preload.extend(
                    term_id
                    for term_id in shard.get("term_ids", [])
                    if isinstance(term_id, str)
                )
    if configured_preload != declared_preload or not all(
        isinstance(term, str) and term in terms for term in configured_preload or []
    ):
        raise ContextPlanningError(
            "SEMANTIC_PRELOAD_STALE",
            "router semantic preload does not resolve through the installed codebook",
            upgrade_required=True,
        )
    owner_root = _target_path(target, index_path, "semantic codebook index").parent.parent
    for term_id, term in terms.items():
        owner = term.get("canonical_owner")
        if not isinstance(owner, str):
            raise ContextPlanningError(
                "SEMANTIC_OWNER_UNAVAILABLE",
                f"semantic term has no canonical owner: {term_id}",
                upgrade_required=True,
            )
        owner_path = (
            owner_root / _normalize_relative(owner, f"semantic owner {term_id}")
        ).resolve()
        if owner_path != owner_root and owner_root not in owner_path.parents:
            raise ContextPlanningError(
                "SEMANTIC_OWNER_UNAVAILABLE",
                f"semantic owner escapes the framework contour: {term_id}",
                upgrade_required=True,
            )
        if not owner_path.is_file():
            raise ContextPlanningError(
                "SEMANTIC_OWNER_UNAVAILABLE",
                f"semantic canonical owner is missing: {term_id}",
                upgrade_required=True,
                details={"canonical_owner": owner},
            )
    return terms, index_path


def _ready_plan(request: ContextPlanRequest) -> dict[str, Any]:
    target = request.target.resolve()
    if not target.is_dir():
        raise ContextPlanningError(
            "TARGET_UNAVAILABLE", "target repository directory does not exist",
            status="invalid-request",
        )
    router = _load_router(target)
    descriptor, descriptor_path = _resolve_profile(target, router, request.profile)
    operation, operation_id, operation_index_path, operation_catalog_path = _resolve_operation(
        target, router, request.operation
    )
    operation_profiles = operation.get("context_profiles")
    if not isinstance(operation_profiles, list):
        raise ContextPlanningError(
            "OPERATION_PROFILE_CONTRACT_INVALID",
            f"operation has no valid context profile list: {operation_id}",
            upgrade_required=True,
        )
    if operation_profiles and request.profile not in operation_profiles:
        raise ContextPlanningError(
            "OPERATION_PROFILE_MISMATCH",
            f"operation {operation_id} does not permit profile {request.profile}",
            status="invalid-request",
            details={"permitted_profiles": operation_profiles},
        )
    candidates = descriptor.get("operation_candidates")
    if operation_profiles and (
        not isinstance(candidates, list) or operation_id not in candidates
    ):
        raise ContextPlanningError(
            "PROFILE_OPERATION_ROUTING_STALE",
            f"profile {request.profile} does not route operation {operation_id}",
            upgrade_required=True,
        )
    catalogs = _load_catalogs(target, router)
    surface, surface_evidence = _resolve_surface(
        target, router, request.assistant_surface
    )
    selected: dict[str, CatalogItem] = {}
    reasons: dict[str, set[str]] = {}
    _select_path(descriptor_path, "selected-profile-descriptor", catalogs, selected, reasons)
    required_context = descriptor.get("required_context")
    if not isinstance(required_context, list) or not required_context:
        raise ContextPlanningError(
            "CONTEXT_PROFILE_INVALID",
            f"profile has no required context: {request.profile}",
            upgrade_required=True,
        )
    for relpath in required_context:
        if not isinstance(relpath, str):
            raise ContextPlanningError(
                "CONTEXT_PROFILE_INVALID",
                f"profile required context must contain paths: {request.profile}",
                upgrade_required=True,
            )
        _select_path(relpath, "profile-required-context", catalogs, selected, reasons)
    flow = operation.get("flow")
    if not isinstance(flow, str):
        raise ContextPlanningError(
            "OPERATION_FLOW_INVALID", f"operation has no flow: {operation_id}",
            upgrade_required=True,
        )
    _select_path(flow, "operation-flow", catalogs, selected, reasons)
    impact = _impact_selection(
        request, target, router, catalogs, selected, reasons
    )
    _add_owner_closure(catalogs, selected, reasons)
    _verify_selected_content(target, selected.values())
    terms, semantic_index_path = _semantic_terms(
        target, router, selected.values(), request.profile, operation_id
    )
    budget = router.get("context_budgets", {}).get("profile_default", {})
    configured_words = budget.get("max_total_words")
    configured_files = budget.get("max_files")
    if not isinstance(configured_words, int) or not isinstance(configured_files, int):
        raise ContextPlanningError(
            "CONTEXT_BUDGET_INVALID",
            "target router profile budget is invalid",
            upgrade_required=True,
        )
    if request.max_words is not None and request.max_words < 1:
        raise ContextPlanningError(
            "INVALID_CONTEXT_BUDGET", "--max-words must be positive",
            status="invalid-request",
        )
    if request.max_words is not None and request.max_words > configured_words:
        raise ContextPlanningError(
            "CONTEXT_BUDGET_OVERRIDE_TOO_LARGE",
            "requested context budget exceeds the target router limit",
            status="invalid-request",
            details={"requested": request.max_words, "configured": configured_words},
        )
    max_words = request.max_words or configured_words
    if len(selected) > configured_files:
        raise ContextPlanningError(
            "CONTEXT_FILE_BUDGET_EXCEEDED",
            "required context exceeds the configured file budget",
            status="blocked",
            details={"required_files": len(selected), "max_files": configured_files},
            actions=("record a context expansion or split the task without omitting owners",),
        )
    normalized_reasons = {
        item_id: sorted(values) for item_id, values in sorted(reasons.items())
    }
    try:
        content_packet = build_context_packet(
            profile=request.profile,
            operation=operation_id,
            selected_items=selected.values(),
            semantic_terms=terms,
            max_words=max_words,
            assistant_surface=surface,
            selection_reasons=normalized_reasons,
            expansion_triggers=(
                "changed paths or facts selected bounded consistency relationships",
            ) if impact["used"] else (),
        )
    except ContextCatalogError as exc:
        if "exceeds budget" in str(exc):
            raise ContextPlanningError(
                "CONTEXT_WORD_BUDGET_EXCEEDED",
                str(exc),
                status="blocked",
                details={
                    "max_words": max_words,
                    "selected_content_words": sum(
                        item.estimated_words for item in selected.values()
                    ),
                },
                actions=("record a context expansion or split the task without omitting owners",),
            ) from exc
        raise ContextPlanningError(
            "CONTEXT_PACKET_INVALID", str(exc), upgrade_required=True
        ) from exc
    packet = _packet_projection(content_packet)
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_kind": PLAN_KIND,
        "status": "ready",
        "read_only": True,
        "upgrade_required": False,
        "request": {
            "profile": request.profile,
            "requested_operation": request.operation,
            "operation": operation_id,
            "changed_paths": list(request.changed_paths),
            "fact_ids": list(request.fact_ids),
            "assistant_surface": surface,
            "max_words": max_words,
        },
        "routing_sources": {
            "context_router": ".ai/assistant/context-router.json",
            "context_router_digest": file_digest(
                target / ".ai/assistant/context-router.json"
            ),
            "profile_descriptor": descriptor_path,
            "profile_descriptor_digest": file_digest(target / descriptor_path),
            "operation_index": operation_index_path,
            "operation_index_digest": file_digest(target / operation_index_path),
            "operation_catalog": operation_catalog_path,
            "operation_catalog_digest": file_digest(target / operation_catalog_path),
            "semantic_codebook": semantic_index_path,
            "semantic_codebook_digest": file_digest(target / semantic_index_path),
            "assistant_capability": surface_evidence,
            "catalogs": list(catalogs.evidence),
        },
        "impact": impact,
        "context_packet": packet,
        "omission_summary": {
            "unselected_catalog_item_count": len(catalogs.items) - sum(
                1 for item_id in selected if item_id in catalogs.by_id
            ),
            "policy": "unselected catalog branches remain unloaded",
        },
        "reasoning_boundary": (
            "deterministic routing selects context candidates; it does not prove "
            "semantic correctness, model delivery, comprehension, or compliance"
        ),
    }
    plan["plan_digest"] = _canonical_digest(plan)
    return plan


def _error_plan(request: ContextPlanRequest, error: ContextPlanningError) -> dict[str, Any]:
    result = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_kind": PLAN_KIND,
        "status": error.status,
        "read_only": True,
        "upgrade_required": error.upgrade_required,
        "request": {
            "profile": request.profile,
            "requested_operation": request.operation,
            "changed_paths": list(request.changed_paths),
            "fact_ids": list(request.fact_ids),
            "assistant_surface": request.assistant_surface,
            "max_words": request.max_words,
        },
        "errors": [
            {
                "code": error.code,
                "message": str(error),
                "details": error.details,
            }
        ],
        "required_actions": list(error.actions),
        "context_packet": None,
    }
    result["plan_digest"] = _canonical_digest(result)
    return result


def plan_target_context(request: ContextPlanRequest) -> dict[str, Any]:
    """Return a usable context plan or structured fail-closed evidence."""

    try:
        normalized = replace(
            request,
            changed_paths=tuple(
                sorted(
                    {
                        _normalize_relative(path, "changed path")
                        for path in request.changed_paths
                    }
                )
            ),
            fact_ids=tuple(sorted(set(request.fact_ids))),
        )
        if any(not fact_id or PLACEHOLDER_RE.search(fact_id) for fact_id in normalized.fact_ids):
            raise ContextPlanningError(
                "INVALID_FACT_ID", "fact IDs must be concrete non-empty values",
                status="invalid-request",
            )
        return _ready_plan(normalized)
    except ContextPlanningError as exc:
        return _error_plan(request, exc)
