"""Optional coverage-aware selection; never remove canonical required context."""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from dataclasses import replace
from pathlib import Path, PureWindowsPath
from typing import Any, Callable

if __package__:
    from .context_catalog import CatalogItem, context_packet_usage
    from .context_input_snapshot import ContextInputLimit, read_context_bytes
else:
    from context_catalog import CatalogItem, context_packet_usage
    from context_input_snapshot import ContextInputLimit, read_context_bytes

SCHEMA_ROOT = Path(__file__).resolve().parents[1] / "schemas"
MAX_SCOPE_ITEMS = 512
MAX_SCOPE_CATALOG_ITEMS = 16384


class WorkingSetError(ValueError):
    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code, self.details = code, details


def canonical_digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def read_evidence(value: str, target: Path) -> dict:
    if "\x00" in value:
        raise WorkingSetError("CONTEXT_PLAN_EVIDENCE_INVALID", "evidence path contains a null character")
    path = Path(value)
    relative = not path.is_absolute()
    if relative:
        if path.drive or PureWindowsPath(value).drive or any(part in {"..", "."} for part in path.parts) or "\\" in value:
            raise WorkingSetError("CONTEXT_PLAN_EVIDENCE_INVALID", "evidence must be absolute or normalized target-relative")
        path = target / path
    try:
        resolved = path.resolve()
        if relative and resolved != target.resolve() and target.resolve() not in resolved.parents:
            raise WorkingSetError("CONTEXT_PLAN_EVIDENCE_INVALID", "relative evidence escapes the target; select external evidence explicitly by absolute path")
        if path.is_symlink() or not path.is_file():
            raise WorkingSetError("CONTEXT_PLAN_EVIDENCE_INVALID", "evidence must be an explicitly selected regular JSON file")
        raw = read_context_bytes(resolved, routing_input=False, max_bytes=4 * 1024 * 1024)
        result = json.loads(raw.decode("utf-8"))
    except WorkingSetError:
        raise
    except (OSError, RuntimeError, UnicodeError, ValueError, ContextInputLimit) as exc:
        raise WorkingSetError("CONTEXT_PLAN_EVIDENCE_INVALID", "cannot read bounded context evidence", reason=type(exc).__name__) from exc
    if not isinstance(result, dict):
        raise WorkingSetError("CONTEXT_PLAN_EVIDENCE_INVALID", "context evidence must be a JSON object")
    return result


def validate_document(value: Any, schema_name: str) -> None:
    from jsonschema import Draft202012Validator

    try:
        schema = json.loads((SCHEMA_ROOT / schema_name).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkingSetError("CONTEXT_WORKING_SET_SCHEMA_UNAVAILABLE", "matching source-tool schema is unavailable", schema=schema_name) from exc
    try:
        failure = next(Draft202012Validator(schema).iter_errors(value), None)
    except RecursionError as exc:
        raise WorkingSetError("CONTEXT_WORKING_SET_INVALID", "working-set input nesting exceeds the validation bound") from exc
    if failure is not None:
        field = ".".join(str(part) for part in failure.path) or "$"
        raise WorkingSetError("CONTEXT_WORKING_SET_INVALID", "working-set input violates its schema", fields=[field])


def required_selection(document: dict, items: dict[str, CatalogItem], selected: dict, reasons: dict) -> dict:
    validate_document(document, "alatyr-context-working-set-request.schema.json")
    for item_id, item in selected.items():
        catalog_item = items.get(item_id)
        if catalog_item is not None and replace(item, estimated_characters=catalog_item.estimated_characters) != catalog_item:
            raise WorkingSetError("CONTEXT_ID_COLLISION", "working-set catalog identity conflicts with mandatory context", context_ids=[item_id])
    optional = document["optional_context"]
    candidate_ids = [row["context_id"] for row in optional]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise WorkingSetError("CONTEXT_WORKING_SET_INVALID", "optional context IDs must be unique")
    named = set(document["required_context_ids"]) | set(candidate_ids)
    missing = sorted(named - items.keys())
    if missing:
        raise WorkingSetError("CONTEXT_WORKING_SET_UNKNOWN_ID", "working-set IDs are absent from the current catalogs", context_ids=missing)
    required = set(document["required_context_ids"])
    exhaustive = []
    if document.get("exhaustive_contours") and len(items) > MAX_SCOPE_CATALOG_ITEMS:
        raise WorkingSetError("CONTEXT_WORKING_SET_WORK_LIMIT", "exhaustive inventory exceeds the bounded routing scan", enumeration_complete=False, catalog_items=len(items), maximum=MAX_SCOPE_CATALOG_ITEMS)
    for contour in document.get("exhaustive_contours", []):
        matching = []
        for item in items.values():
            if item.path.startswith(f".ai/{contour}/"):
                matching.append(item.item_id)
                if len(exhaustive) + len(matching) > MAX_SCOPE_ITEMS:
                    raise WorkingSetError("CONTEXT_WORKING_SET_WORK_LIMIT", "exhaustive scope requires bounded decomposition", enumeration_complete=False, maximum=MAX_SCOPE_ITEMS)
        matching.sort()
        if not matching:
            raise WorkingSetError("CONTEXT_WORKING_SET_EMPTY_SCOPE", "exhaustive contour has no indexed content", contour=contour)
        exhaustive.extend(matching)
    required.update(exhaustive)
    for item_id in sorted(required):
        selected.setdefault(item_id, items[item_id])
        reasons.setdefault(item_id, set()).add("working-set-required")
    return {
        "schema_version": 1, "view_kind": "context-working-set", "authority": "none",
        "phase": document["phase"], "information_need": document["information_need"],
        "request_digest": canonical_digest(document),
        "scope": {"contours": document.get("exhaustive_contours", []),
                  "indexed_item_count": len(exhaustive), "indexed_ids_digest": canonical_digest(sorted(exhaustive)),
                  "semantic_review_performed": False, "unindexed_source_coverage": "not-established"},
        "mandatory_item_ids": [], "optional_selected_ids": [], "optional_omissions": [],
        "declared_topics_selected": [], "declared_topics_unselected": [],
        "authorization_granted": False, "acceptance_granted": False,
        "host_context_eviction_performed": False,
        "limitation": "Routing and declared topic coverage only; not proof-obligation discharge, semantic completeness, host delivery, authorization, cache hits or acceptance.",
    }


def select_optional(document: dict, view: dict, items: dict[str, CatalogItem], selected: dict,
                    reasons: dict, terms: dict, *, max_files: int, max_words: int,
                    max_characters: int | None, close: Callable, hydrate: Callable,
                    resolve_terms: Callable) -> dict:
    view["mandatory_item_ids"] = sorted(selected)
    if not _fits(selected, terms, max_files, max_words, max_characters):
        return terms
    covered = {topic for row in document["optional_context"] if row["context_id"] in selected for topic in row["topics"]}
    all_topics = {topic for row in document["optional_context"] for topic in row["topics"]}
    pending = {}
    term_words = {key: context_packet_usage((), {key: term})["total_words"] for key, term in terms.items()}
    for row in document["optional_context"]:
        item_id = row["context_id"]
        if item_id in selected:
            covered.update(row["topics"])
        elif document["phase"] not in row.get("phases", [document["phase"]]):
            view["optional_omissions"].append({"id": item_id, "reason": "phase-not-selected"})
        elif not set(row["topics"]) - covered:
            view["optional_omissions"].append({"id": item_id, "reason": "no-new-declared-topic"})
        else:
            closure = {item_id: items[item_id]}
            closure_reasons = {item_id: {"working-set-optional"}}
            close(closure, closure_reasons)
            trial_ids = selected.keys() | closure.keys()
            if len(trial_ids) > min(max_files, MAX_SCOPE_ITEMS) or sum((selected.get(key) or closure[key]).estimated_words for key in trial_ids) > max_words:
                view["optional_omissions"].append({"id": item_id, "reason": "budget"})
                continue
            closure_terms = resolve_terms(closure.values())
            for key, term in closure_terms.items():
                if key not in term_words:
                    term_words[key] = context_packet_usage((), {key: term})["total_words"]
            pending[item_id] = (row, closure, closure_reasons, closure_terms)
    while pending:
        def score(item_id: str) -> tuple:
            row, closure, _, closure_terms = pending[item_id]
            cost = sum(item.estimated_words for key, item in closure.items() if key not in selected)
            cost += sum(term_words[key] for key in closure_terms if key not in terms)
            return (-Fraction(len(set(row["topics"]) - covered), max(1, cost)), cost, item_id)

        item_id = min(pending, key=score)
        row, closure, closure_reasons, closure_terms = pending.pop(item_id)
        additions = {key: item for key, item in closure.items() if key not in selected}
        if not set(row["topics"]) - covered:
            view["optional_omissions"].append({"id": item_id, "reason": "no-new-declared-topic"})
            continue
        if len(selected) + len(additions) > min(max_files, MAX_SCOPE_ITEMS) or sum(item.estimated_words for item in selected.values()) + sum(item.estimated_words for item in additions.values()) > max_words:
            view["optional_omissions"].append({"id": item_id, "reason": "budget"})
            continue
        hydrate(additions)
        trial = {**selected, **additions}
        trial_terms = {**terms, **closure_terms}
        if not _fits(trial, trial_terms, max_files, max_words, max_characters):
            view["optional_omissions"].append({"id": item_id, "reason": "budget"})
            continue
        selected.update(additions)
        for key, values in closure_reasons.items():
            reasons.setdefault(key, set()).update(values)
        terms = trial_terms
        covered.update(row["topics"])
        view["optional_selected_ids"].append(item_id)
    view["declared_topics_selected"] = sorted(covered)
    view["declared_topics_unselected"] = sorted(all_topics - covered)
    return terms


def _fits(items: dict, terms: dict, max_files: int, max_words: int, max_characters: int | None) -> bool:
    usage = context_packet_usage(items.values(), terms)
    return len(items) <= min(max_files, MAX_SCOPE_ITEMS) and usage["total_words"] <= max_words and (max_characters is None or usage["total_characters"] <= max_characters)


def target_identity(target: Path) -> str:
    return canonical_digest({"physical_target": str(target.resolve())})


def plan_delta(previous: dict, plan: dict, target: Path) -> dict:
    if not isinstance(previous, dict) or type(previous.get("schema_version")) is not int or previous["schema_version"] != 1 or previous.get("plan_kind") != "target-context-plan" or previous.get("status") != "ready":
        raise WorkingSetError("CONTEXT_PREVIOUS_PLAN_INVALID", "previous context plan must be a ready version-1 plan")
    content = {key: value for key, value in previous.items() if key != "plan_digest"}
    if previous.get("plan_digest") != canonical_digest(content):
        raise WorkingSetError("CONTEXT_PREVIOUS_PLAN_INVALID", "previous plan digest does not match its contents")
    view = previous.get("working_set")
    if not isinstance(view, dict) or view.get("target_identity") != target_identity(target):
        raise WorkingSetError("CONTEXT_PREVIOUS_PLAN_INVALID", "previous plan is not bound to this physical target")
    prior_request = previous.get("request")
    if not isinstance(prior_request, dict) or any(prior_request.get(key) != plan["request"].get(key) for key in ("profile", "operation", "assistant_surface")):
        raise WorkingSetError("CONTEXT_PREVIOUS_PLAN_INVALID", "previous plan belongs to another profile, operation or assistant surface")
    def identities(value: Any) -> dict:
        if not isinstance(value, dict) or not isinstance(value.get("selected_items"), list) or len(value["selected_items"]) > MAX_SCOPE_ITEMS:
            raise WorkingSetError("CONTEXT_PREVIOUS_PLAN_INVALID", "previous packet selected items must be a bounded list")
        result = {}
        for row in value["selected_items"]:
            if not isinstance(row, dict) or not all(isinstance(row.get(key), str) and row[key] for key in ("id", "path", "content_digest")) or row["id"] in result:
                raise WorkingSetError("CONTEXT_PREVIOUS_PLAN_INVALID", "previous packet identities must be unique resolved strings")
            result[row["id"]] = canonical_digest(row)
        return result
    before, after = identities(previous.get("context_packet")), identities(plan["context_packet"])
    common = before.keys() & after.keys()
    def semantic_identities(packet: dict) -> dict:
        rows = packet.get("semantic_term_identities")
        if not isinstance(rows, list) or len(rows) > MAX_SCOPE_CATALOG_ITEMS:
            raise WorkingSetError("CONTEXT_PREVIOUS_PLAN_INVALID", "previous semantic identities must be a bounded list")
        result = {}
        for row in rows:
            if not isinstance(row, dict) or not all(isinstance(row.get(key), str) and row[key] for key in ("id", "canonical_owner", "definition_digest")) or type(row.get("version")) is not int or row["version"] < 1 or row["id"] in result:
                raise WorkingSetError("CONTEXT_PREVIOUS_PLAN_INVALID", "previous semantic identities must be unique resolved records")
            result[row["id"]] = canonical_digest(row)
        return result
    prior_terms, current_terms = semantic_identities(previous["context_packet"]), semantic_identities(plan["context_packet"])
    return {"previous_plan_digest": previous["plan_digest"],
            "added_ids": sorted(after.keys() - before.keys()), "retired_ids": sorted(before.keys() - after.keys()),
            "changed_ids": sorted(key for key in common if before[key] != after[key]),
            "retained_ids": sorted(key for key in common if before[key] == after[key]),
            "semantic_added_ids": sorted(current_terms.keys() - prior_terms.keys()),
            "semantic_retired_ids": sorted(prior_terms.keys() - current_terms.keys()),
            "semantic_changed_ids": sorted(key for key in current_terms.keys() & prior_terms.keys() if current_terms[key] != prior_terms[key]),
            "authority_reused": False, "previous_content_reused": False,
            "host_eviction_performed": False, "provider_cache_hit": "unobserved"}


def delivery_accounting(document: dict, packet: dict) -> dict:
    validate_document(document, "alatyr-context-delivery-observation.schema.json")
    receipt = document["context_receipt"]
    validate_document(receipt, "alatyr-context-receipt.schema.json")
    if __package__:
        from .context_receipt import validate_context_receipt
    else:
        from context_receipt import validate_context_receipt

    failures = validate_context_receipt(receipt)
    expected_paths = [row["path"] for row in packet["selected_items"]]
    if document["packet_digest"] != packet["source_packet"]["content_bound_digest"]:
        failures.append("observation packet digest differs from the current packet")
    for stage in ("planned", "resolved"):
        if set(receipt[stage]["paths"]) != set(expected_paths) or receipt[stage]["approximate_words"] != packet["budget"]["total_words"]:
            failures.append(f"{stage} context differs from the current packet")
    if receipt["measurement_state"] != "observed" or receipt["observed"]["evidence_level"] == "unavailable":
        failures.append("delivery observation requires recorded observed evidence")
    if failures:
        raise WorkingSetError("CONTEXT_DELIVERY_OBSERVATION_INVALID", "delivery observation does not bind the current context", failures=failures[:8])
    observed = receipt["observed"]
    evidence = observed["evidence"].encode("utf-8")
    return {"measurement": "recorded-observation", "receipt_digest": canonical_digest(receipt),
            "observed": {key: observed[key] for key in ("evidence_level", "source", "files_loaded", "input_tokens", "output_tokens")},
            "evidence_reference": {"field": "context_receipt.observed.evidence", "character_count": len(observed["evidence"]), "sha256": "sha256:" + hashlib.sha256(evidence).hexdigest()},
            "independently_verified": False,
            "cached_input_tokens": "unknown", "total_task_and_worker_tokens": "unknown",
            "billing_savings": "unknown", "acceptance_granted": False}
