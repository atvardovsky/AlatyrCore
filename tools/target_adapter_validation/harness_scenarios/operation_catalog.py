"""Target-validator scenarios for operation catalog."""

from __future__ import annotations

from .common import (
    validator,
    write_json,
)


def run(target: Path, failures: list[str]) -> None:
    router_path = target / ".ai" / "assistant" / "context-router.json"
    catalog_path = target / ".ai" / "assistant" / "operation-catalog.json"
    write_json(
        catalog_path,
        {
            "schema_version": 1,
            "catalog_kind": "target-operation-catalog",
            "fallback_operation": "help",
            "compact_help": ".ai/assistant/help.md",
            "human_reference": ".ai/assistant/help-reference.md",
            "routing_flow": ".ai/assistant/flows/operation-routing.flow.md",
            "health_flow": ".ai/assistant/flows/adapter-health.flow.md",
            "pre_change_preview": ".ai/assistant/templates/pre-change-preview.md",
            "module_profile": ".ai/assistant/module-profile.md",
            "operations": [
                {
                    "id": operation_id,
                    "title": operation_id,
                    "summary": "fixture operation",
                    "use_when": ["fixture"],
                    "context_profiles": ["docs-local"],
                    "required_module": "core-profile",
                    "flow": ".ai/assistant/flows/operation-routing.flow.md",
                    "minimum_inputs": ["fixture"],
                    "allowed_actions": ["read-only"],
                    "preview": "never",
                    "aliases": [alias],
                    "final_evidence": ["fixture evidence"],
                }
                for operation_id, alias in [
                    ("help", "Alatyr"),
                    ("adapter-health", "Alatyr status"),
                ]
            ],
        },
    )
    write_json(
        router_path,
        {
            "schema_version": 2,
            "router_kind": "target-context-router",
            "human_reference": ".ai/assistant/context-profiles.md",
            "bootstrap_context": [
                ".ai/alatyr.yaml",
                ".ai/README.md",
                ".ai/assistant/context-router.json",
            ],
            "operation_routing": {
                "catalog": ".ai/assistant/operation-catalog.json",
                "health_operation": "adapter-health",
            },
            "profiles": {
                "docs-local": {
                    "operation_candidates": ["unknown-operation"]
                }
            },
        },
    )
    catalog_validator = validator(target)
    catalog_validator.check_operation_catalog()
    catalog_codes = {finding.code for finding in catalog_validator.findings}
    if "OPERATION_CANDIDATE_UNKNOWN" not in catalog_codes:
        failures.append("operation catalog must reject unknown profile candidates")
