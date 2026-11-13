"""Bounded, read-only evidence selection for a question, not another change planner."""

from __future__ import annotations

import hashlib
import json
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from path_spec import logical_path
from project_evidence import ProjectEvidence
from registry_facts import REGISTRY_PATH, parse_registry_fact_entries, registry_route_health
from registry_ownership import owner_paths

PURPOSES = ("observed-code", "project-intent", "change-impact")
MAX_SOURCES = 8
MAX_CONTENT_BYTES = 24 * 1024
MAX_CONTENT_WORDS = 4000
MAX_REPORT_BYTES = 64 * 1024
ARCHITECTURE_PATH = ".ai/project/architecture/catalog.json"


def render_lookup(result: dict) -> str:
    rendered = json.dumps(result, ensure_ascii=True, separators=(",", ":")) + "\n"
    if len(rendered.encode("utf-8")) > MAX_REPORT_BYTES:
        raise ValueError(f"lookup report exceeds {MAX_REPORT_BYTES} bytes; narrow or decompose")
    return rendered


def _projection(evidence: ProjectEvidence, item_id: str) -> dict:
    from architecture_review import review_failures
    catalog = evidence.object(ARCHITECTURE_PATH)
    if (type(catalog.get("schema_version")) is not int or catalog["schema_version"] not in {1, 2}
            or catalog.get("catalog_kind") != "target-architecture-knowledge-catalog"):
        raise ValueError("selected architecture catalog has an unsupported identity or schema")
    rows = []
    for name in ("areas", "patterns"):
        items = catalog.get(name)
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise ValueError(f"architecture {name} must be an object list")
        rows.extend(item for item in items if item.get("id") == item_id)
    if len(rows) != 1:
        raise ValueError("architecture item must identify one exact catalog entry")
    item = rows[0]
    status = item.get("status")
    if not isinstance(status, str) or status not in {
            "observed", "proposed", "accepted", "preferred", "restricted", "deprecated", "contradicted", "unknown"}:
        raise ValueError("selected architecture item has an invalid knowledge state")
    def digest(path: str) -> str | None:
        try:
            return hashlib.sha256(evidence.exact(path)).hexdigest()
        except FileNotFoundError:
            return None
    failures = review_failures(item.get("source_review"), digest)
    if catalog.get("schema_version") != 2 or catalog.get("module_state") != "enabled":
        failures.append("selected catalog is legacy or not enabled; review freshness is not established")
    review = item.get("source_review")
    state = review.get("state") if isinstance(review, dict) else None
    if state != "reviewed":
        failures.append("selected explanation does not have a reviewed source-bound disposition")
    return {"path": ARCHITECTURE_PATH, "id": item_id, "declared_state": item.get("status"),
            "review_state": state, "review_findings": failures,
            "source_review": "current-bindings-only" if not failures else "revalidation-required",
            "authority": "canonical-owners-not-replaced", "semantic_correctness": "not-verified"}


def project_lookup(target: Path, question: str, sources: list[str], *, purpose: str = "observed-code",
                   fact_type: str | None = None, start_line: int | None = None,
                   end_line: int | None = None, architecture_item: str | None = None,
                   navigation_report: Path | None = None) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip() or len(question) > 2000 or len(question.split()) > 200:
        raise ValueError("question requires 1..200 words and at most 2000 characters")
    if not isinstance(purpose, str) or purpose not in PURPOSES:
        raise ValueError("unknown lookup purpose")
    if (not isinstance(sources, list) or len(sources) > MAX_SOURCES
            or any(not isinstance(path, str) or len(path) > 512 for path in sources)
            or len({path.casefold() for path in sources}) != len(sources)):
        raise ValueError(f"lookup requires at most {MAX_SOURCES} unique exact source paths")
    for path in sources:
        logical_path(path)
    if purpose == "observed-code" and not sources:
        raise ValueError("observed-code lookup requires explicitly selected source files")
    if fact_type is not None and (not isinstance(fact_type, str) or not fact_type.strip() or len(fact_type) > 256):
        raise ValueError("fact type must be a concrete bounded registry heading")
    if purpose != "observed-code" and fact_type is None:
        raise ValueError("intent and impact lookup require one exact fact type")
    if architecture_item is not None and (not isinstance(architecture_item, str)
                                           or not architecture_item.strip() or len(architecture_item) > 256):
        raise ValueError("architecture item must be a concrete bounded ID")
    ranged = start_line is not None or end_line is not None
    if ranged and (purpose != "observed-code" or len(sources) != 1 or type(start_line) is not int
                   or type(end_line) is not int or not 1 <= start_line <= end_line):
        raise ValueError("line ranges require one observed-code source and positive start <= end")
    with ExitStack() as snapshots:
        evidence = snapshots.enter_context(ProjectEvidence(target))
        findings, selected, registry, projection = [], list(sources), None, None
        if fact_type is not None:
            entries = [entry for entry in parse_registry_fact_entries(evidence.exact(REGISTRY_PATH).decode("utf-8"))
                       if entry.heading_fact_type == fact_type]
            if len(entries) != 1:
                raise ValueError("fact type must identify one unique registry entry")
            entry = entries[0]
            if entry.conflicts or entry.declared_fact_type != fact_type:
                raise ValueError("selected registry entry has conflicting declarations")
            health = registry_route_health(entry)
            registry = {"path": REGISTRY_PATH, "line": entry.line, "fact_type": fact_type,
                        "declaration": entry.block, "health": health, "canonical_sources": []}
            for declaration in entry.owner_declarations:
                try:
                    owners = owner_paths(declaration.raw)
                except ValueError as exc:
                    findings.append({"code": "LOOKUP_OWNER_SELECTION", "message": str(exc)})
                    continue
                for owner in owners:
                    path = owner.partition("#")[0]
                    if path.endswith("/") or any(token in path for token in "*?["):
                        findings.append({"code": "LOOKUP_OWNER_SELECTION", "message": "select exact owner files for " + owner})
                        continue
                    registry["canonical_sources"].append(owner)
                    if purpose != "observed-code" and path not in selected:
                        selected.append(path)
            if not registry["canonical_sources"]:
                findings.append({"code": "LOOKUP_OWNER_MISSING", "message": "selected fact has no exact canonical source declaration"})
            if health["applicability"] != "applicable" or health["authority"] != "accepted":
                findings.append({"code": "LOOKUP_AUTHORITY_REVIEW", "message": "retain declared applicability and authority; do not promote the answer"})
            if health["mapping"] == "unavailable":
                findings.append({"code": "LOOKUP_COVERAGE_UNAVAILABLE", "message": "relationship coverage is unavailable, not factual non-applicability"})
        if len(selected) > MAX_SOURCES or len({path.casefold() for path in selected}) != len(selected):
            raise ValueError(f"owner closure exceeds {MAX_SOURCES} distinct files; decompose")
        content, total_bytes, total_words = [], 0, 0
        for path in selected:
            raw = evidence.exact(path)
            lines = raw.decode("utf-8").splitlines(keepends=True)
            first, last = (start_line, end_line) if ranged else ((1, len(lines)) if lines else (0, 0))
            if ranged and last > len(lines):
                raise ValueError("selected line range exceeds the source; no silent truncation")
            text = "".join(lines[first - 1:last]) if lines else ""
            total_bytes += len(text.encode("utf-8"))
            total_words += len(text.split())
            content.append({"path": path, "start_line": first, "end_line": last,
                            "sha256": hashlib.sha256(raw).hexdigest(), "text": text})
        if registry is not None:
            total_bytes += len(registry["declaration"].encode("utf-8"))
            total_words += len(registry["declaration"].split())
        if total_bytes > MAX_CONTENT_BYTES or total_words > MAX_CONTENT_WORDS:
            raise ValueError(f"selected content exceeds {MAX_CONTENT_BYTES} bytes or {MAX_CONTENT_WORDS} words; narrow or decompose")
        if architecture_item is not None:
            projection = _projection(evidence, architecture_item)
            if projection["review_findings"] or projection["declared_state"] == "contradicted":
                findings.append({"code": "LOOKUP_PROJECTION_REVIEW", "message": "selected architecture explanation needs canonical owner review"})
        navigation, navigation_binding = None, None
        if navigation_report is not None:
            from code_navigation import navigation_evidence
            path = navigation_report.absolute()
            captured = snapshots.enter_context(ProjectEvidence(path.parent))
            navigation = navigation_evidence(captured.object(path.name), question, set(selected), evidence)
            navigation_binding = captured.bindings()[0]
        expansion = []
        if purpose == "project-intent":
            expansion = ["Read canonical owners and distinguish observed, proposed, accepted and contradicted claims."]
        elif purpose == "change-impact":
            expansion = ["Use the existing context profile and impact route; inspect mapped relationships or re-derive invariants from canonical owners."]
        if findings:
            expansion.append("Resolve the named gaps before making authority, completeness or change-safety claims.")
        result = {
            "schema_version": 1, "report_kind": "project-lookup", "purpose": purpose,
            "status": "expansion-required" if expansion else "ready-for-inspection",
            "question": question, "content": content, "registry": registry, "projection": projection,
            "navigation": navigation, "navigation_report_binding": navigation_binding,
            "findings": findings, "required_expansion": expansion, "input_bindings": evidence.bindings(),
            "measurement": {"input_files": len(evidence.inputs), "input_bytes": sum(evidence.measured.values()),
                            "selected_content_bytes": total_bytes, "selected_content_words": total_words,
                            "scope": "this helper only; excludes host bootstrap, prior context, latency and billing"},
            "authorization_granted": False, "acceptance_granted": False, "code_executed": False,
            "limitations": ["Selected implementation is observed evidence, not accepted intent or proof of correctness.",
                            "Host instructions and applicable project constraints still apply; this helper does not validate compliance.",
                            "A narrow lookup is not complete impact analysis, exhaustive caller discovery or change authorization.",
                            "Input identity is rechecked at delivery; recheck selected context after concurrent changes."]}
        render_lookup(result)
    return result
