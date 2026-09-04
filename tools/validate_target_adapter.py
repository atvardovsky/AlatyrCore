#!/usr/bin/env python3
"""Validate an installed Alatyr target adapter.

This is an optional helper. It checks structural adapter consistency in a
target repository; it does not install Alatyr Core, approve changes, validate
project business facts, or replace assistant logical integrity review.

The implementation is cross-platform and uses the dependencies declared in
the source repository's `requirements.txt` for YAML and schema validation.
With those dependencies installed, it runs on Linux, macOS, and Windows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import jsonschema

from agent_entry_packet import (
    PACKET_PATH,
    build_from_target as build_entry_packet,
    render as render_entry_packet,
)
from bootstrap_index import BOOTSTRAP_PATH, build_from_target
from target_validation_support import (
    ManifestData,
    PathKey,
    UNRESOLVED_WORDS,
    dotted,
    duplicates,
    expect_string_list,
    extract_field,
    extract_list_field,
    git_changed_files,
    git_branch_name,
    git_diff_patch,
    git_head_revision,
    git_is_ancestor,
    git_range_changed_files,
    git_resolve_object,
    git_resolve_ref,
    git_snapshot_sha256,
    is_placeholder,
    is_protected_surface,
    is_target_relative_path,
    is_target_scope_pattern,
    load_manifest_object,
    is_unresolved_value,
    json_string_list,
    markdown_sections,
    nested_json_value,
    normalize_hash_field,
    parse_manifest,
    refs_match,
    scope_entries_cover,
    section_items,
    sha256,
    should_skip_path,
)
from target_adapter_validation.context import (
    TargetMutation,
    TargetPathEscapeError,
    TargetRepositoryView,
    ValidationContext,
)
from target_adapter_validation.context_catalogs import (
    validate_context_catalog_contract,
)
from target_adapter_validation.capability import CapabilityValidationContext
from target_adapter_validation.ai_infrastructure import (
    AI_INFRASTRUCTURE_ROUTER_MODULE,
)
from target_adapter_validation.action_modes import ALLOWED_ACTION_MODES
from target_adapter_validation.assistant_capabilities import (
    CACHE_EXPOSURE_STATES,
    CACHE_FALLBACK,
    CACHE_PROVIDER_MODES,
    CACHE_ROUTE_STATES,
    CAPABILITY_INDEX_KIND,
    CAPABILITY_INDEX_SCHEMA_VERSION,
    EVIDENCE_STATES,
    INDEX_STATE_EVIDENCE_STRING_FIELDS,
    INDEX_STATE_EVIDENCE_TRUE_FIELDS,
    OVERALL_STATES,
    SURFACE_CAPABILITY_KIND,
    SURFACE_CAPABILITY_SCHEMA_VERSION,
    SURFACE_STATE_FIELDS,
    YES_NO_UNKNOWN,
    capability_record_path,
    is_concrete_capability_value,
)
from target_adapter_validation.consistency_map import (
    CONSISTENCY_MAP_MODULE,
    RegistryFactEntry,
    parse_registry_fact_entries,
)
from target_adapter_validation.debug_mode import validate_debug_mode
from target_adapter_validation.diagrams import validate_discussion_diagrams
from target_adapter_validation.engineering_evidence import (
    validate_engineering_evidence,
)
from target_adapter_validation.framework_baseline import source_pack_expectation
from target_adapter_validation.installation_state import validate_installation_state
from target_adapter_validation.module_profile import ModuleProfileState, parse_module_profile
from target_adapter_validation.project_knowledge import (
    validate_project_knowledge_contract,
)
from target_adapter_validation.subagent_delegation import validate_subagent_delegation
from target_adapter_validation.task_decomposition import validate_task_decomposition
from target_adapter_validation.team_collaboration import validate_team_collaboration
from target_adapter_validation.development_evidence import validate_development_evidence
from target_adapter_validation.dependency_knowledge import validate_dependency_knowledge
from target_adapter_validation.extensions import validate_extensions
from target_adapter_validation.test_first_development import validate_test_first_development
from target_adapter_validation.project_vocabulary import validate_project_vocabulary
from target_adapter_validation.code_documentation import validate_code_documentation
from target_adapter_validation.architecture_knowledge import validate_architecture_knowledge
from target_adapter_validation.support_state import validate_support_state
from target_adapter_validation.workspace_modes import validate_workspace_modes
from target_adapter_validation.values import is_resolved_string
from scaffold_state import validate_installation_state_record
from target_adapter_validation.modules import dispatch_capability_checks
from target_adapter_validation.router_costs import (
    validate_budget_shape,
    validate_installed_costs,
)
from target_tool_compat import (
    generated_json_equivalent,
    generation_provenance_errors,
)
from task_classification_contract import (
    AMBIGUITY_READ_ONLY_MARKER,
    DEFAULT_TASK_CLASS,
    SMALL_TASK_CLASS,
    TARGET_REQUIRED_EXPANSION_TRIGGERS,
    TARGET_REQUIRED_SMALL_TASK_EXPANSION_TRIGGERS,
    TASK_CLASSES,
    TASK_CLASSIFICATION_SCHEMA_VERSION,
    missing_required_values,
)
ROOT = Path(__file__).resolve().parents[1]
ADAPTER_MANIFEST_SCHEMA = ROOT / "schemas" / "alatyr-adapter.schema.json"

CANONICAL_PROFILES = [
    "docs-local",
    "code-local",
    "business-change",
    "architecture-change",
    "data-change",
    "security-sensitive",
    "ai-infrastructure",
    "framework-upgrade",
]
ROUTER_SCHEMA_VERSIONS = {2, 3, 4, 5, 6, 7, 8, 9, 10}

KERNEL_REQUIRED_FILES = [
    "AGENTS.md",
    "CODEOWNERS",
    ".ai/alatyr.yaml",
    ".ai/README.md",
    ".ai/assistant/bootstrap-index.json",
    ".ai/assistant/entry-packet.json",
    ".ai/framework/context-index.json",
    ".ai/project/context-index.json",
    ".ai/assistant/context-index.json",
    ".ai/framework/semantics/index.json",
    ".ai/assistant/templates/context-packet.json",
    ".ai/project/contour.md",
    ".ai/project/source-of-truth-registry.md",
    ".ai/project/support-policy.json",
    ".ai/support-state.json",
    ".ai/assistant/contour.md",
    ".ai/assistant/context-router.json",
    ".ai/assistant/context-profiles.md",
    ".ai/assistant/context/profiles/architecture-change.json",
    ".ai/assistant/context/profiles/business-change.json",
    ".ai/assistant/context/profiles/code-local.json",
    ".ai/assistant/context/profiles/data-change.json",
    ".ai/assistant/context/profiles/docs-local.json",
    ".ai/assistant/context/profiles/framework-upgrade.json",
    ".ai/assistant/context/profiles/security-sensitive.json",
    ".ai/assistant/context/task-scales/small-task.json",
    ".ai/assistant/installation-state.json",
    ".ai/assistant/module-profile.md",
    ".ai/assistant/maturity-profile.md",
    ".ai/assistant/task-decomposition.json",
    ".ai/assistant/gates/index.json",
    ".ai/assistant/gates/core.md",
    ".ai/assistant/gates/code-and-tests.md",
    ".ai/assistant/gates/documentation.md",
    ".ai/assistant/gates/final-evidence.md",
    ".ai/assistant/gates/security-approval.md",
    ".ai/assistant/gates/semantic-integrity.md",
    ".ai/assistant/help.md",
    ".ai/assistant/policies/action-authorization.json",
    ".ai/assistant/templates/adapter-output-contracts.md",
    ".ai/assistant/templates/installation-note.md",
    ".ai/assistant/templates/operation-request.md",
    ".ai/assistant/templates/small-task-evidence.md",
    ".ai/assistant/templates/task-decomposition.md",
    ".ai/assistant/flows/logical-integrity-review.flow.md",
]

CORE_REQUIRED_FILES = [
    ".ai/assistant/checklists/change-impact.md",
    ".ai/project/engineering-evidence/README.md",
    ".ai/project/engineering-evidence/index.json",
    ".ai/project/engineering-evidence/records/README.md",
    ".ai/project/knowledge/README.md",
    ".ai/project/knowledge/index.json",
    ".ai/project/knowledge/routes/README.md",
    ".ai/project/knowledge/promotions/README.md",
    ".ai/assistant/flows/documentation-sync.flow.md",
    ".ai/assistant/flows/engineering-evidence-capture.flow.md",
    ".ai/assistant/flows/project-knowledge.flow.md",
    ".ai/assistant/gates/checklist.md",
    ".ai/assistant/gates/engineering-evidence.md",
    ".ai/assistant/gates/project-knowledge.md",
    ".ai/assistant/templates/engineering-evidence-record.json",
    ".ai/assistant/templates/project-knowledge-promotion.json",
    ".ai/assistant/templates/project-knowledge-route-shard.json",
    ".ai/assistant/context/project-knowledge-routing.json",
    ".ai/assistant/context/cost-scenarios.json",
    ".ai/assistant/context/migration-routing.json",
    ".ai/assistant/context/task-scales/engineering-evidence.json",
]

STANDARD_REQUIRED_FILES = [
    ".ai/assistant/operation-index.json",
    ".ai/assistant/operation-catalog.json",
    ".ai/assistant/flows/adapter-recheck.flow.md",
    ".ai/assistant/flows/adapter-health.flow.md",
    ".ai/assistant/flows/operation-routing.flow.md",
    ".ai/assistant/templates/pre-change-preview.md",
]

SUPPORT_PROFILES = {"kernel", "core", "standard", "full"}
PROFILE_MIN_PACK = {
    "kernel": "kernel",
    "core": "core",
    "standard": "standard",
    "full": "complete",
}
FRAMEWORK_PACK_RANK = {"kernel": 0, "core": 1, "standard": 2, "complete": 3}
VALIDATION_PHASES = {"acceptance", "migration-staging"}
INSTALLATION_STATES = {"scaffolded", "staged", "accepted", "degraded"}


def required_files_for_support_profile(support_profile: str) -> list[str]:
    required = list(KERNEL_REQUIRED_FILES)
    if support_profile in {"core", "standard", "full"}:
        required.extend(CORE_REQUIRED_FILES)
    if support_profile in {"standard", "full"}:
        required.extend(STANDARD_REQUIRED_FILES)
    return required

AUTHORING_FILE_PATTERNS = (
    re.compile(r"^\.ai/assistant/templates/"),
    re.compile(r"^\.ai/assistant/approvals/.*template", re.IGNORECASE),
    re.compile(r"^\.ai/assistant/team/task-record-template\.json$"),
    re.compile(r"^\.ai/project/workspace-modes/modes/_template/"),
    re.compile(r"(?:^|/)examples?/"),
    re.compile(r"\.example\.[^/]+$"),
)

REQUIRED_PRELOADED = [
    "AGENTS.md",
]

REQUIRED_BOOTSTRAP = [
    ".ai/assistant/bootstrap-index.json",
]

LEGACY_REQUIRED_BOOTSTRAP = [
    ".ai/alatyr.yaml",
    ".ai/README.md",
    ".ai/assistant/context-router.json",
]

DEFERRED_BOOTSTRAP = {
    "AGENTS.md",
    ".ai/alatyr.yaml",
    ".ai/README.md",
    ".ai/assistant/context-router.json",
    ".ai/assistant/context-profiles.md",
    ".ai/assistant/module-profile.md",
    ".ai/project/contour.md",
    ".ai/project/source-of-truth-registry.md",
    ".ai/assistant/contour.md",
}

BRIDGE_FILES = [
    "AI_ASSISTANTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
    ".cursorrules",
    ".cursor/rules/alatyr-core.mdc",
    ".devin/rules/alatyr-core.md",
    ".windsurfrules",
    ".windsurf/rules/alatyr-core.md",
    ".roo/rules/alatyr-core.md",
    ".rules",
]

NEUTRAL_ASSISTANT_ENTRY_FILES = {"AGENTS.md", "AI_ASSISTANTS.md"}

MANIFEST_REQUIRED_SCALARS: set[PathKey] = {
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
    ("source_of_truth", "project_contour"),
    ("source_of_truth", "registry"),
    ("source_of_truth", "engineering_evidence_index"),
    ("source_of_truth", "assistant_contour"),
    ("source_of_truth", "context_router"),
    ("source_of_truth", "bootstrap_index"),
    ("source_of_truth", "framework_context_index"),
    ("source_of_truth", "project_context_index"),
    ("source_of_truth", "assistant_context_index"),
    ("source_of_truth", "semantic_codebook"),
    ("source_of_truth", "agent_entry_packet"),
    ("source_of_truth", "context_profiles"),
    ("source_of_truth", "module_profile"),
    ("context_routing", "router_schema_version"),
    ("context_routing", "recursive_index_schema_version"),
    ("context_routing", "recursive_index_max_depth"),
    ("context_routing", "semantic_codebook_schema_version"),
    ("context_routing", "semantic_preload_policy"),
    ("context_routing", "context_packet_schema_version"),
    ("context_routing", "context_packet_template"),
    ("context_routing", "agent_entry_packet_schema_version"),
    ("context_routing", "agent_entry_packet"),
    ("context_routing", "bootstrap_max_files"),
    ("context_routing", "bootstrap_max_words"),
    ("context_routing", "profile_default_max_files"),
    ("context_routing", "profile_default_max_total_words"),
    ("context_routing", "profile_default_max_portable_words"),
    ("context_routing", "profile_default_reserved_target_words"),
    ("context_routing", "budget_behavior"),
    ("operations", "help"),
    ("operations", "gate_index"),
    ("operations", "operation_request"),
    ("operations", "output_contracts"),
    ("operations", "action_authorization_policy"),
    ("operations", "task_decomposition"),
    ("operations", "task_decomposition_plan"),
    ("operations", "engineering_evidence_capture"),
    ("operations", "engineering_evidence_record"),
    ("operations", "project_knowledge"),
    ("operations", "project_knowledge_promotion"),
    ("operations", "project_knowledge_route_shard"),
    ("engineering_evidence", "index"),
    ("engineering_evidence", "records"),
    ("engineering_evidence", "flow"),
    ("engineering_evidence", "gate"),
    ("engineering_evidence", "machine_template"),
    ("engineering_evidence", "storage_mode"),
    ("engineering_evidence", "external_patch_policy"),
    ("engineering_evidence", "retention_policy"),
    ("engineering_evidence", "redaction_policy"),
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
    ("maturity", "profile"),
}

MANIFEST_STANDARD_REQUIRED_SCALARS: set[PathKey] = {
    ("operations", "index"),
    ("operations", "catalog"),
    ("operations", "routing"),
    ("operations", "health"),
    ("operations", "pre_change_preview"),
}

MANIFEST_FULL_REQUIRED_SCALARS: set[PathKey] = {
    ("operations", "diagram_discussion"),
    ("operations", "diagram_presentation"),
    ("bridges", "capability_matrix"),
    ("bridges", "capabilities"),
    ("operations", "change_package_flow"),
    ("operations", "change_package_index"),
    ("operations", "change_package_record"),
    ("operations", "change_package_report"),
    ("change_packages", "index"),
    ("change_packages", "machine_template"),
    ("change_packages", "human_report_template"),
    ("source_of_truth", "code_documentation_index"),
    ("source_of_truth", "code_documentation_catalog"),
    ("source_of_truth", "code_documentation_profiles"),
    ("operations", "documentation_sync"),
    ("operations", "code_documentation_profile_review"),
    ("operations", "contract_artifact_review"),
    ("operations", "visual_validation_review"),
    ("code_documentation", "catalog"),
    ("code_documentation", "profiles"),
    ("code_documentation", "intent"),
    ("code_documentation", "flow"),
    ("code_documentation", "skill"),
    ("code_documentation", "profile_review"),
    ("source_of_truth", "vocabulary_index"),
    ("source_of_truth", "vocabulary_catalog"),
    ("source_of_truth", "vocabulary_terms"),
    ("source_of_truth", "vocabulary_data_dictionary_links"),
    ("operations", "project_vocabulary"),
    ("operations", "vocabulary_term_review"),
    ("project_vocabulary", "catalog"),
    ("project_vocabulary", "terms"),
    ("project_vocabulary", "data_dictionary_links"),
    ("project_vocabulary", "intent"),
    ("project_vocabulary", "flow"),
    ("project_vocabulary", "skill"),
    ("project_vocabulary", "term_review"),
    ("source_of_truth", "testing_index"),
    ("source_of_truth", "test_first_policy"),
    ("operations", "test_first_configuration"),
    ("operations", "test_first_change"),
    ("operations", "test_first_evidence"),
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
}

CORE_PLUS_MANIFEST_SCALARS: set[PathKey] = {
    ("source_of_truth", "engineering_evidence_index"),
    ("operations", "engineering_evidence_capture"),
    ("operations", "engineering_evidence_record"),
    ("operations", "project_knowledge"),
    ("operations", "project_knowledge_promotion"),
    ("operations", "project_knowledge_route_shard"),
    ("engineering_evidence", "index"),
    ("engineering_evidence", "records"),
    ("engineering_evidence", "flow"),
    ("engineering_evidence", "gate"),
    ("engineering_evidence", "machine_template"),
    ("engineering_evidence", "storage_mode"),
    ("engineering_evidence", "external_patch_policy"),
    ("engineering_evidence", "retention_policy"),
    ("engineering_evidence", "redaction_policy"),
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
}
KERNEL_MANIFEST_REQUIRED_SCALARS = MANIFEST_REQUIRED_SCALARS - CORE_PLUS_MANIFEST_SCALARS

MANIFEST_PATH_SCALARS: set[PathKey] = {
    ("framework", "rule_registry"),
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
    ("source_of_truth", "team_operating_model"),
    ("source_of_truth", "assistant_contour"),
    ("source_of_truth", "context_router"),
    ("source_of_truth", "context_profiles"),
    ("source_of_truth", "module_profile"),
    ("operations", "help"),
    ("operations", "index"),
    ("operations", "catalog"),
    ("operations", "routing"),
    ("operations", "health"),
    ("operations", "pre_change_preview"),
    ("operations", "action_authorization_policy"),
    ("operations", "task_decomposition"),
    ("operations", "task_decomposition_plan"),
    ("operations", "engineering_evidence_capture"),
    ("operations", "engineering_evidence_record"),
    ("operations", "debug_mode"),
    ("operations", "operation_request"),
    ("operations", "output_contracts"),
    ("operations", "development_evidence_capture"),
    ("operations", "documentation_sync"),
    ("operations", "code_documentation_profile_review"),
    ("operations", "contract_artifact_review"),
    ("operations", "visual_validation_review"),
    ("operations", "project_vocabulary"),
    ("operations", "vocabulary_term_review"),
    ("operations", "change_package_flow"),
    ("operations", "change_package_index"),
    ("operations", "change_package_record"),
    ("operations", "change_package_report"),
    ("ai_infrastructure", "router"),
    ("ai_infrastructure", "inventory"),
    ("ai_infrastructure", "recommendation"),
    ("ai_infrastructure", "adaptation_record"),
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
    ("engineering_evidence", "index"),
    ("engineering_evidence", "records"),
    ("engineering_evidence", "flow"),
    ("engineering_evidence", "gate"),
    ("engineering_evidence", "machine_template"),
    ("debug_mode", "index"),
    ("debug_mode", "records"),
    ("debug_mode", "overlay"),
    ("debug_mode", "flow"),
    ("debug_mode", "gate"),
    ("debug_mode", "record_template"),
    ("debug_mode", "summary_template"),
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
    ("source_of_truth", "testing_index"),
    ("source_of_truth", "test_first_policy"),
    ("operations", "test_first_configuration"),
    ("operations", "test_first_change"),
    ("operations", "test_first_evidence"),
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
    ("workspace_modes", "index"),
    ("workspace_modes", "catalog"),
    ("workspace_modes", "root_context"),
    ("workspace_modes", "modes"),
    ("workspace_modes", "mode_template"),
    ("workspace_modes", "intent"),
    ("workspace_modes", "flow"),
    ("workspace_modes", "gate"),
    ("workspace_modes", "suggestion"),
    ("workspace_modes", "preflight"),
    ("operations", "workspace_mode"),
    ("operations", "workspace_mode_preflight"),
    ("policies", "source_access"),
    ("policies", "prompt_injection"),
    ("team_collaboration", "operating_model"),
    ("team_collaboration", "context_overlay"),
    ("team_collaboration", "work_registry"),
    ("team_collaboration", "gate"),
}

PLACEHOLDER_RE = re.compile(r"\{[A-Z0-9_][A-Z0-9_ -]*\}")
UNIX_LOCAL_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])/(?:home|Users|tmp|var/folders|private/tmp)/[^\s)`>\"']+"
)
WINDOWS_LOCAL_PATH_RE = re.compile(
    r"\b[A-Za-z]:\\(?:Users|Temp|tmp|Projects|projects|[^\\\s`\"']+)"
    r"(?:\\[^\s`\"']+)*"
)
LOCAL_PATH_RE = re.compile(
    f"(?:{UNIX_LOCAL_PATH_RE.pattern})|(?:{WINDOWS_LOCAL_PATH_RE.pattern})"
)
CHECKER_MISSING_RE = re.compile(
    r"no.{0,180}(?:local\s+)?alatyr\s+checker\s+(?:was\s+)?found|"
    r"(?:no|without)\s+(?:local\s+)?(?:alatyr\s+|adapter\s+)?checker"
    r"(?:\s+(?:was\s+)?found)?|"
    r"(?:local\s+)?(?:alatyr\s+|adapter\s+)?checker\s+"
    r"(?:was\s+)?(?:not found|missing|unavailable)|"
    r"checker\s+(?:does\s+not|doesn't)\s+exist",
    re.IGNORECASE | re.DOTALL,
)
CHECKER_REFERENCE_RE = re.compile(
    r"(?:alatyr:check|check-alatyr|check_alatyr|validate_target_adapter)",
    re.IGNORECASE,
)
DEFAULT_CHECKER_COVERAGE = {
    "context-router": "context-router coverage",
    "placeholder": "placeholder coverage",
    "local path": "local path leakage coverage",
    "stale": "stale checker-claim coverage",
    "manifest": "manifest coverage",
}

STALE_ENABLED_MODULE_STATE_RE = re.compile(
    r"\b(?:is|remains|was|still\s+is)\s+"
    r"(?:not\s+installed|not\s+enabled|deferred|disabled|not-applicable|blocked)\b",
    re.IGNORECASE,
)
STALE_GENERIC_MODULE_STATE_RE = re.compile(
    r"\b(?:this|the)\s+(?:optional\s+)?(?:module|capability)\s+"
    r"(?:is|remains|was|still\s+is)\s+"
    r"(?:not\s+installed|not\s+enabled|deferred|disabled|not-applicable|blocked)\b",
    re.IGNORECASE,
)
CONDITIONAL_STATUS_RE = re.compile(
    r"\b(?:if|when|unless|until|while|may|might|can|could|example|possible)\b",
    re.IGNORECASE,
)
AUTHORIZATION_PHASES = ["inspect", "modify", "commit", "publish", "live-external"]


OPERATION_REQUIRED_FIELDS = {
    "id",
    "title",
    "summary",
    "required_module",
    "flow",
    "preview",
}
OPERATION_LIST_FIELDS = {
    "use_when",
    "context_profiles",
    "minimum_inputs",
    "allowed_actions",
    "aliases",
    "final_evidence",
}


def repair_operation_for(code: str) -> str:
    routes = [
        (("TEAM_LOCAL_IDENTITY_", "TEAM_ACTOR_ALIAS_"), "team-identity"),
        (("TEAM_MERGE_",), "team-merge-check"),
        (("TEAM_REVIEW_",), "team-review"),
        (("TEAM_OVERLAP_", "TEAM_ACTIVE_OVERLAP_"), "team-conflict-review"),
        (
            (
                "TEAM_TASK_",
                "TEAM_CLAIM_",
                "TEAM_ACTIVE_CLAIM_",
                "TEAM_TERMINAL_TASK_",
            ),
            "team-task",
        ),
        (("TEAM_",), "team-status"),
        (("FRAMEWORK_", "MIGRATION_"), "recheck-after-framework-update"),
        (("EXTENSION_",), "extension-management"),
        (("AI_", "PROMPT_", "DEVELOPMENT_EVIDENCE_"), "ai-infrastructure-recommendation"),
        (("CONSISTENCY_", "SOURCE_"), "logical-integrity-review"),
        (("PACKAGE_",), "logical-integrity-review"),
        (("DEBUG_MODE_",), "debug-mode"),
        (("BRIDGE_",), "drift-review"),
        (("DIAGRAM_",), "diagram-discussion"),
        (("APPROVAL_",), "logical-integrity-review"),
        (("AUTHORIZATION_",), "help"),
        (
            (
                "OPERATION_",
                "ROUTER_",
                "PROFILE_",
                "BOOTSTRAP_",
                "MANIFEST_",
                "REQUIRED_",
                "CHECKER_",
                "STALE_",
                "LOCAL_",
                "PLACEHOLDER_",
            ),
            "recheck-after-installation",
        ),
    ]
    for prefixes, operation in routes:
        if code.startswith(prefixes):
            return operation
    return "recheck-after-installation"


@dataclass(frozen=True)
class ValidationPhase:
    """One ordered target-validation phase with explicit execution metadata."""

    phase_id: str
    run: Callable[[], None]
    dependencies: tuple[str, ...] = ()
    cost_class: str = "light"


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    path: str | None = None

    def render(self) -> str:
        prefix = f"{self.level.upper()} {self.code}"
        if self.path:
            return f"{prefix} {self.path}: {self.message}"
        return f"{prefix}: {self.message}"

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }
        if self.path:
            payload["path"] = self.path
        payload["blocking"] = is_blocking_finding(self)
        if self.level in {"error", "warning"}:
            payload["owner_surface"] = self.path or "target adapter"
            payload["repair_operation"] = repair_operation_for(self.code)
            payload["approval_required"] = "evaluate target approval policy"
            payload["automatic_repair"] = False
        return payload


@dataclass(frozen=True)
class AcceptedDeviation:
    code: str
    path: str | None = None
    reason: str = ""


# Integrity drift is advisory only after a target records an explicit accepted
# deviation or severity override. Silent success would make baseline checks
# unsuitable for CI and framework-update gates.
BLOCKING_WARNING_CODES = {
    "FRAMEWORK_FILE_DRIFT",
    "FRAMEWORK_FILE_EXTRA",
    "FRAMEWORK_FILE_MISSING",
    "FRAMEWORK_PACK_INVENTORY_CONTENT_DRIFT",
    "FRAMEWORK_PACK_INVENTORY_DIGEST_DRIFT",
    "FRAMEWORK_PACK_INVENTORY_DRIFT",
    "FRAMEWORK_PACK_REGISTRY_DRIFT",
    "FRAMEWORK_PACK_REGISTRY_INVALID",
    "FRAMEWORK_PACK_SELECTION_DRIFT",
    "FRAMEWORK_SOURCE_PACK_INVALID",
    "MIGRATION_DIFF_MISSING",
}


def is_blocking_finding(finding: Finding) -> bool:
    return finding.level == "error" or (
        finding.level == "warning" and finding.code in BLOCKING_WARNING_CODES
    )


@dataclass
class AdapterValidatorConfig:
    source: Path | None = None
    allow_local_path_patterns: list[str] | None = None
    severity_overrides: dict[str, str] | None = None
    accepted_deviations: list[AcceptedDeviation] | None = None
    required_checker_coverage: dict[str, str] | None = None

    def local_path_patterns(self) -> list[str]:
        return self.allow_local_path_patterns or []

    def checker_coverage(self) -> dict[str, str]:
        return self.required_checker_coverage or DEFAULT_CHECKER_COVERAGE

    def deviations(self) -> list[AcceptedDeviation]:
        return self.accepted_deviations or []

    def severity_for(self, level: str, code: str) -> str | None:
        overrides = self.severity_overrides or {}
        override = overrides.get(code)
        if not override:
            return level
        normalized = override.lower()
        if normalized not in {"error", "warning", "info", "ignore"}:
            return level
        if level == "error" and normalized != "error":
            return level
        return normalized


@dataclass(frozen=True)
class ApprovalScope:
    path: Path
    allowed: list[str]
    excluded: list[str]
    diff_base: str
    machine_readable: bool


def validate_router_manifest_schema(
    validator: "Validator",
    manifest: ManifestData | None,
    schema_version: Any,
) -> None:
    manifest_path = validator.target_path(".ai/alatyr.yaml")
    if manifest is None and manifest_path.is_file():
        manifest = parse_manifest(validator.context.text_source(manifest_path))
    if manifest is None:
        return
    manifest_schema = manifest.scalars.get(
        ("context_routing", "router_schema_version")
    )
    if (
        manifest_schema
        and not is_unresolved_value(manifest_schema.value)
        and manifest_schema.value != str(schema_version)
    ):
        validator.error(
            "ROUTER_MANIFEST_SCHEMA_DRIFT",
            "manifest router_schema_version differs from context router",
            ".ai/alatyr.yaml",
        )


class Validator:
    def __init__(
        self,
        target: Path,
        *,
        framework_source: Path | None,
        diff_ref: str | None,
        approval_records: list[Path],
        enforce_approval_scope: bool,
        change_packages: list[Path],
        enforce_change_package: bool,
        migration_diff: Path | None,
        allow_placeholders: bool,
        allow_local_paths: list[str],
        config: AdapterValidatorConfig,
        initial_findings: list[Finding] | None = None,
        validation_phase: str | None = None,
        debug_git_state: bool = False,
        debug_remote_ref: str | None = None,
        validation_scope: str = "full",
    ) -> None:
        self.target = target.resolve()
        self.context = TargetRepositoryView(self.target)
        self.unsafe_target_paths: set[str] = set()
        self.findings: list[Finding] = list(initial_findings or [])
        self.config = config
        self.framework_source = framework_source.resolve() if framework_source else None
        self.diff_ref = diff_ref
        self.enforce_approval_scope = enforce_approval_scope
        self.approval_records = self.selected_target_paths(
            approval_records, "--approval-record"
        )
        self.change_packages = self.selected_target_paths(
            change_packages, "--change-package"
        )
        self.enforce_change_package = enforce_change_package
        self.migration_diff = migration_diff.resolve() if migration_diff else None
        self.debug_git_state = debug_git_state
        self.debug_remote_ref = debug_remote_ref
        if validation_scope not in {"full", "changed"}:
            raise ValueError(f"unsupported validation scope: {validation_scope}")
        self.validation_scope = validation_scope
        self.validation_phase = validation_phase or (
            "migration-staging" if allow_placeholders else "acceptance"
        )
        if self.validation_phase not in VALIDATION_PHASES:
            raise ValueError(f"unsupported validation phase: {self.validation_phase}")
        self.allow_placeholders = self.validation_phase == "migration-staging"
        self.unresolved_active_placeholders = 0
        self.installation_state = "unverified"
        self.capability_modules: dict[str, Any] = {}
        self.allow_local_paths = allow_local_paths + config.local_path_patterns()
        self.framework_drift_detected = False
        self.target_mutations: tuple[TargetMutation, ...] = ()
        self._module_profile_cache: dict[str, list[ModuleProfileState]] | None = None
        self._scan_text_files_cache: tuple[Path, ...] | None = None

    def error(self, code: str, message: str, path: str | None = None) -> None:
        self.add_finding("error", code, message, path)

    def warn(self, code: str, message: str, path: str | None = None) -> None:
        self.add_finding("warning", code, message, path)

    def info(self, code: str, message: str, path: str | None = None) -> None:
        self.add_finding("info", code, message, path)

    def add_finding(
        self, level: str, code: str, message: str, path: str | None = None
    ) -> None:
        if self.deviation_accepts(level, code, path):
            reason = self.deviation_reason(code, path)
            suffix = f" Accepted deviation: {reason}" if reason else " Accepted deviation."
            self.findings.append(Finding("info", code, message + suffix, path))
            return
        configured_level = self.config.severity_for(level, code)
        if configured_level == "ignore":
            return
        self.findings.append(Finding(configured_level or level, code, message, path))

    def deviation_accepts(self, level: str, code: str, path: str | None) -> bool:
        if level == "error":
            return False
        for deviation in self.config.deviations():
            if deviation.code != code:
                continue
            if deviation.path and deviation.path != path:
                continue
            return True
        return False

    def deviation_reason(self, code: str, path: str | None) -> str:
        for deviation in self.config.deviations():
            if deviation.code == code and (not deviation.path or deviation.path == path):
                return deviation.reason
        return ""

    def run(self) -> list[Finding]:
        if not self.target.exists():
            self.error("TARGET_MISSING", f"target does not exist: {self.target}")
            return self.findings
        if not self.target.is_dir():
            self.error("TARGET_NOT_DIRECTORY", f"target is not a directory: {self.target}")
            return self.findings

        manifest = self.check_manifest()
        support_profile = self.manifest_support_profile(manifest)
        enabled_modules = self.enabled_modules(manifest)
        for phase in self.validation_phases(
            manifest, support_profile, enabled_modules
        ):
            phase.run()
        return self.findings

    def validation_phases(
        self,
        manifest: ManifestData | None,
        support_profile: str,
        enabled_modules: set[str],
    ) -> tuple[ValidationPhase, ...]:
        """Build the sequential phase plan without changing finding semantics."""

        def installation_state() -> None:
            validate_installation_state(self.capability_validation_context(), manifest)
            self.installation_state = target_installation_state(
                self.target, manifest, context=self.context
            )

        def operation_catalog() -> None:
            if support_profile in {"standard", "full"} or self.target_path(
                ".ai/assistant/operation-catalog.json"
            ).is_file():
                self.check_operation_catalog()

        def capabilities() -> None:
            routed_modules = self.changed_scope_modules(enabled_modules)
            dispatch_capability_checks(self, routed_modules, manifest)

        def checker_claims() -> None:
            checker_files, checker_commands = self.discover_checkers(manifest)
            self.check_checker_claims(checker_files, checker_commands)

        def engineering_evidence() -> None:
            if support_profile != "kernel" or self.target_path(
                ".ai/project/engineering-evidence/index.json"
            ).is_file():
                self.check_engineering_evidence(manifest)

        def project_knowledge() -> None:
            if support_profile != "kernel" or self.target_path(
                ".ai/project/knowledge/index.json"
            ).is_file():
                self.check_project_knowledge(manifest)

        def finalize_inputs() -> None:
            self.target_mutations = self.context.finalize()
            for mutation in self.target_mutations:
                self.error(
                    "TARGET_INPUT_MUTATED",
                    "target input changed during validation; discard these findings and rerun",
                    self.rel(mutation.path),
                )
            self.info(
                "EVIDENCE_SCOPE_CURRENT_STATE",
                "validator findings describe current structural state; historical actions "
                "require dated operation, approval, or migration records",
            )

        phases = (
            ValidationPhase("installation-state", installation_state),
            ValidationPhase("required-files", lambda: self.check_required_files(support_profile), ("installation-state",)),
            ValidationPhase("capability-closure", lambda: self.check_capability_closure(manifest), ("required-files",)),
            ValidationPhase("module-profile", lambda: self.check_module_profile_sync(manifest), ("capability-closure",)),
            ValidationPhase("bootstrap-index", self.check_bootstrap_index, ("required-files",)),
            ValidationPhase("agent-entry-packet", self.check_agent_entry_packet, ("bootstrap-index",)),
            ValidationPhase("action-authorization", self.check_action_authorization_contract, ("agent-entry-packet",)),
            ValidationPhase("context-router", lambda: self.check_router(enabled_modules, manifest), ("module-profile",)),
            ValidationPhase("task-decomposition", lambda: validate_task_decomposition(self, manifest), ("context-router",)),
            ValidationPhase("context-catalogs", lambda: validate_context_catalog_contract(self, manifest), ("context-router",)),
            ValidationPhase("support-state", lambda: validate_support_state(self.capability_validation_context(), manifest), ("installation-state",)),
            ValidationPhase("operation-catalog", operation_catalog, ("required-files",)),
            ValidationPhase("capabilities", capabilities, ("capability-closure",), "heavy"),
            ValidationPhase("module-status", lambda: self.check_enabled_module_status_claims(enabled_modules), ("capabilities",)),
            ValidationPhase("bootstrap-references", self.check_bootstrap_references, ("bootstrap-index",)),
            ValidationPhase("assistant-instructions", lambda: self.check_assistant_instruction_capabilities(manifest), ("bootstrap-references",)),
            ValidationPhase("placeholders", lambda: self.check_placeholders(manifest, support_profile, enabled_modules), ("required-files",)),
            ValidationPhase("local-paths", self.check_local_paths, ("required-files",)),
            ValidationPhase("checker-claims", checker_claims, ("required-files",), "standard"),
            ValidationPhase("approval-scope", self.check_approval_scope, ("action-authorization",)),
            ValidationPhase("engineering-evidence", engineering_evidence, ("capabilities",)),
            ValidationPhase("project-knowledge", project_knowledge, ("capabilities",)),
            ValidationPhase("change-package-index", self.check_change_package_index, ("approval-scope",)),
            ValidationPhase("change-packages", self.check_change_packages, ("change-package-index",), "standard"),
            ValidationPhase("framework-baseline", lambda: self.check_framework_baseline(manifest), ("installation-state",), "standard"),
            ValidationPhase("migration-evidence", self.check_migration_diff_evidence, ("framework-baseline",)),
            ValidationPhase("finalize-inputs", finalize_inputs, tuple(), "standard"),
        )
        known = {phase.phase_id for phase in phases}
        if len(known) != len(phases):
            raise ValueError("target validation phase IDs must be unique")
        positions = {phase.phase_id: index for index, phase in enumerate(phases)}
        for index, phase in enumerate(phases):
            unknown = set(phase.dependencies) - known
            if unknown:
                raise ValueError(
                    f"target validation phase {phase.phase_id} has unknown dependencies: {sorted(unknown)}"
                )
            unordered = {
                dependency
                for dependency in phase.dependencies
                if positions[dependency] >= index
            }
            if unordered:
                raise ValueError(
                    f"target validation phase {phase.phase_id} depends on non-prior phases: "
                    f"{sorted(unordered)}"
                )
        return phases

    def changed_scope_modules(self, enabled_modules: set[str]) -> set[str]:
        """Select optional module validators; universal checks always run."""

        if self.validation_scope == "full":
            return enabled_modules
        changed = git_changed_files(self.target, self.diff_ref)
        if changed is None:
            self.error(
                "CHANGED_VALIDATION_DIFF_UNAVAILABLE",
                "changed validation requires a resolvable Git diff; all modules were selected",
            )
            return enabled_modules
        universal_boundaries = {
            ".ai/alatyr.yaml",
            ".ai/assistant/module-profile.md",
            ".ai/assistant/context-router.json",
        }
        if any(path in universal_boundaries or path.startswith(".ai/framework/") for path in changed):
            selected = set(enabled_modules)
        else:
            selected: set[str] = set()
            product_changed = any(not path.startswith(".ai/") for path in changed)
            for module_id in enabled_modules:
                capability = self.capability_modules.get(module_id, {})
                target_files = capability.get("target_files", []) if isinstance(capability, dict) else []
                if product_changed and capability.get("module_kind") == "project-facing":
                    selected.add(module_id)
                elif any(
                    path == declared or path.startswith(str(declared).rstrip("/") + "/")
                    for path in changed
                    for declared in target_files
                    if isinstance(declared, str)
                ):
                    selected.add(module_id)
            pending = list(selected)
            while pending:
                module_id = pending.pop()
                capability = self.capability_modules.get(module_id, {})
                for dependency in capability.get("requires", []) if isinstance(capability, dict) else []:
                    if dependency in enabled_modules and dependency not in selected:
                        selected.add(dependency)
                        pending.append(dependency)
        self.info(
            "CHANGED_VALIDATION_SCOPE",
            "focused validation selected optional modules: "
            + (", ".join(sorted(selected)) if selected else "none"),
        )
        return selected

    def check_assistant_instruction_capabilities(
        self, manifest: ManifestData | None
    ) -> None:
        index_relpath = ".ai/assistant/assistant-capabilities.json"
        if not self.target_path(index_relpath).is_file():
            return
        index = self.load_json_object(
            self.target_path(index_relpath), "ASSISTANT_CAPABILITY_INDEX"
        )
        if isinstance(index, dict):
            if index.get("schema_version") != CAPABILITY_INDEX_SCHEMA_VERSION:
                self.error(
                    "ASSISTANT_CAPABILITY_INDEX_SCHEMA",
                    "assistant capability index schema_version should be "
                    f"{CAPABILITY_INDEX_SCHEMA_VERSION}",
                    index_relpath,
                )
            state_evidence = index.get("state_evidence")
            if not isinstance(state_evidence, dict):
                self.error(
                    "ASSISTANT_CAPABILITY_INDEX_STATE",
                    "assistant capability index requires state_evidence",
                    index_relpath,
                )
            else:
                for field in sorted(INDEX_STATE_EVIDENCE_STRING_FIELDS):
                    value = state_evidence.get(field)
                    if not isinstance(value, str) or not value.strip():
                        self.error(
                            "ASSISTANT_CAPABILITY_INDEX_STATE",
                            f"assistant capability index state_evidence.{field} must be recorded",
                            index_relpath,
                        )
                for field in sorted(INDEX_STATE_EVIDENCE_TRUE_FIELDS):
                    if state_evidence.get(field) is not True:
                        self.error(
                            "ASSISTANT_CAPABILITY_INDEX_STATE",
                            f"assistant capability index state_evidence.{field} must be true",
                            index_relpath,
                        )
        surfaces = index.get("surfaces") if isinstance(index, dict) else None
        if not isinstance(surfaces, dict) or not surfaces:
            self.error(
                "ASSISTANT_CAPABILITY_SURFACES",
                "assistant capability index requires surface records",
                index_relpath,
            )
            return

        selected = {
            scalar.value
            for scalar in manifest.lists.get(("supported_assistants",), [])
            if is_concrete_capability_value(scalar.value)
        } if manifest is not None else set()
        unknown_selected = sorted(selected - set(surfaces))
        if unknown_selected:
            self.error(
                "ASSISTANT_CAPABILITY_SELECTED_MISSING",
                f"selected assistants lack capability records: {unknown_selected}",
                index_relpath,
            )

        evidence_fields = {
            "verified_at",
            "client_version",
            "evidence",
            "expires_at",
            "review_triggers",
        }
        sections = {
            "instruction_loading": {
                "route",
                "runtime_variant",
                "selected_entry_path",
                "competing_sources",
                "auto_load_observed",
                "precedence_evidence",
                "configuration_state",
            },
            "skills": {
                "route",
                "discovery_paths",
                "selected_source",
                "activation_mode",
            },
            "tool_permissions": {
                "client_permission_mode",
                "effective_restrictions",
                "alatyr_authorization_separate",
            },
            "context_caching": {
                "route",
                "provider",
                "model",
                "provider_cache_mode",
                "client_control_exposure",
                "client_telemetry_exposure",
                "retention",
                "minimum_cacheable_tokens",
                "stable_prefix_ordering",
                "context_window_reduction",
                "fallback",
            },
        }
        for surface_id, relpath in surfaces.items():
            if not isinstance(surface_id, str) or not isinstance(relpath, str):
                self.error(
                    "ASSISTANT_CAPABILITY_INDEX_ENTRY",
                    "assistant capability index entries must map IDs to paths",
                    index_relpath,
                )
                continue
            expected_relpath = capability_record_path(surface_id)
            if relpath != expected_relpath:
                self.error(
                    "ASSISTANT_CAPABILITY_INDEX_ENTRY",
                    f"assistant capability index entry for {surface_id} must be {expected_relpath}",
                    index_relpath,
                )
            record = self.load_json_object(
                self.target_path(relpath), "ASSISTANT_SURFACE_CAPABILITIES"
            )
            if record is None:
                continue
            if record.get("schema_version") != SURFACE_CAPABILITY_SCHEMA_VERSION:
                self.error(
                    "ASSISTANT_CAPABILITY_SCHEMA",
                    f"assistant surface {surface_id} must use capability schema "
                    f"{SURFACE_CAPABILITY_SCHEMA_VERSION}",
                    relpath,
                )
            if record.get("assistant_surface") != surface_id:
                self.error(
                    "ASSISTANT_CAPABILITY_ID",
                    f"assistant surface record identity must be {surface_id}",
                    relpath,
                )
            surface_state = record.get("surface_state")
            if not isinstance(surface_state, dict):
                self.error(
                    "ASSISTANT_CAPABILITY_STATE",
                    f"assistant surface {surface_id} lacks surface_state",
                    relpath,
                )
            else:
                missing_state = sorted(SURFACE_STATE_FIELDS - set(surface_state))
                if missing_state:
                    self.error(
                        "ASSISTANT_CAPABILITY_STATE_FIELDS",
                        f"assistant surface {surface_id} surface_state is missing {missing_state}",
                        relpath,
                    )
                overall = surface_state.get("overall")
                selected_for_target = surface_state.get("selected_for_target")
                evidence_state = surface_state.get("evidence_state")
                verified_for_target = surface_state.get("verified_for_target")
                advertised_by_surface = surface_state.get("advertised_by_surface")
                overall_state = str(overall).casefold()
                selected_state = str(selected_for_target).casefold()
                evidence_state_value = str(evidence_state).casefold()
                if (
                    is_concrete_capability_value(overall)
                    and overall_state not in OVERALL_STATES
                ):
                    self.error(
                        "ASSISTANT_CAPABILITY_STATE_VALUE",
                        f"assistant surface {surface_id} overall state is invalid",
                        relpath,
                    )
                for label, value in [
                    ("selected_for_target", selected_for_target),
                    ("advertised_by_surface", advertised_by_surface),
                    ("verified_for_target", verified_for_target),
                ]:
                    if (
                        is_concrete_capability_value(value)
                        and str(value).casefold() not in YES_NO_UNKNOWN
                    ):
                        self.error(
                            "ASSISTANT_CAPABILITY_STATE_VALUE",
                            f"assistant surface {surface_id} {label} must be yes, no, or unknown",
                            relpath,
                        )
                if (
                    is_concrete_capability_value(evidence_state)
                    and evidence_state_value not in EVIDENCE_STATES
                ):
                    self.error(
                        "ASSISTANT_CAPABILITY_STATE_VALUE",
                        f"assistant surface {surface_id} evidence_state is invalid",
                        relpath,
                    )
                for list_field in ["limitations", "review_triggers"]:
                    value = surface_state.get(list_field)
                    if not isinstance(value, list) or not value:
                        self.error(
                            "ASSISTANT_CAPABILITY_STATE_LIST",
                            f"assistant surface {surface_id} surface_state.{list_field} must be a list",
                            relpath,
                        )
                if surface_id in selected:
                    if selected_state == "no":
                        self.error(
                            "ASSISTANT_SELECTED_STATE_CONFLICT",
                            f"selected assistant {surface_id} is marked not selected in capability state",
                            relpath,
                        )
                    if overall_state == "unsupported":
                        self.error(
                            "ASSISTANT_SELECTED_UNSUPPORTED",
                            f"selected assistant {surface_id} has unsupported capability state",
                            relpath,
                        )
                    if is_concrete_capability_value(evidence_state) and evidence_state_value in {
                        "stale",
                        "expired",
                        "unverified",
                        "unknown",
                    }:
                        self.warn(
                            "ASSISTANT_CAPABILITY_STATE_UNVERIFIED",
                            f"selected assistant {surface_id} capability evidence is {evidence_state_value}",
                            relpath,
                        )
            for section_name, required in sections.items():
                section = record.get(section_name)
                self.check_assistant_capability_section(
                    surface_id,
                    section_name,
                    section,
                    required | evidence_fields,
                    relpath,
                )

            loading = record.get("instruction_loading")
            if isinstance(loading, dict):
                route = loading.get("route")
                route_state = str(route).casefold()
                if (
                    is_concrete_capability_value(route)
                    and route_state not in {"supported", "unsupported", "unknown"}
                ):
                    self.error(
                        "ASSISTANT_INSTRUCTION_ROUTE",
                        f"assistant surface {surface_id} instruction route is invalid",
                        relpath,
                    )
                if surface_id in selected:
                    if route_state == "unsupported":
                        self.error(
                            "ASSISTANT_SELECTED_UNSUPPORTED",
                            f"selected assistant {surface_id} has an unsupported instruction route",
                            relpath,
                        )
                    elif route_state != "supported":
                        self.warn(
                            "ASSISTANT_INSTRUCTION_LOADING_UNVERIFIED",
                            f"selected assistant {surface_id} has no verified instruction-loading evidence",
                            relpath,
                        )
                    else:
                        entry = loading.get("selected_entry_path")
                        observed = str(loading.get("auto_load_observed", "")).casefold()
                        if (
                            not is_concrete_capability_value(entry)
                            or not self.target_path(str(entry)).is_file()
                        ):
                            self.error(
                                "ASSISTANT_SELECTED_ENTRY_MISSING",
                                f"selected assistant {surface_id} has no existing instruction entry",
                                relpath,
                            )
                        if observed not in {"yes", "true"}:
                            self.error(
                                "ASSISTANT_AUTO_LOAD_UNPROVEN",
                                f"selected assistant {surface_id} claims support without observed auto-load",
                                relpath,
                            )
            permissions = record.get("tool_permissions")
            if not isinstance(permissions, dict) or permissions.get(
                "alatyr_authorization_separate"
            ) is not True:
                self.error(
                    "ASSISTANT_PERMISSION_AUTHORIZATION_CONFLICT",
                    f"assistant surface {surface_id} must keep client permissions separate from Alatyr authorization",
                    relpath,
                )
            caching = record.get("context_caching")
            if isinstance(caching, dict):
                self.check_context_caching_capability(surface_id, caching, relpath)

    def check_assistant_capability_section(
        self,
        surface_id: str,
        section_name: str,
        section: Any,
        required: set[str],
        relpath: str,
    ) -> None:
        if not isinstance(section, dict):
            self.error(
                "ASSISTANT_CAPABILITY_SECTION",
                f"assistant surface {surface_id} lacks {section_name}",
                relpath,
            )
            return
        missing = sorted(required - set(section))
        if missing:
            self.error(
                "ASSISTANT_CAPABILITY_FIELDS",
                f"assistant surface {surface_id} {section_name} is missing {missing}",
                relpath,
            )
        review_triggers = section.get("review_triggers")
        if not isinstance(review_triggers, list) or not review_triggers:
            self.error(
                "ASSISTANT_CAPABILITY_REVIEW_TRIGGERS",
                f"assistant surface {surface_id} {section_name} needs review triggers",
                relpath,
            )
        for list_field in ["competing_sources", "discovery_paths"]:
            if list_field in section and not isinstance(section.get(list_field), list):
                self.error(
                    "ASSISTANT_CAPABILITY_LIST",
                    f"assistant surface {surface_id} {list_field} must be a list",
                    relpath,
                )

    def check_context_caching_capability(
        self, surface_id: str, caching: dict[str, Any], relpath: str
    ) -> None:
        cache_route = caching.get("route")
        provider_mode = caching.get("provider_cache_mode")
        control_exposure = caching.get("client_control_exposure")
        telemetry_exposure = caching.get("client_telemetry_exposure")
        for label, value, allowed in [
            ("route", cache_route, CACHE_ROUTE_STATES),
            ("provider_cache_mode", provider_mode, CACHE_PROVIDER_MODES),
            ("client_control_exposure", control_exposure, CACHE_EXPOSURE_STATES),
            ("client_telemetry_exposure", telemetry_exposure, CACHE_EXPOSURE_STATES),
        ]:
            if (
                is_concrete_capability_value(value)
                and str(value).casefold() not in allowed
            ):
                self.error(
                    "ASSISTANT_CONTEXT_CACHE_VALUE",
                    f"assistant surface {surface_id} context_caching.{label} is invalid",
                    relpath,
                )
        if caching.get("stable_prefix_ordering") is not True:
            self.error(
                "ASSISTANT_CONTEXT_CACHE_PREFIX",
                f"assistant surface {surface_id} must preserve stable-prefix ordering",
                relpath,
            )
        if caching.get("context_window_reduction") is not False:
            self.error(
                "ASSISTANT_CONTEXT_CACHE_WINDOW_CLAIM",
                f"assistant surface {surface_id} must not claim caching reduces context-window occupancy",
                relpath,
            )
        if caching.get("fallback") != CACHE_FALLBACK:
            self.error(
                "ASSISTANT_CONTEXT_CACHE_FALLBACK",
                f"assistant surface {surface_id} must use {CACHE_FALLBACK} when caching is unavailable",
                relpath,
            )
        if (
            str(cache_route).casefold() == "supported"
            and str(provider_mode).casefold() == "explicit"
            and str(control_exposure).casefold() != "supported"
        ):
            self.error(
                "ASSISTANT_CONTEXT_CACHE_CONTROL",
                f"assistant surface {surface_id} cannot claim explicit-only caching without client controls",
                relpath,
            )
        route_state = str(cache_route).casefold()
        mode_state = str(provider_mode).casefold()
        if (
            route_state == "supported" and mode_state in {"unsupported", "unknown"}
        ) or (
            route_state == "unsupported"
            and mode_state in {"automatic", "explicit", "both"}
        ):
            self.error(
                "ASSISTANT_CONTEXT_CACHE_STATE_CONFLICT",
                f"assistant surface {surface_id} cache route and provider mode conflict",
                relpath,
            )

    def target_path(self, relpath: str) -> Path:
        candidate = self.target / relpath
        try:
            self.context.resolve_path(candidate)
        except (OSError, TargetPathEscapeError) as exc:
            label = str(relpath)
            if label not in self.unsafe_target_paths:
                self.unsafe_target_paths.add(label)
                self.error(
                    "TARGET_PATH_ESCAPE",
                    f"target-relative path is unsafe: {exc}",
                    label,
                )
            digest = hashlib.sha256(label.encode("utf-8")).hexdigest()
            return self.target / ".ai" / ".invalid-target-path" / digest
        return candidate

    def selected_target_paths(self, paths: list[Path], option: str) -> list[Path]:
        selected: list[Path] = []
        for path in paths:
            label = str(path)
            candidate = path if path.is_absolute() else self.target / path
            try:
                resolved = self.context.resolve_path(candidate)
            except (OSError, TargetPathEscapeError) as exc:
                if label not in self.unsafe_target_paths:
                    self.unsafe_target_paths.add(label)
                    self.error(
                        "TARGET_PATH_ESCAPE",
                        f"{option} must stay inside the target: {exc}",
                        label,
                    )
                continue
            selected.append(resolved)
        return selected

    def rel(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.target).as_posix()
        except ValueError:
            return str(path)

    def read_text(self, path: Path) -> str:
        try:
            return self.context.read_text(path)
        except (OSError, TargetPathEscapeError) as exc:
            label = self.rel(path)
            if label not in self.unsafe_target_paths:
                self.unsafe_target_paths.add(label)
                self.error("TARGET_PATH_ESCAPE", str(exc), label)
            return ""

    def read_bytes(self, path: Path) -> bytes:
        try:
            return self.context.read_bytes(path)
        except (OSError, TargetPathEscapeError) as exc:
            label = self.rel(path)
            if label not in self.unsafe_target_paths:
                self.unsafe_target_paths.add(label)
                self.error("TARGET_PATH_ESCAPE", str(exc), label)
            return b""

    def module_validation_enabled(
        self,
        module_id: str,
        undeclared_code: str,
        state_missing_code: str,
        display_name: str,
    ) -> bool:
        module_relpath = ".ai/assistant/module-profile.md"
        module_path = self.target_path(module_relpath)
        if not module_path.is_file():
            return False
        declarations = self._parsed_module_profile().get(module_id, [])
        state = declarations[0] if declarations else ModuleProfileState(module_id, False, None)
        if not state.declared:
            self.module_profile_undeclared_warning(
                module_id, undeclared_code, display_name, module_relpath
            )
            return False
        if not state.has_parseable_state:
            self.module_profile_state_missing_warning(
                module_id, state_missing_code, display_name, module_relpath
            )
            return False
        return state.validation_enabled

    def _parsed_module_profile(self) -> dict[str, list[ModuleProfileState]]:
        if self._module_profile_cache is not None:
            return self._module_profile_cache
        module_path = self.target_path(".ai/assistant/module-profile.md")
        self._module_profile_cache = (
            parse_module_profile(self.read_text(module_path))
            if module_path.is_file()
            else {}
        )
        return self._module_profile_cache

    def module_profile_undeclared_warning(
        self,
        module_id: str,
        fallback_code: str,
        display_name: str,
        module_relpath: str,
    ) -> None:
        message = f"module profile does not declare {display_name} state"
        if module_id == "diagrams":
            self.warn("DIAGRAM_MODULE_UNDECLARED", message, module_relpath)
        elif module_id == "architecture-knowledge":
            self.warn("ARCHITECTURE_MODULE_UNDECLARED", message, module_relpath)
        elif module_id == "code-documentation":
            self.warn("CODEDOC_MODULE_UNDECLARED", message, module_relpath)
        elif module_id == "project-vocabulary":
            self.warn("VOCABULARY_MODULE_UNDECLARED", message, module_relpath)
        elif module_id == "test-first-development":
            self.warn("TDD_MODULE_UNDECLARED", message, module_relpath)
        elif module_id == "extensions":
            self.warn("EXTENSION_MODULE_UNDECLARED", message, module_relpath)
        else:
            self.warn(fallback_code, message, module_relpath)

    def module_profile_state_missing_warning(
        self,
        module_id: str,
        fallback_code: str,
        display_name: str,
        module_relpath: str,
    ) -> None:
        message = f"{display_name} module has no parseable State field"
        if module_id == "diagrams":
            self.warn("DIAGRAM_MODULE_STATE_MISSING", message, module_relpath)
        elif module_id == "architecture-knowledge":
            self.warn("ARCHITECTURE_MODULE_STATE_MISSING", message, module_relpath)
        elif module_id == "code-documentation":
            self.warn("CODEDOC_MODULE_STATE_MISSING", message, module_relpath)
        elif module_id == "project-vocabulary":
            self.warn("VOCABULARY_MODULE_STATE_MISSING", message, module_relpath)
        elif module_id == "test-first-development":
            self.warn("TDD_MODULE_STATE_MISSING", message, module_relpath)
        elif module_id == "extensions":
            self.warn("EXTENSION_MODULE_STATE_MISSING", message, module_relpath)
        else:
            self.warn(fallback_code, message, module_relpath)

    def capability_validation_context(self) -> CapabilityValidationContext:
        """Expose the stable, narrow host interface used by capability modules."""

        return CapabilityValidationContext(
            filesystem=self.context,
            findings=self,
            allow_placeholders=self.allow_placeholders,
            resolve_target_path=self.target_path,
            read_target_text=self.read_text,
            load_target_json_object=self.load_json_object,
            check_target_reference=self.check_optional_target_reference,
            check_action_modes=self.check_allowed_actions,
            relative_target_path=self.rel,
            module_enabled=self.module_validation_enabled,
        )

    def manifest_support_profile(self, manifest: ManifestData | None) -> str:
        if manifest is None:
            return "full"
        scalar = manifest.scalars.get(("installation", "support_profile"))
        if scalar and scalar.value in SUPPORT_PROFILES:
            return scalar.value
        return "full"

    def enabled_modules(self, manifest: ManifestData | None) -> set[str]:
        """Return enabled modules from the manifest and legacy human profile."""

        enabled: set[str] = set()
        if manifest is not None:
            enabled.update(
                scalar.value
                for scalar in manifest.lists.get(("modules", "enabled"), [])
                if not is_unresolved_value(scalar.value)
            )

        profile_path = self.target_path(".ai/assistant/module-profile.md")
        if not profile_path.is_file():
            return enabled
        for module_id, declarations in self._parsed_module_profile().items():
            if declarations and declarations[0].validation_enabled:
                enabled.add(module_id)
        return enabled

    def module_profile_states(self) -> dict[str, list[str]]:
        profile_path = self.target_path(".ai/assistant/module-profile.md")
        if not profile_path.is_file():
            return {}
        return {
            module_id: [declaration.state or "missing" for declaration in declarations]
            for module_id, declarations in self._parsed_module_profile().items()
        }

    def check_module_profile_sync(self, manifest: ManifestData | None) -> None:
        if manifest is None:
            return
        manifest_enabled = {
            scalar.value
            for scalar in manifest.lists.get(("modules", "enabled"), [])
            if not is_unresolved_value(scalar.value)
        }
        profile_states = self.module_profile_states()
        for module_id, states in sorted(profile_states.items()):
            if len(states) > 1:
                self.error(
                    "MODULE_PROFILE_DUPLICATE",
                    f"module {module_id} has {len(states)} profile blocks",
                    ".ai/assistant/module-profile.md",
                )
            if (
                states
                and states[0] in {"enabled", "required"}
                and module_id not in self.capability_modules
            ):
                self.error(
                    "MODULE_PROFILE_UNKNOWN",
                    f"module profile names unknown capability {module_id}",
                    ".ai/assistant/module-profile.md",
                )

        for module_id in sorted(manifest_enabled):
            states = profile_states.get(module_id, [])
            if not states:
                self.error(
                    "MODULE_PROFILE_ENABLED_MISSING",
                    f"manifest-enabled module {module_id} has no module-profile block",
                    ".ai/assistant/module-profile.md",
                )
                continue
            if states[0] not in {"enabled", "required"}:
                self.error(
                    "MODULE_PROFILE_STATE_DRIFT",
                    f"manifest enables {module_id}, but module profile state is {states[0]}",
                    ".ai/assistant/module-profile.md",
                )

        for module_id, states in sorted(profile_states.items()):
            if states and states[0] in {"enabled", "required"} and module_id not in manifest_enabled:
                self.error(
                    "MODULE_MANIFEST_ENABLED_MISSING",
                    f"module profile enables {module_id}, but manifest modules.enabled does not",
                    ".ai/alatyr.yaml",
                )

    def check_required_files(self, support_profile: str) -> None:
        for relpath in required_files_for_support_profile(support_profile):
            if not self.target_path(relpath).exists():
                self.error("REQUIRED_FILE_MISSING", "required adapter file is missing", relpath)

        framework_dir = self.target_path(".ai/framework")
        if not framework_dir.is_dir():
            self.error(
                "FRAMEWORK_DIR_MISSING",
                "installed adapter has no .ai/framework directory",
                ".ai/framework",
            )
        elif not self.target_path(".ai/framework/rule-registry.json").is_file():
            self.error(
                "RULE_REGISTRY_MISSING",
                "installed framework copy has no rule-registry.json",
                ".ai/framework/rule-registry.json",
            )

    def check_manifest(self) -> ManifestData | None:
        path = self.target_path(".ai/alatyr.yaml")
        if not path.is_file():
            return None

        manifest_source = self.context.text_source(path)
        manifest = parse_manifest(manifest_source)
        for failure in manifest.parse_failures:
            self.error("MANIFEST_PARSE", failure, ".ai/alatyr.yaml")
        try:
            manifest_object = load_manifest_object(manifest_source)
            schema = json.loads(ADAPTER_MANIFEST_SCHEMA.read_text(encoding="utf-8"))
            schema_errors = sorted(
                jsonschema.Draft7Validator(schema).iter_errors(manifest_object),
                key=lambda error: list(error.absolute_path),
            )
            for error in schema_errors:
                location = ".".join(str(item) for item in error.absolute_path) or "root"
                self.error(
                    "MANIFEST_SCHEMA",
                    f"{location}: {error.message}",
                    ".ai/alatyr.yaml",
                )
        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
            jsonschema.SchemaError,
        ) as exc:
            self.error(
                "MANIFEST_SCHEMA_UNAVAILABLE",
                f"cannot validate adapter manifest schema: {exc}",
                ".ai/alatyr.yaml",
            )

        support_scalar = manifest.scalars.get(("installation", "support_profile"))
        support_profile = support_scalar.value if support_scalar else "full"
        required_scalars = set(KERNEL_MANIFEST_REQUIRED_SCALARS)
        if support_profile in {"core", "standard", "full"}:
            required_scalars.update(CORE_PLUS_MANIFEST_SCALARS)
        if support_profile in {"standard", "full"}:
            required_scalars.update(MANIFEST_STANDARD_REQUIRED_SCALARS)
        if support_profile == "full":
            required_scalars.update(MANIFEST_FULL_REQUIRED_SCALARS)

        for key in sorted(required_scalars):
            scalar = manifest.scalars.get(key)
            if not scalar:
                self.error(
                    "MANIFEST_FIELD_MISSING",
                    f"missing scalar {dotted(key)}",
                    ".ai/alatyr.yaml",
                )
                continue
            if is_unresolved_value(scalar.value):
                report = self.warn if self.allow_placeholders else self.error
                report(
                    "MANIFEST_FIELD_UNRESOLVED",
                    f"{dotted(key)} is unresolved",
                    f".ai/alatyr.yaml:{scalar.line}",
                )

        if support_scalar and not is_unresolved_value(support_scalar.value):
            if support_scalar.value not in SUPPORT_PROFILES:
                self.error(
                    "MANIFEST_SUPPORT_PROFILE",
                    "installation.support_profile must be kernel, core, standard, or full",
                    f".ai/alatyr.yaml:{support_scalar.line}",
                )

        state_scalar = manifest.scalars.get(("installation", "state"))
        if (
            state_scalar
            and not is_unresolved_value(state_scalar.value)
            and state_scalar.value in INSTALLATION_STATES
        ):
            self.installation_state = state_scalar.value

        pack_scalar = manifest.scalars.get(("framework", "pack"))
        if pack_scalar and not is_unresolved_value(pack_scalar.value):
            if pack_scalar.value not in {"kernel", "core", "standard", "complete"}:
                self.error(
                    "MANIFEST_FRAMEWORK_PACK",
                    "framework.pack must be kernel, core, standard, or complete",
                    f".ai/alatyr.yaml:{pack_scalar.line}",
                )
            elif support_scalar and support_scalar.value in SUPPORT_PROFILES:
                minimum_pack = PROFILE_MIN_PACK[support_scalar.value]
                if (
                    FRAMEWORK_PACK_RANK[pack_scalar.value]
                    < FRAMEWORK_PACK_RANK[minimum_pack]
                ):
                    self.error(
                        "MANIFEST_FRAMEWORK_PACK",
                        "framework.pack is too small for installation.support_profile",
                        f".ai/alatyr.yaml:{pack_scalar.line}",
                    )

        numeric_context_fields = [
            ("context_routing", "router_schema_version"),
            ("context_routing", "recursive_index_schema_version"),
            ("context_routing", "recursive_index_max_depth"),
            ("context_routing", "semantic_codebook_schema_version"),
            ("context_routing", "context_packet_schema_version"),
            ("context_routing", "agent_entry_packet_schema_version"),
            ("context_routing", "bootstrap_max_files"),
            ("context_routing", "bootstrap_max_words"),
            ("context_routing", "profile_default_max_files"),
            ("context_routing", "profile_default_max_total_words"),
            ("context_routing", "profile_default_max_portable_words"),
            ("context_routing", "profile_default_reserved_target_words"),
        ]
        numeric_values: dict[PathKey, int] = {}
        for key in numeric_context_fields:
            scalar = manifest.scalars.get(key)
            if not scalar or is_unresolved_value(scalar.value):
                continue
            try:
                value = int(scalar.value)
            except ValueError:
                self.error(
                    "MANIFEST_CONTEXT_BUDGET",
                    f"{dotted(key)} must be a positive integer",
                    f".ai/alatyr.yaml:{scalar.line}",
                )
                continue
            if value <= 0:
                self.error(
                    "MANIFEST_CONTEXT_BUDGET",
                    f"{dotted(key)} must be a positive integer",
                    f".ai/alatyr.yaml:{scalar.line}",
                )
            numeric_values[key] = value

        router_schema = numeric_values.get(("context_routing", "router_schema_version"))
        if router_schema not in ROUTER_SCHEMA_VERSIONS:
            self.error(
                "MANIFEST_CONTEXT_SCHEMA",
                "context_routing.router_schema_version must be 2 through 10",
                ".ai/alatyr.yaml",
            )
        expected_context_paths = {
            ("source_of_truth", "agent_entry_packet"): PACKET_PATH.as_posix(),
            ("context_routing", "agent_entry_packet"): PACKET_PATH.as_posix(),
        }
        for key, expected in expected_context_paths.items():
            scalar = manifest.scalars.get(key)
            if scalar and not is_unresolved_value(scalar.value) and scalar.value != expected:
                self.error(
                    "MANIFEST_CONTEXT_PATH",
                    f"{dotted(key)} must be {expected}",
                    f".ai/alatyr.yaml:{scalar.line}",
                )
        total = numeric_values.get(("context_routing", "profile_default_max_total_words"))
        portable = numeric_values.get(("context_routing", "profile_default_max_portable_words"))
        reserved = numeric_values.get(("context_routing", "profile_default_reserved_target_words"))
        if all(isinstance(value, int) for value in [total, portable, reserved]):
            if portable + reserved > total:
                self.error(
                    "MANIFEST_CONTEXT_BUDGET",
                    "portable plus reserved target words exceeds total words",
                    ".ai/alatyr.yaml",
                )

        for key in sorted(MANIFEST_PATH_SCALARS):
            scalar = manifest.scalars.get(key)
            if not scalar:
                continue
            value = scalar.value
            if not value.startswith(".ai/"):
                self.error(
                    "MANIFEST_PATH_NOT_AI",
                    f"{dotted(key)} should point inside .ai/, got {value}",
                    f".ai/alatyr.yaml:{scalar.line}",
                )
                continue
            if not self.target_path(value).exists():
                self.error(
                    "MANIFEST_PATH_MISSING",
                    f"{dotted(key)} points to missing path {value}",
                    f".ai/alatyr.yaml:{scalar.line}",
                )

        backup_owner = manifest.scalars.get(("owner", "backup_owner"))
        if backup_owner and is_unresolved_value(backup_owner.value):
            report = self.warn if self.allow_placeholders else self.error
            report(
                "BACKUP_OWNER_UNRESOLVED",
                "backup owner must be resolved or recorded as an explicit known gap",
                f".ai/alatyr.yaml:{backup_owner.line}",
            )

        return manifest

    def check_capability_closure(self, manifest: ManifestData | None) -> None:
        if manifest is None:
            return
        enabled = [
            scalar.value
            for scalar in manifest.lists.get(("modules", "enabled"), [])
            if not is_unresolved_value(scalar.value)
        ]
        if not enabled:
            return

        catalog_path = self.target_path(".ai/framework/capabilities.json")
        catalog = self.load_json_object(catalog_path, "CAPABILITY_CATALOG")
        if catalog is None:
            self.error(
                "CAPABILITY_CATALOG_MISSING",
                "enabled modules require the installed capability catalog",
                ".ai/framework/capabilities.json",
            )
            return
        modules = catalog.get("modules")
        if (
            catalog.get("schema_version") != 1
            or catalog.get("capability_kind") != "alatyr-optional-module-catalog"
            or not isinstance(modules, dict)
        ):
            self.error(
                "CAPABILITY_CATALOG_INVALID",
                "installed capability catalog schema or kind is invalid",
                ".ai/framework/capabilities.json",
            )
            return
        self.capability_modules = modules

        enabled_set = set(enabled)
        pack_scalar = manifest.scalars.get(("framework", "pack"))
        selected_pack = pack_scalar.value if pack_scalar else "complete"
        pack_rank = {"core": 0, "standard": 1, "complete": 2}
        for module_id in sorted(enabled_set):
            contract = modules.get(module_id)
            if not isinstance(contract, dict):
                self.error(
                    "CAPABILITY_MODULE_UNKNOWN",
                    f"enabled module is absent from capability catalog: {module_id}",
                    ".ai/alatyr.yaml",
                )
                continue
            missing_dependencies = sorted(
                set(contract.get("requires", [])) - enabled_set
            )
            if missing_dependencies:
                self.error(
                    "CAPABILITY_DEPENDENCY_MISSING",
                    f"enabled module {module_id} requires {missing_dependencies}",
                    ".ai/alatyr.yaml",
                )
            minimum_pack = contract.get("min_framework_pack")
            if (
                selected_pack in pack_rank
                and minimum_pack in pack_rank
                and pack_rank[selected_pack] < pack_rank[minimum_pack]
            ):
                self.error(
                    "CAPABILITY_PACK_TOO_SMALL",
                    f"module {module_id} requires framework pack {minimum_pack}",
                    ".ai/alatyr.yaml",
                )
            for filename in contract.get("framework_files", []):
                relpath = f".ai/framework/{filename}"
                if not self.target_path(relpath).is_file():
                    self.error(
                        "CAPABILITY_FRAMEWORK_FILE_MISSING",
                        f"module {module_id} requires installed framework file {filename}",
                        relpath,
                    )
            for relpath in contract.get("target_files", []):
                if not self.target_path(relpath).is_file():
                    self.error(
                        "CAPABILITY_TARGET_FILE_MISSING",
                        f"module {module_id} requires target adapter file {relpath}",
                        relpath,
                    )

    def check_bootstrap_index(self) -> None:
        relpath = BOOTSTRAP_PATH.as_posix()
        path = self.target_path(relpath)
        if not path.is_file():
            self.error(
                "BOOTSTRAP_INDEX_MISSING",
                "compact bootstrap index is missing",
                relpath,
            )
            return
        actual, error = self.context.read_json(path)
        if error is not None or not isinstance(actual, dict):
            self.error(
                "BOOTSTRAP_INDEX_INVALID",
                f"compact bootstrap index is invalid: {error or 'root is not an object'}",
                relpath,
            )
            return
        try:
            expected = build_from_target(self.target)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            self.error(
                "BOOTSTRAP_INDEX_SOURCE_INVALID",
                f"cannot derive compact bootstrap index: {exc}",
                relpath,
            )
            return
        for error in generation_provenance_errors(
            actual.get("generated_by"),
        ):
            self.error("BOOTSTRAP_INDEX_PROVENANCE", error, relpath)
        if not generated_json_equivalent(json.dumps(expected), json.dumps(actual)):
            self.error(
                "BOOTSTRAP_INDEX_DRIFT",
                "compact bootstrap index differs from its canonical manifest, project map, or router sources",
                relpath,
            )
            return
        self.info(
            "BOOTSTRAP_INDEX_CURRENT",
            "compact bootstrap index matches its canonical source hashes and routing projection",
            relpath,
        )

    def check_agent_entry_packet(self) -> None:
        relpath = PACKET_PATH.as_posix()
        path = self.target_path(relpath)
        if not path.is_file():
            self.error(
                "ENTRY_PACKET_MISSING",
                "compact agent entry packet is missing",
                relpath,
            )
            return
        try:
            actual_text = self.read_text(path)
            actual = json.loads(actual_text)
            expected_text = render_entry_packet(build_entry_packet(self.target))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            self.error("ENTRY_PACKET_INVALID", str(exc), relpath)
            return
        for error in generation_provenance_errors(
            actual.get("generated_by"),
        ):
            self.error("ENTRY_PACKET_PROVENANCE", error, relpath)
        if not generated_json_equivalent(expected_text, actual_text):
            self.error(
                "ENTRY_PACKET_STALE",
                "compact agent entry packet differs from canonical target sources",
                relpath,
            )
            return
        if (
            not isinstance(actual, dict)
            or actual.get("schema_version") != 2
            or actual.get("packet_kind") != "target-agent-entry-packet"
        ):
            self.error(
                "ENTRY_PACKET_SCHEMA",
                "entry packet schema or kind is invalid",
                relpath,
            )
            return
        routing_sources = actual.get("routing_sources")
        if not isinstance(routing_sources, dict) or routing_sources.get(
            "installed_profile_routes"
        ) != ".ai/assistant/bootstrap-index.json":
            self.warn(
                "ENTRY_PACKET_PROFILE_RECOMMENDATION",
                "entry packet should route installed profiles through the bootstrap index",
                relpath,
            )
        delta = actual.get("support_delta_first")
        if not isinstance(delta, dict) or "tools/alatyr.py support-delta" not in json.dumps(
            delta,
            sort_keys=True,
        ):
            self.warn(
                "ENTRY_PACKET_SUPPORT_DELTA",
                "entry packet should route support review through delta-first evidence",
                relpath,
            )
        lazy = actual.get("lazy_human_fallbacks")
        if not isinstance(lazy, list) or ".ai/assistant/help-reference.md" not in lazy:
            self.warn(
                "ENTRY_PACKET_LAZY_REFERENCES",
                "entry packet should keep full human references lazy",
                relpath,
            )
        self.info(
            "ENTRY_PACKET_CURRENT",
            "compact agent entry packet matches canonical target sources",
            relpath,
        )

    def check_router(
        self,
        enabled_modules: set[str] | None = None,
        manifest: ManifestData | None = None,
    ) -> None:
        router_path = self.target_path(".ai/assistant/context-router.json")
        profiles_path = self.target_path(".ai/assistant/context-profiles.md")
        if not router_path.is_file():
            return

        router, router_error = self.context.read_json(router_path)
        if router_error is not None:
            self.error(
                "ROUTER_INVALID_JSON",
                router_error,
                ".ai/assistant/context-router.json",
            )
            return
        if not isinstance(router, dict):
            self.error(
                "ROUTER_INVALID_SHAPE",
                "context router must be a JSON object",
                ".ai/assistant/context-router.json",
            )
            return
        if router.get("router_kind") != "target-context-router":
            self.error(
                "ROUTER_KIND",
                "router_kind should be target-context-router",
                ".ai/assistant/context-router.json",
            )
        schema_version = router.get("schema_version")
        if schema_version == 1:
            self.warn(
                "ROUTER_SCHEMA_LEGACY",
                "context router schema 1 should migrate to task-classification routing schema 10",
                ".ai/assistant/context-router.json",
            )
        elif schema_version not in ROUTER_SCHEMA_VERSIONS:
            self.error(
                "ROUTER_SCHEMA",
                "context router schema_version should be 2 through 10",
                ".ai/assistant/context-router.json",
            )
        validate_router_manifest_schema(self, manifest, schema_version)
        if router.get("human_reference") != ".ai/assistant/context-profiles.md":
            self.error(
                "ROUTER_HUMAN_REFERENCE",
                "human_reference should be .ai/assistant/context-profiles.md",
                ".ai/assistant/context-router.json",
            )

        if schema_version in ROUTER_SCHEMA_VERSIONS:
            preloaded = expect_string_list(
                router.get("preloaded_context"),
                self,
                "ROUTER_PRELOADED",
                ".ai/assistant/context-router.json",
            )
            for required in REQUIRED_PRELOADED:
                if required not in preloaded:
                    self.warn(
                        "ROUTER_PRELOADED_MISSING",
                        f"preloaded_context missing {required}",
                        ".ai/assistant/context-router.json",
                    )

            bootstrap = expect_string_list(
                router.get("bootstrap_context"),
                self,
                "ROUTER_BOOTSTRAP",
                ".ai/assistant/context-router.json",
            )
            for duplicate in duplicates(bootstrap):
                self.error(
                    "ROUTER_DUPLICATE_BOOTSTRAP",
                    f"duplicate bootstrap entry {duplicate}",
                    ".ai/assistant/context-router.json",
                )
            required_bootstrap = (
                REQUIRED_BOOTSTRAP
                if schema_version in {5, 6, 7, 8, 9, 10}
                else LEGACY_REQUIRED_BOOTSTRAP
            )
            for required in required_bootstrap:
                if required not in bootstrap:
                    self.error(
                        "ROUTER_BOOTSTRAP_MISSING",
                        f"bootstrap_context missing {required}",
                        ".ai/assistant/context-router.json",
                    )
            deferred = (
                sorted(set(bootstrap) & DEFERRED_BOOTSTRAP)
                if schema_version in {5, 6, 7, 8, 9, 10}
                else []
            )
            if deferred:
                self.warn(
                    "ROUTER_BOOTSTRAP_BROAD",
                    "bootstrap contains context routed after task selection: "
                    + ", ".join(deferred),
                    ".ai/assistant/context-router.json",
                )

            budgets = router.get("context_budgets")
            if not isinstance(budgets, dict):
                self.error(
                    "ROUTER_BUDGETS_MISSING",
                    "schema 2 through 10 router must define context_budgets",
                    ".ai/assistant/context-router.json",
                )
                budgets = {}
            elif schema_version in {4, 5, 6, 7, 8, 9, 10}:
                self.check_router_budget_shape(budgets)
            if not isinstance(router.get("context_receipt"), dict):
                self.error(
                    "ROUTER_RECEIPT_MISSING",
                    "schema 2 through 10 router must define context_receipt",
                    ".ai/assistant/context-router.json",
                )
            migration_entry = router.get("migration_routing")
            migration = migration_entry
            if schema_version in {3, 4, 5, 6, 7, 8, 9, 10} and isinstance(migration_entry, dict):
                migration = self.load_context_descriptor(
                    migration_entry,
                    "target-migration-routing",
                    "migration_routing",
                )
            if not isinstance(migration, dict) and self.target_path(
                ".ai/assistant/context/migration-routing.json"
            ).is_file():
                self.error(
                    "ROUTER_MIGRATION_MISSING",
                    "schema 2 through 10 router must define migration-first routing",
                    ".ai/assistant/context-router.json",
                )
            elif isinstance(migration, dict):
                assessment_source = (
                    migration_entry if isinstance(migration_entry, dict) else migration
                )
                if assessment_source.get("assessment_required_before_changes") is not True:
                    self.error(
                        "ROUTER_MIGRATION_ASSESSMENT",
                        "migration assessment must be required before upgrade changes",
                        ".ai/assistant/context-router.json",
                    )
                for field in [
                    "required_context",
                    "impact_selectors",
                    "candidate_context",
                    "expand_when",
                    "final_evidence",
                ]:
                    values = expect_string_list(
                        migration.get(field),
                        self,
                        "ROUTER_MIGRATION_FIELD",
                        ".ai/assistant/context-router.json",
                        label=f"migration_routing.{field}",
                    )
                    if field in {"required_context", "candidate_context"}:
                        for value in values:
                            self.check_router_path(value, "migration_routing", field)

            if schema_version == 10:
                self.check_task_classification(router)

        self.check_router_routing_order(router)

        profiles = self.router_profiles(router)
        if not isinstance(profiles, dict):
            self.error(
                "ROUTER_PROFILES_SHAPE",
                "profiles must be an object",
                ".ai/assistant/context-router.json",
            )
            profiles = {}

        expected_profiles = set(CANONICAL_PROFILES)
        if "ai-infrastructure" not in (enabled_modules or set()):
            expected_profiles.discard("ai-infrastructure")
        for profile in sorted(expected_profiles):
            if profile not in profiles:
                self.warn(
                    "ROUTER_PROFILE_MISSING",
                    f"canonical profile {profile} is missing",
                    ".ai/assistant/context-router.json",
                )

        for profile, data in profiles.items():
            if not isinstance(data, dict):
                self.error(
                    "ROUTER_PROFILE_SHAPE",
                    f"profile {profile} must be an object",
                    ".ai/assistant/context-router.json",
                )
                continue
            for field in [
                "use_when",
                "required_context",
                "expand_when",
                "approval_gates",
                "validation",
                "final_evidence",
            ]:
                values = expect_string_list(
                    data.get(field),
                    self,
                    "ROUTER_PROFILE_FIELD",
                    ".ai/assistant/context-router.json",
                    label=f"profiles.{profile}.{field}",
                )
                for duplicate in duplicates(values):
                    self.error(
                        "ROUTER_DUPLICATE_ENTRY",
                        f"profiles.{profile}.{field} repeats {duplicate}",
                        ".ai/assistant/context-router.json",
                    )
                if field in {"required_context", "validation"}:
                    for value in values:
                        self.check_router_path(value, profile, field)
            conditional = data.get("conditional_context", [])
            if conditional is not None and not isinstance(conditional, list):
                self.error(
                    "ROUTER_CONDITIONAL_CONTEXT",
                    f"profiles.{profile}.conditional_context must be a list",
                    ".ai/assistant/context-router.json",
                )
            elif isinstance(conditional, list):
                for index, entry in enumerate(conditional):
                    if not isinstance(entry, dict):
                        self.error(
                            "ROUTER_CONDITIONAL_CONTEXT",
                            f"profiles.{profile}.conditional_context[{index}] must be an object",
                            ".ai/assistant/context-router.json",
                        )
                        continue
                    path_value = entry.get("path")
                    when = entry.get("when")
                    if not isinstance(path_value, str) or not path_value:
                        self.error(
                            "ROUTER_CONDITIONAL_CONTEXT",
                            f"profiles.{profile}.conditional_context[{index}].path is missing",
                            ".ai/assistant/context-router.json",
                        )
                    else:
                        self.check_router_path(path_value, profile, "conditional_context")
                    if not isinstance(when, str) or not when:
                        self.error(
                            "ROUTER_CONDITIONAL_CONTEXT",
                            f"profiles.{profile}.conditional_context[{index}].when is missing",
                            ".ai/assistant/context-router.json",
                        )

        if schema_version == 10:
            self.check_small_task_overlay(router)

        if schema_version in {7, 8, 9, 10}:
            knowledge_entry = router.get("project_knowledge_routing")
            if not isinstance(knowledge_entry, dict) and self.target_path(
                ".ai/assistant/context/project-knowledge-routing.json"
            ).is_file():
                self.error(
                    "ROUTER_PROJECT_KNOWLEDGE_MISSING",
                    "schema 7 through 10 requires project_knowledge_routing",
                    ".ai/assistant/context-router.json",
                )
            elif isinstance(knowledge_entry, dict):
                if knowledge_entry.get("profile_only_match_allowed") is not False:
                    self.error(
                        "ROUTER_PROJECT_KNOWLEDGE_PROFILE_ONLY",
                        "project knowledge routing must reject profile-only matches",
                        ".ai/assistant/context-router.json",
                    )
                knowledge = self.load_context_descriptor(
                    knowledge_entry,
                    "target-project-knowledge-routing",
                    "project_knowledge_routing",
                )
                if isinstance(knowledge, dict):
                    descriptor_path = str(knowledge_entry.get("descriptor"))
                    if knowledge.get("index") != ".ai/project/knowledge/index.json":
                        self.error(
                            "ROUTER_PROJECT_KNOWLEDGE_INDEX",
                            "project knowledge route must use the compact target index",
                            descriptor_path,
                        )
                    for field in [
                        "enabled_when",
                        "initial_selectors",
                        "refined_selectors",
                        "delivery_rules",
                        "expand_when",
                        "context_receipt",
                    ]:
                        expect_string_list(
                            knowledge.get(field),
                            self,
                            "ROUTER_PROJECT_KNOWLEDGE_FIELD",
                            descriptor_path,
                            label=f"project_knowledge_routing.{field}",
                        )
                    if not isinstance(knowledge.get("budget_behavior"), str):
                        self.error(
                            "ROUTER_PROJECT_KNOWLEDGE_BUDGET",
                            "project knowledge route must define bounded budget behavior",
                            descriptor_path,
                        )
                    self.check_router_path(
                        ".ai/project/knowledge/index.json",
                        "project_knowledge_routing",
                        "index",
                    )

        if "consistency-map" in (enabled_modules or set()):
            consistency_entry = router.get("consistency_routing")
            if not isinstance(consistency_entry, dict):
                self.error(
                    "ROUTER_CONSISTENCY_MISSING",
                    "enabled consistency-map requires consistency_routing",
                    ".ai/assistant/context-router.json",
                )
            else:
                consistency = self.load_context_descriptor(
                    consistency_entry,
                    "target-consistency-routing",
                    "consistency_routing",
                )
                if isinstance(consistency, dict):
                    descriptor_path = str(consistency_entry.get("descriptor"))
                    required_context = expect_string_list(
                        consistency.get("required_context"),
                        self,
                        "ROUTER_CONSISTENCY_CONTEXT",
                        descriptor_path,
                        label="consistency_routing.required_context",
                    )
                    for required in [
                        ".ai/project/source-of-truth-registry.md",
                        ".ai/project/consistency-map.json",
                    ]:
                        if required not in required_context:
                            self.error(
                                "ROUTER_CONSISTENCY_CONTEXT",
                                f"consistency routing missing {required}",
                                descriptor_path,
                            )
                    for reference in required_context:
                        self.check_router_path(
                            reference, "consistency_routing", "required_context"
                        )
                    if ".ai/framework/consistency-model.md" in required_context:
                        self.warn(
                            "ROUTER_CONSISTENCY_PORTABLE_EAGER",
                            "portable consistency-model guidance should be conditional after target registry and map evidence",
                            descriptor_path,
                        )
                    conditional = consistency.get("conditional_context")
                    if not isinstance(conditional, list):
                        self.error(
                            "ROUTER_CONSISTENCY_CONDITIONAL",
                            "consistency routing must define conditional_context",
                            descriptor_path,
                        )
                    else:
                        portable_condition = next(
                            (
                                item
                                for item in conditional
                                if isinstance(item, dict)
                                and item.get("path")
                                == ".ai/framework/consistency-model.md"
                            ),
                            None,
                        )
                        if not isinstance(portable_condition, dict) or not isinstance(
                            portable_condition.get("when"), str
                        ):
                            self.error(
                                "ROUTER_CONSISTENCY_CONDITIONAL",
                                "portable consistency-model guidance needs an explicit conditional load trigger",
                                descriptor_path,
                            )
                        else:
                            self.check_router_path(
                                str(portable_condition["path"]),
                                "consistency_routing",
                                "conditional_context",
                            )

        if schema_version in {4, 5, 6, 7, 8, 9, 10} and isinstance(budgets, dict):
            self.check_installed_context_costs(router, profiles, budgets)

        upgrade = profiles.get("framework-upgrade")
        if isinstance(upgrade, dict):
            upgrade_context = upgrade.get("required_context")
            if isinstance(upgrade_context, list) and len(upgrade_context) > 8:
                self.warn(
                    "ROUTER_UPGRADE_CONTEXT_BROAD",
                    "framework-upgrade should assess migration impact before broad context loading",
                    ".ai/assistant/context-router.json",
                )

        if profiles_path.is_file():
            markdown_profiles = set(
                re.findall(
                    r"^## Profile: `([^`]+)`",
                    self.read_text(profiles_path),
                    flags=re.MULTILINE,
                )
            )
            for profile in profiles:
                if profile not in markdown_profiles:
                    self.warn(
                        "PROFILE_MARKDOWN_MISSING",
                        f"router profile {profile} is missing from context-profiles.md",
                        ".ai/assistant/context-profiles.md",
                    )
            self.check_markdown_required_context_duplicates(profiles_path)

    def check_router_budget_shape(self, budgets: dict[str, Any]) -> None:
        validate_budget_shape(self, budgets)

    def check_router_routing_order(self, router: dict[str, Any]) -> None:
        routing_order = expect_string_list(
            router.get("routing_order"),
            self,
            "ROUTER_ROUTING_ORDER",
            ".ai/assistant/context-router.json",
        )
        for duplicate in duplicates(routing_order):
            self.error(
                "ROUTER_DUPLICATE_PROFILE",
                f"duplicate routing profile {duplicate}",
                ".ai/assistant/context-router.json",
            )

    def check_task_classification(self, router: dict[str, Any]) -> None:
        relpath = ".ai/assistant/context-router.json"
        classification = router.get("task_classification")
        if not isinstance(classification, dict):
            self.error(
                "ROUTER_TASK_CLASSIFICATION_MISSING",
                "schema 10 router must define task_classification",
                relpath,
            )
            return
        if classification.get("schema_version") != TASK_CLASSIFICATION_SCHEMA_VERSION:
            self.error(
                "ROUTER_TASK_CLASSIFICATION_SCHEMA",
                "task_classification.schema_version must be 1",
                relpath,
            )
        if classification.get("classification_order") != TASK_CLASSES:
            self.error(
                "ROUTER_TASK_CLASSIFICATION_ORDER",
                "task classification order must match the canonical class order",
                relpath,
            )
        if classification.get("default_class") != DEFAULT_TASK_CLASS:
            self.error(
                "ROUTER_TASK_CLASSIFICATION_DEFAULT",
                "task_classification.default_class must be standard-task",
                relpath,
            )
        if AMBIGUITY_READ_ONLY_MARKER not in str(
            classification.get("ambiguity_behavior", "")
        ):
            self.error(
                "ROUTER_TASK_CLASSIFICATION_AMBIGUITY",
                "ambiguous task classification must stay read-only",
                relpath,
            )
        classes = classification.get("classes")
        if not isinstance(classes, dict):
            self.error(
                "ROUTER_TASK_CLASSIFICATION_CLASSES",
                "task_classification.classes must be an object",
                relpath,
            )
            classes = {}
        for task_class in TASK_CLASSES:
            item = classes.get(task_class)
            if not isinstance(item, dict):
                self.error(
                    "ROUTER_TASK_CLASSIFICATION_CLASS",
                    f"task classification class {task_class} must be an object",
                    relpath,
                )
                continue
            expect_string_list(
                item.get("use_when"),
                self,
                "ROUTER_TASK_CLASSIFICATION_USE_WHEN",
                relpath,
                label=f"task_classification.classes.{task_class}.use_when",
            )
        small = classes.get(SMALL_TASK_CLASS) if isinstance(classes, dict) else None
        if (
            isinstance(small, dict)
            and small.get("task_scale_overlay") != SMALL_TASK_CLASS
        ):
            self.error(
                "ROUTER_TASK_CLASSIFICATION_SMALL_OVERLAY",
                "small-task class must map to the small-task overlay",
                relpath,
            )
        triggers = expect_string_list(
            classification.get("expansion_triggers"),
            self,
            "ROUTER_TASK_CLASSIFICATION_TRIGGERS",
            relpath,
            label="task_classification.expansion_triggers",
        )
        for required in missing_required_values(
            triggers, TARGET_REQUIRED_EXPANSION_TRIGGERS
        ):
            self.error(
                "ROUTER_TASK_CLASSIFICATION_TRIGGER",
                f"task classification missing expansion trigger {required}",
                relpath,
            )

    def check_small_task_overlay(self, router: dict[str, Any]) -> None:
        relpath = ".ai/assistant/context-router.json"
        overlays = router.get("task_scale_overlays")
        if not isinstance(overlays, dict):
            self.error(
                "ROUTER_TASK_SCALE_OVERLAYS",
                "schema 10 router must define task_scale_overlays",
                relpath,
            )
            return
        small_entry = overlays.get(SMALL_TASK_CLASS)
        if not isinstance(small_entry, dict):
            self.error(
                "ROUTER_SMALL_TASK_OVERLAY_MISSING",
                "schema 10 router must define the small-task overlay",
                relpath,
            )
            return
        small_task = self.load_context_descriptor(
            small_entry,
            "target-task-scale-overlay",
            "task_scale_overlays.small-task",
        )
        if not isinstance(small_task, dict):
            return
        descriptor_path = str(small_entry.get("descriptor"))
        required_context = expect_string_list(
            small_task.get("required_context"),
            self,
            "ROUTER_SMALL_TASK_CONTEXT",
            descriptor_path,
            label="task_scale_overlays.small-task.required_context",
        )
        for required in [
            ".ai/assistant/gates/core.md",
            ".ai/assistant/gates/final-evidence.md",
        ]:
            if required not in required_context:
                self.error(
                    "ROUTER_SMALL_TASK_CONTEXT",
                    f"small-task overlay missing {required}",
                    descriptor_path,
                )
        for reference in required_context:
            self.check_router_path(
                reference,
                "task_scale_overlays.small-task",
                "required_context",
            )
        triggers = expect_string_list(
            small_task.get("expand_when"),
            self,
            "ROUTER_SMALL_TASK_EXPANSION",
            descriptor_path,
            label="task_scale_overlays.small-task.expand_when",
        )
        for required in missing_required_values(
            triggers, TARGET_REQUIRED_SMALL_TASK_EXPANSION_TRIGGERS
        ):
            self.error(
                "ROUTER_SMALL_TASK_EXPANSION",
                f"small-task overlay missing expansion trigger {required}",
                descriptor_path,
            )
        if "large-task" not in str(small_task.get("budget_behavior", "")):
            self.error(
                "ROUTER_SMALL_TASK_BUDGET",
                "small-task overlay must keep large-task context lazy",
                descriptor_path,
            )

    def check_installed_context_costs(
        self,
        router: dict[str, Any],
        profiles: dict[str, Any],
        budgets: dict[str, Any],
    ) -> None:
        validate_installed_costs(self, router, profiles, budgets)

    def load_context_descriptor(
        self,
        entry: dict[str, Any],
        expected_kind: str,
        label: str,
    ) -> dict[str, Any] | None:
        reference = entry.get("descriptor")
        if not isinstance(reference, str) or not reference.startswith(".ai/"):
            self.error(
                "ROUTER_DESCRIPTOR",
                f"{label}.descriptor must be a target path",
                ".ai/assistant/context-router.json",
            )
            return None
        data = self.load_json_object(self.target_path(reference), "CONTEXT_DESCRIPTOR")
        if data is None:
            return None
        if data.get("schema_version") != 1:
            self.error(
                "ROUTER_DESCRIPTOR_SCHEMA",
                f"{label} descriptor schema_version should be 1",
                reference,
            )
        if data.get("descriptor_kind") != expected_kind:
            self.error(
                "ROUTER_DESCRIPTOR_KIND",
                f"{label} descriptor_kind should be {expected_kind}",
                reference,
            )
        return data

    def router_profiles(self, router: dict[str, Any]) -> dict[str, Any]:
        if router.get("schema_version") not in {3, 4, 5, 6, 7, 8, 9, 10}:
            profiles = router.get("profiles")
            return profiles if isinstance(profiles, dict) else {}
        index = router.get("profile_index")
        if not isinstance(index, dict):
            self.error(
                "ROUTER_PROFILE_INDEX",
                "schema 3 through 10 router must define profile_index",
                ".ai/assistant/context-router.json",
            )
            return {}
        profiles: dict[str, Any] = {}
        for name, entry in index.items():
            if not isinstance(entry, dict):
                self.error(
                    "ROUTER_PROFILE_INDEX_ITEM",
                    f"profile_index.{name} must be an object",
                    ".ai/assistant/context-router.json",
                )
                continue
            profile = self.load_context_descriptor(
                entry, "target-context-profile", f"profile_index.{name}"
            )
            if profile is not None:
                if profile.get("profile") != name:
                    self.error(
                        "ROUTER_PROFILE_IDENTITY",
                        f"profile descriptor identity differs for {name}",
                        str(entry.get("descriptor")),
                    )
                profiles[name] = profile
        return profiles

    def check_action_authorization_contract(self) -> None:
        relpath = ".ai/assistant/policies/action-authorization.json"
        path = self.target_path(relpath)
        if not path.is_file():
            self.error(
                "AUTHORIZATION_POLICY_MISSING",
                "current-scope action authorization policy is missing",
                relpath,
            )
            return

        policy = self.load_json_object(path, "AUTHORIZATION_POLICY")
        if policy is None:
            return
        if (
            policy.get("schema_version") != 1
            or policy.get("policy_kind") != "target-action-authorization-policy"
            or policy.get("canonical_rule") != "ALATYR-AUTHORIZATION-001"
        ):
            self.error(
                "AUTHORIZATION_POLICY_SCHEMA",
                "action authorization policy schema, kind, or canonical rule is invalid",
                relpath,
            )
        if policy.get("default_phase") != "inspect" or policy.get("phases") != AUTHORIZATION_PHASES:
            self.error(
                "AUTHORIZATION_POLICY_PHASES",
                "ambiguous intent must default to inspect and expose the canonical phase order",
                relpath,
            )
        phase_effects = policy.get("phase_effects")
        if (
            not isinstance(phase_effects, dict)
            or set(phase_effects) != set(AUTHORIZATION_PHASES)
            or not all(isinstance(value, str) and value for value in phase_effects.values())
        ):
            self.error(
                "AUTHORIZATION_POLICY_EFFECTS",
                "action authorization phase effects must describe every canonical phase",
                relpath,
            )

        scope = policy.get("scope")
        if not isinstance(scope, dict):
            self.error(
                "AUTHORIZATION_POLICY_SCOPE",
                "action authorization scope must be an object",
                relpath,
            )
        else:
            if scope.get("prior_authorization_reusable") is not False:
                self.error(
                    "AUTHORIZATION_SCOPE_REUSE",
                    "authorization from a prior logical scope must not be reusable",
                    relpath,
                )
            invalidations = scope.get("invalidate_on")
            required_invalidations = {
                "operation completed",
                "new logical scope",
                "user redirection",
                "material changed-fact or surface expansion",
            }
            if not isinstance(invalidations, list) or not required_invalidations.issubset(
                {value for value in invalidations if isinstance(value, str)}
            ):
                self.error(
                    "AUTHORIZATION_SCOPE_INVALIDATION",
                    "authorization scope is missing required invalidation triggers",
                    relpath,
                )

        expected_separation = {
            "allowed_actions": "ceiling-not-grant",
            "protected_change_approval": "additional-gate-not-grant",
            "tool_permission": "capability-not-grant",
            "operation_routing": "process-selection-not-grant",
            "team_assignment": "coordination-not-grant",
            "project_decision": "fact-authority-not-grant",
            "workspace_mode": "context-selection-not-grant",
            "delegation": "inherited-boundary-not-grant",
            "validation_result": "evidence-not-grant",
        }
        if policy.get("separation") != expected_separation:
            self.error(
                "AUTHORIZATION_BOUNDARY_CONFLATED",
                "allowed actions, approval, tools, routing, team state, and modes must not grant action phases",
                relpath,
            )

        phase_rules = policy.get("phase_rules")
        if not isinstance(phase_rules, dict) or not all(
            phase_rules.get(field) is True
            for field in [
                "publish_requires_explicit_current_scope_intent",
                "live_external_requires_explicit_current_scope_intent",
                "recheck_newest_user_instruction_before_each_state_changing_phase",
            ]
        ):
            self.error(
                "AUTHORIZATION_PHASE_GATE",
                "publish, live external, and newest-instruction phase gates are incomplete",
                relpath,
            )
        delegation = policy.get("delegation")
        if not isinstance(delegation, dict) or (
            delegation.get("inherits_parent_scope") is not True
            or delegation.get("may_broaden_phases") is not False
            or delegation.get(
                "primary_rechecks_before_integration_commit_publish_or_live_action"
            )
            is not True
        ):
            self.error(
                "AUTHORIZATION_DELEGATION_ESCALATION",
                "delegation must inherit and never broaden parent authorization",
                relpath,
            )
        if policy.get("final_evidence_field") != "current_user_authorization":
            self.error(
                "AUTHORIZATION_EVIDENCE_FIELD",
                "action authorization policy must require current_user_authorization evidence",
                relpath,
            )

        required_surfaces = {
            "AGENTS.md": [
                "ALATYR-AUTHORIZATION-001",
                "Implementation does not imply commit; commit does not imply push",
            ],
            ".ai/assistant/gates/core.md": [
                "Issue/backlog returns",
                "Do not infer commit from implementation, publish from commit",
            ],
            ".ai/assistant/gates/final-evidence.md": [
                "`current_user_authorization`",
                "latest commit/publish/live confirmation",
            ],
            ".ai/assistant/contour.md": [
                ".ai/assistant/policies/action-authorization.json",
                "current-scope action authorization",
            ],
            ".ai/assistant/module-profile.md": [
                "current-scope-action-authorization",
                ".ai/assistant/policies/action-authorization.json",
            ],
            ".ai/assistant/maturity-profile.md": [
                ".ai/assistant/policies/action-authorization.json",
                "Prior authorization",
            ],
            ".ai/assistant/templates/installation-note.md": [
                ".ai/assistant/policies/action-authorization.json",
                "previous task's authorization expires",
            ],
            ".ai/assistant/templates/operation-request.md": [
                "Current logical scope:",
                "Current user authorization:",
                "Authorization source/message:",
                "Prior authorization invalidated:",
            ],
        }
        for surface, snippets in required_surfaces.items():
            surface_path = self.target_path(surface)
            if not surface_path.is_file():
                self.error(
                    "AUTHORIZATION_SURFACE_MISSING",
                    "required action authorization surface is missing",
                    surface,
                )
                continue
            text = self.read_text(surface_path)
            for snippet in snippets:
                if snippet not in text:
                    self.error(
                        "AUTHORIZATION_SURFACE_DRIFT",
                        f"action authorization surface is missing {snippet}",
                        surface,
                    )

    def check_operation_catalog(self) -> None:
        relpath = ".ai/assistant/operation-catalog.json"
        path = self.target_path(relpath)
        if not path.is_file():
            self.error(
                "OPERATION_CATALOG_MISSING",
                "machine-readable operation catalog is missing",
                relpath,
            )
            return

        catalog = self.load_json_object(path, "OPERATION_CATALOG")
        if catalog is None:
            return
        if catalog.get("schema_version") != 1:
            self.error(
                "OPERATION_CATALOG_SCHEMA",
                "schema_version should be 1",
                relpath,
            )
        if catalog.get("catalog_kind") != "target-operation-catalog":
            self.error(
                "OPERATION_CATALOG_KIND",
                "catalog_kind should be target-operation-catalog",
                relpath,
            )
        if catalog.get("authorization_phases") != AUTHORIZATION_PHASES:
            self.error(
                "AUTHORIZATION_CATALOG_PHASES",
                "operation catalog authorization phases differ from the canonical policy",
                relpath,
            )
        if catalog.get("required_final_evidence") != [
            "current_user_authorization",
            "durable_engineering_evidence",
        ]:
            self.error(
                "AUTHORIZATION_CATALOG_EVIDENCE",
                "operation catalog must require current_user_authorization and durable_engineering_evidence",
                relpath,
            )
        if catalog.get("action_authorization_policy") != (
            ".ai/assistant/policies/action-authorization.json"
        ):
            self.error(
                "AUTHORIZATION_CATALOG_ROUTE",
                "operation catalog does not route the canonical action authorization policy",
                relpath,
            )

        operations = catalog.get("operations")
        if not isinstance(operations, list) or not operations:
            self.error(
                "OPERATION_CATALOG_OPERATIONS",
                "operations must be a non-empty list",
                relpath,
            )
            return

        operation_ids: set[str] = set()
        aliases: dict[str, str] = {}
        exact_aliases: dict[str, str] = {}
        expected_index_operations: dict[str, list[str]] = {}
        for index, operation in enumerate(operations):
            label = f"operations[{index}]"
            if not isinstance(operation, dict):
                self.error(
                    "OPERATION_CATALOG_ITEM",
                    f"{label} must be an object",
                    relpath,
                )
                continue
            for field in OPERATION_REQUIRED_FIELDS:
                value = operation.get(field)
                if not isinstance(value, str) or not value:
                    self.error(
                        "OPERATION_CATALOG_FIELD",
                        f"{label}.{field} must be a non-empty string",
                        relpath,
                    )

            operation_id = operation.get("id")
            if isinstance(operation_id, str) and operation_id:
                if operation_id in operation_ids:
                    self.error(
                        "OPERATION_CATALOG_DUPLICATE_ID",
                        f"duplicate operation id {operation_id}",
                        relpath,
                    )
                operation_ids.add(operation_id)

            for field in OPERATION_LIST_FIELDS:
                values = operation.get(field)
                if not isinstance(values, list) or not all(
                    isinstance(value, str) and value for value in values
                ):
                    self.error(
                        "OPERATION_CATALOG_LIST",
                        f"{label}.{field} must be a string list",
                        relpath,
                    )
                    continue
                if field == "allowed_actions":
                    self.check_allowed_actions(values, relpath, f"{label}.{field}")
                if field == "context_profiles":
                    for profile in values:
                        if profile not in CANONICAL_PROFILES:
                            self.warn(
                                "OPERATION_CATALOG_PROFILE",
                                f"{label}.{field} references non-canonical profile {profile}",
                                relpath,
                            )
                if field == "aliases":
                    for alias in values:
                        normalized = alias.casefold()
                        previous = aliases.get(normalized)
                        if previous and previous != operation_id:
                            self.error(
                                "OPERATION_CATALOG_DUPLICATE_ALIAS",
                                f"alias {alias!r} maps to {previous} and {operation_id}",
                                relpath,
                            )
                        aliases[normalized] = str(operation_id)
                        exact_aliases[alias] = str(operation_id)

            if operation.get("preview") not in {"never", "risk-gated"}:
                self.error(
                    "OPERATION_CATALOG_PREVIEW",
                    f"{label}.preview must be never or risk-gated",
                    relpath,
                )
            flow = operation.get("flow")
            if isinstance(flow, str):
                self.check_optional_target_reference(flow, relpath, f"{label}.flow")
            module = operation.get("required_module")
            actions = operation.get("allowed_actions")
            if (
                isinstance(operation_id, str)
                and isinstance(module, str)
                and isinstance(flow, str)
                and isinstance(actions, list)
                and all(isinstance(action, str) for action in actions)
            ):
                expected_index_operations[operation_id] = [module, flow, *actions]

        fallback = catalog.get("fallback_operation")
        if not isinstance(fallback, str) or fallback not in operation_ids:
            self.error(
                "OPERATION_CATALOG_FALLBACK",
                "fallback_operation must identify a catalog operation",
                relpath,
            )
        for required in ["help", "adapter-health"]:
            if required not in operation_ids:
                self.error(
                    "OPERATION_CATALOG_REQUIRED_OPERATION",
                    f"catalog is missing required operation {required}",
                    relpath,
                )

        for field in [
            "compact_help",
            "human_reference",
            "routing_flow",
            "health_flow",
            "pre_change_preview",
            "module_profile",
        ]:
            value = catalog.get(field)
            if not isinstance(value, str) or not value:
                self.error(
                    "OPERATION_CATALOG_PATH",
                    f"{field} must be a non-empty target path",
                    relpath,
                )
            else:
                self.check_optional_target_reference(value, relpath, field)

        index_relpath = ".ai/assistant/operation-index.json"
        index = self.load_json_object(self.target_path(index_relpath), "OPERATION_INDEX")
        if index is None:
            self.error(
                "OPERATION_INDEX_MISSING",
                "checked compact operation index is missing",
                index_relpath,
            )
        else:
            if index.get("schema_version") != 1:
                self.error("OPERATION_INDEX_SCHEMA", "schema_version should be 1", index_relpath)
            if index.get("index_kind") != "target-operation-index":
                self.error(
                    "OPERATION_INDEX_KIND",
                    "index_kind should be target-operation-index",
                    index_relpath,
                )
            if index.get("catalog") != relpath:
                self.error(
                    "OPERATION_INDEX_CATALOG",
                    f"catalog should be {relpath}",
                    index_relpath,
                )
            if index.get("aliases") != exact_aliases:
                self.error(
                    "OPERATION_INDEX_ALIAS_DRIFT",
                    "aliases do not exactly derive from the operation catalog",
                    index_relpath,
                )
            if index.get("operations") != expected_index_operations:
                self.error(
                    "OPERATION_INDEX_CONTRACT_DRIFT",
                    "module, flow, or allowed-action projection differs from the catalog",
                    index_relpath,
                )

        router_path = self.target_path(".ai/assistant/context-router.json")
        router = self.load_json_object(router_path, "ROUTER")
        if router is None:
            return
        operation_routing = router.get("operation_routing")
        if not isinstance(operation_routing, dict):
            self.error(
                "OPERATION_ROUTING_MISSING",
                "context router must define operation_routing",
                ".ai/assistant/context-router.json",
            )
        else:
            if operation_routing.get("index") != index_relpath:
                self.error(
                    "OPERATION_ROUTING_INDEX",
                    f"operation_routing.index should be {index_relpath}",
                    ".ai/assistant/context-router.json",
                )
            if operation_routing.get("catalog") != relpath:
                self.error(
                    "OPERATION_ROUTING_CATALOG",
                    f"operation_routing.catalog should be {relpath}",
                    ".ai/assistant/context-router.json",
                )
            if operation_routing.get("health_operation") != "adapter-health":
                self.error(
                    "OPERATION_ROUTING_HEALTH",
                    "health_operation should be adapter-health",
                    ".ai/assistant/context-router.json",
                )

        bootstrap = router.get("bootstrap_context")
        if isinstance(bootstrap, list) and relpath in bootstrap:
            self.warn(
                "OPERATION_CATALOG_IN_BOOTSTRAP",
                "operation catalog should load on routing demand, not for every task",
                ".ai/assistant/context-router.json",
            )

        profiles = self.router_profiles(router)
        routed_ids: set[str] = set()
        if isinstance(profiles, dict):
            for profile, profile_data in profiles.items():
                if not isinstance(profile_data, dict):
                    continue
                candidates = profile_data.get("operation_candidates")
                if not isinstance(candidates, list) or not candidates:
                    self.warn(
                        "OPERATION_CANDIDATES_MISSING",
                        f"profile {profile} has no bounded operation_candidates",
                        ".ai/assistant/context-router.json",
                    )
                    continue
                for candidate in candidates:
                    if not isinstance(candidate, str) or candidate not in operation_ids:
                        self.error(
                            "OPERATION_CANDIDATE_UNKNOWN",
                            f"profile {profile} references unknown operation {candidate}",
                            ".ai/assistant/context-router.json",
                        )
                    else:
                        routed_ids.add(candidate)

        overlays = router.get("task_scale_overlays")
        if isinstance(overlays, dict):
            for overlay_name, overlay_data in overlays.items():
                if not isinstance(overlay_data, dict):
                    continue
                candidate_source = overlay_data
                descriptor = overlay_data.get("descriptor")
                if isinstance(descriptor, str):
                    loaded = self.load_json_object(
                        self.target_path(descriptor),
                        "CONTEXT_OVERLAY",
                    )
                    if loaded is not None:
                        candidate_source = loaded
                candidates = candidate_source.get("operation_candidates")
                if candidates is None:
                    continue
                if not isinstance(candidates, list):
                    self.error(
                        "OPERATION_CANDIDATE_SHAPE",
                        f"task-scale overlay {overlay_name} operation_candidates must be a list",
                        ".ai/assistant/context-router.json",
                    )
                    continue
                for candidate in candidates:
                    if not isinstance(candidate, str) or candidate not in operation_ids:
                        self.error(
                            "OPERATION_CANDIDATE_UNKNOWN",
                            f"task-scale overlay {overlay_name} references unknown operation {candidate}",
                            ".ai/assistant/context-router.json",
                        )
                    else:
                        routed_ids.add(candidate)

        intent_overlays = router.get("intent_overlays")
        if isinstance(intent_overlays, dict):
            for overlay_name, overlay_data in intent_overlays.items():
                if not isinstance(overlay_data, dict):
                    continue
                candidates = overlay_data.get("operation_candidates")
                if not isinstance(candidates, list):
                    self.error(
                        "OPERATION_CANDIDATE_SHAPE",
                        f"intent overlay {overlay_name} operation_candidates must be a list",
                        ".ai/assistant/context-router.json",
                    )
                    continue
                for candidate in candidates:
                    if not isinstance(candidate, str) or candidate not in operation_ids:
                        self.error(
                            "OPERATION_CANDIDATE_UNKNOWN",
                            f"intent overlay {overlay_name} references unknown operation {candidate}",
                            ".ai/assistant/context-router.json",
                        )
                    else:
                        routed_ids.add(candidate)

        unrouted = sorted(operation_ids - routed_ids - {"help", "large-task"})
        if unrouted:
            self.warn(
                "OPERATION_CANDIDATE_COVERAGE",
                "catalog operations have no compact profile candidate: "
                + ", ".join(unrouted),
                ".ai/assistant/context-router.json",
            )

    def check_subagent_delegation(self, manifest: ManifestData | None) -> None:
        validate_subagent_delegation(self, manifest)

    def check_discussion_diagrams(self, manifest: ManifestData | None) -> None:
        validate_discussion_diagrams(self, manifest)

    def check_architecture_knowledge(self, manifest: ManifestData | None) -> None:
        validate_architecture_knowledge(self.capability_validation_context(), manifest)

    def check_code_documentation(self, manifest: ManifestData | None) -> None:
        validate_code_documentation(self.capability_validation_context(), manifest)

    def check_project_vocabulary(self, manifest: ManifestData | None) -> None:
        validate_project_vocabulary(self.capability_validation_context(), manifest)

    def check_test_first_development(self, manifest: ManifestData | None) -> None:
        validate_test_first_development(self.capability_validation_context(), manifest)

    def check_extensions(self, manifest: ManifestData | None) -> None:
        validate_extensions(self.capability_validation_context(), manifest)

    def check_dependency_knowledge(self, manifest: ManifestData | None) -> None:
        validate_dependency_knowledge(self.capability_validation_context(), manifest)

    def check_workspace_modes(self, manifest: ManifestData | None) -> None:
        validate_workspace_modes(self, manifest)

    def check_consistency_map(
        self, manifest: ManifestData | None = None
    ) -> None:
        CONSISTENCY_MAP_MODULE.validate(
            self.capability_validation_context(), manifest
        )

    def check_enabled_module_status_claims(
        self, enabled_modules: set[str]
    ) -> None:
        if not enabled_modules:
            return

        catalog_path = self.target_path(".ai/framework/capabilities.json")
        catalog, error = self.context.read_json(catalog_path)
        modules = catalog.get("modules") if isinstance(catalog, dict) else None
        if error is not None or not isinstance(modules, dict):
            return

        shared_surfaces = {
            ".ai/README.md",
            ".ai/assistant/contour.md",
            ".ai/assistant/context-profiles.md",
            ".ai/assistant/help.md",
            ".ai/assistant/help-reference.md",
            ".ai/assistant/maturity-profile.md",
            ".ai/project/contour.md",
            ".ai/project/blueprint.md",
        }
        for module_id in sorted(enabled_modules):
            contract = modules.get(module_id)
            module_surfaces = {
                value
                for value in (
                    contract.get("target_files", [])
                    if isinstance(contract, dict)
                    else []
                )
                if isinstance(value, str)
            }
            for relpath in sorted(shared_surfaces | module_surfaces):
                path = self.target_path(relpath)
                if not path.is_file() or path.suffix.lower() not in {
                    ".md",
                    ".flow",
                    ".txt",
                }:
                    continue
                text = self.read_text(path)
                paragraphs = re.finditer(
                    r"(?:\A|\n\s*\n)(\S[\s\S]*?)(?=\n\s*\n|\Z)", text
                )
                for paragraph_match in paragraphs:
                    paragraph = paragraph_match.group(1).strip()
                    normalized = " ".join(paragraph.split())
                    status_match = STALE_ENABLED_MODULE_STATE_RE.search(normalized)
                    if status_match is None:
                        continue
                    conditional_prefix = normalized[: status_match.start()]
                    if CONDITIONAL_STATUS_RE.search(conditional_prefix):
                        continue
                    module_named = module_id.casefold() in normalized.casefold()
                    generic_claim = STALE_GENERIC_MODULE_STATE_RE.search(normalized)
                    if not module_named and not (
                        relpath in module_surfaces and generic_claim is not None
                    ):
                        continue
                    line = text.count("\n", 0, paragraph_match.start(1)) + 1
                    self.error(
                        "ENABLED_MODULE_STALE_STATUS",
                        f"enabled module {module_id!r} is described with an unavailable module state",
                        f"{relpath}:{line}",
                    )
                    break

    def check_ai_infrastructure_router(self) -> None:
        AI_INFRASTRUCTURE_ROUTER_MODULE.validate(
            self.capability_validation_context(), None
        )

    def check_development_evidence(self, manifest: ManifestData | None) -> None:
        validate_development_evidence(self.capability_validation_context(), manifest)

    def check_team_collaboration(self, manifest: ManifestData | None) -> None:
        validate_team_collaboration(self.capability_validation_context(), manifest)

    def load_json_object(self, path: Path, code_prefix: str) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        data, error = self.context.read_json(path)
        if error is not None:
            self.error(f"{code_prefix}_INVALID_JSON", error, self.rel(path))
            return None
        if not isinstance(data, dict):
            self.error(
                f"{code_prefix}_INVALID_SHAPE",
                "document must be a JSON object",
                self.rel(path),
            )
            return None
        return data

    def check_optional_target_reference(self, value: str, source: str, label: str) -> None:
        if is_placeholder(value) or value in {"none", "not-applicable", "not applicable"}:
            return
        if value.startswith(".ai/framework/"):
            if not self.target_path(value).is_file():
                self.warn("ROUTED_PATH_MISSING", f"{label} points to missing {value}", source)
            return
        if value.startswith(".ai/") and not self.target_path(value).exists():
            self.warn("ROUTED_PATH_MISSING", f"{label} points to missing {value}", source)

    def check_allowed_actions(self, values: list[str], source: str, label: str) -> None:
        for value in values:
            if is_placeholder(value):
                continue
            if value not in ALLOWED_ACTION_MODES:
                self.error(
                    "AI_ROUTER_ALLOWED_ACTION",
                    f"{label} contains unsupported allowed-action mode: {value}",
                    source,
                )

    def check_router_path(self, value: str, profile: str, field: str) -> None:
        if is_placeholder(value):
            return
        if value == ".ai/framework":
            if not self.target_path(".ai/framework").is_dir():
                self.error(
                    "ROUTER_PATH_MISSING",
                    f"profiles.{profile}.{field} points to missing {value}",
                    ".ai/assistant/context-router.json",
                )
            return
        if value.startswith(".ai/") or value in {"AGENTS.md", "AI_ASSISTANTS.md"}:
            if not self.target_path(value).exists():
                self.warn(
                    "ROUTER_PATH_MISSING",
                    f"profiles.{profile}.{field} points to missing {value}",
                    ".ai/assistant/context-router.json",
                )

    def check_markdown_required_context_duplicates(self, path: Path) -> None:
        text = self.read_text(path)
        current_profile = None
        in_required_context = False
        values: list[str] = []

        def flush() -> None:
            if not current_profile:
                return
            for duplicate in duplicates(values):
                self.error(
                    "PROFILE_DUPLICATE_CONTEXT",
                    f"profile {current_profile} repeats required context {duplicate}",
                    self.rel(path),
                )

        for raw_line in text.splitlines():
            profile_match = re.match(r"^## Profile: `([^`]+)`", raw_line)
            if profile_match:
                flush()
                current_profile = profile_match.group(1)
                in_required_context = False
                values = []
                continue
            if raw_line.strip() == "Required context:":
                in_required_context = True
                values = []
                continue
            if in_required_context and raw_line.startswith("## "):
                flush()
                in_required_context = False
                values = []
                continue
            if not in_required_context:
                continue
            if raw_line.startswith("- "):
                values.extend(re.findall(r"`([^`]+)`", raw_line))
            elif raw_line.strip() and not raw_line.startswith("  "):
                flush()
                in_required_context = False
                values = []
        flush()

    def check_bootstrap_references(self) -> None:
        files_to_check = ["AGENTS.md", *BRIDGE_FILES]
        for relpath in files_to_check:
            path = self.target_path(relpath)
            if not path.is_file():
                continue
            text = self.read_text(path)
            if ".ai/assistant/bootstrap-index.json" not in text:
                level = self.error if relpath == "AGENTS.md" else self.warn
                level(
                    "BOOTSTRAP_INDEX_REFERENCE_MISSING",
                    "bootstrap references do not include .ai/assistant/bootstrap-index.json",
                    relpath,
                )
            if relpath == "AGENTS.md" and ".ai/assistant/context-router.json" not in text:
                self.error(
                    "BOOTSTRAP_CONTEXT_ROUTER_MISSING",
                    "bootstrap recovery references do not include .ai/assistant/context-router.json",
                    relpath,
                )
            if relpath == "AGENTS.md" and ".ai/README.md" not in text:
                self.error(
                    "BOOTSTRAP_AREA_MAP_MISSING",
                    "bootstrap recovery references do not include .ai/README.md",
                    relpath,
                )

        gates = self.target_path(".ai/assistant/gates/checklist.md")
        if gates.is_file() and ".ai/assistant/gates/index.json" not in self.read_text(gates):
            self.error(
                "GATE_CONTEXT_ROUTER_MISSING",
                "complete gate checklist does not route through gates/index.json",
                ".ai/assistant/gates/checklist.md",
            )

        routing = self.target_path(".ai/assistant/flows/operation-routing.flow.md")
        if routing.is_file():
            text = self.read_text(routing)
            if "Load bootstrap context only" not in text:
                self.warn(
                    "ROUTING_BROAD_CONTEXT",
                    "operation routing should load bootstrap context before profile context",
                    ".ai/assistant/flows/operation-routing.flow.md",
                )
            positive_broad_load = any(
                re.search(r"\b(?:load|read)\s+(?:all\s+)?`\.ai/framework`", line, re.IGNORECASE)
                and not re.search(
                    r"\b(?:do not|don't|never|avoid)\b.*\b(?:load|read)\b",
                    line,
                    re.IGNORECASE,
                )
                for line in text.splitlines()
            )
            legacy_broad_load = (
                "Load `AGENTS.md`, `AI_ASSISTANTS.md`, `.ai/README.md`, "
                "`.ai/framework`"
            ) in text
            if positive_broad_load or legacy_broad_load:
                self.error(
                    "ROUTING_LOADS_BROAD_CONTEXT",
                    "operation routing appears to load broad framework/project context before routing",
                    ".ai/assistant/flows/operation-routing.flow.md",
                )

    def is_authoring_file(self, relpath: str) -> bool:
        return any(pattern.search(relpath) for pattern in AUTHORING_FILE_PATTERNS)

    def active_adapter_files(
        self,
        manifest: ManifestData | None,
        support_profile: str,
        enabled_modules: set[str],
    ) -> list[Path]:
        relpaths = set(required_files_for_support_profile(support_profile))
        relpaths.add("AGENTS.md")
        relpaths.update(self.active_assistant_bridge_files(manifest))
        for module_id in enabled_modules:
            contract = self.capability_modules.get(module_id)
            if isinstance(contract, dict):
                relpaths.update(contract.get("target_files", []))
        if manifest is not None:
            for scalar in manifest.scalars.values():
                if isinstance(scalar.value, str) and scalar.value.startswith(".ai/"):
                    path = self.target_path(scalar.value)
                    if path.is_file():
                        relpaths.add(scalar.value)
        return [
            self.target_path(relpath)
            for relpath in sorted(relpaths)
            if not self.is_authoring_file(relpath)
        ]

    def active_assistant_bridge_files(
        self, manifest: ManifestData | None
    ) -> set[str]:
        selected = {
            scalar.value
            for scalar in manifest.lists.get(("supported_assistants",), [])
            if not is_placeholder(scalar.value)
            and not is_unresolved_value(scalar.value)
        } if manifest is not None else set()
        index_path = self.target_path(
            ".ai/assistant/assistant-capabilities.json"
        )
        index, error = self.context.read_json(index_path)
        if error or not isinstance(index, dict):
            return set(BRIDGE_FILES)
        surfaces = index.get("surfaces")
        bridge_paths = index.get("bridge_paths")
        if not isinstance(surfaces, dict) or not isinstance(bridge_paths, dict):
            return set(BRIDGE_FILES)

        bridge_surfaces: dict[str, set[str]] = {}
        for surface_id, paths in bridge_paths.items():
            if (
                not isinstance(surface_id, str)
                or not isinstance(paths, list)
                or not all(isinstance(path, str) and path for path in paths)
            ):
                return set(BRIDGE_FILES)
            for path in paths:
                bridge_surfaces.setdefault(path, set()).add(surface_id)

        routes: dict[str, str | None] = {}
        for surface_id, relpath in surfaces.items():
            if not isinstance(surface_id, str) or not isinstance(relpath, str):
                continue
            record_path = self.target_path(relpath)
            record, record_error = self.context.read_json(record_path)
            if record_error or not isinstance(record, dict):
                routes[surface_id] = None
                continue
            loading = record.get("instruction_loading")
            route_value = loading.get("route") if isinstance(loading, dict) else None
            route = (
                str(route_value).casefold()
                if is_concrete_capability_value(route_value)
                else None
            )
            surface_state = record.get("surface_state")
            overall_value = (
                surface_state.get("overall") if isinstance(surface_state, dict) else None
            )
            selected_value = (
                surface_state.get("selected_for_target")
                if isinstance(surface_state, dict)
                else None
            )
            overall = (
                str(overall_value).casefold()
                if is_concrete_capability_value(overall_value)
                else None
            )
            selected_for_target = (
                str(selected_value).casefold()
                if is_concrete_capability_value(selected_value)
                else None
            )
            routes[surface_id] = (
                "unsupported"
                if route == "unsupported"
                and overall == "unsupported"
                and selected_for_target == "no"
                else None
            )

        active = set(NEUTRAL_ASSISTANT_ENTRY_FILES) & set(BRIDGE_FILES)
        indexed = set(routes)
        for relpath in BRIDGE_FILES:
            if relpath in NEUTRAL_ASSISTANT_ENTRY_FILES:
                continue
            associated = bridge_surfaces.get(relpath, set())
            if not associated or selected & associated:
                active.add(relpath)
                continue
            if not associated.issubset(indexed) or any(
                routes.get(surface_id) != "unsupported" for surface_id in associated
            ):
                active.add(relpath)
        return active

    def check_placeholders(
        self,
        manifest: ManifestData | None = None,
        support_profile: str = "full",
        enabled_modules: set[str] | None = None,
    ) -> None:
        paths = self.active_adapter_files(
            manifest,
            support_profile,
            enabled_modules or self.enabled_modules(manifest),
        )
        report = self.warn if self.allow_placeholders else self.error
        finding_code = (
            "PLACEHOLDER_STAGING_UNRESOLVED"
            if self.allow_placeholders
            else "PLACEHOLDER_UNRESOLVED"
        )
        for path in paths:
            if not path.is_file():
                continue
            text = self.read_text(path)
            for line_number, line in enumerate(text.splitlines(), start=1):
                if PLACEHOLDER_RE.search(line):
                    self.unresolved_active_placeholders += 1
                    report(
                        finding_code,
                        "unresolved template placeholder remains in an active adapter surface",
                        f"{self.rel(path)}:{line_number}",
                    )
                if "not defined" in line.lower():
                    self.warn(
                        "UNRESOLVED_NOT_DEFINED",
                        "unresolved 'not defined' marker remains",
                        f"{self.rel(path)}:{line_number}",
                    )
        if self.allow_placeholders:
            self.info(
                "PLACEHOLDERS_ALLOWED",
                "migration-staging records unresolved active placeholders but cannot accept the adapter",
            )

    def check_local_paths(self) -> None:
        scan_paths = self.scan_text_files()
        target_string = str(self.target)
        for path in scan_paths:
            text = self.read_text(path)
            for line_number, line in enumerate(text.splitlines(), start=1):
                raw_matches = [match.group(0) for match in LOCAL_PATH_RE.finditer(line)]
                if target_string and target_string in line:
                    raw_matches.append(target_string)
                for value in raw_matches:
                    if any(allowed in value for allowed in self.allow_local_paths):
                        continue
                    self.error(
                        "LOCAL_PATH_LEAKAGE",
                        f"hard-coded local path found: {value}",
                        f"{self.rel(path)}:{line_number}",
                    )

    def scan_text_files(self) -> list[Path]:
        if self._scan_text_files_cache is not None:
            return list(self._scan_text_files_cache)
        roots = [self.target_path(".ai")]
        files = [self.target_path(relpath) for relpath in ["AGENTS.md", *BRIDGE_FILES]]
        for root in roots:
            if not root.is_dir():
                continue
            for path in root.rglob("*"):
                if path.is_file() and not should_skip_path(path):
                    files.append(path)
        self._scan_text_files_cache = tuple(
            sorted({path for path in files if path.is_file()})
        )
        return list(self._scan_text_files_cache)

    def discover_checkers(
        self,
        manifest: ManifestData | None,
    ) -> tuple[list[Path], list[str]]:
        checker_files: list[Path] = []
        for relroot in ["scripts", "tools", "bin", ".github/workflows"]:
            root = self.target_path(relroot)
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                name = path.name.lower()
                rel = self.rel(path).lower()
                if "alatyr" in rel and ("check" in name or "validate" in name):
                    checker_files.append(path)
        for relpath in [
            "scripts/check-alatyr.sh",
            "scripts/check_alatyr.py",
            "tools/check-alatyr.sh",
            "tools/check_alatyr.py",
            "tools/validate_target_adapter.py",
        ]:
            path = self.target_path(relpath)
            if path.is_file():
                checker_files.append(path)

        checker_commands: list[str] = []
        package_json = self.target_path("package.json")
        if package_json.is_file():
            package, package_error = self.context.read_json(package_json)
            if package_error is not None:
                package = {}
            scripts = package.get("scripts") if isinstance(package, dict) else {}
            if isinstance(scripts, dict):
                for name, command in scripts.items():
                    if "alatyr" in str(name).lower() and "check" in str(name).lower():
                        checker_commands.append(f"npm run {name}")
                    if CHECKER_REFERENCE_RE.search(str(command)):
                        checker_commands.append(str(command))

        if manifest:
            for key, values in manifest.lists.items():
                if key[-2:] == ("commands", "[]"):
                    continue
                for scalar in values:
                    if CHECKER_REFERENCE_RE.search(scalar.value):
                        checker_commands.append(scalar.value)
            for key, scalar in manifest.scalars.items():
                if key[-1:] == ("command",) and CHECKER_REFERENCE_RE.search(scalar.value):
                    checker_commands.append(scalar.value)

        return sorted(set(checker_files)), sorted(set(checker_commands))

    def check_checker_claims(
        self,
        checker_files: list[Path],
        checker_commands: list[str],
    ) -> None:
        checker_exists = bool(checker_files or checker_commands)
        # Portable framework guidance may name the optional source validator.
        # Only target-owned adapter surfaces can make target-local checker claims.
        adapter_text_files = [
            path
            for path in self.scan_text_files()
            if not self.rel(path).startswith(".ai/framework/")
        ]
        for path in adapter_text_files:
            text = self.read_text(path)
            if checker_exists and CHECKER_MISSING_RE.search(text):
                self.error(
                    "STALE_CHECKER_MISSING_CLAIM",
                    "adapter claims checker is missing even though checker evidence exists",
                    self.rel(path),
                )

        referenced = [
            self.rel(path)
            for path in adapter_text_files
            if CHECKER_REFERENCE_RE.search(self.read_text(path))
        ]
        if referenced and not checker_exists:
            report = self.warn if self.allow_placeholders else self.error
            report(
                "STALE_CHECKER_REFERENCE",
                "adapter references an Alatyr checker but no checker command or file was found",
            )

        if not checker_exists:
            self.warn(
                "TARGET_CHECKER_MISSING",
                "no target-local Alatyr checker command or file was found",
            )
            return

        self.info(
            "TARGET_CHECKER_FOUND",
            "target-local checker evidence found: "
            + ", ".join([self.rel(path) for path in checker_files] + checker_commands),
        )
        checker_text = "\n".join(self.read_text(path) for path in checker_files)
        coverage_terms = self.config.checker_coverage()
        for term, label in coverage_terms.items():
            if term not in checker_text.lower():
                self.warn(
                    "TARGET_CHECKER_COVERAGE_GAP",
                    f"target-local checker may be missing {label}",
                )

    def check_approval_scope(self) -> None:
        approval_records = self.resolve_approval_records()
        archive_records = [
            record
            for record in self.discover_approval_archive_records()
            if record not in approval_records
        ]
        if archive_records:
            self.check_approval_record_shape(archive_records)
            self.check_approval_hash_evidence(
                archive_records, compare_current_patch=False
            )
            self.info(
                "APPROVAL_ARCHIVE_CHECKED",
                f"checked {len(archive_records)} historical approval record(s) "
                "without applying them to the current operation",
            )
        if approval_records:
            self.check_approval_record_shape(approval_records)

        if self.enforce_approval_scope and not self.diff_ref:
            self.error(
                "APPROVAL_DIFF_REF_REQUIRED",
                "--enforce-approval-scope requires --diff-ref",
            )
            return
        if self.enforce_approval_scope and not self.approval_records:
            self.error(
                "APPROVAL_RECORD_SELECTION_REQUIRED",
                "strict approval enforcement requires one or more explicit "
                "--approval-record values; historical records are not auto-selected",
            )
            return

        if not self.diff_ref:
            if approval_records:
                self.check_approval_hash_evidence(approval_records)
            self.info(
                "DIFF_SCOPE_SKIPPED",
                "approval scope versus diff check skipped because --diff-ref was not provided",
            )
            return

        changed_files = git_changed_files(self.target, self.diff_ref)
        if changed_files is None:
            self.warn(
                "DIFF_SCOPE_UNAVAILABLE",
                f"could not compute git diff against {self.diff_ref}",
            )
            return
        checked_files = (
            changed_files
            if self.enforce_approval_scope
            else [path for path in changed_files if is_protected_surface(path)]
        )
        if not checked_files:
            message = (
                "no changed paths were found"
                if self.enforce_approval_scope
                else "no protected adapter surfaces changed"
            )
            self.info("DIFF_SCOPE_CLEAN", message)
            return
        if not approval_records:
            finding = self.error if self.enforce_approval_scope else self.warn
            finding(
                "APPROVAL_RECORD_MISSING",
                "changed files require approval scope but no applicable approval records were supplied",
            )
            return

        scopes: list[ApprovalScope] = []
        for record in approval_records:
            scope = self.load_approval_scope(record)
            if scope is None:
                continue
            scopes.append(scope)
            if self.enforce_approval_scope:
                if not scope.machine_readable:
                    self.error(
                        "APPROVAL_RECORD_MACHINE_READABLE_REQUIRED",
                        "strict approval enforcement requires a JSON approval record",
                        self.rel(record),
                    )
                if not refs_match(self.target, scope.diff_base, self.diff_ref):
                    self.error(
                        "APPROVAL_DIFF_BASE_MISMATCH",
                        f"approval diff base {scope.diff_base or '<missing>'} does not "
                        f"match --diff-ref {self.diff_ref}",
                        self.rel(record),
                    )
            for changed in checked_files:
                if scope_entries_cover(changed, scope.excluded):
                    finding = self.error if self.enforce_approval_scope else self.warn
                    finding(
                        "APPROVAL_SCOPE_EXCLUDED",
                        f"changed file is explicitly excluded: {changed}",
                        self.rel(record),
                    )

        self.check_approval_hash_evidence([scope.path for scope in scopes])
        for changed in checked_files:
            if any(
                scope_entries_cover(changed, scope.allowed)
                for scope in scopes
            ):
                continue
            finding = self.error if self.enforce_approval_scope else self.warn
            finding(
                "APPROVAL_SCOPE_MISMATCH",
                f"changed file is not covered by an explicit approval scope: {changed}",
            )
        if self.enforce_approval_scope and scopes:
            self.info(
                "APPROVAL_SCOPE_ENFORCED",
                f"checked {len(checked_files)} changed path(s) against "
                f"{len(scopes)} explicitly selected machine-readable approval record(s)",
            )

    def resolve_approval_records(self) -> list[Path]:
        if self.approval_records:
            records: list[Path] = []
            for record in self.approval_records:
                try:
                    record.relative_to(self.target)
                except ValueError:
                    finding = self.error if self.enforce_approval_scope else self.warn
                    finding(
                        "APPROVAL_RECORD_OUTSIDE_TARGET",
                        "supplied approval record must be inside the target repository",
                        str(record),
                    )
                    continue
                if not record.is_file():
                    finding = self.error if self.enforce_approval_scope else self.warn
                    finding(
                        "APPROVAL_RECORD_MISSING",
                        "supplied approval record does not exist",
                        self.rel(record),
                    )
                    continue
                records.append(record)
            return records
        # Approval records are historical evidence, not implicit current-task
        # inputs. Callers must select the records whose scope and result should
        # be validated for the current operation.
        return []

    def discover_approval_archive_records(self) -> list[Path]:
        directory = self.target_path(".ai/assistant/approvals")
        return sorted(
            path
            for pattern in ("*.md", "*.json")
            for path in directory.glob(pattern)
            if path.name
            not in {
                "approval-template.md",
                "approval-record-template.json",
                "context-index.json",
            }
        )

    def load_approval_scope(self, record: Path) -> ApprovalScope | None:
        if record.suffix.lower() == ".json":
            try:
                data = json.loads(self.read_text(record))
            except json.JSONDecodeError as exc:
                self.error(
                    "APPROVAL_RECORD_INVALID_JSON",
                    str(exc),
                    self.rel(record),
                )
                return None
            if not isinstance(data, dict):
                self.error(
                    "APPROVAL_RECORD_INVALID_SHAPE",
                    "machine-readable approval record must be a JSON object",
                    self.rel(record),
                )
                return None
            scope = data.get("scope")
            diff = data.get("diff")
            if not isinstance(scope, dict) or not isinstance(diff, dict):
                self.error(
                    "APPROVAL_RECORD_INVALID_SHAPE",
                    "machine-readable approval record requires scope and diff objects",
                    self.rel(record),
                )
                return None
            return ApprovalScope(
                path=record,
                allowed=json_string_list(scope.get("allowed_files_or_surfaces")),
                excluded=json_string_list(scope.get("excluded_files_or_surfaces")),
                diff_base=str(diff.get("base", "")).strip(),
                machine_readable=True,
            )

        text = self.read_text(record)
        return ApprovalScope(
            path=record,
            allowed=extract_list_field(text, "Allowed files or surfaces:"),
            excluded=extract_list_field(text, "Excluded files or surfaces:"),
            diff_base=extract_field(text, "Approved diff base:"),
            machine_readable=False,
        )

    def check_approval_record_shape(self, approval_records: list[Path]) -> None:
        for record in approval_records:
            relpath = self.rel(record)
            finding = self.error if self.enforce_approval_scope else self.warn
            if record.suffix.lower() == ".json":
                try:
                    data = json.loads(self.read_text(record))
                except json.JSONDecodeError as exc:
                    finding(
                        "APPROVAL_RECORD_INVALID_JSON",
                        str(exc),
                        relpath,
                    )
                    continue
                if not isinstance(data, dict):
                    finding(
                        "APPROVAL_RECORD_INVALID_SHAPE",
                        "machine-readable approval record must be a JSON object",
                        relpath,
                    )
                    continue
                required_scalars = [
                    ("schema_version",),
                    ("record_kind",),
                    ("evidence_classification",),
                    ("approval_id",),
                    ("operation", "id"),
                    ("operation", "type"),
                    ("plan", "version"),
                    ("diff", "base"),
                    ("scope", "allowed_actions_mode"),
                    ("scope", "invalidation_rule"),
                    ("approval", "approved_by"),
                    ("approval", "approved_at"),
                ]
                required_lists = [
                    ("scope", "allowed_protected_changes"),
                    ("scope", "allowed_files_or_surfaces"),
                    ("scope", "excluded_files_or_surfaces"),
                    ("scope", "excluded_actions"),
                ]
                if data.get("schema_version") == 2:
                    required_lists.extend(
                        [
                            ("scope", "allowed_changed_fact_ids"),
                            ("scope", "allowed_architecture_areas"),
                            ("scope", "allowed_behavior_categories"),
                            ("scope", "excluded_semantic_effects"),
                            ("scope", "permitted_external_effects"),
                        ]
                    )
                elif data.get("schema_version") != 1:
                    finding(
                        "APPROVAL_RECORD_SCHEMA",
                        "approval record schema_version must be 1 or 2",
                        relpath,
                    )
                for key_path in required_scalars:
                    value = nested_json_value(data, key_path)
                    if value is None or value == "":
                        finding(
                            "APPROVAL_RECORD_FIELD_MISSING",
                            "machine-readable approval record is missing "
                            + ".".join(key_path),
                            relpath,
                        )
                for key_path in required_lists:
                    value = nested_json_value(data, key_path)
                    if not isinstance(value, list):
                        finding(
                            "APPROVAL_RECORD_FIELD_MISSING",
                            "machine-readable approval record requires list "
                            + ".".join(key_path),
                            relpath,
                        )
                if data.get("record_kind") != "alatyr-approval-record":
                    finding(
                        "APPROVAL_RECORD_KIND",
                        "record_kind must be alatyr-approval-record",
                        relpath,
                    )
                if data.get("evidence_classification") != "historical-record":
                    finding(
                        "APPROVAL_RECORD_EVIDENCE_CLASS",
                        "approval record must identify itself as historical-record evidence",
                        relpath,
                    )
                allowed = json_string_list(
                    nested_json_value(data, ("scope", "allowed_files_or_surfaces"))
                )
                if not allowed:
                    finding(
                        "APPROVAL_RECORD_SCOPE_EMPTY",
                        "machine-readable approval record has no allowed files or surfaces",
                        relpath,
                    )
                for value in allowed:
                    if is_placeholder(value) or not is_target_scope_pattern(value):
                        finding(
                            "APPROVAL_RECORD_SCOPE_INVALID",
                            f"allowed scope contains an unresolved or unsafe target pattern: {value}",
                            relpath,
                        )
                excluded = json_string_list(
                    nested_json_value(data, ("scope", "excluded_files_or_surfaces"))
                )
                for value in excluded:
                    if is_placeholder(value) or not is_target_scope_pattern(value):
                        finding(
                            "APPROVAL_RECORD_SCOPE_INVALID",
                            f"excluded scope contains an unresolved or unsafe target pattern: {value}",
                            relpath,
                        )
                continue

            text = self.read_text(record)
            for required in [
                "Approval ID:",
                "Operation ID:",
                "Plan version:",
                "Plan hash:",
                "Approved diff base:",
                "Allowed actions mode:",
                "Allowed files or surfaces:",
                "Excluded files or surfaces:",
                "Scope invalidation rule:",
                "Approved by:",
                "Approved at:",
                "Repository revision at approval:",
            ]:
                if required not in text:
                    finding(
                        "APPROVAL_RECORD_FIELD_MISSING",
                        f"approval record does not include {required}",
                        relpath,
                    )
            if "Evidence classification: `historical-record`" not in text:
                finding(
                    "APPROVAL_RECORD_EVIDENCE_CLASS",
                    "approval record must identify itself as historical-record evidence",
                    relpath,
                )
            for field in ["Allowed files or surfaces:"]:
                values = extract_list_field(text, field)
                if not values:
                    finding(
                        "APPROVAL_RECORD_SCOPE_EMPTY",
                        f"approval record has no explicit entries under {field}",
                        relpath,
                    )
                for value in values:
                    if is_placeholder(value) or not is_target_scope_pattern(value):
                        finding(
                            "APPROVAL_RECORD_SCOPE_INVALID",
                            f"{field} contains an unresolved or unsafe target pattern: {value}",
                            relpath,
                        )

    def check_approval_hash_evidence(
        self,
        approval_records: list[Path],
        *,
        compare_current_patch: bool = True,
    ) -> None:
        for record in approval_records:
            text = self.read_text(record)
            relpath = self.rel(record)
            if record.suffix.lower() == ".json":
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    continue
                plan_hash = normalize_hash_field(
                    str(nested_json_value(data, ("plan", "sha256")) or "")
                )
                plan_file = str(nested_json_value(data, ("plan", "file")) or "")
                patch_hash = normalize_hash_field(
                    str(nested_json_value(data, ("diff", "patch_sha256")) or "")
                )
                patch_changed = str(
                    nested_json_value(data, ("use_result", "patch_changed_after_approval"))
                    or ""
                ).lower()
                within_scope = str(
                    nested_json_value(data, ("use_result", "implementation_within_scope"))
                    or ""
                ).lower()
                plan_hash_field_present = nested_json_value(data, ("plan", "sha256")) is not None
                patch_hash_field_present = (
                    nested_json_value(data, ("diff", "patch_sha256")) is not None
                )
            else:
                plan_hash = normalize_hash_field(extract_field(text, "Plan hash:"))
                plan_file = extract_field(text, "Approved plan file:")
                patch_hash = normalize_hash_field(extract_field(text, "Patch hash:"))
                patch_changed = extract_field(
                    text, "Patch changed after approval:"
                ).lower()
                within_scope = extract_field(
                    text, "Implementation stayed within approved scope:"
                ).lower()
                plan_hash_field_present = "Plan hash:" in text
                patch_hash_field_present = "Patch hash:" in text

            if patch_changed:
                if patch_changed.startswith("yes"):
                    self.warn(
                        "APPROVAL_PATCH_CHANGED",
                        "approval record says the patch changed after approval",
                        relpath,
                    )
            if within_scope:
                if within_scope.startswith("no"):
                    self.warn(
                        "APPROVAL_SCOPE_DECLARED_BROKEN",
                        "approval record says implementation did not stay within scope",
                        relpath,
                    )

            if plan_hash:
                if not plan_file:
                    self.info(
                        "APPROVAL_PLAN_HASH_UNVERIFIED",
                        "plan hash is recorded but no Approved plan file is available for verification",
                        relpath,
                    )
                elif not is_target_relative_path(plan_file):
                    self.warn(
                        "APPROVAL_PLAN_FILE_OUTSIDE_TARGET",
                        f"approved plan file must be target-relative: {plan_file}",
                        relpath,
                    )
                else:
                    plan_path = self.target_path(plan_file)
                    if not plan_path.is_file():
                        self.warn(
                            "APPROVAL_PLAN_FILE_MISSING",
                            f"approved plan file is missing: {plan_file}",
                            relpath,
                        )
                    elif self.context.content_digest(plan_path) != plan_hash:
                        self.warn(
                            "APPROVAL_PLAN_HASH_MISMATCH",
                            f"approved plan file hash does not match Plan hash: {plan_file}",
                            relpath,
                        )
                    else:
                        self.info(
                            "APPROVAL_PLAN_HASH_MATCH",
                            f"approved plan file hash matches: {plan_file}",
                            relpath,
                        )
            elif plan_hash_field_present:
                self.info(
                    "APPROVAL_PLAN_HASH_NOT_VERIFIABLE",
                    "plan hash is unavailable or non-deterministic",
                    relpath,
                )

            if not patch_hash:
                if patch_hash_field_present:
                    self.info(
                        "APPROVAL_PATCH_HASH_NOT_VERIFIABLE",
                        "patch hash is unavailable or non-deterministic",
                        relpath,
                    )
                continue
            if not compare_current_patch or not self.diff_ref:
                self.info(
                    "APPROVAL_PATCH_HASH_SKIPPED",
                    "patch hash recorded but current-diff comparison was not requested",
                    relpath,
                )
                continue
            patch_text = git_diff_patch(self.target, self.diff_ref)
            if patch_text is None:
                self.warn(
                    "APPROVAL_PATCH_HASH_UNAVAILABLE",
                    f"could not compute git patch against {self.diff_ref}",
                    relpath,
                )
                continue
            actual_hash = hashlib.sha256(patch_text.encode("utf-8")).hexdigest()
            if actual_hash.lower() != patch_hash:
                self.warn(
                    "APPROVAL_PATCH_HASH_MISMATCH",
                    "current diff hash does not match approved Patch hash",
                    relpath,
                )
            else:
                self.info(
                    "APPROVAL_PATCH_HASH_MATCH",
                    "current diff hash matches approved Patch hash",
                    relpath,
                )

    def check_repository_binding(
        self,
        *,
        binding: Any,
        record_relpath: str,
        code_prefix: str,
        record_status: str,
        schema_version: int,
        implementation_surfaces: list[str],
    ) -> tuple[str | None, str | None]:
        if not isinstance(binding, dict):
            self.error(f"{code_prefix}_BINDING", "repository_binding must be an object", record_relpath)
            return None, None

        concrete = is_resolved_string

        binding_kind = binding.get("kind")
        binding_state = binding.get("binding_state")
        base_revision = binding.get("base_revision")
        result_revision = binding.get("result_revision")
        historical_status = record_status in {"completed", "validated", "superseded"}

        if schema_version >= 2:
            if binding_state not in {"provisional", "final"}:
                self.error(f"{code_prefix}_BINDING_STATE", "version-2 binding_state must be provisional or final", record_relpath)
            if historical_status and binding_state != "final":
                self.error(f"{code_prefix}_BINDING_STATE", f"{record_status} version-2 evidence requires a final binding", record_relpath)
            prior_bindings = binding.get("prior_bindings")
            if not isinstance(prior_bindings, list):
                self.error(f"{code_prefix}_BINDING_LINEAGE", "version-2 prior_bindings must be a list", record_relpath)
        else:
            self.warn(
                f"{code_prefix}_LEGACY_BINDING",
                "schema-version-1 repository binding is accepted as legacy evidence; attribution and rebinding lineage were not enforced",
                record_relpath,
            )

        if binding_kind in {"commit", "pull-request", "tree"}:
            base_resolved = git_resolve_object(self.target, str(base_revision), "commit") if concrete(base_revision) else None
            result_object_kind = "tree" if binding_kind == "tree" else "commit"
            result_resolved = (
                git_resolve_object(self.target, str(result_revision), result_object_kind)
                if concrete(result_revision)
                else None
            )
            for field, value, resolved in [
                ("base_revision", base_revision, base_resolved),
                ("result_revision", result_revision, result_resolved),
            ]:
                if resolved is None:
                    self.error(f"{code_prefix}_REVISION", f"{field} does not resolve to the required Git object: {value}", record_relpath)
                elif schema_version >= 2 and binding_state == "final" and str(value).casefold() != resolved.casefold():
                    self.error(f"{code_prefix}_REVISION_EXACT", f"final {field} must be the immutable object ID {resolved}", record_relpath)
            if binding_kind == "pull-request" and not concrete(binding.get("review_reference")):
                self.error(f"{code_prefix}_REVIEW_REFERENCE", "pull-request binding requires a stable review reference", record_relpath)
            if binding_kind in {"commit", "pull-request"} and base_resolved and result_resolved:
                ancestry = git_is_ancestor(self.target, base_resolved, result_resolved)
                if ancestry is False:
                    self.error(f"{code_prefix}_REVISION_ANCESTRY", "base_revision is not an ancestor of result_revision", record_relpath)
                elif ancestry is None:
                    self.error(f"{code_prefix}_REVISION_ANCESTRY", "could not verify repository-binding ancestry", record_relpath)
                if base_resolved == result_resolved and implementation_surfaces:
                    self.error(f"{code_prefix}_REVISION_EMPTY_RANGE", "base_revision equals result_revision despite recorded implementation surfaces", record_relpath)
        elif binding_kind == "selected-file-snapshot":
            selected_paths = binding.get("selected_paths")
            paths = selected_paths if isinstance(selected_paths, list) else []
            if not paths:
                self.error(f"{code_prefix}_SNAPSHOT_PATH", "selected-file snapshot requires paths", record_relpath)
            digest = hashlib.sha256()
            current_snapshot_valid = bool(paths)
            historical_binding = historical_status and (schema_version == 1 or binding_state == "final")
            for selected_path in sorted(set(paths)):
                path_is_valid = concrete(selected_path) and is_target_relative_path(str(selected_path))
                if not path_is_valid:
                    self.error(f"{code_prefix}_SNAPSHOT_PATH", f"invalid snapshot path: {selected_path}", record_relpath)
                    current_snapshot_valid = False
                    continue
                selected_file = self.target_path(str(selected_path))
                if not selected_file.is_file():
                    finding = self.warn if historical_binding else self.error
                    finding(
                        f"{code_prefix}_SNAPSHOT_HISTORICAL" if historical_binding else f"{code_prefix}_SNAPSHOT_PATH",
                        f"snapshot path is not present in the current worktree: {selected_path}",
                        record_relpath,
                    )
                    current_snapshot_valid = False
                    continue
                digest.update(str(selected_path).replace("\\", "/").encode("utf-8"))
                digest.update(b"\0")
                digest.update(self.read_bytes(selected_file))
                digest.update(b"\0")
            recorded_digest = binding.get("snapshot_sha256")
            digest_matches = current_snapshot_valid and concrete(recorded_digest) and recorded_digest.casefold() == digest.hexdigest()
            if current_snapshot_valid and not digest_matches:
                finding = self.warn if historical_binding else self.error
                finding(
                    f"{code_prefix}_SNAPSHOT_HISTORICAL" if historical_binding else f"{code_prefix}_SNAPSHOT_HASH",
                    "historical selected-file snapshot no longer matches current files" if historical_binding else "selected-file snapshot SHA-256 does not match current files",
                    record_relpath,
                )
            if historical_binding and not digest_matches and concrete(recorded_digest):
                head = git_head_revision(self.target)
                head_digest = git_snapshot_sha256(self.target, head or "", [str(path) for path in paths])
                if head and head_digest and head_digest.casefold() == str(recorded_digest).casefold():
                    self.info(
                        f"{code_prefix}_SNAPSHOT_COMMIT_CANDIDATE",
                        f"snapshot matches immutable commit {head}; rebind only through an explicit lineage-preserving update",
                        record_relpath,
                    )
        elif binding_kind == "unverified":
            if historical_status:
                finding = (
                    self.warn
                    if schema_version == 1 and code_prefix == "DEBUG_MODE"
                    else self.error
                )
                finding(f"{code_prefix}_UNVERIFIED_FINAL", f"{record_status} evidence requires a reproducible repository result binding", record_relpath)
            else:
                self.warn(f"{code_prefix}_UNVERIFIED", "record has no reproducible repository result binding", record_relpath)
        else:
            self.error(f"{code_prefix}_BINDING_KIND", f"unsupported repository binding kind: {binding_kind}", record_relpath)

        return binding_kind if isinstance(binding_kind, str) else None, result_revision if isinstance(result_revision, str) else None

    def check_policy_readme_projection(
        self,
        *,
        index: dict[str, Any],
        readme_relpath: str,
        fields: dict[str, str],
        code_prefix: str,
    ) -> None:
        readme_path = self.target_path(readme_relpath)
        if not readme_path.is_file():
            self.error(f"{code_prefix}_README_MISSING", "policy README is missing", readme_relpath)
            return
        text = self.read_text(readme_path)
        for label, index_field in fields.items():
            match = re.search(
                rf"^{re.escape(label)}:\s*`?([^`\n]+?)`?\s*$",
                text,
                flags=re.MULTILINE,
            )
            if not match:
                self.error(
                    f"{code_prefix}_FIELD_MISSING",
                    f"README does not declare {label}",
                    readme_relpath,
                )
                continue
            readme_value = match.group(1).strip()
            index_value = index.get(index_field)
            if not isinstance(index_value, str) or readme_value != index_value.strip():
                self.error(
                    f"{code_prefix}_DRIFT",
                    f"README {label} differs from index.{index_field}",
                    readme_relpath,
                )

    def check_engineering_evidence(self, manifest: ManifestData | None) -> None:
        validate_engineering_evidence(self, manifest)


    def check_project_knowledge(self, manifest: ManifestData | None) -> None:
        validate_project_knowledge_contract(self, manifest)


    def check_debug_mode(self, manifest: ManifestData | None) -> None:
        validate_debug_mode(self, manifest)


    def change_package_finding(
        self, code: str, message: str, path: str | None = None
    ) -> None:
        finding = self.error if self.enforce_change_package else self.warn
        finding(code, message, path)

    def check_change_package_index(self) -> None:
        relpath = ".ai/assistant/change-packages/index.json"
        path = self.target_path(relpath)
        if not path.exists():
            return
        data, data_error = self.context.read_json(path)
        if data_error is not None:
            self.error(
                "PACKAGE_INDEX_JSON",
                f"invalid change-package index: {data_error}",
                relpath,
            )
            return
        if not isinstance(data, dict):
            self.error("PACKAGE_INDEX_ROOT", "change-package index must be an object", relpath)
            return
        if data.get("schema_version") != 1:
            self.error("PACKAGE_INDEX_SCHEMA", "schema_version must be 1", relpath)
        if data.get("index_kind") != "target-change-package-index":
            self.error(
                "PACKAGE_INDEX_KIND",
                "index_kind must be target-change-package-index",
                relpath,
            )
        records = data.get("records")
        if not isinstance(records, list):
            self.error("PACKAGE_INDEX_RECORDS", "records must be a list", relpath)
            return
        seen: set[str] = set()
        for index, entry in enumerate(records):
            if not isinstance(entry, dict):
                self.error(
                    "PACKAGE_INDEX_ENTRY",
                    f"records[{index}] must be an object",
                    relpath,
                )
                continue
            for field in [
                "package_id",
                "status",
                "record",
                "changed_fact_ids",
                "canonical_owners",
                "project_areas",
                "evidence_quality",
                "approval_records",
                "active_workstream",
                "residual_risk",
            ]:
                if field not in entry:
                    self.error(
                        "PACKAGE_INDEX_FIELD",
                        f"records[{index}] missing {field}",
                        relpath,
                    )
            package_id = entry.get("package_id")
            if isinstance(package_id, str):
                if package_id in seen:
                    self.error(
                        "PACKAGE_INDEX_DUPLICATE",
                        f"duplicate package_id: {package_id}",
                        relpath,
                    )
                seen.add(package_id)
            record = entry.get("record")
            if isinstance(record, str) and not is_placeholder(record):
                if not is_target_relative_path(record) or not self.target_path(record).is_file():
                    self.error(
                        "PACKAGE_INDEX_RECORD_PATH",
                        f"records[{index}].record does not resolve inside target: {record}",
                        relpath,
                    )

    def resolve_change_packages(self) -> list[Path]:
        resolved: list[Path] = []
        for package in self.change_packages:
            try:
                package.relative_to(self.target)
            except ValueError:
                self.change_package_finding(
                    "PACKAGE_OUTSIDE_TARGET",
                    "selected change package must be inside the target repository",
                    str(package),
                )
                continue
            if not package.is_file():
                self.change_package_finding(
                    "PACKAGE_MISSING",
                    "selected change package does not exist",
                    self.rel(package),
                )
                continue
            resolved.append(package)
        return resolved

    def package_string(
        self,
        data: dict[str, Any],
        path: tuple[str, ...],
        source: str,
        *,
        allow_unavailable: bool = False,
    ) -> str:
        value = nested_json_value(data, path)
        if not isinstance(value, str) or not value.strip() or is_placeholder(value):
            self.change_package_finding(
                "PACKAGE_FIELD_MISSING",
                f"change package requires {'.'.join(path)}",
                source,
            )
            return ""
        if not allow_unavailable and "not available" in value.lower():
            self.change_package_finding(
                "PACKAGE_FIELD_UNAVAILABLE",
                f"change package requires available {'.'.join(path)}",
                source,
            )
            return ""
        return value.strip()

    def package_list(
        self,
        data: dict[str, Any],
        path: tuple[str, ...],
        source: str,
        *,
        required: bool = True,
    ) -> list[str]:
        value = nested_json_value(data, path)
        if not isinstance(value, list) or (required and not value):
            self.change_package_finding(
                "PACKAGE_LIST_MISSING",
                f"change package requires list {'.'.join(path)}",
                source,
            )
            return []
        result: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip() or is_placeholder(item):
                self.change_package_finding(
                    "PACKAGE_LIST_VALUE",
                    f"{'.'.join(path)}[{index}] must be a resolved string",
                    source,
                )
                continue
            result.append(item.strip())
        return result

    def package_snapshot_digest(
        self, paths: list[str], source: str, *, historical: bool = False
    ) -> str | None:
        digest = hashlib.sha256()
        for relpath in sorted(set(paths)):
            if not is_target_relative_path(relpath):
                self.change_package_finding(
                    "PACKAGE_SNAPSHOT_PATH",
                    f"snapshot path must be target-relative: {relpath}",
                    source,
                )
                return None
            path = self.target_path(relpath)
            if not path.is_file():
                finding = self.warn if historical else self.change_package_finding
                finding(
                    "PACKAGE_SNAPSHOT_HISTORICAL" if historical else "PACKAGE_SNAPSHOT_FILE",
                    f"snapshot path is not a file: {relpath}",
                    source,
                )
                return None
            digest.update(relpath.replace("\\", "/").encode("utf-8"))
            digest.update(b"\0")
            content = self.context.read_bytes_result(path)
            if content.value is None:
                self.change_package_finding(
                    "PACKAGE_SNAPSHOT_READ",
                    f"cannot read snapshot path {relpath}: {content.error}",
                    source,
                )
                return None
            digest.update(content.value)
            digest.update(b"\0")
        return digest.hexdigest()

    def check_change_packages(self) -> None:
        if self.enforce_change_package and not self.change_packages:
            self.error(
                "PACKAGE_SELECTION_REQUIRED",
                "--enforce-change-package requires one or more explicit "
                "--change-package values; historical records are not auto-selected",
            )
            return
        if not self.change_packages:
            self.info(
                "PACKAGE_CHECK_SKIPPED",
                "change-package validation skipped because no explicit record was selected",
            )
            return

        index_path = self.target_path(".ai/assistant/change-packages/index.json")
        indexed_records: set[str] = set()
        if index_path.is_file():
            index_data, index_error = self.context.read_json(index_path)
            if index_error is not None:
                index_data = {}
            if isinstance(index_data, dict):
                for entry in index_data.get("records", []):
                    if isinstance(entry, dict) and isinstance(entry.get("record"), str):
                        indexed_records.add(entry["record"])
        elif self.enforce_change_package:
            self.error(
                "PACKAGE_INDEX_REQUIRED",
                "strict change-package validation requires the target package index",
                ".ai/assistant/change-packages/index.json",
            )

        packages = self.resolve_change_packages()
        engineering_evidence_ids: set[str] = set()
        engineering_index_path = self.target_path(
            ".ai/project/engineering-evidence/index.json"
        )
        if engineering_index_path.is_file():
            engineering_index, engineering_error = self.context.read_json(
                engineering_index_path
            )
            if engineering_error is not None:
                engineering_index = {}
            if isinstance(engineering_index, dict):
                engineering_evidence_ids = {
                    entry.get("evidence_id")
                    for entry in engineering_index.get("records", [])
                    if isinstance(entry, dict)
                    and isinstance(entry.get("evidence_id"), str)
                }
        for package in packages:
            source = self.rel(package)
            if self.enforce_change_package and source not in indexed_records:
                self.error(
                    "PACKAGE_NOT_INDEXED",
                    "strictly selected change package is not present in the compact index",
                    source,
                )
            data, package_error = self.context.read_json(package)
            if package_error is not None:
                self.change_package_finding(
                    "PACKAGE_INVALID_JSON",
                    f"invalid change package: {package_error}",
                    source,
                )
                continue
            if not isinstance(data, dict):
                self.change_package_finding(
                    "PACKAGE_INVALID_ROOT",
                    "change package must be a JSON object",
                    source,
                )
                continue
            if data.get("schema_version") != 1:
                self.change_package_finding(
                    "PACKAGE_SCHEMA", "schema_version must be 1", source
                )
            if data.get("record_kind") != "alatyr-change-package":
                self.change_package_finding(
                    "PACKAGE_KIND", "record_kind must be alatyr-change-package", source
                )
            if data.get("evidence_classification") != "historical-record":
                self.change_package_finding(
                    "PACKAGE_EVIDENCE_CLASS",
                    "change package must identify historical-record evidence",
                    source,
                )

            package_id = self.package_string(data, ("package_id",), source)
            package_type = self.package_string(data, ("package_type",), source)
            if package_type and package_type not in {
                "architecture-segment",
                "business-capability",
                "cross-cutting-change",
                "migration",
                "public-contract",
                "other",
            }:
                self.change_package_finding(
                    "PACKAGE_TYPE", f"unsupported package_type: {package_type}", source
                )
            status = self.package_string(data, ("status",), source)
            if status and status not in {
                "proposed",
                "approved",
                "implementing",
                "validated",
                "complete",
                "blocked",
            }:
                self.change_package_finding(
                    "PACKAGE_STATUS", f"unsupported package status: {status}", source
                )
            self.package_string(data, ("activation_reason",), source)

            changed_facts = data.get("changed_facts")
            declared_fact_ids: list[str] = []
            if not isinstance(changed_facts, list) or not changed_facts:
                self.change_package_finding(
                    "PACKAGE_CHANGED_FACTS",
                    "change package requires changed_facts",
                    source,
                )
            else:
                for index, fact in enumerate(changed_facts):
                    if not isinstance(fact, dict):
                        self.change_package_finding(
                            "PACKAGE_CHANGED_FACT",
                            f"changed_facts[{index}] must be an object",
                            source,
                        )
                        continue
                    for field in ["id", "statement", "canonical_owner"]:
                        value = fact.get(field)
                        if not isinstance(value, str) or not value or is_placeholder(value):
                            self.change_package_finding(
                                "PACKAGE_CHANGED_FACT_FIELD",
                                f"changed_facts[{index}].{field} must be resolved",
                                source,
                            )
                    if isinstance(fact.get("id"), str):
                        declared_fact_ids.append(fact["id"])
                    invariants = fact.get("invariants")
                    if not isinstance(invariants, list) or not invariants:
                        self.change_package_finding(
                            "PACKAGE_INVARIANTS",
                            f"changed_facts[{index}] requires re-derived invariants",
                            source,
                        )

            approved_facts = self.package_list(
                data, ("approved_scope", "changed_fact_ids"), source
            )
            approved_areas = self.package_list(
                data, ("approved_scope", "architecture_areas"), source, required=False
            )
            approved_behaviors = self.package_list(
                data, ("approved_scope", "behavior_categories"), source
            )
            permitted_effects = self.package_list(
                data, ("approved_scope", "permitted_external_effects"), source, required=False
            )
            self.package_list(
                data, ("approved_scope", "excluded_semantic_effects"), source, required=False
            )
            allowed_paths = self.package_list(
                data, ("approved_scope", "allowed_files_or_surfaces"), source
            )
            excluded_paths = self.package_list(
                data, ("approved_scope", "excluded_files_or_surfaces"), source, required=False
            )
            actual_facts = self.package_list(
                data, ("actual_scope", "changed_fact_ids"), source
            )
            actual_areas = self.package_list(
                data, ("actual_scope", "architecture_areas"), source, required=False
            )
            actual_behaviors = self.package_list(
                data, ("actual_scope", "behavior_categories"), source
            )
            actual_effects = self.package_list(
                data, ("actual_scope", "external_effects"), source, required=False
            )
            actual_paths = self.package_list(
                data, ("actual_scope", "changed_paths"), source
            )

            for label, actual, approved in [
                ("changed fact", actual_facts, approved_facts),
                ("architecture area", actual_areas, approved_areas),
                ("behavior category", actual_behaviors, approved_behaviors),
                ("external effect", actual_effects, permitted_effects),
            ]:
                for value in sorted(set(actual) - set(approved)):
                    self.change_package_finding(
                        "PACKAGE_SEMANTIC_SCOPE",
                        f"actual {label} is outside approved scope: {value}",
                        source,
                    )
            for fact_id in sorted(set(actual_facts) - set(declared_fact_ids)):
                self.change_package_finding(
                    "PACKAGE_FACT_DECLARATION",
                    f"actual changed fact has no changed_facts record: {fact_id}",
                    source,
                )
            for path in actual_paths:
                if not is_target_scope_pattern(path):
                    self.change_package_finding(
                        "PACKAGE_ACTUAL_PATH", f"invalid target-relative path: {path}", source
                    )
                if not scope_entries_cover(path, allowed_paths):
                    self.change_package_finding(
                        "PACKAGE_PATH_SCOPE",
                        f"actual path is outside package allowed scope: {path}",
                        source,
                    )
                if scope_entries_cover(path, excluded_paths):
                    self.change_package_finding(
                        "PACKAGE_EXCLUDED_PATH",
                        f"actual path matches package excluded scope: {path}",
                        source,
                    )

            plan_file = self.package_string(
                data, ("plan", "file"), source, allow_unavailable=True
            )
            plan_hash_value = nested_json_value(data, ("plan", "sha256"))
            plan_hash = normalize_hash_field(plan_hash_value if isinstance(plan_hash_value, str) else "")
            if (
                isinstance(plan_hash_value, str)
                and plan_hash_value
                and not is_placeholder(plan_hash_value)
                and "not available" not in plan_hash_value.lower()
                and not plan_hash
            ):
                self.change_package_finding(
                    "PACKAGE_PLAN_HASH_FORMAT",
                    "plan.sha256 must be a SHA-256 digest or an unavailable value with reason",
                    source,
                )
            if plan_file and "not available" not in plan_file.lower():
                if not is_target_relative_path(plan_file):
                    self.change_package_finding(
                        "PACKAGE_PLAN_PATH", "plan file must be target-relative", source
                    )
                else:
                    plan_path = self.target_path(plan_file)
                    if not plan_path.is_file():
                        self.change_package_finding(
                            "PACKAGE_PLAN_MISSING", f"plan file does not exist: {plan_file}", source
                        )
                    elif plan_hash and self.context.content_digest(plan_path) != plan_hash:
                        self.change_package_finding(
                            "PACKAGE_PLAN_HASH", "plan SHA-256 does not match plan file", source
                        )

            approval_refs = self.package_list(
                data, ("approved_scope", "approval_records"), source, required=False
            )
            approval_semantic: dict[str, set[str]] = {
                "allowed_changed_fact_ids": set(),
                "allowed_architecture_areas": set(),
                "allowed_behavior_categories": set(),
                "permitted_external_effects": set(),
            }
            linked_approvals = 0
            for relpath in approval_refs:
                if not is_target_relative_path(relpath):
                    self.change_package_finding(
                        "PACKAGE_APPROVAL_PATH", f"approval path must be target-relative: {relpath}", source
                    )
                    continue
                approval_path = self.target_path(relpath)
                approval, approval_error = self.context.read_json(approval_path)
                if approval_error is not None:
                    self.change_package_finding(
                        "PACKAGE_APPROVAL_RECORD",
                        f"cannot load approval {relpath}: {approval_error}",
                        source,
                    )
                    continue
                if not isinstance(approval, dict):
                    self.change_package_finding(
                        "PACKAGE_APPROVAL_RECORD", f"approval is not an object: {relpath}", source
                    )
                    continue
                linked_approvals += 1
                scope = approval.get("scope")
                if not isinstance(scope, dict):
                    self.change_package_finding(
                        "PACKAGE_APPROVAL_SCOPE", f"approval has no scope object: {relpath}", source
                    )
                    continue
                for key in approval_semantic:
                    approval_semantic[key].update(json_string_list(scope.get(key)))
            if linked_approvals:
                comparisons = [
                    ("changed fact", actual_facts, approval_semantic["allowed_changed_fact_ids"]),
                    ("architecture area", actual_areas, approval_semantic["allowed_architecture_areas"]),
                    ("behavior category", actual_behaviors, approval_semantic["allowed_behavior_categories"]),
                    ("external effect", actual_effects, approval_semantic["permitted_external_effects"]),
                ]
                for label, actual, approved in comparisons:
                    for value in sorted(set(actual) - approved):
                        self.change_package_finding(
                            "PACKAGE_APPROVAL_SEMANTIC_SCOPE",
                            f"actual {label} is not covered by linked approval records: {value}",
                            source,
                        )

            companion = data.get("companion_decisions")
            missing_companion = False
            if not isinstance(companion, list) or not companion:
                self.change_package_finding(
                    "PACKAGE_COMPANION_DECISIONS",
                    "change package requires companion_decisions",
                    source,
                )
            else:
                for index, decision in enumerate(companion):
                    if not isinstance(decision, dict):
                        self.change_package_finding(
                            "PACKAGE_COMPANION_DECISION",
                            f"companion_decisions[{index}] must be an object",
                            source,
                        )
                        continue
                    state = decision.get("decision")
                    if state not in {"updated", "not-required", "missing"}:
                        self.change_package_finding(
                            "PACKAGE_COMPANION_STATE",
                            f"companion_decisions[{index}].decision is invalid",
                            source,
                        )
                    if state == "missing":
                        missing_companion = True
                    for field in ["surface_type", "owner_or_path", "reason", "evidence"]:
                        value = decision.get(field)
                        if not isinstance(value, str) or not value or is_placeholder(value):
                            self.change_package_finding(
                                "PACKAGE_COMPANION_FIELD",
                                f"companion_decisions[{index}].{field} must be resolved",
                                source,
                            )

            corrections = data.get("discoveries_and_corrections")
            if not isinstance(corrections, list):
                self.change_package_finding(
                    "PACKAGE_CORRECTIONS", "discoveries_and_corrections must be a list", source
                )
            else:
                for index, correction in enumerate(corrections):
                    if not isinstance(correction, dict):
                        self.change_package_finding(
                            "PACKAGE_CORRECTION", f"correction[{index}] must be an object", source
                        )
                        continue
                    for field in ["id", "statement", "approval_action", "evidence"]:
                        value = correction.get(field)
                        if not isinstance(value, str) or not value or is_placeholder(value):
                            self.change_package_finding(
                                "PACKAGE_CORRECTION_FIELD",
                                f"correction[{index}].{field} must be resolved",
                                source,
                            )
                    correction_facts = correction.get("changed_fact_ids")
                    if not isinstance(correction_facts, list):
                        self.change_package_finding(
                            "PACKAGE_CORRECTION_FACTS",
                            f"correction[{index}].changed_fact_ids must be a list",
                            source,
                        )
                    else:
                        for fact_id in correction_facts:
                            if fact_id not in declared_fact_ids:
                                self.change_package_finding(
                                    "PACKAGE_CORRECTION_FACT",
                                    f"correction[{index}] references undeclared fact: {fact_id}",
                                    source,
                                )
                    if correction.get("kind") not in {"discovery", "correction"}:
                        self.change_package_finding(
                            "PACKAGE_CORRECTION_KIND", f"correction[{index}].kind is invalid", source
                        )
                    impact = correction.get("scope_impact")
                    if impact not in {"none", "within-approved-scope", "reapproval-required"}:
                        self.change_package_finding(
                            "PACKAGE_CORRECTION_SCOPE", f"correction[{index}].scope_impact is invalid", source
                        )
                    action = correction.get("approval_action")
                    if impact == "reapproval-required" and (
                        not isinstance(action, str)
                        or not action
                        or "not required" in action.lower()
                    ):
                        self.change_package_finding(
                            "PACKAGE_REAPPROVAL_MISSING",
                            f"correction[{index}] requires a reapproval action",
                            source,
                        )

            residual_risks = self.package_list(
                data, ("validation", "residual_risks"), source, required=False
            )
            if missing_companion and not residual_risks and status != "blocked":
                self.change_package_finding(
                    "PACKAGE_MISSING_COMPANION_RISK",
                    "missing companion decisions require blocked status or residual risk",
                    source,
                )

            quality = self.package_string(data, ("provenance", "evidence_quality"), source)
            claim = self.package_string(data, ("provenance", "public_claim_strength"), source)
            before = self.package_string(
                data, ("provenance", "before_revision"), source, allow_unavailable=True
            )
            after = self.package_string(
                data, ("provenance", "after_revision"), source, allow_unavailable=True
            )
            for field in ["working_tree_at_start", "working_tree_at_validation"]:
                state = self.package_string(
                    data, ("provenance", field), source, allow_unavailable=True
                )
                normalized_state = state.split(" ", 1)[0].lower()
                if normalized_state not in {"clean", "dirty", "unavailable"}:
                    self.change_package_finding(
                        "PACKAGE_WORKTREE_STATE",
                        f"provenance.{field} must start with clean, dirty, or unavailable",
                        source,
                    )
            self.package_string(
                data,
                ("provenance", "unrelated_changes_handling"),
                source,
                allow_unavailable=True,
            )
            if quality in {"git-range", "pull-request"}:
                before_resolved = git_resolve_ref(self.target, before)
                after_resolved = git_resolve_ref(self.target, after)
                if before_resolved is None:
                    self.change_package_finding(
                        "PACKAGE_BEFORE_REF", f"before revision does not resolve: {before}", source
                    )
                if after_resolved is None:
                    self.change_package_finding(
                        "PACKAGE_AFTER_REF", f"after revision does not resolve: {after}", source
                    )
                if before_resolved and after_resolved:
                    ancestry = git_is_ancestor(self.target, before_resolved, after_resolved)
                    if ancestry is not True:
                        self.change_package_finding(
                            "PACKAGE_REVISION_ANCESTRY",
                            "before_revision must be an ancestor of after_revision",
                            source,
                        )
                range_paths = git_range_changed_files(self.target, before, after)
                if range_paths is None:
                    self.change_package_finding(
                        "PACKAGE_GIT_RANGE", "cannot compute declared Git range", source
                    )
                elif set(range_paths) != set(actual_paths):
                    missing = sorted(set(range_paths) - set(actual_paths))
                    extra = sorted(set(actual_paths) - set(range_paths))
                    self.change_package_finding(
                        "PACKAGE_RANGE_PATHS",
                        f"actual paths do not match Git range; missing={missing}, extra={extra}",
                        source,
                    )
                if quality == "pull-request":
                    pull_request = self.package_string(
                        data, ("provenance", "pull_request"), source
                    )
                    if pull_request.lower() in {"none", "not applicable", "n/a"}:
                        self.change_package_finding(
                            "PACKAGE_PULL_REQUEST",
                            "pull-request evidence requires a stable pull-request reference",
                            source,
                        )
                if claim not in {"strong", "limited", "unsupported"}:
                    self.change_package_finding(
                        "PACKAGE_PUBLIC_CLAIM",
                        f"{quality} evidence has invalid public claim strength: {claim}",
                        source,
                    )
            elif quality == "selected-file-snapshot":
                snapshot_paths = self.package_list(
                    data, ("provenance", "selected_file_snapshot", "paths"), source
                )
                recorded_digest = self.package_string(
                    data, ("provenance", "selected_file_snapshot", "digest"), source
                ).lower()
                historical_snapshot = status in {"validated", "complete"}
                computed_digest = self.package_snapshot_digest(
                    snapshot_paths, source, historical=historical_snapshot
                )
                if computed_digest and recorded_digest != computed_digest:
                    if historical_snapshot:
                        self.warn(
                            "PACKAGE_SNAPSHOT_HISTORICAL",
                            "historical selected-file snapshot no longer matches current files",
                            source,
                        )
                    else:
                        self.change_package_finding(
                            "PACKAGE_SNAPSHOT_HASH",
                            "selected-file snapshot SHA-256 does not match current files",
                            source,
                        )
                if claim not in {"limited", "unsupported"}:
                    self.change_package_finding(
                        "PACKAGE_PUBLIC_CLAIM",
                        "selected-file-snapshot cannot support a strong public claim",
                        source,
                    )
            elif quality == "unverified":
                if claim != "unsupported":
                    self.change_package_finding(
                        "PACKAGE_PUBLIC_CLAIM",
                        "unverified evidence must declare unsupported public claim strength",
                        source,
                    )
            else:
                self.change_package_finding(
                    "PACKAGE_EVIDENCE_QUALITY",
                    f"unsupported evidence quality: {quality}",
                    source,
                )

            architecture = data.get("architecture_discussion")
            if not isinstance(architecture, dict):
                self.change_package_finding(
                    "PACKAGE_ARCHITECTURE_DISCUSSION",
                    "architecture_discussion must be an object",
                    source,
                )
            else:
                applies_value = architecture.get("applies")
                applies = applies_value is True or (
                    isinstance(applies_value, str) and applies_value.lower() == "yes"
                )
                if applies_value not in {True, False, "yes", "no"}:
                    self.change_package_finding(
                        "PACKAGE_ARCHITECTURE_APPLIES",
                        "architecture_discussion.applies must be a boolean or yes/no",
                        source,
                    )
                if package_type == "architecture-segment" and not applies:
                    self.change_package_finding(
                        "PACKAGE_ARCHITECTURE_REQUIRED",
                        "architecture-segment package requires architecture discussion evidence",
                        source,
                    )
                if applies:
                    for field in ["problem_and_boundary", "selected_direction", "decision_status"]:
                        value = architecture.get(field)
                        if not isinstance(value, str) or not value or is_placeholder(value):
                            self.change_package_finding(
                                "PACKAGE_ARCHITECTURE_FIELD",
                                f"architecture_discussion.{field} must be resolved",
                                source,
                            )
                    for field in ["alternatives", "sources", "assumptions_or_disagreement"]:
                        if not isinstance(architecture.get(field), list):
                            self.change_package_finding(
                                "PACKAGE_ARCHITECTURE_LIST",
                                f"architecture_discussion.{field} must be a list",
                                source,
                            )
                if not isinstance(architecture.get("raw_chat_retained"), bool):
                    self.change_package_finding(
                        "PACKAGE_RAW_CHAT",
                        "raw_chat_retained must be a boolean",
                        source,
                    )
                elif architecture.get("raw_chat_retained") is True:
                    self.warn(
                        "PACKAGE_RAW_CHAT_REVIEW",
                        "raw chat retention requires target privacy, retention, and redaction review",
                        source,
                    )

            linked_evidence = self.package_list(
                data, ("engineering_evidence_ids",), source, required=False
            )
            for evidence_id in linked_evidence:
                if evidence_id.casefold() in {"none", "not applicable", "n/a"}:
                    continue
                if evidence_id not in engineering_evidence_ids:
                    self.change_package_finding(
                        "PACKAGE_ENGINEERING_EVIDENCE_REFERENCE",
                        f"change package references unknown engineering evidence: {evidence_id}",
                        source,
                    )

            self.info(
                "PACKAGE_CHECKED",
                f"checked change package {package_id or source}; structural checks do not prove semantic completeness or architecture correctness",
                source,
            )

    def check_framework_baseline(
        self,
        manifest: ManifestData | None = None,
    ) -> None:
        if not self.framework_source:
            self.info(
                "FRAMEWORK_COMPARE_SKIPPED",
                "framework baseline comparison skipped because --framework-source was not provided",
            )
            return
        source_framework = self.framework_source / "framework"
        target_framework = self.target_path(".ai/framework")
        if not source_framework.is_dir():
            self.error(
                "FRAMEWORK_SOURCE_MISSING",
                f"framework source directory missing: {source_framework}",
            )
            return
        if not target_framework.is_dir():
            return

        if manifest is None:
            manifest_path = self.target_path(".ai/alatyr.yaml")
            manifest = parse_manifest(self.context.text_source(manifest_path))
        pack_scalar = manifest.scalars.get(("framework", "pack"))
        framework_pack = pack_scalar.value if pack_scalar else "complete"
        if framework_pack in {"kernel", "core", "standard"}:
            inventory_path = target_framework / "file-inventory.json"
            inventory = self.load_json_object(inventory_path, "FRAMEWORK_INVENTORY")
            if inventory is None:
                self.error(
                    "FRAMEWORK_PACK_INVENTORY_MISSING",
                    "selective framework pack requires a projected file inventory",
                    ".ai/framework/file-inventory.json",
                )
                return
            if inventory.get("framework_pack") != framework_pack:
                self.error(
                    "FRAMEWORK_PACK_INVENTORY_DRIFT",
                    "framework inventory pack differs from the adapter manifest",
                    ".ai/framework/file-inventory.json",
                )
            entries = inventory.get("files")
            if not isinstance(entries, list):
                self.error(
                    "FRAMEWORK_PACK_INVENTORY_SHAPE",
                    "framework pack inventory files must be a list",
                    ".ai/framework/file-inventory.json",
                )
                return
            expected: dict[str, dict[str, Any]] = {}
            for index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    self.error(
                        "FRAMEWORK_PACK_INVENTORY_ENTRY",
                        f"framework pack inventory entry {index} must be an object",
                        ".ai/framework/file-inventory.json",
                    )
                    continue
                relpath = entry.get("path")
                digest = entry.get("sha256")
                framework_relpath = (
                    relpath[len("framework/") :]
                    if isinstance(relpath, str) and relpath.startswith("framework/")
                    else None
                )
                if (
                    not isinstance(framework_relpath, str)
                    or not framework_relpath
                    or "\\" in framework_relpath
                    or Path(framework_relpath).is_absolute()
                    or any(part in {"", ".", ".."} for part in framework_relpath.split("/"))
                    or not isinstance(digest, str)
                    or len(digest) != 64
                ):
                    self.error(
                        "FRAMEWORK_PACK_INVENTORY_ENTRY",
                        f"framework pack inventory entry {index} is invalid",
                        ".ai/framework/file-inventory.json",
                    )
                    continue
                if framework_relpath in expected:
                    self.error(
                        "FRAMEWORK_PACK_INVENTORY_ENTRY",
                        f"framework pack inventory entry {index} duplicates {framework_relpath}",
                        ".ai/framework/file-inventory.json",
                    )
                    continue
                expected[framework_relpath] = entry
            expected_names = set(expected) | {"file-inventory.json"}
            try:
                source_expected_names, source_projected_registry, source_expected_hashes = (
                    source_pack_expectation(source_framework, framework_pack)
                )
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                self.warn(
                    "FRAMEWORK_SOURCE_PACK_INVALID",
                    f"cannot resolve source framework pack: {exc}",
                    ".ai/framework/framework-packs.json",
                )
                source_expected_names = expected_names
                source_projected_registry = None
                source_expected_hashes = {}
            if expected_names != source_expected_names:
                self.framework_drift_detected = True
                self.warn(
                    "FRAMEWORK_PACK_SELECTION_DRIFT",
                    "installed framework pack file set differs from the source pack catalog",
                    ".ai/framework/file-inventory.json",
                )
            target_registry, registry_error = self.context.read_json(
                target_framework / "rule-registry.json"
            )
            if registry_error is not None:
                self.warn(
                    "FRAMEWORK_PACK_REGISTRY_INVALID",
                    f"cannot read projected rule registry: {registry_error}",
                    ".ai/framework/rule-registry.json",
                )
            elif (
                source_projected_registry is not None
                and target_registry != source_projected_registry
            ):
                self.framework_drift_detected = True
                self.warn(
                    "FRAMEWORK_PACK_REGISTRY_DRIFT",
                    "installed projected rule registry differs from the source pack",
                    ".ai/framework/rule-registry.json",
                )
            target_names = {
                path.relative_to(target_framework).as_posix()
                for path in target_framework.rglob("*")
                if path.is_file() and path.suffix in {".md", ".json"}
            }
            for name in sorted(expected_names - target_names):
                self.framework_drift_detected = True
                self.warn(
                    "FRAMEWORK_FILE_MISSING",
                    f"installed framework pack is missing {name}",
                    f".ai/framework/{name}",
                )
            for name in sorted(target_names - expected_names):
                self.framework_drift_detected = True
                self.warn(
                    "FRAMEWORK_FILE_EXTRA",
                    f"installed framework has file outside selected pack: {name}",
                    f".ai/framework/{name}",
                )
            for name, entry in sorted(expected.items()):
                target_path = target_framework / name
                if not target_path.is_file():
                    continue
                actual_digest = self.context.content_digest(target_path)
                source_digest = source_expected_hashes.get(name)
                if source_digest is not None and entry["sha256"] != source_digest:
                    self.framework_drift_detected = True
                    self.warn(
                        "FRAMEWORK_PACK_INVENTORY_DIGEST_DRIFT",
                        f"framework inventory digest differs from source projection: {name}",
                        ".ai/framework/file-inventory.json",
                    )
                baseline_digest = source_digest or entry["sha256"]
                if actual_digest != baseline_digest:
                    self.framework_drift_detected = True
                    self.warn(
                        "FRAMEWORK_FILE_DRIFT",
                        f"installed framework pack file differs from source projection: {name}",
                        f".ai/framework/{name}",
                    )
            source_inventory_digest = source_expected_hashes.get("file-inventory.json")
            if (
                source_inventory_digest is not None
                and self.context.content_digest(inventory_path)
                != source_inventory_digest
            ):
                self.framework_drift_detected = True
                self.warn(
                    "FRAMEWORK_PACK_INVENTORY_CONTENT_DRIFT",
                    "installed framework pack inventory differs from source projection",
                    ".ai/framework/file-inventory.json",
                )
            return

        source_files = {
            path.relative_to(source_framework).as_posix(): path
            for path in source_framework.rglob("*")
            if path.is_file() and path.suffix in {".md", ".json"}
        }
        target_files = {
            path.relative_to(target_framework).as_posix(): path
            for path in target_framework.rglob("*")
            if path.is_file() and path.suffix in {".md", ".json"}
        }
        for name in sorted(set(source_files) - set(target_files)):
            self.framework_drift_detected = True
            self.warn(
                "FRAMEWORK_FILE_MISSING",
                f"installed framework is missing source file {name}",
                f".ai/framework/{name}",
            )
        for name in sorted(set(target_files) - set(source_files)):
            self.framework_drift_detected = True
            self.warn(
                "FRAMEWORK_FILE_EXTRA",
                f"installed framework has file not present in source baseline: {name}",
                f".ai/framework/{name}",
            )
        for name in sorted(set(source_files) & set(target_files)):
            if sha256(source_files[name]) != self.context.content_digest(
                target_files[name]
            ):
                self.framework_drift_detected = True
                self.warn(
                    "FRAMEWORK_FILE_DRIFT",
                    f"installed framework file differs from source baseline: {name}",
                    f".ai/framework/{name}",
                )

    def check_migration_diff_evidence(self) -> None:
        if not self.migration_diff:
            if self.framework_drift_detected:
                self.warn(
                    "MIGRATION_DIFF_MISSING",
                    "framework drift was detected but no --migration-diff evidence was provided",
                )
            else:
                self.info(
                    "MIGRATION_DIFF_SKIPPED",
                    "migration diff evidence skipped because --migration-diff was not provided",
                )
            return
        if not self.migration_diff.is_file():
            self.error(
                "MIGRATION_DIFF_FILE_MISSING",
                f"migration diff file does not exist: {self.migration_diff}",
            )
            return

        try:
            text = self.migration_diff.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            self.error(
                "MIGRATION_DIFF_INVALID",
                f"cannot read explicitly selected migration diff: {exc}",
                str(self.migration_diff),
            )
            return
        sections = markdown_sections(text)
        required_sections = [
            "Affected Rule Categories",
            "Affected Task Profiles",
            "Migration Action Hints",
            "Required Target Actions",
        ]
        for section in required_sections:
            if section not in sections:
                self.warn(
                    "MIGRATION_DIFF_SECTION_MISSING",
                    f"migration diff is missing section: {section}",
                    str(self.migration_diff),
                )

        changed_rules = section_items(sections.get("Changed Rules", []))
        added_rules = section_items(sections.get("Added Rules", []))
        removed_rules = section_items(sections.get("Removed Rules", []))
        categories = section_items(sections.get("Affected Rule Categories", []))
        hints = section_items(sections.get("Migration Action Hints", []))
        if changed_rules or added_rules or removed_rules or categories:
            self.info(
                "MIGRATION_DIFF_IMPACT",
                "migration diff impact: "
                f"added_rules={len(added_rules)} "
                f"changed_rules={len(changed_rules)} "
                f"removed_rules={len(removed_rules)} "
                f"categories={len(categories)} "
                f"action_hints={len(hints)}",
                str(self.migration_diff),
            )
        elif self.framework_drift_detected:
            self.warn(
                "MIGRATION_DIFF_NO_RULE_IMPACT",
                "framework drift exists but migration diff reports no rule/category impact",
                str(self.migration_diff),
            )
        else:
            self.info(
                "MIGRATION_DIFF_NO_IMPACT",
                "migration diff reports no rule/category impact",
                str(self.migration_diff),
            )


def load_validator_config(
    target: Path, config_path: Path | None
) -> tuple[AdapterValidatorConfig, list[Finding]]:
    findings: list[Finding] = []
    if config_path:
        path = config_path
    else:
        path = target / ".ai" / "assistant" / "validator-config.json"
        if not path.is_file():
            return AdapterValidatorConfig(), findings

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        findings.append(
            Finding("warning", "VALIDATOR_CONFIG_MISSING", f"config file missing: {path}")
        )
        return AdapterValidatorConfig(source=path), findings
    except json.JSONDecodeError as exc:
        findings.append(
            Finding(
                "error",
                "VALIDATOR_CONFIG_INVALID_JSON",
                f"invalid validator config JSON: {exc}",
                str(path),
            )
        )
        return AdapterValidatorConfig(source=path), findings

    if not isinstance(data, dict):
        findings.append(
            Finding(
                "error",
                "VALIDATOR_CONFIG_INVALID_SHAPE",
                "validator config must be a JSON object",
                str(path),
            )
        )
        return AdapterValidatorConfig(source=path), findings

    config = AdapterValidatorConfig(source=path)
    schema_version = data.get("schema_version")
    if schema_version not in (None, 1):
        findings.append(
            Finding(
                "warning",
                "VALIDATOR_CONFIG_SCHEMA_VERSION",
                f"unsupported validator config schema_version: {schema_version}",
                str(path),
            )
        )

    config.allow_local_path_patterns = string_list_config(
        data, "allow_local_path_patterns", path, findings
    )
    required_coverage = string_list_config(
        data, "required_checker_coverage", path, findings
    )
    if required_coverage:
        config.required_checker_coverage = {
            term.lower(): f"{term} coverage" for term in required_coverage
        }

    severity_overrides = data.get("severity_overrides")
    if severity_overrides is None:
        config.severity_overrides = {}
    elif isinstance(severity_overrides, dict):
        parsed: dict[str, str] = {}
        for code, level in severity_overrides.items():
            if not isinstance(code, str) or not isinstance(level, str):
                findings.append(
                    Finding(
                        "warning",
                        "VALIDATOR_CONFIG_SEVERITY_OVERRIDE",
                        "severity_overrides entries must map strings to strings",
                        str(path),
                    )
                )
                continue
            parsed[code] = level
        config.severity_overrides = parsed
    else:
        findings.append(
            Finding(
                "warning",
                "VALIDATOR_CONFIG_SEVERITY_OVERRIDES",
                "severity_overrides must be an object",
                str(path),
            )
        )
        config.severity_overrides = {}

    deviations = data.get("accepted_deviations")
    parsed_deviations: list[AcceptedDeviation] = []
    if deviations is None:
        pass
    elif isinstance(deviations, list):
        for item in deviations:
            if not isinstance(item, dict) or not isinstance(item.get("code"), str):
                findings.append(
                    Finding(
                        "warning",
                        "VALIDATOR_CONFIG_ACCEPTED_DEVIATION",
                        "accepted_deviations entries must be objects with code",
                        str(path),
                    )
                )
                continue
            item_path = item.get("path")
            reason = item.get("reason", "")
            parsed_deviations.append(
                AcceptedDeviation(
                    code=item["code"],
                    path=item_path if isinstance(item_path, str) else None,
                    reason=reason if isinstance(reason, str) else "",
                )
            )
    else:
        findings.append(
            Finding(
                "warning",
                "VALIDATOR_CONFIG_ACCEPTED_DEVIATIONS",
                "accepted_deviations must be a list",
                str(path),
            )
        )
    config.accepted_deviations = parsed_deviations
    findings.append(
        Finding("info", "VALIDATOR_CONFIG_LOADED", f"loaded validator config: {path}")
    )
    return config, findings


def string_list_config(
    data: dict[str, Any],
    key: str,
    path: Path,
    findings: list[Finding],
) -> list[str]:
    value = data.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        findings.append(
            Finding(
                "warning",
                "VALIDATOR_CONFIG_LIST_FIELD",
                f"{key} must be a list of strings",
                str(path),
            )
        )
        return []
    return value


def adapter_health_state(
    findings: list[Finding],
    *,
    validation_phase: str = "acceptance",
    installation_state: str = "unverified",
    validation_scope: str = "full",
) -> str:
    if any(finding.code in {"TARGET_MISSING", "TARGET_NOT_DIRECTORY"} for finding in findings):
        return "unverified"
    if any(is_blocking_finding(finding) for finding in findings):
        return "blocked"
    if (
        installation_state != "accepted"
        or validation_phase != "acceptance"
        or validation_scope != "full"
    ):
        return "unverified"
    if any(finding.level == "warning" for finding in findings):
        return "attention"
    return "ready"


def target_installation_state(
    target: Path,
    manifest: ManifestData | None = None,
    *,
    context: ValidationContext | None = None,
) -> str:
    """Read installation state only when its transition evidence is valid."""

    context = context or ValidationContext(target)
    manifest_path = target / ".ai" / "alatyr.yaml"
    if not manifest_path.is_file():
        return "unverified"
    if manifest is None:
        try:
            manifest = parse_manifest(context.text_source(manifest_path))
        except (OSError, UnicodeError, ValueError):
            return "unverified"
    scalar = manifest.scalars.get(("installation", "state"))
    if scalar is None or scalar.value not in INSTALLATION_STATES:
        return "unverified"
    record_scalar = manifest.scalars.get(("installation", "state_record"))
    if record_scalar is None or not is_target_relative_path(record_scalar.value):
        return "unverified"
    try:
        record_path = context.resolve_path(target / record_scalar.value)
        record, record_error = context.read_json(record_path)
        if record_error is not None:
            return "unverified"
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return "unverified"
    if validate_installation_state_record(record, manifest_state=scalar.value):
        return "unverified"
    return scalar.value


def prioritized_repair_operations(findings: list[Finding]) -> list[str]:
    order = {"error": 0, "warning": 1, "info": 2}
    operations: list[str] = []
    for finding in sorted(findings, key=lambda item: (order[item.level], item.code)):
        if finding.level not in {"error", "warning"}:
            continue
        operation = repair_operation_for(finding.code)
        if operation not in operations:
            operations.append(operation)
        if len(operations) == 3:
            break
    return operations


def render_summary(
    findings: list[Finding],
    *,
    strict_warnings: bool,
    validation_phase: str,
    installation_state: str = "unverified",
    validation_scope: str = "full",
) -> int:
    order = {"error": 0, "warning": 1, "info": 2}
    for finding in sorted(findings, key=lambda item: (order[item.level], item.code, item.path or "")):
        print(finding.render())

    errors = sum(1 for finding in findings if finding.level == "error")
    warnings = sum(1 for finding in findings if finding.level == "warning")
    infos = sum(1 for finding in findings if finding.level == "info")
    blocking_warnings = sum(
        1
        for finding in findings
        if finding.level == "warning" and is_blocking_finding(finding)
    )
    health = adapter_health_state(
        findings,
        validation_phase=validation_phase,
        installation_state=installation_state,
        validation_scope=validation_scope,
    )
    print(
        f"\nSummary: errors={errors} warnings={warnings} "
        f"blocking_warnings={blocking_warnings} info={infos}"
    )
    print(f"Alatyr adapter health: {health}")
    print(f"Validation phase: {validation_phase}")
    print(f"Validation scope: {validation_scope}")
    if validation_phase == "migration-staging":
        print("Acceptance eligible: no; rerun in acceptance phase after resolving active placeholders")
    elif validation_scope == "changed":
        print("Acceptance eligible: no; rerun with --validation-scope full for final evidence")
    repairs = prioritized_repair_operations(findings)
    if repairs:
        print("Suggested repair operations: " + ", ".join(repairs))

    if errors or blocking_warnings:
        return 1
    if strict_warnings and warnings:
        return 1
    return 0


def result_code(findings: list[Finding], *, strict_warnings: bool) -> int:
    errors = sum(1 for finding in findings if finding.level == "error")
    warnings = sum(1 for finding in findings if finding.level == "warning")
    if errors or any(is_blocking_finding(finding) for finding in findings):
        return 1
    if strict_warnings and warnings:
        return 1
    return 0


def findings_payload(
    findings: list[Finding],
    *,
    target: Path,
    strict_warnings: bool,
    validation_phase: str = "acceptance",
    installation_state: str | None = None,
    validation_scope: str = "full",
) -> dict[str, Any]:
    errors = sum(1 for finding in findings if finding.level == "error")
    warnings = sum(1 for finding in findings if finding.level == "warning")
    infos = sum(1 for finding in findings if finding.level == "info")
    blocking_warnings = sum(
        1
        for finding in findings
        if finding.level == "warning" and is_blocking_finding(finding)
    )
    exit_code = result_code(findings, strict_warnings=strict_warnings)
    observed_revision = git_head_revision(target)
    observed_branch = git_branch_name(target)
    observed_at = datetime.now(timezone.utc).isoformat()
    resolved_installation_state = installation_state or target_installation_state(target)
    unresolved_active = sum(
        1
        for finding in findings
        if finding.code in {"PLACEHOLDER_UNRESOLVED", "PLACEHOLDER_STAGING_UNRESOLVED"}
    )
    acceptance_eligible = (
        resolved_installation_state == "accepted"
        and validation_phase == "acceptance"
        and validation_scope == "full"
        and exit_code == 0
    )
    return {
        "schema_version": 3,
        "tool": "validate_target_adapter",
        "target": str(target),
        "evidence": {
            "basis": "current-state-structural",
            "observed_at": observed_at,
            "observed_revision": observed_revision,
            "observed_branch": observed_branch,
            "installation_state": resolved_installation_state,
            "historical_actions_verified": False,
            "limitation": (
                "Current files do not prove historical installation, update, "
                "approval, or validation actions without dated records."
            ),
        },
        "status": (
            "failed"
            if exit_code
            else "staged"
            if validation_phase == "migration-staging"
            else "passed"
        ),
        "validation_phase": validation_phase,
        "validation_scope": validation_scope,
        "installation_state": resolved_installation_state,
        "placeholder_validation": {
            "mode": "staging-only" if validation_phase == "migration-staging" else "strict",
            "unresolved_active": unresolved_active,
            "acceptance_eligible": acceptance_eligible,
            "required_final_phase": "acceptance",
            "required_final_scope": "full",
        },
        "adapter_health": {
            "state": adapter_health_state(
                findings,
                validation_phase=validation_phase,
                installation_state=resolved_installation_state,
                validation_scope=validation_scope,
            ),
            "observed_at": observed_at,
            "observed_revision": observed_revision,
            "observed_branch": observed_branch,
            "repair_operations": prioritized_repair_operations(findings),
            "automatic_repair_performed": False,
        },
        "strict_warnings": strict_warnings,
        "counts": {
            "errors": errors,
            "warnings": warnings,
            "blocking_warnings": blocking_warnings,
            "info": infos,
        },
        "exit_code": exit_code,
        "findings": [
            finding.to_json()
            for finding in sorted(
                findings,
                key=lambda item: (
                    {"error": 0, "warning": 1, "info": 2}[item.level],
                    item.code,
                    item.path or "",
                ),
            )
        ],
    }


def approval_enforcement_enabled(
    *,
    diff_ref: str | None,
    approval_records: list[Path],
    explicitly_enforced: bool,
) -> bool:
    return explicitly_enforced or bool(diff_ref and approval_records)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate structural consistency of an installed Alatyr target adapter."
        )
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path("."),
        help="Target repository directory. Defaults to the current directory.",
    )
    parser.add_argument(
        "--framework-source",
        type=Path,
        help=(
            "Optional AlatyrCore source checkout used to compare target "
            ".ai/framework files against the source framework baseline."
        ),
    )
    parser.add_argument(
        "--diff-ref",
        help=(
            "Optional git ref used for approval-scope comparison. Strict mode "
            "checks the complete committed and working-tree change set."
        ),
    )
    parser.add_argument(
        "--approval-record",
        type=Path,
        action="append",
        default=[],
        help=(
            "Approval record to bind to --diff-ref. Relative paths are resolved "
            "inside the target. May be provided multiple times."
        ),
    )
    parser.add_argument(
        "--enforce-approval-scope",
        action="store_true",
        help=(
            "Fail unless every changed path is covered by explicitly selected "
            "machine-readable JSON approval records bound to --diff-ref. This "
            "is automatic when both --diff-ref and --approval-record are supplied."
        ),
    )
    parser.add_argument(
        "--change-package",
        type=Path,
        action="append",
        default=[],
        help=(
            "Explicit target-relative change-package JSON record to validate. "
            "May be provided multiple times; historical records are not auto-selected."
        ),
    )
    parser.add_argument(
        "--enforce-change-package",
        action="store_true",
        help=(
            "Fail on invalid selected package shape, hashes, refs, declared "
            "semantic/path scope, companion decisions, corrections, or provenance."
        ),
    )
    parser.add_argument(
        "--migration-diff",
        type=Path,
        help=(
            "Optional migration diff report used to classify framework drift "
            "by changed rules, affected categories, profiles, and target actions."
        ),
    )
    parser.add_argument(
        "--debug-git-state",
        action="store_true",
        help=(
            "Reconcile Debug Mode records with the current Git branch, HEAD, "
            "working tree, and optional --debug-remote-ref evidence."
        ),
    )
    parser.add_argument(
        "--debug-remote-ref",
        help=(
            "Optional remote or local ref used as explicit publication evidence "
            "for Debug Mode reconciliation."
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        help=(
            "Optional validator config JSON. Defaults to "
            ".ai/assistant/validator-config.json when that file exists."
        ),
    )
    parser.add_argument(
        "--validation-phase",
        choices=sorted(VALIDATION_PHASES),
        default="acceptance",
        help=(
            "Validation contract. acceptance is strict; migration-staging records "
            "unresolved active placeholders but is never acceptance eligible."
        ),
    )
    parser.add_argument(
        "--validation-scope",
        choices=["full", "changed"],
        default="full",
        help=(
            "Run every validator or a non-acceptance changed-surface route. "
            "Changed scope requires --diff-ref and never qualifies as final evidence."
        ),
    )
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help=(
            "Deprecated compatibility alias for --validation-phase migration-staging. "
            "It never produces accepted or ready adapter evidence."
        ),
    )
    parser.add_argument(
        "--allow-local-path",
        action="append",
        default=[],
        help="Allow a specific local path substring. May be provided multiple times.",
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Return non-zero when warnings are present.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of text findings.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write machine-readable JSON findings to this file.",
    )
    args = parser.parse_args()
    if args.validation_scope == "changed" and not args.diff_ref:
        parser.error("--validation-scope changed requires --diff-ref")
    validation_phase = (
        "migration-staging" if args.allow_placeholders else args.validation_phase
    )

    config, config_findings = load_validator_config(args.target, args.config)
    enforce_approval_scope = approval_enforcement_enabled(
        diff_ref=args.diff_ref,
        approval_records=args.approval_record,
        explicitly_enforced=args.enforce_approval_scope,
    )
    validator = Validator(
        args.target,
        framework_source=args.framework_source,
        diff_ref=args.diff_ref,
        approval_records=args.approval_record,
        enforce_approval_scope=enforce_approval_scope,
        change_packages=args.change_package,
        enforce_change_package=args.enforce_change_package,
        migration_diff=args.migration_diff,
        debug_git_state=args.debug_git_state,
        debug_remote_ref=args.debug_remote_ref,
        allow_placeholders=args.allow_placeholders,
        allow_local_paths=args.allow_local_path,
        config=config,
        initial_findings=config_findings,
        validation_phase=validation_phase,
        validation_scope=args.validation_scope,
    )
    findings = validator.run()
    payload = findings_payload(
        findings,
        target=args.target.resolve(),
        strict_warnings=args.strict_warnings,
        validation_phase=validation_phase,
        installation_state=validator.installation_state,
        validation_scope=args.validation_scope,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return payload["exit_code"]
    return render_summary(
        findings,
        strict_warnings=args.strict_warnings,
        validation_phase=validation_phase,
        installation_state=validator.installation_state,
        validation_scope=args.validation_scope,
    )


if __name__ == "__main__":
    raise SystemExit(main())
