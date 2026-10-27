"""Explicit, bounded knowledge lookup for the existing context planner."""

from __future__ import annotations

import hashlib
import json
import copy
from datetime import date
from pathlib import Path
from typing import Callable

import jsonschema

from project_knowledge import select_project_knowledge


INDEX = ".ai/project/knowledge/index.json"
SELECTORS = {"project_areas", "subsystems", "architecture_item_ids", "dependency_coordinates",
             "contract_ids", "issue_lineage", "fact_ids", "paths", "symbols"}
MAX_SHARDS = 8
MAX_ENTRIES = 256


def select_context_knowledge(profile: str, query: dict, load: Callable[[str], dict], read: Callable[[str], bytes]) -> dict:
    """Search named shards only; absence is never global knowledge coverage."""
    if not isinstance(query, dict) or set(query) != {"schema_version", "stage", "shard_ids", "selectors", "limit"}:
        raise ValueError("knowledge request requires schema_version, stage, shard_ids, selectors and limit")
    if type(query["schema_version"]) is not int or query["schema_version"] != 1 or not isinstance(query["stage"], str) or query["stage"] not in {"initial", "refined"}:
        raise ValueError("knowledge request requires schema 1 and initial/refined stage")
    ids, selectors, limit = query["shard_ids"], query["selectors"], query["limit"]
    if not isinstance(ids, list) or not 1 <= len(ids) <= MAX_SHARDS or not all(isinstance(value, str) and value.strip() for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("knowledge request requires 1..8 unique named shard IDs")
    if not isinstance(selectors, dict) or not selectors or not set(selectors) <= SELECTORS:
        raise ValueError("knowledge request has missing or unknown selectors")
    for key, values in selectors.items():
        if not isinstance(values, list) or not 1 <= len(values) <= 32 or not all(isinstance(value, str) and value.strip() for value in values):
            raise ValueError(f"knowledge selector {key} requires 1..32 non-empty strings")
    if query["stage"] == "initial" and set(selectors) & {"fact_ids", "paths", "symbols"}:
        raise ValueError("fact, path and symbol selectors require the refined stage")
    if type(limit) is not int or not 1 <= limit <= 30:
        raise ValueError("knowledge request limit must be an integer in 1..30")
    schemas = Path(__file__).resolve().parents[1] / "schemas"
    def validate(value: dict, name: str):
        schema = json.loads((schemas / f"alatyr-project-knowledge-{name}.schema.json").read_text(encoding="utf-8"))
        errors = list(jsonschema.Draft7Validator(schema).iter_errors(value))
        if errors:
            raise ValueError(f"knowledge {name} schema: {errors[0].json_path}: {errors[0].message}")
    index = load(INDEX)
    validate(index, "index")
    descriptors = {row["shard_id"]: row for row in index["shards"]}
    if len(descriptors) != len(index["shards"]) or not set(ids) <= descriptors.keys():
        raise ValueError("knowledge shard IDs must be unique and registered")
    cap = index["routing_policy"][f"max_{query['stage']}_items"]
    if limit > cap:
        raise ValueError(f"knowledge request limit {limit} exceeds configured {cap}")
    entries, seen = [], set()
    for identity in ids:
        descriptor = descriptors[identity]
        if profile not in descriptor["task_profiles"]:
            raise ValueError(f"knowledge shard {identity} does not support profile {profile}")
        path = descriptor["path"]
        if not path.startswith(".ai/project/knowledge/routes/"):
            raise ValueError("knowledge shards must remain in their registered routes directory")
        shard = load(path)
        validate(shard, "shard")
        if any(shard[key] != descriptor[key] for key in ("shard_id", "task_profiles", "project_areas", "subsystems", "architecture_item_ids", "dependency_coordinates", "path_prefixes")):
            raise ValueError(f"knowledge shard {identity} metadata differs from its index")
        entries.extend(shard["entries"])
        if len(entries) > MAX_ENTRIES:
            raise ValueError("knowledge query exceeds 256 entries; narrow or decompose the query")
        for entry in shard["entries"]:
            key = entry["knowledge_id"]
            if key in seen:
                raise ValueError(f"duplicate selected knowledge ID: {key}")
            seen.add(key)
            if len(entry["summary"].split()) > index["routing_policy"]["max_summary_words"]:
                raise ValueError(f"knowledge {key} summary exceeds configured word budget")
    declared_freshness = {entry["knowledge_id"]: entry["freshness"]["state"] for entry in entries}
    entries = copy.deepcopy(entries)
    for entry in entries:
        if entry["freshness"]["state"] == "current" and any(trigger["kind"] not in {"canonical-owner-sha256", "review-expiry"} for trigger in entry["freshness"]["triggers"]):
            entry["freshness"]["state"] = "revalidation-required"
    route = dict(selectors, task_profile=profile)
    selected = select_project_knowledge(entries, route, stage=query["stage"], limit=limit)
    # Never rank away applicable accepted duties, even when the legacy selector
    # reports them as omitted. The caller must narrow or explicitly decompose.
    overflow = [row["knowledge_id"] for row in selected["omitted"] if (row["authority_state"] == "accepted" and row["freshness_state"] == "current") or row["freshness_state"] == "revalidation-required"]
    if overflow:
        raise ValueError(f"knowledge packet would omit relevant constraints/warnings: {overflow}")
    if selected["blockers"]:
        raise ValueError("contradicted knowledge blocks planning: " + ", ".join(row["knowledge_id"] for row in selected["blockers"]))
    by_id = {row["knowledge_id"]: row for row in entries}
    owners = []
    for row in selected["constraints"] + selected["warnings"]:
        entry = by_id[row["knowledge_id"]]
        authority = entry["authority"]
        if entry["relations"]["conflicts_with"] or entry["relations"]["superseded_by"]:
            raise ValueError(f"knowledge {row['knowledge_id']} has unresolved conflict or supersession links")
        if any(authority[key].strip().casefold() in {"unknown", "unresolved", "pending", "not-applicable", ""} or "{" in authority[key] for key in ("canonical_owner", "decision_owner", "decision_reference")):
            raise ValueError(f"knowledge {row['knowledge_id']} has unresolved accepted authority")
        raw = read(authority["canonical_owner"])
        owner_triggers = [trigger for trigger in entry["freshness"]["triggers"] if trigger["kind"] == "canonical-owner-sha256"]
        if declared_freshness[row["knowledge_id"]] == "current" and (len(owner_triggers) != 1 or
                owner_triggers[0]["subject"] != authority["canonical_owner"] or
                owner_triggers[0]["expected"].lower() != authority["canonical_owner_sha256"].lower()):
            raise ValueError(f"knowledge {row['knowledge_id']} owner digest trigger disagrees with its authority binding")
        if declared_freshness[row["knowledge_id"]] == "current" and hashlib.sha256(raw).hexdigest().lower() != authority["canonical_owner_sha256"].lower():
            raise ValueError(f"knowledge {row['knowledge_id']} owner changed; revalidate before using it as a constraint")
        for trigger in entry["freshness"]["triggers"]:
            if trigger["kind"] == "review-expiry":
                try:
                    expired = date.fromisoformat(trigger["expected"]) < date.today()
                except ValueError as exc:
                    raise ValueError(f"knowledge {row['knowledge_id']} has invalid review expiry") from exc
                if expired:
                    raise ValueError(f"knowledge {row['knowledge_id']} review expired; revalidation required")
        owners.append(authority["canonical_owner"])
        row["unverified_trigger_kinds"] = sorted({trigger["kind"] for trigger in entry["freshness"]["triggers"] if trigger["kind"] not in {"canonical-owner-sha256", "review-expiry"}})
        row["declared_freshness_state"] = declared_freshness[row["knowledge_id"]]
        row["freshness_verification"] = "owner-digest-and-review-expiry-only"
    selected["omitted_count"] = len(selected["omitted"])
    selected["omitted"] = [{key: row[key] for key in ("knowledge_id", "authority_state", "freshness_state")} for row in selected["omitted"]]
    return {"stage": query["stage"], "selection": selected, "owner_paths": sorted(set(owners)),
            "searched_shard_ids": ids, "unsearched_shard_ids": sorted(set(descriptors) - set(ids)),
            "global_coverage": False, "actual_use": "not-observed", "authority_promoted": False,
            "limitation": "Explicit selected-shard search only. No match does not mean no project knowledge. Selection is not evidence of comprehension, reuse or effectiveness."}
