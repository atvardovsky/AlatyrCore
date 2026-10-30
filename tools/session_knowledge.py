"""Bind selected ready-plan knowledge without creating another knowledge registry."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Callable

from knowledge_freshness import SHA256, review_deadlines, source_path


MAX_PLANS = 8
MAX_ITEMS = 240


def _digest(value: object) -> bool:
    return (isinstance(value, str) and value.startswith("sha256:")
            and SHA256.fullmatch(value[7:]) is not None and value == value.lower())


def validate_binding(binding: object, input_paths: set[str]) -> dict:
    if not isinstance(binding, dict) or set(binding) != {"plans", "items"}:
        raise ValueError("invalid retained knowledge binding")
    plans, items = binding["plans"], binding["items"]
    if not isinstance(plans, list) or not 1 <= len(plans) <= MAX_PLANS:
        raise ValueError("knowledge binding requires 1..8 plans")
    seen_plans = set()
    for plan in plans:
        if not isinstance(plan, dict) or set(plan) != {"path", "routing_paths"}:
            raise ValueError("invalid retained knowledge plan")
        path = source_path(plan["path"])
        paths = plan["routing_paths"]
        if not isinstance(paths, list) or not paths or len(paths) > 256:
            raise ValueError("knowledge routing paths require bounded file bindings")
        normalized = [source_path(value) for value in paths]
        if (normalized != sorted(set(normalized)) or path not in normalized
                or not set(normalized) <= input_paths or path in seen_plans):
            raise ValueError("knowledge routing paths are missing, duplicated or unbound")
        seen_plans.add(path)
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise ValueError("knowledge items exceed their bounded limit")
    seen_items = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {
            "plan", "knowledge_id", "source_paths", "review_expires_on", "unverified_trigger_kinds",
            "authority_state", "freshness_state"
        }:
            raise ValueError("invalid retained knowledge item")
        plan, identity = item["plan"], item["knowledge_id"]
        if (not isinstance(plan, str) or plan not in seen_plans or not isinstance(identity, str)
                or not identity.strip() or len(identity) > 256 or (plan, identity) in seen_items):
            raise ValueError("knowledge item requires a unique plan and resolved ID")
        seen_items.add((plan, identity))
        if (not isinstance(item["authority_state"], str)
                or item["authority_state"] not in {"accepted", "observed", "proposed", "unresolved"}
                or not isinstance(item["freshness_state"], str)
                or item["freshness_state"] not in {"current", "revalidation-required"}):
            raise ValueError("invalid retained knowledge authority/freshness state")
        paths = item["source_paths"]
        if not isinstance(paths, list) or not 1 <= len(paths) <= 33:
            raise ValueError("knowledge item requires bounded owner/source paths")
        normalized = [source_path(value) for value in paths]
        if normalized != sorted(set(normalized)) or not set(normalized) <= input_paths:
            raise ValueError("knowledge owner/source paths are duplicated or unbound")
        expiry = item["review_expires_on"]
        if expiry is not None:
            review_deadlines([{"kind": "review-expiry", "expected": expiry}])
        kinds = item["unverified_trigger_kinds"]
        if (not isinstance(kinds, list) or len(kinds) > 32
                or not all(isinstance(kind, str) and kind.strip() for kind in kinds)
                or kinds != sorted(set(kinds))):
            raise ValueError("knowledge unverified trigger kinds must be bounded unique strings")
    return binding


def plan_projection(path: str, plan: dict) -> tuple[dict, list[dict], dict[str, str]]:
    """Project only declared metadata; callers separately verify current sources."""
    if (type(plan.get("schema_version")) is not int or plan["schema_version"] != 1
            or plan.get("plan_kind") != "target-context-plan" or plan.get("status") != "ready"
            or plan.get("read_only") is not True):
        raise ValueError(f"{path} must be a ready read-only context plan")
    request, packet = plan.get("request"), plan.get("context_packet")
    if not isinstance(request, dict) or not isinstance(packet, dict):
        raise ValueError(f"{path} is missing its request or context packet")
    if (not isinstance(request.get("profile"), str) or not request["profile"]
            or not isinstance(request.get("operation"), str) or not request["operation"]
            or request.get("profile") != packet.get("profile")
            or request.get("operation") != packet.get("operation")):
        raise ValueError(f"{path} request and context packet disagree")
    selected = packet.get("selected_items")
    if not isinstance(selected, list) or not 1 <= len(selected) <= 256:
        raise ValueError(f"{path} requires bounded selected context")
    expected = {}
    for item in selected:
        if not isinstance(item, dict):
            raise ValueError(f"{path} selected item must be an object")
        selected_path = source_path(item.get("path"))
        value = item.get("content_digest")
        if not _digest(value) or selected_path in expected:
            raise ValueError(f"{path} requires unique content-bound selected context")
        expected[selected_path] = value
    return request, selected, expected


def knowledge_projection(path: str, plan: dict) -> tuple[dict, list[dict], dict[str, str]]:
    request, _, selected = plan_projection(path, plan)
    routing, items, expected = {path}, [], {}
    query_path = request.get("knowledge_request")
    if query_path is not None or "knowledge" in plan:
        query_path = source_path(query_path)
        knowledge, sources = plan.get("knowledge"), plan.get("routing_sources")
        if not isinstance(knowledge, dict) or not isinstance(sources, dict):
            raise ValueError(f"{path} requires knowledge selection and input bindings")
        expected = sources.get("knowledge_inputs")
        if not isinstance(expected, dict) or not 1 <= len(expected) <= 256:
            raise ValueError(f"{path} requires bounded knowledge input bindings")
        for relpath, value in expected.items():
            source_path(relpath)
            if not _digest(value):
                raise ValueError(f"{path} has an invalid knowledge digest")
        routes = knowledge.get("routing_paths")
        if not isinstance(routes, list) or not routes or len(routes) > 9:
            raise ValueError(f"{path} requires bounded knowledge routing paths")
        routing.update(source_path(value) for value in routes)
        routing.add(query_path)
        if not routing.difference({path}) <= expected.keys():
            raise ValueError(f"{path} is missing knowledge routing bindings")
        selection = knowledge.get("selection")
        if not isinstance(selection, dict):
            raise ValueError(f"{path} requires its knowledge selection")
        rows = []
        for key in ("constraints", "warnings"):
            values = selection.get(key)
            if not isinstance(values, list) or len(values) > 30:
                raise ValueError(f"{path} has invalid knowledge {key}")
            rows.extend(values)
        for row in rows:
            if (not isinstance(row, dict) or not isinstance(row.get("source_paths", []), list)
                    or len(row.get("source_paths", [])) > 32):
                raise ValueError(f"{path} has invalid knowledge item bindings")
            owner = source_path(row.get("canonical_owner"))
            paths = {owner, *(source_path(value) for value in row.get("source_paths", []))}
            if owner not in selected or not paths <= expected.keys():
                raise ValueError(f"{path} omits a selected knowledge owner or source")
            items.append({"plan": path, "knowledge_id": row.get("knowledge_id"),
                          "source_paths": sorted(paths), "review_expires_on": row.get("review_expires_on"),
                          "unverified_trigger_kinds": row.get("unverified_trigger_kinds"),
                          "authority_state": row.get("authority_state"), "freshness_state": row.get("freshness_state")})
    return {"path": path, "routing_paths": sorted(routing)}, items, expected


def bind_plans(paths: list[str], load: Callable[[str], dict], read: Callable[[str], bytes]) -> dict:
    from context_catalog import catalog_content_bytes_for_name

    if not 1 <= len(paths) <= MAX_PLANS or len(paths) != len(set(paths)):
        raise ValueError("session context requires 1..8 unique context plans")
    result: dict = {"plans": [], "items": []}
    for path in sorted(paths):
        path = source_path(path)
        plan = load(path)
        request, selected, expected_items = plan_projection(path, plan)
        for item in selected:
            selected_path = source_path(item.get("path"))
            raw = read(selected_path)
            digest = "sha256:" + hashlib.sha256(catalog_content_bytes_for_name(selected_path, raw)).hexdigest()
            if expected_items[selected_path] != digest:
                raise ValueError(f"{path} has stale selected context: {selected_path}")
        query_path = request.get("knowledge_request")
        if query_path is not None or "knowledge" in plan:
            from knowledge_context import select_context_knowledge

            query_path = source_path(query_path)
            observed = {}
            def knowledge_read(relpath):
                raw = read(source_path(relpath))
                observed[relpath] = "sha256:" + hashlib.sha256(raw).hexdigest()
                return raw
            def knowledge_load(relpath):
                value = load(relpath)
                knowledge_read(relpath)
                return value
            actual = select_context_knowledge(request["profile"], knowledge_load(query_path), knowledge_load, knowledge_read)
            sources = plan.get("routing_sources")
            if (not isinstance(sources, dict) or sources.get("knowledge_inputs") != observed
                    or plan.get("knowledge") != actual):
                raise ValueError(f"{path} has stale or incomplete knowledge bindings; rebuild its query")
        descriptor, items, _ = knowledge_projection(path, plan)
        result["plans"].append(descriptor)
        result["items"].extend(items)
    return result


def verify_retained(binding: dict, expected: dict[str, str], current: dict[str, str],
                    load: Callable[[str], dict], read: Callable[[str], bytes]) -> None:
    from context_catalog import PROVENANCE_NEUTRAL_JSON_FILES, catalog_content_bytes_for_name
    from pathlib import PurePosixPath

    for descriptor in binding["plans"]:
        path = descriptor["path"]
        if "sha256:" + hashlib.sha256(read(path)).hexdigest() != expected[path]:
            continue  # Changed plan bytes require rerouting, not reuse of its projection.
        plan = load(path)
        projected, items, sources = knowledge_projection(path, plan)
        _, _, selected = plan_projection(path, plan)
        if (descriptor != projected or items != [item for item in binding["items"] if item["plan"] == path]
                or not selected.keys() <= expected.keys()
                or any(expected.get(relpath) != value for relpath, value in sources.items())):
            raise ValueError("retained knowledge omits or disagrees with its bound context plan")
        for relpath, selected_digest in selected.items():
            if PurePosixPath(relpath).name not in PROVENANCE_NEUTRAL_JSON_FILES:
                matches = expected[relpath] == selected_digest
            elif current.get(relpath) == expected[relpath]:
                matches = "sha256:" + hashlib.sha256(catalog_content_bytes_for_name(relpath, read(relpath))).hexdigest() == selected_digest
            else:
                continue
            if not matches:
                raise ValueError("retained context binding disagrees with its bound selected content")


def knowledge_delta(binding: dict, changed_paths: list[str], *, today: date | None = None) -> dict:
    today = today or date.today()
    changed = set(changed_paths)
    routing_changed = {plan["path"] for plan in binding["plans"] if changed.intersection(plan["routing_paths"])}
    expired, affected = set(), set()
    for item in binding["items"]:
        expiry = item["review_expires_on"]
        if expiry is not None and date.fromisoformat(expiry) < today:
            expired.add(item["knowledge_id"])
        if item["plan"] in routing_changed or changed.intersection(item["source_paths"]):
            affected.add(item["knowledge_id"])
    return {"affected_ids": sorted(affected | expired), "expired_ids": sorted(expired),
            "reroute_required": bool(routing_changed),
            "warning_ids": sorted({item["knowledge_id"] for item in binding["items"] if item["freshness_state"] == "revalidation-required"}),
            "unverified_trigger_kinds": sorted({kind for item in binding["items"] for kind in item["unverified_trigger_kinds"]}),
            "global_coverage": False, "authority_promoted": False}
