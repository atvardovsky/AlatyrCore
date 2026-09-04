"""Target-validator scenarios for context routing."""

from __future__ import annotations

from .common import (
    validator,
    write_json,
)


def run(target: Path, failures: list[str]) -> None:
    router_path = target / ".ai" / "assistant" / "context-router.json"
    profiles_path = target / ".ai" / "assistant" / "context-profiles.md"
    profiles_path.parent.mkdir(parents=True, exist_ok=True)
    profiles_path.write_text("# Profiles\n", encoding="utf-8")
    write_json(
        router_path,
        {
            "schema_version": 1,
            "router_kind": "target-context-router",
            "human_reference": ".ai/assistant/context-profiles.md",
            "routing_order": ["docs-local"],
            "profiles": {},
        },
    )
    legacy = validator(target)
    legacy.check_router()
    legacy_codes = {finding.code for finding in legacy.findings}
    if "ROUTER_SCHEMA_LEGACY" not in legacy_codes:
        failures.append("schema-1 router must produce a migration warning")
    for forbidden in [
        "ROUTER_PRELOADED",
        "ROUTER_BOOTSTRAP",
        "ROUTER_BUDGETS_MISSING",
        "ROUTER_RECEIPT_MISSING",
    ]:
        if forbidden in legacy_codes:
            failures.append(
                f"schema-1 router must not receive schema-2 finding {forbidden}"
            )

    schema_seven_descriptor = (
        target
        / ".ai"
        / "assistant"
        / "context"
        / "profiles"
        / "docs-local.json"
    )
    write_json(
        schema_seven_descriptor,
        {
            "schema_version": 1,
            "descriptor_kind": "target-context-profile",
            "profile": "docs-local",
        },
    )
    schema_seven = validator(target)
    schema_seven_profiles = schema_seven.router_profiles(
        {
            "schema_version": 7,
            "profile_index": {
                "docs-local": {
                    "descriptor": (
                        ".ai/assistant/context/profiles/docs-local.json"
                    )
                }
            },
        }
    )
    if set(schema_seven_profiles) != {"docs-local"}:
        failures.append(
            "schema-7 router must load descriptor-backed canonical profiles"
        )

    consistency_descriptor = (
        target
        / ".ai"
        / "assistant"
        / "context"
        / "consistency-routing.json"
    )
    write_json(
        consistency_descriptor,
        {
            "schema_version": 1,
            "descriptor_kind": "target-consistency-routing",
            "required_context": [".ai/project/consistency-map.json"],
        },
    )
    write_json(
        router_path,
        {
            "schema_version": 1,
            "router_kind": "target-context-router",
            "human_reference": ".ai/assistant/context-profiles.md",
            "routing_order": ["docs-local"],
            "profiles": {},
            "consistency_routing": {
                "descriptor": ".ai/assistant/context/consistency-routing.json"
            },
        },
    )
    consistency_router = validator(target)
    consistency_router.check_router({"consistency-map"})
    consistency_router_codes = {
        finding.code for finding in consistency_router.findings
    }
    for required in [
        "ROUTER_CONSISTENCY_CONTEXT",
        "ROUTER_CONSISTENCY_CONDITIONAL",
    ]:
        if required not in consistency_router_codes:
            failures.append(
                f"broken consistency routing missing finding {required}"
            )

    large_context_path = target / ".ai" / "framework" / "large-context.md"
    large_context_path.parent.mkdir(parents=True, exist_ok=True)
    large_context_path.write_text("one two three four five\n", encoding="utf-8")
    budget_validator = validator(target)
    budget_validator.check_installed_context_costs(
        {"preloaded_context": [], "bootstrap_context": [], "profile_index": {}},
        {
            "docs-local": {
                "required_context": [".ai/framework/large-context.md"]
            }
        },
        {
            "bootstrap": {"max_files": 4, "max_words": 100},
            "profile_default": {
                "max_files": 4,
                "max_total_words": 100,
                "max_portable_words": 1,
            },
        },
    )
    if "ROUTER_PROFILE_COST" not in {
        finding.code for finding in budget_validator.findings
    }:
        failures.append("portable context over-budget must produce ROUTER_PROFILE_COST")

    consistency_cost_descriptor = (
        target / ".ai" / "assistant" / "context" / "cost-consistency.json"
    )
    write_json(
        consistency_cost_descriptor,
        {
            "required_context": [
                ".ai/project/source-of-truth-registry.md",
                ".ai/project/consistency-map.json",
            ]
        },
    )
    (target / ".ai" / "project").mkdir(parents=True, exist_ok=True)
    (target / ".ai" / "project" / "source-of-truth-registry.md").write_text(
        "one two three four five\n", encoding="utf-8"
    )
    (target / ".ai" / "project" / "consistency-map.json").write_text(
        "one two three four five\n", encoding="utf-8"
    )
    composition_validator = validator(target)
    composition_validator.check_installed_context_costs(
        {
            "preloaded_context": [],
            "bootstrap_context": [],
            "profile_index": {},
            "consistency_routing": {
                "descriptor": ".ai/assistant/context/cost-consistency.json"
            },
        },
        {
            "code-local": {
                "required_context": [".ai/framework/large-context.md"]
            }
        },
        {
            "bootstrap": {"max_files": 4, "max_words": 100},
            "profile_default": {
                "max_files": 8,
                "max_total_words": 10,
                "max_portable_words": 100,
                "reserved_target_words": 100,
            },
        },
    )
    if "ROUTER_CONSISTENCY_COMPOSITION_COST" not in {
        finding.code for finding in composition_validator.findings
    }:
        failures.append(
            "profile plus consistency routing over-budget must be rejected"
        )
