"""Deliver selected, source-bound diagnostics without promoting relationships."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft7Validator

from architecture_review import BoundedReviewDigests, review_failures
from target_adapter_validation.context import TargetRepositoryView
from path_spec import logical_path
from relationship_candidates import candidate_semantic_failures

SCHEMA = Path(__file__).resolve().parents[1] / "schemas/alatyr-relationship-candidates.schema.json"


def selected_candidate_warnings(target: Path, candidate_path: str | None, selected_nodes: Iterable[str], *, graph: Any = None) -> dict[str, Any]:
    result = {"source": None, "warnings": [], "diagnostics": [], "authority": "none"}
    if candidate_path is None:
        return result
    view = TargetRepositoryView(target)
    try:
        logical_path(candidate_path)
        read = view.read_bytes_result(Path(candidate_path), max_bytes=512 * 1024)
    except (OSError, ValueError, TypeError):
        result["diagnostics"].append("relationship candidate path must be a contained repository-relative file")
        return result
    result["source"] = {"path": candidate_path, "sha256": read.digest}
    if read.value is None:
        result["diagnostics"].append("relationship candidates unavailable; reviewed warnings require revalidation")
        return result
    data = view.read_json_result(Path(candidate_path)).value
    schema = TargetRepositoryView(SCHEMA.parent).read_json_result(SCHEMA).value
    if not isinstance(schema, dict) or not isinstance(data, dict) or type(data.get("schema_version")) is not int or list(Draft7Validator(schema).iter_errors(data)):
        result["diagnostics"].append("relationship candidates invalid; reviewed warnings require revalidation")
        return result
    if graph is None:
        result["diagnostics"].append("reviewed warning graph is unavailable; revalidation required")
        return result
    semantic = candidate_semantic_failures(data["records"], graph.nodes)
    if semantic:
        result["diagnostics"].extend(message for _, message in semantic)
        return result
    selected = set(selected_nodes)
    digests = BoundedReviewDigests(view)
    for candidate in sorted(data["records"], key=lambda item: item["id"]):
        warning = candidate.get("reviewed_warning")
        if warning is None or candidate["state"] in ("rejected", "removed") or not selected.intersection((candidate["source_node"], candidate["target_node"])):
            continue
        review = warning["source_review"]
        failures = review_failures(review, digests)
        inputs = review.get("inputs", []) if isinstance(review, dict) else []
        bound = {item.get("path") for item in inputs if isinstance(item, dict) and isinstance(item.get("path"), str)} if isinstance(inputs, list) else set()
        required = {warning["document"], warning["finding_ref"].partition("#")[0], *warning["comparison_sources"]}
        if not required <= bound or review.get("state") != "reviewed":
            failures.append("review must bind the document, finding and canonical comparison sources")
        failures.extend(_finding_failures(view, warning, graph, candidate))
        result["warnings"].append({"candidate_id": candidate["id"], "document": warning["document"], "finding_ref": warning["finding_ref"],
                                   "state": "revalidation-required" if failures else "reviewed-warning", "failures": failures,
                                   "authority": "none", "relationship_state": candidate["state"]})
    if view.finalize():
        result["diagnostics"].append("warning inputs changed during lookup; revalidation required")
        for warning in result["warnings"]:
            warning["state"] = "revalidation-required"
    return result


def _finding_failures(view: TargetRepositoryView, warning: dict, graph: Any, candidate: dict) -> list[str]:
    path, _, finding_id = warning["finding_ref"].partition("#")
    try:
        logical_path(path)
        raw = view.read_bytes_result(Path(path), max_bytes=128 * 1024)
        finding = view.read_json_result(Path(path)).value if raw.value is not None else None
    except (OSError, ValueError, TypeError):
        finding = None
    expected = {"schema_version": 1, "record_kind": "target-reviewed-document-warning", "finding_id": finding_id,
                "document": warning["document"], "comparison_sources": warning["comparison_sources"],
                "source_node": candidate["source_node"], "target_node": candidate["target_node"]}
    if not finding_id or not isinstance(finding, dict) or type(finding.get("schema_version")) is not int or set(finding) != {*expected, "reason"} or any(finding.get(key) != value for key, value in expected.items()):
        return ["finding_ref must select a matching structured reviewed-document-warning record; warning identities cannot be retargeted"]
    from target_adapter_validation.values import is_resolved_string
    failures = [] if is_resolved_string(finding.get("reason")) else ["reviewed finding requires a concrete reason"]
    owners = set()
    for node_id in (candidate["source_node"], candidate["target_node"]):
        node = graph.nodes[node_id]
        if isinstance(node.get("canonical_owner"), str):
            owners.add(node["canonical_owner"].partition("#")[0])
        owners.update(binding["path"] for binding in node.get("bindings", []) if isinstance(binding, dict) and binding.get("authority") == "canonical" and isinstance(binding.get("path"), str) and binding.get("selector_kind") != "glob")
    if not set(warning["comparison_sources"]) <= owners:
        failures.append("comparison sources must resolve to the candidate endpoints' canonical file owners")
    return failures
