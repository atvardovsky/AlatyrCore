"""Build deterministic, read-only context plans for installed Alatyr targets."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable
from architecture_context import architecture_context
from validation_route_contract import CONTRACT_PATH, validation_route_failures
from context_input_snapshot import ContextInputChanged, ContextInputLimit, ContextInputSnapshot, read_context_bytes

from context_catalog import (
    CatalogItem,
    ContextCatalogError,
    ContextCatalogVersionError,
    build_context_packet,
    catalog_content_stats,
    file_digest,
    load_codebook,
    discover_context_catalog,
)
from context_recovery import decomposition_proposal
from reviewed_warnings import selected_candidate_warnings
from impact_graph import (
    ImpactGraph,
    ImpactGraphError,
    ImpactLookup,
    CHANGE_KINDS,
    load_impact_graph,
    relationship_review_paths,
    validate_graph,
    assert_graph_current,
)


PLAN_SCHEMA_VERSION = 1
PLAN_KIND = "target-context-plan"
PLACEHOLDER_RE = re.compile(r"\{[A-Z][A-Z0-9_]*\}")
REQUIRED_CONTOURS = ("framework", "project", "assistant")
ROUTER_PATH = ".ai/assistant/context-router.json"


@dataclass(frozen=True)
class ContextPlanRequest:
    target: Path
    profile: str
    operation: str
    changed_paths: tuple[str, ...] = ()
    fact_ids: tuple[str, ...] = ()
    assistant_surface: str | None = None
    max_words: int | None = None
    max_characters: int | None = None
    architecture_mode: str | None = None
    document_warnings: bool = False
    change_kinds: tuple[str, ...] = ()
    working_set_request: str | None = None
    previous_plan: str | None = None
    delivery_observation: str | None = None
    knowledge_request: str | None = None


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


def _field_error(artifact: str, field: str, expected: str, value: Any) -> ContextPlanningError:
    return ContextPlanningError(
        "INVALID_CONTEXT_PLAN_REQUEST" if artifact == "request" else "ADAPTER_FIELD_INVALID",
        f"{artifact}:{field} must be {expected}; got {type(value).__name__}",
        status="invalid-request" if artifact == "request" else "blocked",
        details={"artifact": artifact, "field": field, "expected": expected,
                 "actual_type": type(value).__name__},
        actions=("repair the reported field before planning context",),
    )


def _object(value: Any, artifact: str, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _field_error(artifact, field, "an object", value)
    return value


def _text(value: Any, artifact: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _field_error(artifact, field, "a non-empty string", value)
    return value


def _string_list(value: Any, artifact: str, field: str, *, non_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (non_empty and not value):
        raise _field_error(artifact, field, "a non-empty string list" if non_empty else "a string list", value)
    for index, entry in enumerate(value):
        _text(entry, artifact, f"{field}[{index}]")
    return value


def _positive_integer(value: Any, artifact: str, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise _field_error(artifact, field, "a positive integer", value)
    return value


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
        or "\x00" in normalized
        or not posix.parts
        or any(part in {"", ".", ".."} for part in posix.parts)
    ):
        raise ContextPlanningError(
            "INVALID_RELATIVE_PATH",
            f"{label} must be normalized and target-relative: {value}",
            status="invalid-request",
        )
    return posix.as_posix()


def _artifact_path(value: Any, artifact: str, field: str) -> str:
    value = _text(value, artifact, field)
    try:
        return _normalize_relative(value, f"{artifact}:{field}")
    except ContextPlanningError as exc:
        raise ContextPlanningError(
            exc.code, str(exc), status="blocked",
            details={"artifact": artifact, "field": field},
        ) from exc


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


def _load_json(target: Path, relpath: str, label: str, *, digest_evidence: dict[str, str] | None = None, max_bytes: int | None = None) -> dict[str, Any]:
    path = _target_path(target, relpath, label)
    try:
        raw = read_context_bytes(path, max_bytes=max_bytes)
        value = json.loads(raw.decode("utf-8"))
    except ContextInputLimit as exc:
        raise ContextPlanningError("CONTEXT_PLAN_INPUT_TOO_LARGE", str(exc), status="blocked", details={"path": relpath, "maximum_bytes": max_bytes}) from exc
    except ContextInputChanged:
        raise
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise ContextPlanningError(
            "ADAPTER_ARTIFACT_UNAVAILABLE",
            f"cannot load {relpath}: {exc}",
            upgrade_required=True,
            details={"path": relpath},
            actions=("install or update the target adapter artifact",),
        ) from exc
    if not isinstance(value, dict):
        raise _field_error(relpath, "$", "an object", value)
    if digest_evidence is not None:
        digest_evidence[relpath] = "sha256:" + hashlib.sha256(raw).hexdigest()
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
    router = _load_json(target, ROUTER_PATH, "context router")
    _positive_integer(router.get("schema_version"), ROUTER_PATH, "schema_version")
    _text(router.get("router_kind"), ROUTER_PATH, "router_kind")
    if router.get("schema_version") not in {10, 11, 12, 13} or router.get("router_kind") != "target-context-router":
        raise ContextPlanningError(
            "CONTEXT_ROUTER_UNSUPPORTED",
            "target context router must use supported schema 10, 11, 12, or 13 and target-context-router",
            upgrade_required=True,
            actions=("run the Alatyr framework-update assessment",),
        )
    return router


def _resolve_profile(
    target: Path, router: dict[str, Any], profile: str
) -> tuple[dict[str, Any], str]:
    profile_index = _object(router.get("profile_index"), ROUTER_PATH, "profile_index")
    if not profile_index:
        raise _field_error(ROUTER_PATH, "profile_index", "a non-empty object", profile_index)
    if profile not in profile_index:
        raise ContextPlanningError(
            "UNKNOWN_CONTEXT_PROFILE",
            f"unknown target context profile: {profile}",
            status="invalid-request",
            details={"available_profiles": sorted(profile_index or {})},
        )
    field = f"profile_index.{profile}"
    entry = _object(profile_index[profile], ROUTER_PATH, field)
    descriptor_path = _artifact_path(entry.get("descriptor"), ROUTER_PATH, f"{field}.descriptor")
    _require_concrete(entry, f"profile index entry {profile}")
    descriptor = _load_json(target, descriptor_path, "profile descriptor")
    _positive_integer(descriptor.get("schema_version"), descriptor_path, "schema_version")
    _text(descriptor.get("descriptor_kind"), descriptor_path, "descriptor_kind")
    _text(descriptor.get("profile"), descriptor_path, "profile")
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
    _string_list(descriptor.get("operation_candidates"), descriptor_path, "operation_candidates")
    _string_list(descriptor.get("required_context"), descriptor_path, "required_context", non_empty=True)
    for index, path in enumerate(descriptor["required_context"]):
        _artifact_path(path, descriptor_path, f"required_context[{index}]")
    return descriptor, descriptor_path


def _resolve_operation(
    target: Path, router: dict[str, Any], requested: str
) -> tuple[dict[str, Any], str, str, str]:
    routing = _object(router.get("operation_routing"), ROUTER_PATH, "operation_routing")
    index_path = _artifact_path(routing.get("index"), ROUTER_PATH, "operation_routing.index")
    catalog_path = _artifact_path(routing.get("catalog"), ROUTER_PATH, "operation_routing.catalog")
    index = _load_json(target, index_path, "operation index")
    catalog = _load_json(target, catalog_path, "operation catalog")
    _positive_integer(index.get("schema_version"), index_path, "schema_version")
    _positive_integer(catalog.get("schema_version"), catalog_path, "schema_version")
    _text(index.get("index_kind"), index_path, "index_kind")
    _text(catalog.get("catalog_kind"), catalog_path, "catalog_kind")
    _artifact_path(index.get("catalog"), index_path, "catalog")
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
            status="blocked", details={"artifact": index_path, "field": "catalog"},
        )
    aliases = _object(index.get("aliases"), index_path, "aliases")
    indexed_operations = _object(index.get("operations"), index_path, "operations")
    operation_id = _text(aliases[requested], index_path, f"aliases.{requested}") if requested in aliases else requested
    operations = catalog.get("operations")
    if not isinstance(operations, list):
        raise _field_error(catalog_path, "operations", "a list", operations)
    # Inspect identities in the already-loaded catalog, not unrelated operation bodies.
    by_id: dict[str, dict[str, Any]] = {}
    operation_fields: dict[str, str] = {}
    for position, record in enumerate(operations):
        field = f"operations[{position}]"
        record = _object(record, catalog_path, field)
        record_id = _text(record.get("id"), catalog_path, f"{field}.id")
        if record_id in by_id:
            raise ContextPlanningError(
                "OPERATION_CATALOG_INVALID", f"duplicate operation ID: {record_id}",
                status="blocked", details={"artifact": catalog_path, "field": f"{field}.id"},
            )
        by_id[record_id] = record
        operation_fields[record_id] = field
    operation = by_id.get(operation_id)
    if operation is None:
        if requested in aliases or operation_id in indexed_operations:
            field = f"aliases.{requested}" if requested in aliases else f"operations.{operation_id}"
            raise ContextPlanningError(
                "OPERATION_INDEX_STALE", f"indexed operation is absent from the catalog: {operation_id}",
                status="blocked", details={"artifact": index_path, "field": field},
                actions=("repair the selected operation route and regenerate its index",),
            )
        raise ContextPlanningError(
            "UNKNOWN_OPERATION",
            f"unknown target operation or alias: {requested}",
            status="invalid-request",
            details={"available_operations": sorted(by_id)},
        )
    _require_concrete(operation, f"operation {operation_id}")
    field = operation_fields[operation_id]
    _text(operation.get("required_module"), catalog_path, f"{field}.required_module")
    _artifact_path(operation.get("flow"), catalog_path, f"{field}.flow")
    actions = _string_list(operation.get("allowed_actions"), catalog_path, f"{field}.allowed_actions")
    _string_list(operation.get("context_profiles"), catalog_path, f"{field}.context_profiles")
    indexed = _string_list(indexed_operations.get(operation_id), index_path, f"operations.{operation_id}")
    expected_index = [
        operation.get("required_module"),
        operation.get("flow"),
        *actions,
    ]
    if indexed != expected_index:
        raise ContextPlanningError(
            "OPERATION_INDEX_STALE",
            f"compact operation route is stale: {operation_id}",
            upgrade_required=True,
            status="blocked", details={"artifact": index_path, "field": f"operations.{operation_id}"},
        )
    return operation, operation_id, index_path, catalog_path


def _load_catalogs(target: Path, router: dict[str, Any]) -> _Catalogs:
    recursive = _object(router.get("recursive_context"), ROUTER_PATH, "recursive_context")
    indexes = _object(recursive.get("contour_indexes"), ROUTER_PATH, "recursive_context.contour_indexes")
    if set(indexes) != set(REQUIRED_CONTOURS):
        raise ContextPlanningError(
            "RECURSIVE_CONTEXT_UNAVAILABLE",
            "target router must define framework, project, and assistant context indexes",
            upgrade_required=True,
        )
    for contour in REQUIRED_CONTOURS:
        _artifact_path(indexes[contour], ROUTER_PATH, f"recursive_context.contour_indexes.{contour}")
    items: list[CatalogItem] = []
    evidence: list[dict[str, Any]] = []
    root_index = target
    try:
        for contour in REQUIRED_CONTOURS:
            relpath = _normalize_relative(indexes[contour], f"{contour} context index")
            root_index = _target_path(target, relpath, f"{contour} context index")
            catalog_root = root_index.parent
            resolution = discover_context_catalog(
                root_index, catalog_root=catalog_root
            )
            prefix = root_index.parent.relative_to(target).as_posix()
            items.extend(
                replace(item, path=f"{prefix}/{item.path}", index_chain=tuple(f"{prefix}/{path}" for path in item.index_chain))
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
            upgrade_required=isinstance(exc, ContextCatalogVersionError),
            details={"repair_kind": "local-context-projection", "failed_index": str(getattr(exc, "index_path", root_index).relative_to(target)),
                     "index_chain": [path.relative_to(target).as_posix() for path in getattr(exc, "chain", (root_index,))],
                     "affected_path": getattr(exc, "content_path", root_index).relative_to(target).as_posix()},
            actions=(f"repair the reported entry and regenerate its ancestor index chain from {root_index.relative_to(target).as_posix()}; this is not a framework upgrade",),
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
    path = _target_path(target, relpath, "selected target context")
    if not path.is_file():
        raise ContextPlanningError(
            "CANONICAL_OWNER_UNAVAILABLE",
            f"selected target context is not a file: {relpath}",
            status="blocked",
            details={"path": relpath},
        )
    try:
        raw = read_context_bytes(path)
        text = raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise ContextPlanningError(
            "CANONICAL_OWNER_UNREADABLE",
            f"selected target context cannot be read as UTF-8: {relpath}",
            status="blocked",
        ) from exc
    return CatalogItem(
        item_id=item_id,
        kind="content",
        path=relpath,
        summary="directly selected target context",
        selectors={},
        load_when=(reason,),
        semantic_refs=(),
        owner_refs=(),
        estimated_words=len(re.findall(r"\S+", text)),
        estimated_characters=len(text),
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


def _select_profile_required_path(
    target: Path,
    relpath: str,
    catalogs: _Catalogs,
    selected: dict[str, CatalogItem],
    reasons: dict[str, set[str]],
) -> None:
    normalized = _normalize_relative(relpath, "profile required context")
    if normalized in catalogs.by_path:
        _select_path(
            normalized, "profile-required-context", catalogs, selected, reasons
        )
        return
    if normalized == ".ai" or normalized.startswith(".ai/"):
        _select_path(
            normalized, "profile-required-context", catalogs, selected, reasons
        )
        return
    synthetic = _synthetic_file_item(
        target,
        normalized,
        "target.required." + hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "profile-required-context",
    )
    _select_synthetic(
        synthetic, "profile-required-context", selected, reasons
    )


def _load_reverse_index(target: Path, graph: ImpactGraph) -> tuple[ImpactLookup, str]:
    relpath = graph.root.get("reverse_index")
    if not isinstance(relpath, str) or not relpath:
        relpath = ".ai/assistant/consistency-reverse-index.json"
    relpath = _normalize_relative(relpath, "consistency reverse index")
    reverse = _load_json(target, relpath, "consistency reverse index")
    try:
        lookup = ImpactLookup(graph, reverse)
    except ImpactGraphError as exc:
        raise ContextPlanningError(
            "CONSISTENCY_REVERSE_INDEX_STALE",
            "installed consistency reverse index differs from the active graph",
            upgrade_required=True,
            details={"path": relpath, "graph_digest": graph.graph_digest},
            actions=("regenerate the consistency reverse index",),
        ) from exc
    return lookup, relpath


def _impact_selection(
    request: ContextPlanRequest,
    target: Path,
    router: dict[str, Any],
    catalogs: _Catalogs,
    selected: dict[str, CatalogItem],
    reasons: dict[str, set[str]],
    graph_snapshot: dict[str, ImpactGraph],
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
    graph_snapshot["active"] = graph
    lookup, reverse_path = _load_reverse_index(target, graph)
    changed_path_matches = {
        path: sorted(lookup.matching(path)) for path in request.changed_paths
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
            "requested graph node IDs are absent; --fact-id takes consistency-map node IDs, not task-local finding IDs",
            status="blocked",
            upgrade_required=False,
            details={"fact_ids": unknown_facts},
            actions=("look up the exact node ID in the target consistency map; route task-local findings through their changed paths",),
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
        resolution = lookup.resolve(request.changed_paths, request.fact_ids,
            max_depth=max_depth, max_nodes=max_nodes, change_kinds=request.change_kinds)
        node_ids = resolution["selected_node_ids"]
        selected_edges, skipped_edges = resolution["selected_edges"], resolution["skipped_edges"]
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

    graph_paths = {graph.source_paths[0]} | {graph.node_sources.get(node_id, graph.source_paths[0]) for node_id in node_ids}
    for graph_path in sorted(graph_paths):
        _select_path(graph_path, "selected-consistency-evidence", catalogs, selected, reasons)

    canonical_owners: list[dict[str, Any]] = []
    impacted_surfaces: list[dict[str, Any]] = []
    for node_id in node_ids:
        node = graph.nodes[node_id]
        owner = node.get("canonical_owner")
        if isinstance(owner, str) and owner:
            owner, _, owner_selector = owner.partition("#")
            owner = _normalize_relative(owner, f"canonical owner for {node_id}")
            if PLACEHOLDER_RE.search(owner):
                _require_concrete(owner, f"canonical owner for {node_id}")
            owner_path = _target_path(target, owner, f"canonical owner for {node_id}")
            owner_record: dict[str, Any] = {"node_id": node_id, "path": owner}
            if owner_selector:
                owner_record["selector"] = owner_selector
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
            _select_binding_owner(target, node_id, binding, catalogs, selected, reasons)
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
        "unresolved_relationships": resolution["review_required"],
        "owner_lookup_node_ids": resolution["owner_lookup_node_ids"],
        "relationship_candidate_triggers": relationship_review_paths(request.changed_paths),
        "graph_evidence": {"validated_paths": list(graph.source_paths),
                           "delivered_paths": sorted(graph_paths),
                           "reverse_index": reverse_path,
                           "validation_scope": "whole-graph", "authorization_granted": False},
        "reviewed_warnings": selected_candidate_warnings(target, graph.root.get("relationship_candidates"), node_ids, graph=graph,
                                                       selected_paths=(item.path for item in selected.values())),
        "limits": {"max_depth": max_depth, "max_nodes": max_nodes},
    }


def _select_binding_owner(target: Path, node_id: str, binding: dict, catalogs: _Catalogs, selected: dict, reasons: dict) -> None:
    if binding.get("authority") != "canonical":
        return
    if binding.get("selector_kind") == "glob":
        if not binding.get("context_ids"):
            raise ContextPlanningError("CANONICAL_OWNER_CONTEXT_UNRESOLVED", f"canonical scope {binding.get('path')!r} on {node_id!r} needs explicit bounded context IDs; never load the directory by default", status="blocked")
        return
    path = binding.get("path")
    if not isinstance(path, str):
        return
    reason = f"canonical-binding:{node_id}"
    existing = next((item for item in selected.values() if item.path == path), None)
    if existing is not None:
        reasons.setdefault(existing.item_id, set()).add(reason)
    elif path in catalogs.by_path:
        _select_path(path, reason, catalogs, selected, reasons)
    else:
        item = _synthetic_file_item(target, path, "impact.binding." + hashlib.sha256(path.encode()).hexdigest()[:16], reason)
        _select_synthetic(item, reason, selected, reasons)


def _add_owner_closure(
    catalogs: _Catalogs,
    selected: dict[str, CatalogItem],
    reasons: dict[str, set[str]],
    *, max_items: int | None = None, owner_index: dict | None = None,
) -> None:
    if max_items is not None and len(selected) > max_items:
        raise ContextPlanningError("CONTEXT_WORKING_SET_WORK_LIMIT", "required context exceeds the bounded working-set limit; decompose without dropping owners", status="blocked", details={"maximum": max_items, "closure_complete": False})
    by_rule = owner_index if owner_index is not None else _owner_index(catalogs)
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
                if max_items is not None and len(selected) > max_items:
                    raise ContextPlanningError("CONTEXT_WORKING_SET_WORK_LIMIT", "owner closure exceeds the bounded working-set limit; decompose without dropping owners", status="blocked", details={"maximum": max_items, "closure_complete": False})
                pending.append(owner)
            reasons.setdefault(owner.item_id, set()).add(
                f"owner-reference:{owner_ref}"
            )


def _owner_index(catalogs: _Catalogs) -> dict[str, list[CatalogItem]]:
    by_rule: dict[str, list[CatalogItem]] = {}
    for item in catalogs.items:
        for rule_id in item.selectors.get("rule_ids", ()):
            by_rule.setdefault(rule_id, []).append(item)
    return by_rule


def _verify_selected_content(
    target: Path, selected: dict[str, CatalogItem]
) -> dict[str, str]:
    """Verify only the content leaves selected by the bounded routing plan."""

    verified = {}
    try:
        for item in tuple(selected.values()):
            stats = catalog_content_stats(target / item.path)
            if stats.words != item.estimated_words:
                raise ContextCatalogError(
                    f"{item.path}.estimated_words is stale"
                )
            if stats.digest != item.content_digest:
                raise ContextCatalogError(
                    f"{item.path}.content_digest is stale"
                )
            selected[item.item_id] = replace(item, estimated_characters=stats.characters)
            verified[item.path] = stats.digest
    except (ContextCatalogError, OSError, UnicodeError) as exc:
        raise ContextPlanningError(
            "CONTEXT_CATALOG_STALE",
            f"selected context content is unavailable or stale: {exc}",
            upgrade_required=False,
            details={"repair_kind": "local-context-projection", "path": item.path, "index_chain": list(item.index_chain)},
            actions=("regenerate the selected context catalog branch",),
        ) from exc
    return verified


def _conditional_dependency_evidence(
    descriptor: dict[str, Any],
    catalogs: _Catalogs,
    selected: Iterable[CatalogItem],
    descriptor_path: str,
) -> list[dict[str, str]]:
    """Record lazy profile dependencies without treating triggers as satisfied."""

    conditional = descriptor.get("conditional_context", [])
    if not isinstance(conditional, list):
        raise _field_error(descriptor_path, "conditional_context", "a list", conditional)
    selected_paths = {item.path for item in selected}
    evidence: list[dict[str, str]] = []
    for index, dependency in enumerate(conditional):
        field = f"conditional_context[{index}]"
        dependency = _object(dependency, descriptor_path, field)
        path = _artifact_path(dependency.get("path"), descriptor_path, f"{field}.path")
        when = _text(dependency.get("when"), descriptor_path, f"{field}.when")
        normalized = _normalize_relative(path, "conditional context path")
        if normalized not in catalogs.by_path:
            raise ContextPlanningError(
                "CONDITIONAL_CONTEXT_UNINDEXED",
                f"conditional context is absent from recursive catalogs: {normalized}",
                upgrade_required=True,
                details={"path": normalized, "condition": when.strip()},
                actions=("regenerate context indexes after repairing the profile",),
            )
        evidence.append(
            {
                "path": normalized,
                "when": when.strip(),
                "status": "selected" if normalized in selected_paths else "omitted",
            }
        )
    return evidence


def _resolve_surface(
    target: Path, router: dict[str, Any], requested: str | None
) -> tuple[str, dict[str, Any]]:
    delivery = _object(router["cache_aware_delivery"], ROUTER_PATH, "cache_aware_delivery") if "cache_aware_delivery" in router else None
    if delivery is None or "provider_capability_index" not in delivery:
        if requested is None:
            return "generic", {
                "state": "unavailable",
                "reason": "assistant capability records are not installed",
                "record": None,
            }
        raise ContextPlanningError(
            "ASSISTANT_CAPABILITY_INDEX_UNAVAILABLE",
            "router does not identify the assistant capability index",
            upgrade_required=True,
        )
    assert delivery is not None
    index_path = _artifact_path(delivery.get("provider_capability_index"), ROUTER_PATH, "cache_aware_delivery.provider_capability_index")
    index = _load_json(target, index_path, "assistant capability index")
    surfaces = _object(index.get("surfaces"), index_path, "surfaces")
    surface = requested if requested is not None else _text(index.get("default_surface"), index_path, "default_surface")
    if surface not in surfaces:
        raise ContextPlanningError(
            "UNKNOWN_ASSISTANT_SURFACE",
            f"unknown assistant surface: {surface}",
            status="invalid-request",
            details={"available_surfaces": sorted(surfaces)},
        )
    record_path = _artifact_path(surfaces[surface], index_path, f"surfaces.{surface}")
    record = _load_json(target, record_path, "assistant capability record")
    _text(record.get("assistant_surface"), record_path, "assistant_surface")
    if record.get("assistant_surface") != surface:
        raise ContextPlanningError(
            "ASSISTANT_CAPABILITY_RECORD_INVALID",
            f"assistant capability record differs from selected surface: {surface}",
            upgrade_required=True,
        )
    _require_concrete(record, record_path)
    return surface, {
        "state": "available",
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
    config = _object(router.get("semantic_codebook"), ROUTER_PATH, "semantic_codebook")
    index_path = _artifact_path(config.get("index"), ROUTER_PATH, "semantic_codebook.index")
    configured_preload = _string_list(config.get("preload_terms"), ROUTER_PATH, "semantic_codebook.preload_terms")
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
            status="blocked", details={"artifact": ROUTER_PATH, "field": "semantic_codebook.preload_terms"},
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


def _document_warning_lookup(request: ContextPlanRequest, target: Path, selected: dict, graph_snapshot: dict[str, ImpactGraph]) -> dict | None:
    if type(request.document_warnings) is not bool:
        raise ContextPlanningError("INVALID_DOCUMENT_WARNING_REQUEST", "document_warnings must be a Boolean", status="invalid-request")
    if not request.document_warnings:
        return None
    try:
        graph = graph_snapshot.get("active")
        if graph is None:
            graph = load_impact_graph(target)
            graph_snapshot["active"] = graph
        failures = validate_graph(graph)
    except ImpactGraphError as exc:
        raise ContextPlanningError("CONSISTENCY_GRAPH_UNAVAILABLE", str(exc), upgrade_required=True) from exc
    if failures:
        raise ContextPlanningError("CONSISTENCY_GRAPH_INVALID", "document warning lookup requires valid consistency evidence", details={"failures": failures})
    return selected_candidate_warnings(target, graph.root.get("relationship_candidates"), (), graph=graph,
                                       selected_paths=(item.path for item in selected.values()))


def _working_call(function: Any, *args: Any, **kwargs: Any) -> Any:
    from context_working_set import WorkingSetError

    try:
        return function(*args, **kwargs)
    except WorkingSetError as exc:
        raise ContextPlanningError(exc.code, str(exc), status="blocked", details=exc.details) from exc


def _add_working_view(request: ContextPlanRequest, plan: dict, view: dict, target: Path, api: Any, selected: dict) -> None:
    view["target_identity"] = api.target_identity(target)
    view["budget"] = dict(plan["context_packet"]["budget"])
    view["mandatory_retained"] = set(view["mandatory_item_ids"]) <= selected.keys()
    plan["working_set"] = view
    plan["request"]["working_set_request"] = request.working_set_request
    plan["routing_sources"]["working_set_request"] = {"path": request.working_set_request, "digest": file_digest(target / request.working_set_request)}
    if request.previous_plan:
        previous = _working_call(api.read_evidence, request.previous_plan, target)
        view["delta"] = _working_call(api.plan_delta, previous, plan, target)
    if request.delivery_observation:
        observation = _working_call(api.read_evidence, request.delivery_observation, target)
        view["accounting"] = _working_call(api.delivery_accounting, observation, plan["context_packet"])
    else:
        view["accounting"] = {"measurement": "planned-only", "input_tokens": "unknown", "cached_input_tokens": "unknown", "total_task_and_worker_tokens": "unknown", "billing_savings": "unknown"}


def _working_request(request: ContextPlanRequest, target: Path) -> tuple:
    if not request.working_set_request:
        return None, None
    import context_working_set as api

    try:
        document = _load_json(target, request.working_set_request, "working-set request", max_bytes=4 * 1024 * 1024)
    except ContextPlanningError as exc:
        raise ContextPlanningError(exc.code, str(exc), status="blocked", details=exc.details, actions=("repair or supply the selected working-set request",)) from exc
    return document, api


def _knowledge_selection(request, target, catalogs, selected, reasons):
    knowledge = None
    knowledge_digests: dict[str, str] = {}
    if request.knowledge_request is not None:
        from knowledge_context import select_context_knowledge
        def load_knowledge(path: str) -> dict:
            return _load_json(target, _normalize_relative(path, "knowledge input"), "knowledge input", digest_evidence=knowledge_digests)
        def read_knowledge(path: str) -> bytes:
            path = _normalize_relative(path, "knowledge owner")
            raw = read_context_bytes(target / path, max_bytes=1024 * 1024)
            knowledge_digests[path] = "sha256:" + hashlib.sha256(raw).hexdigest()
            return raw
        try:
            knowledge = select_context_knowledge(request.profile, load_knowledge(request.knowledge_request), load_knowledge, read_knowledge)
        except (ValueError, OSError, UnicodeError) as exc:
            raise ContextPlanningError("CONTEXT_KNOWLEDGE_INVALID", str(exc), status="blocked",
                actions=("repair, narrow or decompose the selected knowledge query; do not omit applicable constraints",)) from exc
        for path in knowledge["owner_paths"]:
            if path in catalogs.by_path or path.startswith(".ai/"):
                _select_path(path, "selected-knowledge-canonical-owner", catalogs, selected, reasons)
            else:
                item = _synthetic_file_item(target, path, "target.knowledge." + hashlib.sha256(path.encode()).hexdigest(), "selected-knowledge-canonical-owner")
                _select_synthetic(item, "selected-knowledge-canonical-owner", selected, reasons)
    return knowledge, knowledge_digests


def _knowledge_usage(knowledge):
    if knowledge is None:
        return 0, 0
    rendered_knowledge = json.dumps(knowledge, indent=2, ensure_ascii=True, sort_keys=True)
    return len(rendered_knowledge.split()), len(rendered_knowledge)


def _question_selection(document, target, catalogs, selected, reasons):
    if document is None or "question_binding" not in document:
        return None
    from context_question import resolve_context_question

    def read(path, limit):
        normalized = _normalize_relative(path, "question input")
        return read_context_bytes(_target_path(target, normalized, "question input"), max_bytes=limit)
    try:
        question, paths = resolve_context_question(document["question_binding"], read)
    except (ValueError, OSError, UnicodeError, RecursionError) as exc:
        raise ContextPlanningError("CONTEXT_QUESTION_INVALID", str(exc), status="blocked",
            actions=("rebind the request to a current unresolved task question, or narrow the probe",)) from exc
    for path in paths:
        _select_profile_required_path(target, path, catalogs, selected, reasons)
    required_paths = set(paths)
    for item in selected.values():
        if item.path in required_paths:
            reasons[item.item_id].add("selected-task-question")
    return question


def _knowledge_optional_limits(knowledge, max_words, max_characters, question=None):
    words, characters = _knowledge_usage(knowledge)
    question_words, question_characters = _knowledge_usage(question)
    words, characters = words + question_words, characters + question_characters
    return max(0, max_words - words), None if max_characters is None else max(0, max_characters - characters)


def _add_knowledge_view(request, plan, knowledge, knowledge_digests, content_packet, max_words, max_characters, question=None):
    # Reserve the same delivered metadata cost before optional ranking and here.
    knowledge_words, knowledge_characters = _knowledge_usage(knowledge)
    question_words, question_characters = _knowledge_usage(question)
    if content_packet["budget"]["total_words"] + knowledge_words + question_words > max_words:
        raise ContextPlanningError("CONTEXT_WORD_BUDGET_EXCEEDED", "selected delivery metadata plus required context exceeds word budget", status="blocked")
    if max_characters is not None and content_packet["budget"]["total_characters"] + knowledge_characters + question_characters > max_characters:
        raise ContextPlanningError("CONTEXT_CHARACTER_BUDGET_EXCEEDED", "selected delivery metadata plus required context exceeds character budget", status="blocked")
    if knowledge is not None:
        plan["request"]["knowledge_request"] = request.knowledge_request
        plan["knowledge"] = knowledge
        plan["routing_sources"]["knowledge_inputs"] = knowledge_digests
    plan["delivery_budget"] = {"knowledge_words": knowledge_words, "knowledge_characters": knowledge_characters,
        "total_words": content_packet["budget"]["total_words"] + knowledge_words + question_words,
        "total_characters": content_packet["budget"]["total_characters"] + knowledge_characters + question_characters,
        "max_words": max_words, "max_characters": max_characters}
    if question is not None:
        plan["question"] = question
        plan["delivery_budget"].update(question_words=question_words, question_characters=question_characters)


def _ready_plan(request: ContextPlanRequest) -> dict[str, Any]:
    target = request.target.resolve()
    if not target.is_dir():
        raise ContextPlanningError(
            "TARGET_UNAVAILABLE", "target repository directory does not exist",
            status="invalid-request",
        )
    router = _load_router(target)
    descriptor, descriptor_path = _resolve_profile(target, router, request.profile)
    operation, operation_id, operation_index_path, operation_catalog_path = _resolve_operation(target, router, request.operation)
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
    if operation_id != "architecture-assistance" and operation_profiles and (
        not isinstance(candidates, list) or operation_id not in candidates
    ):
        raise ContextPlanningError(
            "PROFILE_OPERATION_ROUTING_STALE",
            f"profile {request.profile} does not route operation {operation_id}",
            upgrade_required=True,
        )
    catalogs = _load_catalogs(target, router)
    working_document, working_api = _working_request(request, target)
    owner_index = _owner_index(catalogs) if working_api is not None else None
    working_view = None
    surface, surface_evidence = _resolve_surface(target, router, request.assistant_surface)
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
        _select_profile_required_path(
            target, relpath, catalogs, selected, reasons
        )
    flow = operation.get("flow")
    if not isinstance(flow, str):
        raise ContextPlanningError(
            "OPERATION_FLOW_INVALID", f"operation has no flow: {operation_id}",
            upgrade_required=True,
        )
    _select_path(flow, "operation-flow", catalogs, selected, reasons)
    if request.architecture_mode is not None and operation_id != "architecture-assistance":
        raise ContextPlanningError("ARCHITECTURE_MODE_OPERATION", "architecture mode requires architecture-assistance", status="invalid-request")
    if operation_id == "architecture-assistance":
        overlays = router.get("intent_overlays")
        if not isinstance(overlays, dict):
            raise ContextPlanningError("ARCHITECTURE_CONTEXT_INVALID", "intent_overlays must be an object", upgrade_required=True)
        entry = overlays.get("architecture-request", {})
        intent_path = entry.get("descriptor") if isinstance(entry, dict) else None
        if not isinstance(intent_path, str):
            raise ContextPlanningError("ARCHITECTURE_CONTEXT_MISSING", "architecture context descriptor is unavailable", upgrade_required=True)
        intent = _load_json(target, intent_path, "architecture context")
        if intent.get("intent") != "architecture-request" or intent.get("operation_candidates") != [operation_id]:
            raise ContextPlanningError("ARCHITECTURE_CONTEXT_INVALID", "architecture intent does not route the selected operation", upgrade_required=True)
        try:
            architecture_paths = architecture_context(intent, request.architecture_mode)
        except ValueError as exc:
            raise ContextPlanningError("ARCHITECTURE_CONTEXT_INVALID", str(exc), status="invalid-request") from exc
        _select_path(intent_path, "architecture-mode-descriptor", catalogs, selected, reasons)
        for path in architecture_paths:
            _select_profile_required_path(target, path, catalogs, selected, reasons)
    graph_snapshot: dict[str, ImpactGraph] = {}
    impact = _impact_selection(
        request, target, router, catalogs, selected, reasons, graph_snapshot
    )
    knowledge, knowledge_digests = _knowledge_selection(request, target, catalogs, selected, reasons)
    if working_api is not None:
        working_view = _working_call(working_api.required_selection, working_document, catalogs.by_id, selected, reasons)
    question = _question_selection(working_document, target, catalogs, selected, reasons)
    _add_owner_closure(catalogs, selected, reasons, max_items=working_api.MAX_SCOPE_ITEMS if working_api is not None else None, owner_index=owner_index)
    _verify_selected_content(target, selected)
    terms, semantic_index_path = _semantic_terms(
        target, router, selected.values(), request.profile, operation_id
    )
    budgets = _object(router.get("context_budgets"), ROUTER_PATH, "context_budgets")
    budget = _object(budgets.get("profile_default"), ROUTER_PATH, "context_budgets.profile_default")
    configured_words = _positive_integer(budget.get("max_total_words"), ROUTER_PATH, "context_budgets.profile_default.max_total_words")
    configured_files = _positive_integer(budget.get("max_files"), ROUTER_PATH, "context_budgets.profile_default.max_files")
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
    configured_characters = budget.get("max_total_characters")
    if router["schema_version"] in {12, 13} or "max_total_characters" in budget:
        _positive_integer(configured_characters, ROUTER_PATH, "context_budgets.profile_default.max_total_characters")
    if request.max_characters is not None and request.max_characters < 1:
        raise ContextPlanningError(
            "INVALID_CONTEXT_BUDGET", "--max-characters must be positive",
            status="invalid-request",
        )
    if (
        request.max_characters is not None
        and isinstance(configured_characters, int)
        and request.max_characters > configured_characters
    ):
        raise ContextPlanningError(
            "CONTEXT_BUDGET_OVERRIDE_TOO_LARGE",
            "requested character budget exceeds the target router limit",
            status="invalid-request",
            details={
                "requested": request.max_characters,
                "configured": configured_characters,
            },
        )
    max_characters = request.max_characters or (
        configured_characters if isinstance(configured_characters, int) else None
    )
    if len(selected) > configured_files:
        raise ContextPlanningError(
            "CONTEXT_FILE_BUDGET_EXCEEDED",
            "required context exceeds the configured file budget",
            status="blocked",
            details={"required_files": len(selected), "max_files": configured_files,
                     "decomposition": decomposition_proposal(selected.values(), max_files=configured_files, max_words=max_words, max_characters=max_characters)},
            actions=("record a context expansion or split the task without omitting owners",),
        )
    if working_api is not None:
        optional_words, optional_characters = _knowledge_optional_limits(knowledge, max_words, max_characters, question)
        terms = _working_call(working_api.select_optional, working_document, working_view, catalogs.by_id, selected, reasons, terms,
            max_files=configured_files, max_words=optional_words, max_characters=optional_characters,
            close=lambda entries, why: _add_owner_closure(catalogs, entries, why, max_items=working_api.MAX_SCOPE_ITEMS, owner_index=owner_index),
            hydrate=lambda entries: _verify_selected_content(target, entries),
            resolve_terms=lambda entries: _semantic_terms(target, router, entries, request.profile, operation_id)[0])
    normalized_reasons = {
        item_id: sorted(values) for item_id, values in sorted(reasons.items())
    }
    conditional_dependencies = _conditional_dependency_evidence(
        descriptor, catalogs, selected.values(), descriptor_path
    )
    try:
        content_packet = build_context_packet(
            profile=request.profile,
            operation=operation_id,
            selected_items=selected.values(),
            semantic_terms=terms,
            max_words=max_words,
            max_characters=max_characters,
            assistant_surface=surface,
            assistant_capability_record=surface_evidence.get("record"),
            assistant_capability_state=str(surface_evidence["state"]),
            selection_reasons=normalized_reasons,
            expansion_triggers=(
                "changed paths or facts selected bounded consistency relationships",
            ) if impact["used"] else (),
            conditional_dependencies=conditional_dependencies,
        )
    except ContextCatalogError as exc:
        if "exceeds budget" in str(exc):
            dimension = "CHARACTER" if "characters" in str(exc) else "WORD"
            raise ContextPlanningError(
                f"CONTEXT_{dimension}_BUDGET_EXCEEDED",
                str(exc),
                status="blocked",
                details={
                    "max_words": max_words,
                    "max_characters": max_characters,
                    "selected_content_words": sum(
                        item.estimated_words for item in selected.values()
                    ),
                    "selected_content_characters": sum(
                        item.estimated_characters for item in selected.values()
                    ),
                    "decomposition": decomposition_proposal(selected.values(), max_files=configured_files, max_words=max_words, max_characters=max_characters),
                },
                actions=("record a context expansion or split the task without omitting owners",),
            ) from exc
        raise ContextPlanningError(
            "CONTEXT_PACKET_INVALID", str(exc), upgrade_required=True
        ) from exc
    packet = _packet_projection(content_packet)
    document_warnings = _document_warning_lookup(request, target, selected, graph_snapshot)
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
            "change_kinds": list(request.change_kinds),
            "assistant_surface": surface,
            "architecture_mode": request.architecture_mode,
            "max_words": max_words,
            "max_characters": max_characters,
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
            "conditional_dependencies": conditional_dependencies,
        },
        "reasoning_boundary": (
            "deterministic routing selects context candidates; it does not prove "
            "semantic correctness, model delivery, comprehension, or compliance"
        ),
    }
    if impact["used"]:
        plan["task_contract"] = {
            "record_kind": "derived-task-contract-view", "authority": "none",
            "graph_digest": impact["graph_digest"],
            "fact_ids": impact["selected_node_ids"],
            "canonical_owners": impact["canonical_owners"],
            "affected_surfaces": impact["impacted_surfaces"],
            "invariant_owners": impact["canonical_owners"],
            "validation_refs": [{"edge_id": edge["id"], "reference": edge["validation"]} for edge in impact["selected_edges"] if "validation" in edge],
            "approval_triggers": [{"edge_id": edge["id"], "trigger": edge["approval_trigger"]} for edge in impact["selected_edges"] if "approval_trigger" in edge],
            "approval_review": "Selected canonical policies remain applicable even when no edge declares a trigger.",
            "relationship_review_paths": impact["relationship_candidate_triggers"],
            "unknowns": impact["unresolved_relationships"],
            "skipped_relationships": impact["skipped_edges"],
            "worklist": ["review selected owners for invariants, checks and approval triggers",
                         "reconcile affected surfaces and review new relationships",
                         "bind resulting proof obligations to the current task model and its execution readiness"],
            "acceptance_granted": False,
            "limitation": "Routing references only, not a new owner, accepted obligation set, execution order or permission. Read the selected owners; missing applicability remains review-required.",
        }
    if "validation_entrypoints" in descriptor:
        contract_digests: dict[str, str] = {}
        contract = _load_json(target, CONTRACT_PATH, "validation contract", digest_evidence=contract_digests)
        failures = validation_route_failures(descriptor["validation_entrypoints"], contract)
        if failures:
            raise ContextPlanningError("CONTEXT_VALIDATION_ROUTE_INVALID", "; ".join(failures), status="blocked")
        plan["validation_route"] = {
            "contract": CONTRACT_PATH,
            "contract_sha256": contract_digests[CONTRACT_PATH],
            "entrypoints": {role: {"id": entry_id, "command_prefix": contract["entrypoints"][entry_id]["command"]}
                for role, entry_id in descriptor["validation_entrypoints"].items()},
            "execution_performed": False,
            "authorization_granted": False,
            "limitation": "References only; validate the contract and supply current runtime bindings before final acceptance.",
        }
    if document_warnings is not None:
        plan["document_warnings"] = document_warnings
    if knowledge is not None or question is not None:
        _add_knowledge_view(request, plan, knowledge, knowledge_digests, content_packet, max_words, max_characters, question)
    if working_api is not None:
        _add_working_view(request, plan, working_view, target, working_api, selected)
    try:
        for graph in graph_snapshot.values():
            assert_graph_current(graph, target)
    except ImpactGraphError as exc:
        raise ContextPlanningError("CONSISTENCY_INPUT_CHANGED", str(exc), status="blocked") from exc
    plan["plan_digest"] = _canonical_digest(plan)
    return plan


def _request_echo(value: Any, depth: int = 0) -> Any:
    if value is None or type(value) in (str, int, bool):
        return value
    if isinstance(value, (list, tuple)) and depth < 3 and len(value) <= 128:
        return [_request_echo(item, depth + 1) for item in value]
    return {"invalid_type": type(value).__name__}


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
            "changed_paths": list(request.changed_paths) if isinstance(request.changed_paths, (tuple, list)) else request.changed_paths,
            "fact_ids": list(request.fact_ids) if isinstance(request.fact_ids, (tuple, list)) else request.fact_ids,
            "assistant_surface": request.assistant_surface,
            "architecture_mode": request.architecture_mode,
            "max_words": request.max_words,
            "max_characters": request.max_characters,
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
    result["request"] = {key: _request_echo(value) for key, value in result["request"].items()}
    for key in ("working_set_request", "previous_plan", "delivery_observation", "knowledge_request"):
        value = getattr(request, key)
        if value is not None:
            result["request"][key] = _request_echo(value)
    result["plan_digest"] = _canonical_digest(result)
    return result


def _validate_request(request: ContextPlanRequest) -> None:
    if not isinstance(request.target, Path):
        raise _field_error("request", "target", "a pathlib Path", request.target)
    for field in ("profile", "operation"):
        _text(getattr(request, field), "request", field)
    for field in ("assistant_surface", "architecture_mode", "working_set_request", "previous_plan", "delivery_observation", "knowledge_request"):
        value = getattr(request, field)
        if value is not None:
            _text(value, "request", field)
    for field in ("changed_paths", "fact_ids", "change_kinds"):
        values = getattr(request, field)
        if not isinstance(values, (tuple, list)):
            raise _field_error("request", field, "a list or tuple of strings", values)
        for index, value in enumerate(values):
            _text(value, "request", f"{field}[{index}]")
    if any(value not in CHANGE_KINDS for value in request.change_kinds):
        raise _field_error("request", "change_kinds", "supported change kind names", request.change_kinds)
    for field in ("max_words", "max_characters"):
        value = getattr(request, field)
        if value is not None:
            _positive_integer(value, "request", field)
    if not isinstance(request.document_warnings, bool):
        raise _field_error("request", "document_warnings", "a Boolean", request.document_warnings)
    if (request.previous_plan is not None or request.delivery_observation is not None) and request.working_set_request is None:
        raise ContextPlanningError("INVALID_CONTEXT_PLAN_REQUEST", "previous plans and delivery observations require a working-set request", status="invalid-request")


def plan_target_context(request: ContextPlanRequest) -> dict[str, Any]:
    """Return a usable context plan or structured fail-closed evidence."""

    try:
        _validate_request(request)
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
            working_set_request=_normalize_relative(request.working_set_request, "working-set request") if request.working_set_request is not None else None,
            knowledge_request=_normalize_relative(request.knowledge_request, "knowledge request") if request.knowledge_request is not None else None,
        )
        if any(not fact_id or PLACEHOLDER_RE.search(fact_id) for fact_id in normalized.fact_ids):
            raise ContextPlanningError(
                "INVALID_FACT_ID", "fact IDs must be concrete non-empty values",
                status="invalid-request",
            )
        with ContextInputSnapshot(normalized.target):
            return _ready_plan(normalized)
    except ContextInputChanged as exc:
        return _error_plan(request, ContextPlanningError("CONTEXT_INPUT_CHANGED", str(exc), status="blocked",
            details={"artifact": exc.path.relative_to(request.target.resolve()).as_posix() if request.target.resolve() in exc.path.parents else "outside-target"},
            actions=("retry planning on stable input bytes",)))
    except ContextPlanningError as exc:
        return _error_plan(request, exc)
