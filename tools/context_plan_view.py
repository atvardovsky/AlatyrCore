"""Compact navigation for a complete context plan, never a replacement packet."""

from __future__ import annotations

from typing import Any


def _diagnostic(row: dict) -> dict:
    details = row.get("details", {})
    bounded = {}
    for key, value in details.items():
        if type(value) in (int, bool) or value is None:
            bounded[key] = value
        elif isinstance(value, str) and len(value) <= 512:
            bounded[key] = value
        elif key in {"fields", "context_ids", "failures"} and isinstance(value, list):
            bounded[key] = [str(item)[:512] for item in value[:8]]
            bounded[key + "_omitted_count"] = max(0, len(value) - 8)
    message = row["message"]
    return {"code": row["code"], "message": message[:1024], "message_truncated": len(message) > 1024,
            "details": bounded, "omitted_detail_keys": sorted(details.keys() - bounded.keys())}


def compact_plan_view(plan: dict[str, Any], *, source_report: dict | None = None) -> dict[str, Any]:
    packet = plan.get("context_packet") or {}
    working = plan.get("working_set") or {}
    items = packet.get("selected_items", [])
    mandatory = set(working.get("mandatory_item_ids", [row["id"] for row in items]))
    ordered = sorted(items, key=lambda row: (row["id"] not in mandatory, row["id"]))
    shown = ordered[:16]
    impact = plan.get("impact") or {}
    result = {
        "schema_version": 1, "view_kind": "compact-target-context-plan",
        "status": plan["status"], "read_only": True,
        "source_plan_digest": plan["plan_digest"], "source_report": source_report,
        "executable_packet": False, "authorization_granted": False, "acceptance_granted": False,
        "upgrade_required": plan.get("upgrade_required", False),
        "errors": [_diagnostic(row) for row in plan.get("errors", [])],
        "required_actions": plan.get("required_actions", []),
        "selected_item_count": len(items), "mandatory_item_count": len(mandatory),
        "selected_items": [{key: row[key] for key in ("id", "path", "content_digest")} for row in shown],
        "omitted_item_count": len(items) - len(shown),
        "omitted_mandatory_count": len(mandatory - {row["id"] for row in shown}),
        "unresolved_relationship_count": len(impact.get("unresolved_relationships", [])),
        "budget": packet.get("budget"),
        "detail_recovery": "Read the bound full report." if source_report else "Rerun this read-only command without --compact for complete diagnostics and context references.",
        "limitation": "Navigation only. Load the complete plan and required sources before acting; omitted details, missing host telemetry and unresolved relationships are not cleared.",
    }
    if working:
        result["working_set"] = {key: working[key] for key in ("phase", "information_need", "scope", "mandatory_retained", "accounting")}
        result["working_set"]["optional_omission_count"] = len(working["optional_omissions"])
        result["working_set"]["unselected_topic_count"] = len(working["declared_topics_unselected"])
        if "delta" in working:
            delta = working["delta"]
            result["working_set"]["delta"] = {"previous_plan_digest": delta["previous_plan_digest"], **{key.replace("_ids", "_count"): len(delta[key]) for key in ("added_ids", "changed_ids", "retained_ids", "retired_ids", "semantic_added_ids", "semantic_changed_ids", "semantic_retired_ids")}, "host_eviction_performed": False}
    if "knowledge" in plan:
        knowledge = plan["knowledge"]
        result["knowledge"] = {"stage": knowledge["stage"], "searched_shard_ids": knowledge["searched_shard_ids"],
            "constraint_count": len(knowledge["selection"]["constraints"]), "warning_count": len(knowledge["selection"]["warnings"]),
            "global_coverage": False, "actual_use": "not-observed"}
        result["delivery_budget"] = plan["delivery_budget"]
    if "question" in plan:
        question = plan["question"]
        result["question"] = {key: question[key] for key in ("task_id", "model", "obligation_id", "probe_sha256", "actual_use")}
        result["delivery_budget"] = plan["delivery_budget"]
    return result
