"""Derived review-only worker bookkeeping; never execution-tree acceptance."""
from __future__ import annotations

import json
import math

from delegation_evidence import NODE_FIELDS, worker_result_sha256
from prepare_delegation_context import measurement


def observed_metrics(value: dict | None) -> dict:
    if value is None:
        return {}
    allowed = {"packet_preparation_seconds", "worker_seconds", "primary_review_seconds", "rework_count"}
    if not isinstance(value, dict) or not value or set(value) - allowed:
        raise ValueError("metrics must contain only explicit cooperation timing or rework observations")
    for key, number in value.items():
        if type(number) not in (int, float) or not 0 <= number <= 1_000_000_000 or not math.isfinite(number):
            raise ValueError(f"metrics.{key} must be a finite nonnegative number at most 1000000000")
        if key == "rework_count" and type(number) is not int:
            raise ValueError("metrics.rework_count must be an integer")
    return dict(value)


def handoff(result: dict, packet: dict, contents: dict[str, bytes], metrics: dict | None = None) -> tuple[dict, bytes]:
    if (result.get("status") != "requires-review" or result.get("satisfied_proof_obligation_ids") != []
            or result.get("subtree_sha256") != worker_result_sha256(result)):
        raise ValueError("handoff requires an unchanged review-required result draft")
    measured = {name: {"path": name + ".txt", **measurement(content)} for name, content in contents.items()}
    if (set(measured) != {"context", "raw", "summary"}
            or measured["raw"] != result["raw_payload"] or measured["summary"] != result["accepted_summary"]
            or measured["context"]["sha256"] != result["input_context_packet_sha256"]):
        raise ValueError("handoff artifacts do not match the prepared result")
    serialized = (json.dumps(result, indent=2) + "\n").encode("utf-8")
    node = {key: result[key] for key in ("node_id", "packet_id", "parent_packet_id", "result_id", "depth", "stop_reason_id")}
    node.update(status="REVIEW_REQUIRED", result_status="requires-review",
                context_evidence=measured["context"], context_words=measured["context"]["word_count"],
                result_evidence={"path": "result.json", **measurement(serialized)},
                accepted_summary_evidence=measured["summary"], satisfied_acceptance_ids=[], satisfied_proof_obligation_ids=[])
    return {"schema_version": 1, "record_kind": "alatyr-worker-handoff-draft", "status": "requires-review",
            "source_workstream_id": packet["workstream_id"], "base_revision": result["base_revision"],
            "canonical_result_sha256": result["subtree_sha256"], "node_update_candidate": node,
            "required_primary_bindings": sorted(NODE_FIELDS - set(node)),
            "observed_metrics": observed_metrics(metrics),
            "measurement_boundary": "Artifact words and characters are not provider token or billing measurements; supplied timings are advisory observations, not verified runtime provenance.",
            "limitation": "Incomplete node draft only; reconcile packet/event identities, preserve current parent, scope, capability and budget bindings, then perform primary review and canonical tree validation. No acceptance or authorization is granted."}, serialized


def compact_handoff(draft: dict) -> dict:
    node = draft["node_update_candidate"]
    return {"record_kind": "alatyr-worker-handoff-view", "status": draft["status"],
            "workstream_id": draft["source_workstream_id"], "base_revision": draft["base_revision"],
            "node_id": node["node_id"], "packet_id": node["packet_id"], "result_id": node["result_id"],
            "canonical_result_sha256": draft["canonical_result_sha256"], "result_artifact": node["result_evidence"],
            "context_words": node["context_words"], "summary_words": node["accepted_summary_evidence"]["word_count"],
            "required_primary_binding_count": len(draft["required_primary_bindings"]),
            "observed_metrics": draft["observed_metrics"], "handoff_path": "handoff.json",
            "limitation": "Review-only view, not an accepted node. Full candidate bindings remain in handoff.json; no authorization or acceptance is granted."}
