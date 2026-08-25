"""AI-infrastructure capability validation."""

from __future__ import annotations

from typing import Any

from target_adapter_validation.capability import CapabilityValidationContext
from target_validation_support import expect_string_list, is_placeholder


AI_INFRASTRUCTURE_ROUTES_V1 = {
    "inventory",
    "use-existing",
    "adapt-import",
    "gate-checker-change",
    "tool-mcp-change",
    "bridge-wrapper-change",
}
AI_INFRASTRUCTURE_ROUTES = AI_INFRASTRUCTURE_ROUTES_V1 | {"recommend"}
AI_INFRASTRUCTURE_ITEM_TYPES = {
    "skill",
    "prompt",
    "gate",
    "checker",
    "flow",
    "tool",
    "mcp",
    "bridge",
    "wrapper",
    "rule",
    "template",
    "other",
}


class AIInfrastructureRouterModule:
    """Validate the optional AI-infrastructure router."""

    check_id = "check_ai_infrastructure_router"

    def validate(
        self,
        context: CapabilityValidationContext,
        manifest: Any,
    ) -> None:
        del manifest
        relpath = ".ai/assistant/ai-infrastructure-router.json"
        path = context.target_path(relpath)
        data = context.load_json_object(path, "AI_ROUTER")
        if data is None:
            return
        schema_version = data.get("schema_version")
        if schema_version not in {1, 2}:
            context.error("AI_ROUTER_SCHEMA", "schema_version should be 1 or 2", relpath)
        elif schema_version == 1:
            context.warn(
                "AI_ROUTER_LEGACY_SCHEMA",
                "schema_version 1 has no evidence-based recommendation route",
                relpath,
            )
        if data.get("router_kind") != "target-ai-infrastructure-router":
            context.error(
                "AI_ROUTER_KIND",
                "router_kind should be target-ai-infrastructure-router",
                relpath,
            )
        routing_order = expect_string_list(
            data.get("routing_order"), context, "AI_ROUTER_ORDER", relpath
        )
        expected_routes = (
            AI_INFRASTRUCTURE_ROUTES
            if schema_version == 2
            else AI_INFRASTRUCTURE_ROUTES_V1
        )
        if set(routing_order) != expected_routes:
            context.error(
                "AI_ROUTER_ROUTES",
                "routing_order must contain each portable AI infrastructure route",
                relpath,
            )
        item_types = expect_string_list(
            data.get("item_types"), context, "AI_ROUTER_ITEM_TYPES", relpath
        )
        if set(item_types) != AI_INFRASTRUCTURE_ITEM_TYPES:
            context.error(
                "AI_ROUTER_ITEM_TYPES",
                "item_types must match the portable item type set",
                relpath,
            )

        if schema_version == 2:
            recommendation_template = data.get("recommendation_template")
            if not isinstance(recommendation_template, str) or not recommendation_template:
                context.error(
                    "AI_ROUTER_RECOMMENDATION_TEMPLATE",
                    "schema_version 2 requires recommendation_template",
                    relpath,
                )
            else:
                context.check_optional_target_reference(
                    recommendation_template,
                    relpath,
                    "recommendation_template",
                )

        routes = data.get("routes")
        if not isinstance(routes, dict):
            context.error("AI_ROUTER_ROUTE_SHAPE", "routes must be an object", relpath)
            routes = {}
        for route_name in expected_routes:
            route = routes.get(route_name)
            if not isinstance(route, dict):
                context.error(
                    "AI_ROUTER_ROUTE_MISSING",
                    f"route is missing: {route_name}",
                    relpath,
                )
                continue
            for field in [
                "use_when",
                "required_context",
                "expand_when",
                "allowed_actions",
                "approval_gates",
                "validation",
                "final_evidence",
            ]:
                values = expect_string_list(
                    route.get(field),
                    context,
                    "AI_ROUTER_ROUTE_FIELD",
                    relpath,
                    label=f"routes.{route_name}.{field}",
                )
                if field == "required_context":
                    for value in values:
                        context.check_optional_target_reference(
                            value, relpath, f"routes.{route_name}.{field}"
                        )
                if field == "allowed_actions":
                    context.check_allowed_actions(
                        values, relpath, f"routes.{route_name}.{field}"
                    )

        items = data.get("items")
        if not isinstance(items, list) or not items:
            context.error("AI_ROUTER_ITEMS", "items must be a non-empty list", relpath)
            return
        item_ids: set[str] = set()
        for index, item in enumerate(items):
            label = f"items[{index}]"
            if not isinstance(item, dict):
                context.error(
                    "AI_ROUTER_ITEM_SHAPE", f"{label} must be an object", relpath
                )
                continue
            item_id = item.get("id")
            if not isinstance(item_id, str) or not item_id:
                context.error(
                    "AI_ROUTER_ITEM_ID", f"{label}.id must be a string", relpath
                )
            elif not is_placeholder(item_id):
                if item_id in item_ids:
                    context.error(
                        "AI_ROUTER_ITEM_DUPLICATE",
                        f"duplicate item id {item_id}",
                        relpath,
                    )
                item_ids.add(item_id)
            item_type = item.get("type")
            if (
                not is_placeholder(item_type)
                and item_type not in AI_INFRASTRUCTURE_ITEM_TYPES
            ):
                context.error(
                    "AI_ROUTER_ITEM_TYPE",
                    f"{label}.type is invalid: {item_type}",
                    relpath,
                )
            status = item.get("status")
            if not is_placeholder(status) and status not in {
                "active",
                "blocked",
                "deprecated",
                "unresolved",
            }:
                context.error(
                    "AI_ROUTER_ITEM_STATUS",
                    f"{label}.status is invalid: {status}",
                    relpath,
                )
            for field in [
                "activation_triggers",
                "required_context",
                "assistant_surfaces",
                "wrappers",
                "allowed_actions",
                "required_permissions",
                "approval_triggers",
                "gates",
                "validation",
                "conflicts_with",
            ]:
                values = expect_string_list(
                    item.get(field),
                    context,
                    "AI_ROUTER_ITEM_FIELD",
                    relpath,
                    label=f"{label}.{field}",
                )
                if field in {"required_context", "wrappers", "gates"}:
                    for value in values:
                        context.check_optional_target_reference(
                            value, relpath, f"{label}.{field}"
                        )
                if field == "allowed_actions":
                    context.check_allowed_actions(values, relpath, f"{label}.{field}")
            for field in ["canonical_source", "output_contract", "adaptation_record"]:
                value = item.get(field)
                if not isinstance(value, str) or not value:
                    context.error(
                        "AI_ROUTER_ITEM_FIELD",
                        f"{label}.{field} must be a string",
                        relpath,
                    )
                elif field != "output_contract":
                    context.check_optional_target_reference(
                        value, relpath, f"{label}.{field}"
                    )


AI_INFRASTRUCTURE_ROUTER_MODULE = AIInfrastructureRouterModule()
