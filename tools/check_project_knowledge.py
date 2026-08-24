#!/usr/bin/env python3
"""Validate project-knowledge contracts, routing, and reuse scenarios."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import jsonschema

from project_knowledge import select_project_knowledge, validate_project_knowledge


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
SCHEMAS = ROOT / "schemas"


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"{path} must contain an object")
    return data


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def fixture(target: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    owner = target / "docs/contracts/result-mapping.md"
    owner.parent.mkdir(parents=True, exist_ok=True)
    owner.write_text("# Result Mapping\n\nFolding and result-key transformation are independent.\n", encoding="utf-8")
    digest = hashlib.sha256(owner.read_bytes()).hexdigest()
    promotion = {
        "schema_version": 1,
        "record_kind": "alatyr-project-knowledge-promotion",
        "promotion_id": "PROMO-RESULT-TRANSFORM-001",
        "created_at": "2026-08-24T12:00:00Z",
        "candidate": {
            "candidate_id": "CANDIDATE-RESULT-TRANSFORM-001",
            "statement": "Folding and result-key transformation are independent.",
            "knowledge_kind": "compatibility-boundary",
            "reuse_rationale": "The relationship required cross-package investigation.",
            "source_engineering_evidence_ids": ["ENG-RESULT-TRANSFORM-001"],
            "repository_evidence": ["docs/contracts/result-mapping.md"],
            "proposed_fact_type": "integration contract",
            "proposed_fact_ids": ["FACT-RESULT-KEY-TRANSFORM"],
            "proposed_canonical_owner": "docs/contracts/result-mapping.md",
            "proposed_decision_owner": "maintainers",
            "route_hints": {
                "task_profiles": ["code-local"],
                "project_areas": ["hydration"],
                "subsystems": ["result-hydration"],
                "architecture_item_ids": ["ARCH-HYDRATION-BOUNDARY"],
                "dependency_coordinates": ["dbal/package"],
                "path_globs": ["src/Hydration*.php"],
                "symbols": ["hydrateRow"],
                "contract_ids": ["result-key-contract"],
                "issue_lineage": ["related-hydration-family"],
                "conditions": ["DBAL-facing hydration work"],
            },
        },
        "human_review": {
            "disposition": "accepted",
            "decision_owner": "maintainers",
            "decision_reference": "decision:result-mapping",
            "decided_at": "2026-08-24T12:30:00Z",
            "decision_rationale": "This boundary is stable and expensive to rediscover.",
            "accepted_statement": "Folding and result-key transformation are independent.",
            "canonical_update": {
                "state": "complete",
                "owner_path": "docs/contracts/result-mapping.md",
                "content_sha256": digest,
                "fact_ids": ["FACT-RESULT-KEY-TRANSFORM"],
            },
            "route_entry_ids": ["KNOW-RESULT-TRANSFORM-001"],
        },
        "privacy": {
            "raw_chat_stored": False,
            "chain_of_thought_stored": False,
            "secrets_stored": False,
            "personal_data_stored": False,
            "redactions": [],
        },
    }
    entry = {
        "knowledge_id": "KNOW-RESULT-TRANSFORM-001",
        "summary": "Platform folding and result-key transformation are independent contracts.",
        "fact_type": "integration contract",
        "fact_ids": ["FACT-RESULT-KEY-TRANSFORM"],
        "authority": {
            "state": "accepted",
            "canonical_owner": "docs/contracts/result-mapping.md",
            "canonical_owner_sha256": digest,
            "decision_owner": "maintainers",
            "decision_reference": "decision:result-mapping",
        },
        "freshness": {
            "state": "current",
            "verified_revision": "0123456789012345678901234567890123456789",
            "verified_at": "2026-08-24T12:30:00Z",
            "triggers": [
                {
                    "kind": "canonical-owner-sha256",
                    "subject": "docs/contracts/result-mapping.md",
                    "expected": digest,
                    "evidence": "promotion:PROMO-RESULT-TRANSFORM-001",
                    "action": "mark revalidation-required and reread the owner",
                },
                {
                    "kind": "dependency-version",
                    "subject": "dbal/package",
                    "expected": ">=3 <5",
                    "evidence": "composer.lock",
                    "action": "revalidate on resolved-version change",
                },
            ],
        },
        "applicability": {
            "task_profiles": ["code-local"],
            "project_areas": ["hydration"],
            "subsystems": ["result-hydration"],
            "architecture_item_ids": ["ARCH-HYDRATION-BOUNDARY"],
            "dependencies": [
                {"coordinate": "dbal/package", "version_range": ">=3 <5", "resolved_version": "4.0.0"}
            ],
            "path_globs": ["src/Hydration*.php"],
            "symbols": ["hydrateRow"],
            "contract_ids": ["result-key-contract"],
            "issue_lineage": ["related-hydration-family"],
            "conditions": ["DBAL-facing hydration work"],
        },
        "provenance": {
            "engineering_evidence_ids": ["ENG-RESULT-TRANSFORM-001"],
            "promotion_record": ".ai/project/knowledge/promotions/PROMO-RESULT-TRANSFORM-001.json",
            "source_revision": "0123456789012345678901234567890123456789",
        },
        "relations": {"conflicts_with": [], "supersedes": [], "superseded_by": []},
        "validation": {
            "checks": ["canonical owner digest and target tests"],
            "last_result": "passed",
            "residual_uncertainty": [],
        },
    }
    shard = {
        "schema_version": 1,
        "shard_kind": "target-project-knowledge-routing-shard",
        "shard_id": "hydration",
        "task_profiles": ["code-local"],
        "project_areas": ["hydration"],
        "subsystems": ["result-hydration"],
        "architecture_item_ids": ["ARCH-HYDRATION-BOUNDARY"],
        "dependency_coordinates": ["dbal/package"],
        "path_prefixes": ["src/Hydration"],
        "entries": [entry],
    }
    index = {
        "schema_version": 1,
        "index_kind": "target-project-knowledge-routing-index",
        "project": "fixture",
        "owner": "maintainers",
        "review_policy": "maintainer review required",
        "retention_policy": "retain decisions and supersession lineage",
        "redaction_policy": "exclude raw conversations and secrets",
        "routing_policy": {
            "max_initial_items": 6,
            "max_refined_items": 8,
            "max_summary_words": 60,
            "current_constraint_states": ["accepted", "current"],
            "warning_freshness_states": ["revalidation-required"],
            "blocking_freshness_states": ["contradicted"],
            "selection_order": ["task-profile", "project-area", "subsystem-or-architecture-item", "dependency-or-contract", "changed-fact", "path-or-symbol", "issue-lineage"],
            "profile_only_match_allowed": False,
        },
        "promotion_records": [
            {"promotion_id": promotion["promotion_id"], "status": "accepted", "path": ".ai/project/knowledge/promotions/PROMO-RESULT-TRANSFORM-001.json"}
        ],
        "shards": [
            {"shard_id": "hydration", "path": ".ai/project/knowledge/routes/hydration.json", "task_profiles": ["code-local"], "project_areas": ["hydration"], "subsystems": ["result-hydration"], "architecture_item_ids": ["ARCH-HYDRATION-BOUNDARY"], "dependency_coordinates": ["dbal/package"], "path_prefixes": ["src/Hydration"]}
        ],
    }
    policy = target / ".ai/project/knowledge/README.md"
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(
        "# Project Knowledge Delivery\n\nOwner: `maintainers`\n\nReview policy: `maintainer review required`\n\nRetention policy: `retain decisions and supersession lineage`\n\nRedaction policy: `exclude raw conversations and secrets`\n",
        encoding="utf-8",
    )
    write_json(target / ".ai/project/knowledge/index.json", index)
    write_json(target / ".ai/project/knowledge/routes/hydration.json", shard)
    write_json(target / ".ai/project/knowledge/promotions/PROMO-RESULT-TRANSFORM-001.json", promotion)
    write_json(
        target / ".ai/assistant/context/project-knowledge-routing.json",
        load(TARGET / ".ai/assistant/context/project-knowledge-routing.json"),
    )
    return index, shard, promotion


def main() -> int:
    failures: list[str] = []
    for schema_name in [
        "alatyr-project-knowledge-index.schema.json",
        "alatyr-project-knowledge-shard.schema.json",
        "alatyr-project-knowledge-promotion.schema.json",
    ]:
        try:
            jsonschema.Draft7Validator.check_schema(load(SCHEMAS / schema_name))
        except (OSError, json.JSONDecodeError, jsonschema.SchemaError, AssertionError) as exc:
            failures.append(f"invalid {schema_name}: {exc}")

    source_findings = validate_project_knowledge(TARGET, SCHEMAS, allow_placeholders=True)
    if source_findings:
        failures.extend(f"source template {item.code}: {item.message}" for item in source_findings)

    scenarios = load(ROOT / "conformance/project-knowledge-scenarios.json")
    scenario_ids = {item.get("id") for item in scenarios.get("scenarios", []) if isinstance(item, dict)}
    required_scenarios = {
        "capture-promote-deliver",
        "two-stage-refinement",
        "canonical-owner-drift",
        "knowledge-contradiction",
        "knowledge-supersession",
        "shared-will-multi-assistant",
        "paired-rediscovery-measurement",
    }
    if scenario_ids != required_scenarios:
        failures.append("project knowledge scenario coverage drifted")

    shared = load(ROOT / "conformance/project-knowledge-shared-will.json")
    surfaces = load(ROOT / "conformance/runs/assistant-surfaces.json")
    expected_surfaces = {item["id"] for item in surfaces.get("surfaces", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
    if set(shared.get("surface_expectations", {})) != expected_surfaces:
        failures.append("shared-will surface expectations do not cover every supported assistant")
    if shared.get("strategy_equivalence_required") is not False or shared.get("human_walkthrough_is_assistant_conformance") is not False:
        failures.append("shared-will contract confuses constraints with strategy or human evidence")
    human = shared.get("human_walkthrough_expectation", {})
    if (
        human.get("evidence_kind") != "separate-usability-evidence"
        or set(human.get("must_preserve", [])) != set(shared.get("common_expectations", []))
        or human.get("must_not_claim") != "assistant runtime conformance"
    ):
        failures.append("shared-will human walkthrough contract drifted")

    reuse = load(ROOT / "conformance/project-knowledge-reuse.json")
    report_template = load(ROOT / "conformance/benchmarks/project-knowledge-reuse-report-template.json")
    if report_template.get("raw_reasoning_collected") is not False or report_template.get("single_run_counterfactual_claimed") is not False:
        failures.append("reuse benchmark template violates evidence boundaries")
    required_metrics = {
        "orientation_files_opened",
        "dependency_source_files_reopened_for_known_facts",
        "repeated_known_fact_searches",
        "repeated_discovery_of_recorded_invariants",
        "human_repeated_explanations",
        "routed_context_items_used",
        "known_context_items_independently_reconstructed",
        "seconds_to_first_supported_hypothesis",
        "input_tokens",
        "output_tokens",
        "duration_seconds",
        "rework_count",
        "validation_error_count",
        "unresolved_consistency_gaps",
    }
    if set(report_template.get("observable_metrics", {})) != required_metrics:
        failures.append("reuse benchmark observable metric coverage drifted")

    with tempfile.TemporaryDirectory(prefix="alatyr-project-knowledge-") as directory:
        target = Path(directory)
        index, shard, promotion = fixture(target)
        valid = validate_project_knowledge(target, SCHEMAS)
        if valid:
            failures.extend(f"valid fixture {item.code}: {item.message}" for item in valid)

        initial = select_project_knowledge(
            shard["entries"], reuse["second_task"]["initial_route"], stage="initial", limit=index["routing_policy"]["max_initial_items"]
        )
        refined = select_project_knowledge(
            shard["entries"], reuse["second_task"]["refined_route"], stage="refined", limit=index["routing_policy"]["max_refined_items"]
        )
        if [item["knowledge_id"] for item in initial["constraints"]] != reuse["expected"]["initial_selected_ids"]:
            failures.append("initial two-task route did not supply the promoted knowledge")
        if [item["knowledge_id"] for item in refined["constraints"]] != reuse["expected"]["refined_selected_ids"]:
            failures.append("refined two-task route did not supply the promoted knowledge")

        profile_only = copy.deepcopy(reuse["second_task"]["initial_route"])
        for field in ["project_areas", "subsystems", "architecture_item_ids", "dependency_coordinates", "contract_ids", "issue_lineage"]:
            profile_only[field] = []
        if select_project_knowledge(shard["entries"], profile_only, stage="initial", limit=6)["constraints"]:
            failures.append("profile-only routing selected knowledge")

        routing_path = target / ".ai/assistant/context/project-knowledge-routing.json"
        routing = load(routing_path)
        routing["delivery_rules"] = [
            "accepted plus current entries may be candidate constraints only after canonical-owner revalidation",
            "revalidation-required and historical entries are warnings rather than current constraints",
            "contradicted entries block a definitive conclusion and route to the decision owner",
            "observed proposed unresolved and superseded entries remain lazy unless explicitly requested",
        ]
        write_json(routing_path, routing)
        routing_codes = {item.code for item in validate_project_knowledge(target, SCHEMAS)}
        if "PROJECT_KNOWLEDGE_ROUTING_POLICY" not in routing_codes:
            failures.append("stale historical-warning routing policy was not rejected")

        fixture(target)
        owner = target / "docs/contracts/result-mapping.md"
        owner.write_text(owner.read_text(encoding="utf-8") + "Changed.\n", encoding="utf-8")
        drift_codes = {item.code for item in validate_project_knowledge(target, SCHEMAS)}
        if "PROJECT_KNOWLEDGE_CURRENT_OWNER_DRIFT" not in drift_codes:
            failures.append("canonical owner drift did not invalidate current knowledge")

        fixture(target)
        promotion_path = target / ".ai/project/knowledge/promotions/PROMO-RESULT-TRANSFORM-001.json"
        mismatched_promotion = load(promotion_path)
        mismatched_promotion["human_review"]["canonical_update"]["fact_ids"] = [
            "FACT-OTHER"
        ]
        write_json(promotion_path, mismatched_promotion)
        promotion_codes = {
            item.code for item in validate_project_knowledge(target, SCHEMAS)
        }
        if "PROJECT_KNOWLEDGE_PROMOTION_OWNER_DRIFT" not in promotion_codes:
            failures.append("promotion-to-route canonical binding drift was not rejected")

        fixture(target)
        conflicted_shard = copy.deepcopy(shard)
        second = copy.deepcopy(conflicted_shard["entries"][0])
        second["knowledge_id"] = "KNOW-RESULT-TRANSFORM-002"
        second["freshness"]["state"] = "contradicted"
        second["relations"]["conflicts_with"] = ["KNOW-RESULT-TRANSFORM-001"]
        conflicted_shard["entries"].append(second)
        write_json(target / ".ai/project/knowledge/routes/hydration.json", conflicted_shard)
        conflict_codes = {item.code for item in validate_project_knowledge(target, SCHEMAS)}
        if "PROJECT_KNOWLEDGE_CONFLICT_RECIPROCITY" not in conflict_codes:
            failures.append("asymmetric knowledge contradiction was not rejected")

        invalid_promotion = copy.deepcopy(promotion)
        invalid_promotion["human_review"]["canonical_update"]["state"] = "pending"
        promotion_schema = load(SCHEMAS / "alatyr-project-knowledge-promotion.schema.json")
        if not list(jsonschema.Draft7Validator(promotion_schema).iter_errors(invalid_promotion)):
            failures.append("accepted promotion without canonical update passed schema validation")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: checked project knowledge promotion, routing, freshness, reuse, and shared-will contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
