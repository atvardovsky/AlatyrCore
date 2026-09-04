"""Target-validator scenarios for support information."""

from __future__ import annotations

from .common import (
    validator,
    write_json,
)


def run(target: Path, failures: list[str]) -> None:
    framework_tool_reference = target / ".ai" / "framework" / "migration-diff.md"
    framework_tool_reference.parent.mkdir(parents=True, exist_ok=True)
    framework_tool_reference.write_text(
        "The source may provide `tools/validate_target_adapter.py`.\n",
        encoding="utf-8",
    )
    checker_claims = validator(target)
    checker_claims.check_checker_claims([], [])
    if "STALE_CHECKER_REFERENCE" in {
        finding.code for finding in checker_claims.findings
    }:
        failures.append(
            "portable source-tool guidance must not become a target-local checker claim"
        )

    map_path = target / ".ai" / "project" / "consistency-map.json"
    write_json(
        map_path,
        {
            "schema_version": 1,
            "map_kind": "target-consistency-map",
            "levels": ["fact"],
            "relationship_types": ["implements"],
            "nodes": [],
        },
    )
    consistency = validator(target)
    consistency.check_consistency_map()
    consistency_codes = {finding.code for finding in consistency.findings}
    for required in [
        "CONSISTENCY_MAP_LEVELS",
        "CONSISTENCY_MAP_RELATIONSHIPS",
        "CONSISTENCY_MAP_NODES",
    ]:
        if required not in consistency_codes:
            failures.append(f"broken consistency map missing finding {required}")

    registry_path = target / ".ai" / "project" / "source-of-truth-registry.md"
    registry_path.write_text(
        "# Registry\n\n"
        "### Fact Type: `business rule`\n\n"
        "Fact type: `business rule`\n"
        "Consistency map node: `fact-business-rule`\n\n"
        "### Fact Type: `data model`\n\n"
        "Fact type: `data model`\n"
        "Consistency map node: `fact-data-model`\n",
        encoding="utf-8",
    )
    write_json(
        map_path,
        {
            "schema_version": 2,
            "map_kind": "target-consistency-map",
            "human_registry": ".ai/project/source-of-truth-registry.md",
            "registry_sync_policy": {
                "coverage": "every-live-registry-fact-type",
                "node_reference": "registry-consistency-map-node-id",
                "fact_type_match": "exact",
                "extra_nodes": "allowed-for-derived-contract-area-system-and-adapter-surfaces",
            },
            "levels": ["fact", "contract", "area", "system", "adapter"],
            "relationship_types": [
                "implements",
                "verifies",
                "documents",
                "visualizes",
                "generates",
                "constrains",
                "depends-on",
                "routes",
            ],
            "impact_policy": {
                "transitive_expand_when": ["dependent contract changes"],
                "required_evidence": ["selected relationships"],
            },
            "nodes": [
                {
                    "id": "fact-business-rule",
                    "fact_type": "business Rule",
                    "level": "fact",
                    "project_area": "core",
                    "canonical_owner": "docs/business.md",
                    "relationships": [
                        {
                            "id": "documents-business-rule",
                            "type": "documents",
                            "target": "docs/reference.md",
                            "target_level": "contract",
                            "direction": "outbound",
                            "required_when": ["business rule changes"],
                            "validation": ["manual review"],
                        }
                    ],
                }
            ],
        },
    )
    registry_map_sync = validator(target)
    registry_map_sync.check_consistency_map()
    registry_map_codes = {
        finding.code for finding in registry_map_sync.findings
    }
    for required in [
        "CONSISTENCY_REGISTRY_NODE_FACT_TYPE_DRIFT",
        "CONSISTENCY_REGISTRY_NODE_MISSING",
    ]:
        if required not in registry_map_codes:
            failures.append(
                f"registry/map semantic drift missing finding {required}"
            )

    capabilities_path = target / ".ai" / "framework" / "capabilities.json"
    write_json(
        capabilities_path,
        {
            "schema_version": 1,
            "capability_kind": "alatyr-optional-module-catalog",
            "modules": {
                "consistency-map": {
                    "target_files": [
                        ".ai/assistant/flows/consistency-review.flow.md"
                    ]
                }
            },
        },
    )
    stale_flow = (
        target
        / ".ai"
        / "assistant"
        / "flows"
        / "consistency-review.flow.md"
    )
    stale_flow.parent.mkdir(parents=True, exist_ok=True)
    stale_flow.write_text(
        "The consistency-map module is deferred.\n", encoding="utf-8"
    )
    stale_module = validator(target)
    stale_module.check_enabled_module_status_claims({"consistency-map"})
    if "ENABLED_MODULE_STALE_STATUS" not in {
        finding.code for finding in stale_module.findings
    }:
        failures.append("enabled module stale status claim was not rejected")
    stale_flow.write_text(
        "If the consistency-map module is deferred, stop and report it.\n",
        encoding="utf-8",
    )
    conditional_module = validator(target)
    conditional_module.check_enabled_module_status_claims({"consistency-map"})
    if "ENABLED_MODULE_STALE_STATUS" in {
        finding.code for finding in conditional_module.findings
    }:
        failures.append("conditional module-state guidance was treated as stale")

    ai_router_path = target / ".ai" / "assistant" / "ai-infrastructure-router.json"
    write_json(
        ai_router_path,
        {
            "schema_version": 1,
            "router_kind": "target-ai-infrastructure-router",
            "item_types": ["skill"],
            "routing_order": ["inventory"],
            "routes": {},
            "items": [],
        },
    )
    ai_router = validator(target)
    ai_router.check_ai_infrastructure_router()
    ai_codes = {finding.code for finding in ai_router.findings}
    for required in ["AI_ROUTER_ROUTES", "AI_ROUTER_ITEM_TYPES", "AI_ROUTER_ITEMS"]:
        if required not in ai_codes:
            failures.append(f"broken AI router missing finding {required}")

    development_evidence_path = (
        target / ".ai" / "project" / "development-evidence.json"
    )
    write_json(
        development_evidence_path,
        {
            "schema_version": 1,
            "register_kind": "target-development-evidence",
            "project": "fixture",
            "owner": "fixture-owner",
            "retention_policy": "keep bounded references",
            "last_reviewed": "2026-07-17",
            "content_policy": (
                "no raw chat, secrets, credentials, or personal data"
            ),
            "patterns": [
                {
                    "id": "pattern-1",
                    "category": "review-rework",
                    "project_area": "api",
                    "source_owner": "api-contract",
                    "normalized_problem": "companion contract updates are missed",
                    "occurrence_count": 0,
                    "first_observed": "operation-1",
                    "last_observed": "operation-1",
                    "evidence_quality": "invented",
                    "evidence_refs": [],
                    "outcome_signals": ["rework"],
                    "existing_ai_item_ids": [],
                    "status": "unknown",
                }
            ],
        },
    )
    development_evidence = validator(target)
    development_evidence.check_development_evidence(None)
    development_codes = {
        finding.code for finding in development_evidence.findings
    }
    for required in [
        "DEVELOPMENT_EVIDENCE_OCCURRENCE_COUNT",
        "DEVELOPMENT_EVIDENCE_REFERENCE_MISSING",
        "DEVELOPMENT_EVIDENCE_QUALITY",
        "DEVELOPMENT_EVIDENCE_STATUS",
    ]:
        if required not in development_codes:
            failures.append(
                f"broken development evidence missing finding {required}"
            )
