#!/usr/bin/env python3
"""Validate the target adapter manifest template contract.

This validates the AlatyrCore source manifest template only. It is not a
portable framework requirement for target projects.
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

import jsonschema

from scaffold_state import validate_installation_state_record

from target_validation_support import (
    PathKey,
    Scalar,
    dotted,
    load_manifest_object,
    parse_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
MANIFEST = TARGET / ".ai" / "alatyr.yaml"
SCHEMA = ROOT / "schemas" / "alatyr-adapter.schema.json"
INSTALLATION_STATE = TARGET / ".ai" / "assistant" / "installation-state.json"
INSTALLATION_STATE_SCHEMA = ROOT / "schemas" / "alatyr-installation-state.schema.json"


REQUIRED_CONTAINERS: set[PathKey] = {
    ("framework",),
    ("installation",),
    ("owner",),
    ("contours",),
    ("source_of_truth",),
    ("context_routing",),
    ("modules",),
    ("validation",),
    ("ai_infrastructure",),
    ("operations",),
    ("project_knowledge",),
    ("maturity",),
    ("bridges",),
    ("approvals",),
    ("change_packages",),
    ("code_documentation",),
    ("project_vocabulary",),
    ("test_first_development",),
    ("extensions",),
    ("policies",),
}

REQUIRED_LISTS: set[PathKey] = {
    ("owner", "review_triggers"),
    ("supported_assistants",),
    ("source_of_truth", "project_sources"),
    ("context_routing", "preloaded_context"),
    ("context_routing", "compact_bootstrap"),
    ("modules", "enabled"),
    ("modules", "deferred"),
    ("modules", "blocked"),
    ("validation", "commands"),
    ("validation", "commands", "[]", "required_for"),
    ("known_gaps",),
    ("local_deviations",),
}

REQUIRED_SCALARS: set[PathKey] = {
    ("schema_version",),
    ("framework", "name"),
    ("framework", "version"),
    ("framework", "source"),
    ("framework", "template_version"),
    ("framework", "pack"),
    ("framework", "rule_registry"),
    ("installation", "id"),
    ("installation", "date"),
    ("installation", "mode"),
    ("installation", "support_profile"),
    ("installation", "state"),
    ("installation", "state_record"),
    ("owner", "responsible_team"),
    ("owner", "technical_owner"),
    ("owner", "backup_owner"),
    ("owner", "last_review_date"),
    ("owner", "review_cadence"),
    ("owner", "codeowners"),
    ("contours", "framework"),
    ("contours", "project"),
    ("contours", "assistant"),
    ("source_of_truth", "project_contour"),
    ("source_of_truth", "registry"),
    ("source_of_truth", "engineering_evidence_index"),
    ("source_of_truth", "development_evidence"),
    ("source_of_truth", "consistency_map"),
    ("source_of_truth", "code_documentation_index"),
    ("source_of_truth", "code_documentation_catalog"),
    ("source_of_truth", "code_documentation_profiles"),
    ("source_of_truth", "vocabulary_index"),
    ("source_of_truth", "vocabulary_catalog"),
    ("source_of_truth", "vocabulary_terms"),
    ("source_of_truth", "vocabulary_data_dictionary_links"),
    ("source_of_truth", "testing_index"),
    ("source_of_truth", "test_first_policy"),
    ("source_of_truth", "assistant_contour"),
    ("source_of_truth", "context_router"),
    ("source_of_truth", "bootstrap_index"),
    ("source_of_truth", "context_profiles"),
    ("source_of_truth", "module_profile"),
    ("context_routing", "router_schema_version"),
    ("context_routing", "bootstrap_max_files"),
    ("context_routing", "bootstrap_max_words"),
    ("context_routing", "profile_default_max_files"),
    ("context_routing", "profile_default_max_total_words"),
    ("context_routing", "profile_default_max_portable_words"),
    ("context_routing", "profile_default_reserved_target_words"),
    ("context_routing", "budget_behavior"),
    ("modules", "core_profile"),
    ("validation", "commands", "[]", "name"),
    ("validation", "commands", "[]", "command"),
    ("ai_infrastructure", "router"),
    ("ai_infrastructure", "inventory"),
    ("ai_infrastructure", "recommendation"),
    ("ai_infrastructure", "adaptation_record"),
    ("operations", "help"),
    ("operations", "gate_index"),
    ("operations", "index"),
    ("operations", "catalog"),
    ("operations", "routing"),
    ("operations", "health"),
    ("operations", "pre_change_preview"),
    ("operations", "action_authorization_policy"),
    ("operations", "diagram_discussion"),
    ("operations", "diagram_presentation"),
    ("operations", "documentation_sync"),
    ("operations", "code_documentation_profile_review"),
    ("operations", "project_vocabulary"),
    ("operations", "vocabulary_term_review"),
    ("operations", "test_first_configuration"),
    ("operations", "test_first_change"),
    ("operations", "test_first_evidence"),
    ("operations", "help_reference"),
    ("operations", "operation_request"),
    ("operations", "installation_note"),
    ("operations", "output_contracts"),
    ("operations", "large_task_packet"),
    ("operations", "change_package_flow"),
    ("operations", "change_package_index"),
    ("operations", "change_package_record"),
    ("operations", "change_package_report"),
    ("operations", "ai_infrastructure_inventory"),
    ("operations", "ai_infrastructure_recommendation"),
    ("operations", "development_evidence_capture"),
    ("operations", "migration_note"),
    ("operations", "effectiveness_report"),
    ("maturity", "profile"),
    ("bridges", "capability_matrix"),
    ("bridges", "capabilities"),
    ("approvals", "directory"),
    ("approvals", "template"),
    ("approvals", "machine_template"),
    ("change_packages", "directory"),
    ("change_packages", "index"),
    ("change_packages", "machine_template"),
    ("change_packages", "human_report_template"),
    ("change_packages", "retention_policy"),
    ("code_documentation", "catalog"),
    ("code_documentation", "profiles"),
    ("code_documentation", "intent"),
    ("code_documentation", "flow"),
    ("code_documentation", "skill"),
    ("code_documentation", "profile_review"),
    ("project_vocabulary", "catalog"),
    ("project_vocabulary", "terms"),
    ("project_vocabulary", "data_dictionary_links"),
    ("project_vocabulary", "intent"),
    ("project_vocabulary", "flow"),
    ("project_vocabulary", "skill"),
    ("project_vocabulary", "term_review"),
    ("test_first_development", "policy"),
    ("test_first_development", "intent"),
    ("test_first_development", "configuration_flow"),
    ("test_first_development", "change_flow"),
    ("test_first_development", "gate"),
    ("test_first_development", "skill"),
    ("test_first_development", "evidence"),
    ("extensions", "index"),
    ("extensions", "catalog"),
    ("extensions", "lock"),
    ("extensions", "intent"),
    ("extensions", "flow"),
    ("extensions", "gate"),
    ("extensions", "review"),
    ("extensions", "lifecycle_record"),
    ("operations", "extension_management"),
    ("operations", "extension_review"),
    ("operations", "extension_lifecycle_record"),
    ("operations", "project_knowledge"),
    ("operations", "project_knowledge_promotion"),
    ("operations", "project_knowledge_route_shard"),
    ("project_knowledge", "contract_version"),
    ("project_knowledge", "index"),
    ("project_knowledge", "route_shards"),
    ("project_knowledge", "promotions"),
    ("project_knowledge", "routing"),
    ("project_knowledge", "flow"),
    ("project_knowledge", "gate"),
    ("project_knowledge", "promotion_template"),
    ("project_knowledge", "route_shard_template"),
    ("project_knowledge", "owner"),
    ("project_knowledge", "review_policy"),
    ("project_knowledge", "retention_policy"),
    ("project_knowledge", "redaction_policy"),
    ("policies", "source_access"),
    ("policies", "prompt_injection"),
}

PLACEHOLDER_SCALARS: set[PathKey] = {
    ("schema_version",),
    ("framework", "version"),
    ("framework", "source"),
    ("framework", "template_version"),
    ("installation", "id"),
    ("installation", "date"),
    ("installation", "mode"),
    ("installation", "support_profile"),
    ("owner", "responsible_team"),
    ("owner", "technical_owner"),
    ("owner", "backup_owner"),
    ("owner", "last_review_date"),
    ("owner", "review_cadence"),
    ("owner", "codeowners"),
    ("modules", "core_profile"),
    ("validation", "commands", "[]", "name"),
    ("validation", "commands", "[]", "command"),
}

PLACEHOLDER_LISTS: set[PathKey] = {
    ("owner", "review_triggers"),
    ("supported_assistants",),
    ("source_of_truth", "project_sources"),
    ("modules", "enabled"),
    ("modules", "deferred"),
    ("modules", "blocked"),
    ("validation", "commands", "[]", "required_for"),
    ("known_gaps",),
    ("local_deviations",),
}

PATH_SCALARS: set[PathKey] = {
    ("installation", "state_record"),
    ("framework", "rule_registry"),
    ("contours", "framework"),
    ("contours", "project"),
    ("contours", "assistant"),
    ("source_of_truth", "project_contour"),
    ("source_of_truth", "registry"),
    ("source_of_truth", "development_evidence"),
    ("source_of_truth", "consistency_map"),
    ("source_of_truth", "code_documentation_index"),
    ("source_of_truth", "code_documentation_catalog"),
    ("source_of_truth", "code_documentation_profiles"),
    ("source_of_truth", "vocabulary_index"),
    ("source_of_truth", "vocabulary_catalog"),
    ("source_of_truth", "vocabulary_terms"),
    ("source_of_truth", "vocabulary_data_dictionary_links"),
    ("source_of_truth", "testing_index"),
    ("source_of_truth", "test_first_policy"),
    ("source_of_truth", "assistant_contour"),
    ("source_of_truth", "context_router"),
    ("source_of_truth", "context_profiles"),
    ("source_of_truth", "module_profile"),
    ("ai_infrastructure", "router"),
    ("ai_infrastructure", "inventory"),
    ("ai_infrastructure", "recommendation"),
    ("ai_infrastructure", "adaptation_record"),
    ("operations", "help"),
    ("operations", "index"),
    ("operations", "catalog"),
    ("operations", "routing"),
    ("operations", "health"),
    ("operations", "pre_change_preview"),
    ("operations", "action_authorization_policy"),
    ("operations", "diagram_discussion"),
    ("operations", "diagram_presentation"),
    ("operations", "documentation_sync"),
    ("operations", "code_documentation_profile_review"),
    ("operations", "project_vocabulary"),
    ("operations", "vocabulary_term_review"),
    ("operations", "test_first_configuration"),
    ("operations", "test_first_change"),
    ("operations", "test_first_evidence"),
    ("operations", "help_reference"),
    ("operations", "operation_request"),
    ("operations", "installation_note"),
    ("operations", "output_contracts"),
    ("operations", "large_task_packet"),
    ("operations", "change_package_flow"),
    ("operations", "change_package_index"),
    ("operations", "change_package_record"),
    ("operations", "change_package_report"),
    ("operations", "ai_infrastructure_inventory"),
    ("operations", "ai_infrastructure_recommendation"),
    ("operations", "development_evidence_capture"),
    ("operations", "migration_note"),
    ("operations", "effectiveness_report"),
    ("maturity", "profile"),
    ("bridges", "capability_matrix"),
    ("bridges", "capabilities"),
    ("approvals", "directory"),
    ("approvals", "template"),
    ("approvals", "machine_template"),
    ("change_packages", "directory"),
    ("change_packages", "index"),
    ("change_packages", "machine_template"),
    ("change_packages", "human_report_template"),
    ("code_documentation", "catalog"),
    ("code_documentation", "profiles"),
    ("code_documentation", "intent"),
    ("code_documentation", "flow"),
    ("code_documentation", "skill"),
    ("code_documentation", "profile_review"),
    ("project_vocabulary", "catalog"),
    ("project_vocabulary", "terms"),
    ("project_vocabulary", "data_dictionary_links"),
    ("project_vocabulary", "intent"),
    ("project_vocabulary", "flow"),
    ("project_vocabulary", "skill"),
    ("project_vocabulary", "term_review"),
    ("test_first_development", "policy"),
    ("test_first_development", "intent"),
    ("test_first_development", "configuration_flow"),
    ("test_first_development", "change_flow"),
    ("test_first_development", "gate"),
    ("test_first_development", "skill"),
    ("test_first_development", "evidence"),
    ("extensions", "index"),
    ("extensions", "catalog"),
    ("extensions", "lock"),
    ("extensions", "intent"),
    ("extensions", "flow"),
    ("extensions", "gate"),
    ("extensions", "review"),
    ("extensions", "lifecycle_record"),
    ("operations", "extension_management"),
    ("operations", "extension_review"),
    ("operations", "extension_lifecycle_record"),
    ("policies", "source_access"),
    ("policies", "prompt_injection"),
}


def has_placeholder(value: str) -> bool:
    return "{" in value and "}" in value


def target_reference_exists(value: str) -> bool:
    if value == ".ai/framework":
        return (ROOT / "framework").is_dir()
    if value == ".ai/framework/rule-registry.json":
        return (ROOT / "framework" / "rule-registry.json").is_file()
    return (TARGET / value).exists()


def main() -> int:
    failures: list[str] = []

    parsed = parse_manifest(MANIFEST)
    containers = parsed.containers
    scalars = parsed.scalars
    lists = parsed.lists
    failures.extend(parsed.parse_failures)

    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        manifest_object = load_manifest_object(MANIFEST)
        schema_errors = sorted(
            jsonschema.Draft7Validator(schema).iter_errors(manifest_object),
            key=lambda error: list(error.absolute_path),
        )
        for error in schema_errors:
            location = ".".join(str(item) for item in error.absolute_path) or "root"
            failures.append(f"schema {location}: {error.message}")
    except (OSError, ValueError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        failures.append(f"cannot validate manifest schema: {exc}")

    try:
        state_schema = json.loads(INSTALLATION_STATE_SCHEMA.read_text(encoding="utf-8"))
        state_record = json.loads(INSTALLATION_STATE.read_text(encoding="utf-8"))
        state_errors = sorted(
            jsonschema.Draft7Validator(state_schema).iter_errors(state_record),
            key=lambda error: list(error.absolute_path),
        )
        for error in state_errors:
            location = ".".join(str(item) for item in error.absolute_path) or "root"
            failures.append(f"installation-state schema {location}: {error.message}")
        manifest_state = load_manifest_object(MANIFEST).get("installation", {}).get(
            "state", ""
        )
        failures.extend(
            validate_installation_state_record(
                state_record,
                manifest_state=str(manifest_state),
            )
        )
    except (OSError, ValueError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        failures.append(f"cannot validate installation-state schema: {exc}")

    for path in sorted(REQUIRED_CONTAINERS):
        if path not in containers:
            failures.append(f"missing container: {dotted(path)}")

    for path in sorted(REQUIRED_LISTS):
        if path not in lists:
            failures.append(f"missing list: {dotted(path)}")
        elif not lists[path]:
            failures.append(f"empty list: {dotted(path)}")

    for path in sorted(REQUIRED_SCALARS):
        if path not in scalars:
            failures.append(f"missing scalar: {dotted(path)}")
        elif not scalars[path].value:
            failures.append(f"empty scalar: {dotted(path)}")

    for path in sorted(PLACEHOLDER_SCALARS):
        scalar = scalars.get(path)
        if scalar and not has_placeholder(scalar.value):
            failures.append(
                f"line {scalar.line}: {dotted(path)} must remain placeholder-based"
            )

    for path in sorted(PLACEHOLDER_LISTS):
        for scalar in lists.get(path, []):
            if not has_placeholder(scalar.value):
                failures.append(
                    f"line {scalar.line}: {dotted(path)} item must remain placeholder-based"
                )

    for path in sorted(PATH_SCALARS):
        scalar = scalars.get(path)
        if not scalar:
            continue
        value = scalar.value
        if not value.startswith(".ai/"):
            failures.append(f"line {scalar.line}: {dotted(path)} must be a .ai path")
            continue
        if not target_reference_exists(value):
            failures.append(
                f"line {scalar.line}: {dotted(path)} points to missing template path: "
                f"{value}"
            )

    framework_name = scalars.get(("framework", "name"))
    if framework_name and framework_name.value != "Alatyr Core":
        failures.append("framework.name must be Alatyr Core")

    installation_state = scalars.get(("installation", "state"))
    if installation_state and installation_state.value != "scaffolded":
        failures.append("target manifest template must start in scaffolded state")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked manifest contract with "
        f"{len(scalars)} scalars and {len(lists)} lists"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
