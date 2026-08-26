"""Validate and select bounded target project-knowledge routes."""

from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import jsonschema


CANONICAL_PROFILES = {
    "docs-local",
    "code-local",
    "business-change",
    "architecture-change",
    "data-change",
    "security-sensitive",
    "ai-infrastructure",
    "framework-upgrade",
}

GUIDANCE_KINDS = {
    "development-rule",
    "architectural-intent",
    "reviewed-knowledge",
    "validation-contract",
    "known-restriction",
}

PRECEDENCE_KINDS = {"base-rule", "narrower-rule", "authorized-exception"}


@dataclass(frozen=True)
class KnowledgeFinding:
    level: str
    code: str
    message: str
    path: str | None = None


def _load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _safe_path(target: Path, relpath: str) -> Path:
    path = Path(relpath)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe target-relative path: {relpath}")
    root = target.resolve()
    candidate = (target / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"target-relative path escapes target: {relpath}") from exc
    return candidate


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _placeholder(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("{") and value.endswith("}")


def _concrete(value: Any, allow_placeholders: bool) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    if allow_placeholders:
        return True
    return not _placeholder(value) and value.casefold() not in {
        "unknown",
        "unresolved",
        "pending",
        "not-applicable",
    }


def _schema_errors(
    data: dict[str, Any], schema: dict[str, Any], path: str, code: str
) -> list[KnowledgeFinding]:
    validator = jsonschema.Draft7Validator(schema)
    findings: list[KnowledgeFinding] = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(item) for item in error.absolute_path) or "root"
        findings.append(
            KnowledgeFinding("error", code, f"{location}: {error.message}", path)
        )
    return findings


def validate_project_knowledge(
    target: Path,
    schema_root: Path,
    *,
    allow_placeholders: bool = False,
    today: date | None = None,
) -> list[KnowledgeFinding]:
    index_relpath = ".ai/project/knowledge/index.json"
    findings: list[KnowledgeFinding] = []
    today = today or date.today()
    try:
        index_path = _safe_path(target, index_relpath)
    except ValueError as exc:
        return [KnowledgeFinding("error", "PROJECT_KNOWLEDGE_INDEX_PATH", str(exc), index_relpath)]
    if not index_path.is_file():
        return [KnowledgeFinding("error", "PROJECT_KNOWLEDGE_INDEX_MISSING", "project knowledge routing index is missing", index_relpath)]

    try:
        index = _load_object(index_path)
        index_schema = _load_object(schema_root / "alatyr-project-knowledge-index.schema.json")
        shard_schema = _load_object(schema_root / "alatyr-project-knowledge-shard.schema.json")
        promotion_schema = _load_object(schema_root / "alatyr-project-knowledge-promotion.schema.json")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [KnowledgeFinding("error", "PROJECT_KNOWLEDGE_LOAD", str(exc), index_relpath)]

    findings.extend(_schema_errors(index, index_schema, index_relpath, "PROJECT_KNOWLEDGE_INDEX_SCHEMA"))
    if findings:
        return findings

    routing_relpath = ".ai/assistant/context/project-knowledge-routing.json"
    try:
        routing_path = _safe_path(target, routing_relpath)
    except ValueError as exc:
        findings.append(
            KnowledgeFinding("error", "PROJECT_KNOWLEDGE_ROUTING_PATH", str(exc), routing_relpath)
        )
    else:
        if not routing_path.is_file():
            findings.append(
                KnowledgeFinding(
                    "error",
                    "PROJECT_KNOWLEDGE_ROUTING_MISSING",
                    "project knowledge routing descriptor is missing",
                    routing_relpath,
                )
            )
        else:
            try:
                routing = _load_object(routing_path)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                findings.append(
                    KnowledgeFinding(
                        "error", "PROJECT_KNOWLEDGE_ROUTING_LOAD", str(exc), routing_relpath
                    )
                )
            else:
                if (
                    routing.get("descriptor_kind") != "target-project-knowledge-routing"
                    or routing.get("index") != index_relpath
                ):
                    findings.append(
                        KnowledgeFinding(
                            "error",
                            "PROJECT_KNOWLEDGE_ROUTING_DRIFT",
                            "routing descriptor kind or index owner drifted",
                            routing_relpath,
                        )
                    )
                initial = set(routing.get("initial_selectors", []))
                refined = set(routing.get("refined_selectors", []))
                required_initial = {
                    "task profile",
                    "project areas",
                    "subsystems",
                    "architecture item IDs",
                    "named dependencies",
                    "contract IDs",
                    "explicit issue lineage",
                }
                required_refined = {
                    "changed fact IDs",
                    "affected paths",
                    "affected symbols",
                    "architecture item IDs",
                    "dependency instances",
                    "contract IDs",
                    "issue lineage",
                }
                if initial != required_initial or refined != required_refined:
                    findings.append(
                        KnowledgeFinding(
                            "error",
                            "PROJECT_KNOWLEDGE_ROUTING_SELECTORS",
                            "initial or refined selector contract drifted",
                            routing_relpath,
                        )
                    )
                delivery = " ".join(routing.get("delivery_rules", [])).casefold()
                for phrase in [
                    "accepted plus current",
                    "revalidation-required entries are warnings",
                    "contradicted entries block",
                    "historical and superseded entries remain lazy",
                ]:
                    if phrase not in delivery:
                        findings.append(
                            KnowledgeFinding(
                                "error",
                                "PROJECT_KNOWLEDGE_ROUTING_POLICY",
                                f"routing delivery policy is missing: {phrase}",
                                routing_relpath,
                            )
                        )

    policy_path = target / ".ai/project/knowledge/README.md"
    if not policy_path.is_file():
        findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_POLICY_MISSING", "project knowledge policy README is missing", ".ai/project/knowledge/README.md"))
    else:
        text = policy_path.read_text(encoding="utf-8")
        for label, field in {
            "Owner": "owner",
            "Review policy": "review_policy",
            "Retention policy": "retention_policy",
            "Redaction policy": "redaction_policy",
        }.items():
            expected = f"{label}: `{index[field]}`"
            if expected not in text:
                findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_POLICY_DRIFT", f"{label} differs from index.{field}", ".ai/project/knowledge/README.md"))

    promotion_by_id: dict[str, dict[str, Any]] = {}
    promotion_path_by_id: dict[str, str] = {}
    for descriptor in index.get("promotion_records", []):
        promotion_id = descriptor["promotion_id"]
        relpath = descriptor["path"]
        if promotion_id in promotion_by_id:
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_PROMOTION_DUPLICATE", f"duplicate promotion ID {promotion_id}", index_relpath))
            continue
        try:
            path = _safe_path(target, relpath)
        except ValueError as exc:
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_PROMOTION_PATH", str(exc), index_relpath))
            continue
        if not relpath.startswith(".ai/project/knowledge/promotions/") or not path.is_file():
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_PROMOTION_PATH", f"promotion record is missing or outside its directory: {relpath}", relpath))
            continue
        try:
            promotion = _load_object(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_PROMOTION_LOAD", str(exc), relpath))
            continue
        findings.extend(_schema_errors(promotion, promotion_schema, relpath, "PROJECT_KNOWLEDGE_PROMOTION_SCHEMA"))
        if promotion.get("promotion_id") != promotion_id:
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_PROMOTION_DRIFT", f"index promotion ID differs from {relpath}", index_relpath))
        disposition = promotion.get("human_review", {}).get("disposition")
        if disposition != descriptor.get("status"):
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_PROMOTION_DRIFT", f"promotion status differs for {promotion_id}", index_relpath))
        privacy = promotion.get("privacy")
        if isinstance(privacy, dict) and any(privacy.get(field) is not False for field in ["raw_chat_stored", "chain_of_thought_stored", "secrets_stored", "personal_data_stored"]):
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_PRIVACY", f"promotion {promotion_id} stores prohibited content", relpath))
        promotion_by_id[promotion_id] = promotion
        promotion_path_by_id[promotion_id] = relpath

    entries: dict[str, dict[str, Any]] = {}
    entry_paths: dict[str, str] = {}
    shard_ids: set[str] = set()
    for descriptor in index.get("shards", []):
        shard_id = descriptor["shard_id"]
        relpath = descriptor["path"]
        if shard_id in shard_ids:
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_SHARD_DUPLICATE", f"duplicate shard ID {shard_id}", index_relpath))
            continue
        shard_ids.add(shard_id)
        try:
            path = _safe_path(target, relpath)
        except ValueError as exc:
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_SHARD_PATH", str(exc), index_relpath))
            continue
        if not relpath.startswith(".ai/project/knowledge/routes/") or not path.is_file():
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_SHARD_PATH", f"route shard is missing or outside its directory: {relpath}", relpath))
            continue
        try:
            shard = _load_object(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_SHARD_LOAD", str(exc), relpath))
            continue
        findings.extend(_schema_errors(shard, shard_schema, relpath, "PROJECT_KNOWLEDGE_SHARD_SCHEMA"))
        if shard.get("shard_id") != shard_id:
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_SHARD_DRIFT", f"index shard ID differs from {relpath}", index_relpath))
        for field in [
            "task_profiles",
            "project_areas",
            "subsystems",
            "architecture_item_ids",
            "dependency_coordinates",
            "path_prefixes",
        ]:
            if sorted(shard.get(field, [])) != sorted(descriptor.get(field, [])):
                findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_SHARD_DRIFT", f"{shard_id}.{field} differs from index descriptor", index_relpath))
        for entry in shard.get("entries", []):
            knowledge_id = entry.get("knowledge_id")
            if not isinstance(knowledge_id, str):
                continue
            if knowledge_id in entries:
                findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_ID_DUPLICATE", f"duplicate knowledge ID {knowledge_id}", relpath))
                continue
            entries[knowledge_id] = entry
            entry_paths[knowledge_id] = relpath

            if shard.get("schema_version") == 2:
                guidance_kind = entry.get("guidance_kind")
                origin = entry.get("provenance", {}).get("origin")
                precedence = entry.get("precedence")
                if guidance_kind not in GUIDANCE_KINDS:
                    findings.append(KnowledgeFinding("error", "PROJECT_GUIDANCE_KIND", f"{knowledge_id} lacks a valid guidance kind", relpath))
                if origin not in {"engineering-discovery", "decision-owner-directive"}:
                    findings.append(KnowledgeFinding("error", "PROJECT_GUIDANCE_ORIGIN", f"{knowledge_id} lacks a valid guidance origin", relpath))
                if not isinstance(precedence, dict) or precedence.get("kind") not in PRECEDENCE_KINDS:
                    findings.append(KnowledgeFinding("error", "PROJECT_GUIDANCE_PRECEDENCE", f"{knowledge_id} lacks a valid precedence record", relpath))

    max_words = index.get("routing_policy", {}).get("max_summary_words", 0)
    for knowledge_id, entry in entries.items():
        relpath = entry_paths[knowledge_id]
        summary = entry.get("summary", "")
        if isinstance(summary, str) and isinstance(max_words, int) and len(summary.split()) > max_words:
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_SUMMARY_BUDGET", f"{knowledge_id} summary exceeds {max_words} words", relpath))
        applicability = entry.get("applicability", {})
        profiles = set(applicability.get("task_profiles", []))
        unknown_profiles = sorted(profiles - CANONICAL_PROFILES)
        if unknown_profiles:
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_PROFILE", f"{knowledge_id} has unknown task profiles {unknown_profiles}", relpath))
        strong_selectors = (
            list(applicability.get("project_areas", []))
            + list(applicability.get("subsystems", []))
            + list(applicability.get("architecture_item_ids", []))
            + list(applicability.get("dependencies", []))
            + list(entry.get("fact_ids", []))
            + list(applicability.get("path_globs", []))
            + list(applicability.get("symbols", []))
            + list(applicability.get("contract_ids", []))
            + list(applicability.get("issue_lineage", []))
        )
        if not strong_selectors:
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_SELECTOR_MISSING", f"{knowledge_id} has no selector stronger than task profile", relpath))

        authority = entry.get("authority", {})
        freshness = entry.get("freshness", {})
        authority_state = authority.get("state")
        freshness_state = freshness.get("state")
        owner_relpath = authority.get("canonical_owner")
        if authority_state == "accepted" and freshness_state == "current":
            if not _concrete(owner_relpath, allow_placeholders):
                findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_CURRENT_OWNER", f"{knowledge_id} lacks a resolved canonical owner", relpath))
            else:
                try:
                    owner_path = _safe_path(target, owner_relpath)
                except ValueError as exc:
                    findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_CURRENT_OWNER", str(exc), relpath))
                else:
                    expected_digest = authority.get("canonical_owner_sha256")
                    if not owner_path.is_file():
                        findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_CURRENT_OWNER", f"canonical owner is missing: {owner_relpath}", relpath))
                    elif not allow_placeholders and _sha256(owner_path) != expected_digest:
                        findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_CURRENT_OWNER_DRIFT", f"{knowledge_id} cannot remain current because its owner digest changed", relpath))
            owner_triggers = [
                trigger
                for trigger in freshness.get("triggers", [])
                if trigger.get("kind") == "canonical-owner-sha256"
            ]
            if len(owner_triggers) != 1 or any(
                trigger.get("subject") != owner_relpath
                or trigger.get("expected") != authority.get("canonical_owner_sha256")
                for trigger in owner_triggers
            ):
                findings.append(
                    KnowledgeFinding(
                        "error",
                        "PROJECT_KNOWLEDGE_FRESHNESS_TRIGGER",
                        f"{knowledge_id} needs one owner digest trigger matching its canonical owner and digest",
                        relpath,
                    )
                )

        for trigger in freshness.get("triggers", []):
            if trigger.get("kind") == "review-expiry" and freshness_state == "current":
                try:
                    expired = date.fromisoformat(trigger.get("expected", "")) < today
                except ValueError:
                    expired = False
                if expired:
                    findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_REVIEW_EXPIRED", f"{knowledge_id} review expiry passed", relpath))

        promotion_ref = entry.get("provenance", {}).get("promotion_record")
        matching_promotion = next((promotion_id for promotion_id, path in promotion_path_by_id.items() if path == promotion_ref), None)
        if matching_promotion is None:
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_PROMOTION_REFERENCE", f"{knowledge_id} references an unregistered promotion record", relpath))
        elif authority_state == "accepted":
            promotion = promotion_by_id[matching_promotion]
            review = promotion.get("human_review", {})
            if review.get("disposition") not in {"accepted", "narrowed"} or knowledge_id not in review.get("route_entry_ids", []):
                findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_PROMOTION_REFERENCE", f"{knowledge_id} is not accepted by promotion {matching_promotion}", relpath))
            canonical_update = review.get("canonical_update", {})
            candidate = promotion.get("candidate", {})
            if (
                canonical_update.get("owner_path") != owner_relpath
                or canonical_update.get("content_sha256")
                != authority.get("canonical_owner_sha256")
                or set(canonical_update.get("fact_ids", [])) != set(entry.get("fact_ids", []))
                or review.get("decision_owner") != authority.get("decision_owner")
                or review.get("decision_reference") != authority.get("decision_reference")
                or set(candidate.get("source_engineering_evidence_ids", []))
                != set(entry.get("provenance", {}).get("engineering_evidence_ids", []))
                or (
                    promotion.get("schema_version") == 2
                    and candidate.get("origin") != entry.get("provenance", {}).get("origin")
                )
                or (
                    promotion.get("schema_version") == 2
                    and candidate.get("guidance_kind") != entry.get("guidance_kind")
                )
            ):
                findings.append(
                    KnowledgeFinding(
                        "error",
                        "PROJECT_KNOWLEDGE_PROMOTION_OWNER_DRIFT",
                        f"{knowledge_id} authority or evidence differs from promotion {matching_promotion}",
                        relpath,
                    )
                )

        relations = entry.get("relations", {})
        if freshness_state == "contradicted" and not relations.get("conflicts_with"):
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_CONTRADICTION_LINK", f"{knowledge_id} is contradicted without a conflict link", relpath))
        if relations.get("conflicts_with") and freshness_state not in {
            "contradicted",
            "revalidation-required",
        }:
            findings.append(
                KnowledgeFinding(
                    "error",
                    "PROJECT_KNOWLEDGE_CONTRADICTION_STATE",
                    f"{knowledge_id} has unresolved conflicts but remains {freshness_state}",
                    relpath,
                )
            )
        if freshness_state == "superseded" and not relations.get("superseded_by"):
            findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_SUPERSESSION_LINK", f"{knowledge_id} is superseded without a replacement", relpath))
        if relations.get("superseded_by") and freshness_state != "superseded":
            findings.append(
                KnowledgeFinding(
                    "error",
                    "PROJECT_KNOWLEDGE_SUPERSESSION_STATE",
                    f"{knowledge_id} names a replacement but remains {freshness_state}",
                    relpath,
                )
            )

    for knowledge_id, entry in entries.items():
        relations = entry.get("relations", {})
        for other_id in relations.get("conflicts_with", []):
            other = entries.get(other_id)
            if other is None or knowledge_id not in other.get("relations", {}).get("conflicts_with", []):
                findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_CONFLICT_RECIPROCITY", f"{knowledge_id} conflict with {other_id} is not reciprocal", entry_paths[knowledge_id]))
        for other_id in relations.get("supersedes", []):
            other = entries.get(other_id)
            if other is None or knowledge_id not in other.get("relations", {}).get("superseded_by", []):
                findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_SUPERSESSION_RECIPROCITY", f"{knowledge_id} supersedes {other_id} without reciprocal link", entry_paths[knowledge_id]))
        for other_id in relations.get("superseded_by", []):
            other = entries.get(other_id)
            if other is None or knowledge_id not in other.get("relations", {}).get("supersedes", []):
                findings.append(KnowledgeFinding("error", "PROJECT_KNOWLEDGE_SUPERSESSION_RECIPROCITY", f"{knowledge_id} superseded by {other_id} without reciprocal link", entry_paths[knowledge_id]))

        precedence = entry.get("precedence")
        if isinstance(precedence, dict):
            kind = precedence.get("kind")
            base_id = precedence.get("base_guidance_id")
            if kind == "base-rule" and base_id is not None:
                findings.append(KnowledgeFinding("error", "PROJECT_GUIDANCE_BASE_REFERENCE", f"base guidance {knowledge_id} must not reference another base", entry_paths[knowledge_id]))
            if kind in {"narrower-rule", "authorized-exception"}:
                base = entries.get(base_id)
                if base is None or base_id == knowledge_id:
                    findings.append(KnowledgeFinding("error", "PROJECT_GUIDANCE_BASE_REFERENCE", f"{knowledge_id} references a missing or invalid base guidance ID", entry_paths[knowledge_id]))
                elif base.get("fact_type") != entry.get("fact_type"):
                    findings.append(KnowledgeFinding("error", "PROJECT_GUIDANCE_BASE_FACT_TYPE", f"{knowledge_id} and base {base_id} have different fact types", entry_paths[knowledge_id]))
                for field in ["scope", "revalidation_triggers", "validation"]:
                    if not precedence.get(field):
                        findings.append(KnowledgeFinding("error", "PROJECT_GUIDANCE_EXCEPTION_SCOPE", f"{knowledge_id} {field} must be explicit", entry_paths[knowledge_id]))
                for field in ["authority_reference", "rationale"]:
                    if not _concrete(precedence.get(field), allow_placeholders):
                        findings.append(KnowledgeFinding("error", "PROJECT_GUIDANCE_EXCEPTION_AUTHORITY", f"{knowledge_id} {field} must be explicit", entry_paths[knowledge_id]))

    if index.get("schema_version") in {2, 3}:
        coverage = index.get("coverage", {})
        for dimension in ["areas", "fact_types"]:
            seen_subjects: set[str] = set()
            for item in coverage.get(dimension, []):
                subject = item.get("subject")
                status = item.get("status")
                guidance_ids = item.get("guidance_ids", [])
                if subject in seen_subjects:
                    findings.append(KnowledgeFinding("error", "PROJECT_GUIDANCE_COVERAGE_DUPLICATE", f"duplicate {dimension} coverage subject {subject}", index_relpath))
                seen_subjects.add(subject)
                missing_ids = sorted(set(guidance_ids) - set(entries))
                if missing_ids:
                    findings.append(KnowledgeFinding("error", "PROJECT_GUIDANCE_COVERAGE_REFERENCE", f"{dimension} coverage {subject} references missing guidance IDs {missing_ids}", index_relpath))
                if status == "mapped" and not guidance_ids:
                    findings.append(KnowledgeFinding("error", "PROJECT_GUIDANCE_COVERAGE_STATE", f"mapped {dimension} coverage {subject} has no guidance IDs", index_relpath))
                if status in {"known-gap", "unknown"} and guidance_ids:
                    findings.append(KnowledgeFinding("error", "PROJECT_GUIDANCE_COVERAGE_STATE", f"{status} {dimension} coverage {subject} must not imply mapped guidance", index_relpath))
                if status == "known-gap" and not item.get("gap"):
                    findings.append(KnowledgeFinding("error", "PROJECT_GUIDANCE_COVERAGE_GAP", f"known-gap {dimension} coverage {subject} lacks a gap explanation", index_relpath))

    if index.get("schema_version") == 3:
        adoption = index.get("adoption", {})
        adoption_state = adoption.get("state")
        reuse_evidence = adoption.get("reuse_evidence", [])
        has_projection = bool(entries)
        has_registry_state = bool(
            index.get("promotion_records")
            or index.get("shards")
            or index.get("coverage", {}).get("areas")
            or index.get("coverage", {}).get("fact_types")
        )
        if adoption_state == "enabled-empty":
            if has_projection or has_registry_state or reuse_evidence:
                findings.append(
                    KnowledgeFinding(
                        "error",
                        "PROJECT_KNOWLEDGE_ADOPTION_STATE",
                        "enabled-empty requires no promotions, shards, coverage, route entries, or reuse evidence",
                        index_relpath,
                    )
                )
            elif not allow_placeholders:
                findings.append(
                    KnowledgeFinding(
                        "info",
                        "PROJECT_KNOWLEDGE_ENABLED_EMPTY",
                        "project knowledge is enabled but has no reviewed route entries; guidance reuse is not demonstrated",
                        index_relpath,
                    )
                )
        elif adoption_state == "populated":
            if not has_projection or reuse_evidence:
                findings.append(
                    KnowledgeFinding(
                        "error",
                        "PROJECT_KNOWLEDGE_ADOPTION_STATE",
                        "populated requires at least one route entry and no claimed reuse evidence",
                        index_relpath,
                    )
                )
        elif adoption_state == "reuse-observed":
            if not has_projection or not reuse_evidence or not all(
                _concrete(value, allow_placeholders) for value in reuse_evidence
            ):
                findings.append(
                    KnowledgeFinding(
                        "error",
                        "PROJECT_KNOWLEDGE_ADOPTION_STATE",
                        "reuse-observed requires route entries and explicit reuse evidence",
                        index_relpath,
                    )
                )

    return findings


def _matches_any(values: Iterable[str], selected: Iterable[str]) -> bool:
    return bool(set(values) & set(selected))


def _entry_score(entry: dict[str, Any], route: dict[str, Any], stage: str) -> int:
    applicability = entry["applicability"]
    profile = route.get("task_profile")
    if profile not in applicability["task_profiles"]:
        return 0
    score = 1
    strong = 0
    if _matches_any(applicability["project_areas"], route.get("project_areas", [])):
        score += 4
        strong += 1
    if _matches_any(applicability["subsystems"], route.get("subsystems", [])):
        score += 4
        strong += 1
    if _matches_any(
        applicability["architecture_item_ids"], route.get("architecture_item_ids", [])
    ):
        score += 4
        strong += 1
    coordinates = [item["coordinate"] for item in applicability["dependencies"]]
    if _matches_any(coordinates, route.get("dependency_coordinates", [])):
        score += 4
        strong += 1
    if _matches_any(applicability["contract_ids"], route.get("contract_ids", [])):
        score += 4
        strong += 1
    if _matches_any(applicability["issue_lineage"], route.get("issue_lineage", [])):
        score += 3
        strong += 1
    if stage == "refined":
        if _matches_any(entry["fact_ids"], route.get("fact_ids", [])):
            score += 6
            strong += 1
        if _matches_any(applicability["symbols"], route.get("symbols", [])):
            score += 5
            strong += 1
        paths = route.get("paths", [])
        if any(fnmatch.fnmatchcase(path, pattern) for path in paths for pattern in applicability["path_globs"]):
            score += 5
            strong += 1
    return score if strong else 0


def select_project_knowledge(
    entries: Iterable[dict[str, Any]],
    route: dict[str, Any],
    *,
    stage: str,
    limit: int,
) -> dict[str, Any]:
    if stage not in {"initial", "refined"}:
        raise ValueError("stage must be initial or refined")
    scored = [(_entry_score(entry, route, stage), entry) for entry in entries]
    scored = [(score, entry) for score, entry in scored if score > 0]
    scored.sort(key=lambda item: (-item[0], item[1]["knowledge_id"]))
    result: dict[str, Any] = {
        "constraints": [],
        "warnings": [],
        "blockers": [],
        "omitted": [],
    }
    delivered = 0
    for score, entry in scored:
        projected = {
            "knowledge_id": entry["knowledge_id"],
            "guidance_kind": entry.get("guidance_kind", "reviewed-knowledge"),
            "summary": entry["summary"],
            "canonical_owner": entry["authority"]["canonical_owner"],
            "authority_state": entry["authority"]["state"],
            "freshness_state": entry["freshness"]["state"],
            "precedence_kind": entry.get("precedence", {}).get("kind", "base-rule"),
            "score": score,
        }
        authority = entry["authority"]["state"]
        freshness = entry["freshness"]["state"]
        if freshness == "contradicted":
            result["blockers"].append(projected)
            delivered += 1
        elif authority == "accepted" and freshness == "current" and delivered < limit:
            result["constraints"].append(projected)
            delivered += 1
        elif freshness == "revalidation-required" and delivered < limit:
            result["warnings"].append(projected)
            delivered += 1
        else:
            result["omitted"].append(projected)
    result["packet_limit"] = limit
    result["packet_limit_exceeded_for_blockers"] = delivered > limit
    return result
