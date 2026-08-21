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
from typing import Any

import jsonschema

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
    git_diff_patch,
    git_head_revision,
    git_range_changed_files,
    git_resolve_ref,
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
from target_adapter_validation.context import ValidationContext
from target_adapter_validation.framework_baseline import source_pack_expectation
from target_adapter_validation.modules import dispatch_capability_checks
from target_adapter_validation.router_costs import (
    validate_budget_shape,
    validate_installed_costs,
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

CORE_REQUIRED_FILES = [
    "AGENTS.md",
    ".ai/alatyr.yaml",
    ".ai/README.md",
    ".ai/assistant/bootstrap-index.json",
    ".ai/project/contour.md",
    ".ai/project/source-of-truth-registry.md",
    ".ai/assistant/contour.md",
    ".ai/assistant/context-router.json",
    ".ai/assistant/context-profiles.md",
    ".ai/assistant/module-profile.md",
    ".ai/assistant/maturity-profile.md",
    ".ai/assistant/gates/index.json",
    ".ai/assistant/gates/core.md",
    ".ai/assistant/gates/final-evidence.md",
    ".ai/assistant/gates/checklist.md",
    ".ai/assistant/templates/adapter-output-contracts.md",
]

STANDARD_REQUIRED_FILES = [
    ".ai/assistant/operation-index.json",
    ".ai/assistant/operation-catalog.json",
    ".ai/assistant/flows/adapter-recheck.flow.md",
    ".ai/assistant/flows/adapter-health.flow.md",
    ".ai/assistant/flows/operation-routing.flow.md",
    ".ai/assistant/templates/pre-change-preview.md",
]

SUPPORT_PROFILES = {"core", "standard", "full"}

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
]

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
    ("owner", "responsible_team"),
    ("owner", "technical_owner"),
    ("owner", "backup_owner"),
    ("owner", "last_review_date"),
    ("owner", "review_cadence"),
    ("source_of_truth", "project_contour"),
    ("source_of_truth", "registry"),
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
    ("operations", "help"),
    ("operations", "gate_index"),
    ("operations", "operation_request"),
    ("operations", "output_contracts"),
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

MANIFEST_PATH_SCALARS: set[PathKey] = {
    ("framework", "rule_registry"),
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
    ("operations", "operation_request"),
    ("operations", "output_contracts"),
    ("operations", "development_evidence_capture"),
    ("operations", "documentation_sync"),
    ("operations", "code_documentation_profile_review"),
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

CONSISTENCY_LEVELS = ["fact", "contract", "area", "system", "adapter"]
CONSISTENCY_RELATIONSHIPS = {
    "implements",
    "verifies",
    "documents",
    "visualizes",
    "generates",
    "constrains",
    "depends-on",
    "routes",
}
CONSISTENCY_REGISTRY_SYNC_POLICY = {
    "coverage": "every-live-registry-fact-type",
    "node_reference": "registry-consistency-map-node-id",
    "fact_type_match": "exact",
    "extra_nodes": "allowed-for-derived-contract-area-system-and-adapter-surfaces",
}
REGISTRY_ENTRY_HEADING_RE = re.compile(
    r"^### Fact Type: `([^`]+)`\s*$", re.MULTILINE
)
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
AI_INFRASTRUCTURE_ROUTES_V1 = {
    "inventory",
    "use-existing",
    "adapt-import",
    "gate-checker-change",
    "tool-mcp-change",
    "bridge-wrapper-change",
}
AI_INFRASTRUCTURE_ROUTES = AI_INFRASTRUCTURE_ROUTES_V1 | {"recommend"}
AI_INFRASTRUCTURE_ITEM_TYPES = {
    "skill",
    "prompt",
    "gate",
    "checker",
    "flow",
    "tool",
    "mcp",
    "bridge",
    "wrapper",
    "rule",
    "template",
    "other",
}
ALLOWED_ACTION_MODES = {
    "read-only",
    "docs-only",
    "adapter-only",
    "code-and-tests",
    "full-with-approval",
}


@dataclass(frozen=True)
class RegistryFactEntry:
    heading_fact_type: str
    declared_fact_type: str | None
    map_node_id: str | None
    line: int


def markdown_scalar(block: str, field: str) -> str | None:
    match = re.search(
        rf"^{re.escape(field)}:\s*(.*?)\s*$",
        block,
        flags=re.MULTILINE,
    )
    if match is None:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    return value or None


def parse_registry_fact_entries(text: str) -> list[RegistryFactEntry]:
    matches = list(REGISTRY_ENTRY_HEADING_RE.finditer(text))
    entries: list[RegistryFactEntry] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end():end]
        entries.append(
            RegistryFactEntry(
                heading_fact_type=match.group(1).strip(),
                declared_fact_type=markdown_scalar(block, "Fact type"),
                map_node_id=markdown_scalar(block, "Consistency map node"),
                line=text.count("\n", 0, match.start()) + 1,
            )
        )
    return entries

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
        (("BRIDGE_",), "drift-review"),
        (("DIAGRAM_",), "diagram-discussion"),
        (("APPROVAL_",), "logical-integrity-review"),
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
    ) -> None:
        self.target = target.resolve()
        self.framework_source = framework_source.resolve() if framework_source else None
        self.diff_ref = diff_ref
        self.enforce_approval_scope = enforce_approval_scope
        self.approval_records = [
            path.resolve() if path.is_absolute() else (self.target / path).resolve()
            for path in approval_records
        ]
        self.change_packages = [
            path.resolve() if path.is_absolute() else (self.target / path).resolve()
            for path in change_packages
        ]
        self.enforce_change_package = enforce_change_package
        self.migration_diff = migration_diff.resolve() if migration_diff else None
        self.allow_placeholders = allow_placeholders
        self.config = config
        self.allow_local_paths = allow_local_paths + config.local_path_patterns()
        self.findings: list[Finding] = list(initial_findings or [])
        self.framework_drift_detected = False
        self.context = ValidationContext(self.target)

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
        self.check_required_files(support_profile)
        self.check_capability_closure(manifest)
        self.check_bootstrap_index()
        enabled_modules = self.enabled_modules(manifest)
        self.check_router(enabled_modules)
        if support_profile in {"standard", "full"} or self.target_path(
            ".ai/assistant/operation-catalog.json"
        ).is_file():
            self.check_operation_catalog()
        dispatch_capability_checks(self, enabled_modules, manifest)
        self.check_enabled_module_status_claims(enabled_modules)
        self.check_bootstrap_references()
        self.check_placeholders()
        self.check_local_paths()
        checker_files, checker_commands = self.discover_checkers(manifest)
        self.check_checker_claims(checker_files, checker_commands)
        self.check_approval_scope()
        self.check_change_package_index()
        self.check_change_packages()
        self.check_framework_baseline()
        self.check_migration_diff_evidence()
        self.info(
            "EVIDENCE_SCOPE_CURRENT_STATE",
            "validator findings describe current structural state; historical actions "
            "require dated operation, approval, or migration records",
        )
        return self.findings

    def target_path(self, relpath: str) -> Path:
        return self.target / relpath

    def rel(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.target).as_posix()
        except ValueError:
            return str(path)

    def read_text(self, path: Path) -> str:
        return self.context.read_text(path)

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
        text = self.read_text(profile_path)
        for match in re.finditer(
            r"^Module: `([^`]+)`\s*$([\s\S]*?)(?=^Module: `|\Z)",
            text,
            flags=re.MULTILINE,
        ):
            state = re.search(
                r"^State:\s*`?([^`\n]+)`?\s*$",
                match.group(2),
                flags=re.MULTILINE,
            )
            if state and state.group(1).strip().casefold() in {"enabled", "required"}:
                enabled.add(match.group(1))
        return enabled

    def check_required_files(self, support_profile: str) -> None:
        required = list(CORE_REQUIRED_FILES)
        if support_profile in {"standard", "full"}:
            required.extend(STANDARD_REQUIRED_FILES)
        for relpath in required:
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

        manifest = parse_manifest(path)
        for failure in manifest.parse_failures:
            self.error("MANIFEST_PARSE", failure, ".ai/alatyr.yaml")
        try:
            manifest_object = load_manifest_object(path)
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
        required_scalars = set(MANIFEST_REQUIRED_SCALARS)
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
                    "installation.support_profile must be core, standard, or full",
                    f".ai/alatyr.yaml:{support_scalar.line}",
                )

        pack_scalar = manifest.scalars.get(("framework", "pack"))
        if pack_scalar and not is_unresolved_value(pack_scalar.value):
            if pack_scalar.value not in {"core", "standard", "complete"}:
                self.error(
                    "MANIFEST_FRAMEWORK_PACK",
                    "framework.pack must be core, standard, or complete",
                    f".ai/alatyr.yaml:{pack_scalar.line}",
                )
            elif support_scalar and support_scalar.value in SUPPORT_PROFILES:
                pack_rank = {"core": 0, "standard": 1, "complete": 2}
                profile_rank = {"core": 0, "standard": 1, "full": 2}
                if pack_rank[pack_scalar.value] < profile_rank[support_scalar.value]:
                    self.error(
                        "MANIFEST_FRAMEWORK_PACK",
                        "framework.pack is too small for installation.support_profile",
                        f".ai/alatyr.yaml:{pack_scalar.line}",
                    )

        numeric_context_fields = [
            ("context_routing", "router_schema_version"),
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
        if router_schema not in {2, 3, 4, 5, 6}:
            self.error(
                "MANIFEST_CONTEXT_SCHEMA",
                "context_routing.router_schema_version must be 2, 3, 4, 5, or 6",
                ".ai/alatyr.yaml",
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
        if actual != expected:
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

    def check_router(self, enabled_modules: set[str] | None = None) -> None:
        router_path = self.target_path(".ai/assistant/context-router.json")
        profiles_path = self.target_path(".ai/assistant/context-profiles.md")
        if not router_path.is_file():
            return

        try:
            router = json.loads(router_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self.error("ROUTER_INVALID_JSON", str(exc), ".ai/assistant/context-router.json")
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
                "context router schema 1 should migrate to generated-bootstrap routing schema 6",
                ".ai/assistant/context-router.json",
            )
        elif schema_version not in {2, 3, 4, 5, 6}:
            self.error(
                "ROUTER_SCHEMA",
                "context router schema_version should be 2, 3, 4, 5, or 6",
                ".ai/assistant/context-router.json",
            )
        manifest_path = self.target_path(".ai/alatyr.yaml")
        if manifest_path.is_file():
            manifest = parse_manifest(manifest_path)
            manifest_schema = manifest.scalars.get(
                ("context_routing", "router_schema_version")
            )
            if manifest_schema and not is_unresolved_value(manifest_schema.value):
                if manifest_schema.value != str(schema_version):
                    self.error(
                        "ROUTER_MANIFEST_SCHEMA_DRIFT",
                        "manifest router_schema_version differs from context router",
                        ".ai/alatyr.yaml",
                    )
        if router.get("human_reference") != ".ai/assistant/context-profiles.md":
            self.error(
                "ROUTER_HUMAN_REFERENCE",
                "human_reference should be .ai/assistant/context-profiles.md",
                ".ai/assistant/context-router.json",
            )

        if schema_version in {2, 3, 4, 5, 6}:
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
                REQUIRED_BOOTSTRAP if schema_version in {5, 6} else LEGACY_REQUIRED_BOOTSTRAP
            )
            for required in required_bootstrap:
                if required not in bootstrap:
                    self.error(
                        "ROUTER_BOOTSTRAP_MISSING",
                        f"bootstrap_context missing {required}",
                        ".ai/assistant/context-router.json",
                    )
            deferred = sorted(set(bootstrap) & DEFERRED_BOOTSTRAP) if schema_version in {5, 6} else []
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
                    "schema 2, 3, 4, 5, or 6 router must define context_budgets",
                    ".ai/assistant/context-router.json",
                )
                budgets = {}
            elif schema_version in {4, 5, 6}:
                self.check_router_budget_shape(budgets)
            if not isinstance(router.get("context_receipt"), dict):
                self.error(
                    "ROUTER_RECEIPT_MISSING",
                    "schema 2, 3, 4, 5, or 6 router must define context_receipt",
                    ".ai/assistant/context-router.json",
                )
            migration_entry = router.get("migration_routing")
            migration = migration_entry
            if schema_version in {3, 4, 5, 6} and isinstance(migration_entry, dict):
                migration = self.load_context_descriptor(
                    migration_entry,
                    "target-migration-routing",
                    "migration_routing",
                )
            if not isinstance(migration, dict):
                self.error(
                    "ROUTER_MIGRATION_MISSING",
                    "schema 2, 3, 4, 5, or 6 router must define migration-first routing",
                    ".ai/assistant/context-router.json",
                )
            else:
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

        if schema_version in {4, 5, 6} and isinstance(budgets, dict):
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
                    profiles_path.read_text(encoding="utf-8"),
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
        if router.get("schema_version") not in {3, 4, 5, 6}:
            profiles = router.get("profiles")
            return profiles if isinstance(profiles, dict) else {}
        index = router.get("profile_index")
        if not isinstance(index, dict):
            self.error(
                "ROUTER_PROFILE_INDEX",
                "schema 3, 4, 5, or 6 router must define profile_index",
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
        if manifest is None:
            return
        enabled = {
            scalar.value
            for scalar in manifest.lists.get(("modules", "enabled"), [])
        }
        if "subagent-delegation" not in enabled:
            return

        required_paths = [
            ".ai/framework/subagent-delegation.md",
            ".ai/assistant/delegation-policy.json",
            ".ai/assistant/context/task-scales/delegated-execution.json",
            ".ai/assistant/flows/subagent-delegation.flow.md",
            ".ai/assistant/templates/subagent-task-packet.md",
            ".ai/assistant/assistant-capabilities.json",
            ".ai/assistant/bridge-capability-matrix.md",
        ]
        for relpath in required_paths:
            if not self.target_path(relpath).is_file():
                self.error(
                    "DELEGATION_REQUIRED_FILE_MISSING",
                    "enabled subagent delegation is missing a required contract",
                    relpath,
                )

        policy_relpath = ".ai/assistant/delegation-policy.json"
        policy = self.load_json_object(
            self.target_path(policy_relpath), "DELEGATION_POLICY"
        )
        if policy is None:
            return

        def concrete(value: Any) -> bool:
            return (
                isinstance(value, str)
                and bool(value.strip())
                and not is_placeholder(value)
                and not is_unresolved_value(value)
            )

        if policy.get("schema_version") != 1:
            self.error(
                "DELEGATION_POLICY_SCHEMA",
                "delegation policy schema_version must be 1",
                policy_relpath,
            )
        if policy.get("policy_kind") != "target-subagent-delegation-policy":
            self.error(
                "DELEGATION_POLICY_KIND",
                "delegation policy kind is invalid",
                policy_relpath,
            )
        state = policy.get("state")
        if concrete(state) and state not in {"enabled", "suggest-only"}:
            self.error(
                "DELEGATION_POLICY_STATE",
                "enabled module requires enabled or suggest-only policy state",
                policy_relpath,
            )
        decision_mode = policy.get("decision_mode")
        if concrete(decision_mode) and decision_mode not in {
            "automatic",
            "suggest-only",
        }:
            self.error(
                "DELEGATION_DECISION_MODE",
                "enabled delegation decision_mode must be automatic or suggest-only",
                policy_relpath,
            )
        preference = policy.get("default_preference")
        if concrete(preference) and preference not in {
            "auto",
            "allow",
            "forbid",
            "require-supported",
        }:
            self.error(
                "DELEGATION_DEFAULT_PREFERENCE",
                "delegation default_preference is invalid",
                policy_relpath,
            )
        parallel = policy.get("max_parallel_delegates")
        if not is_placeholder(parallel) and (
            not isinstance(parallel, int) or isinstance(parallel, bool) or parallel < 1
        ):
            self.error(
                "DELEGATION_PARALLEL_LIMIT",
                "max_parallel_delegates must be a positive integer",
                policy_relpath,
            )

        requirements = policy.get("requirements")
        required_guards = {
            "primary_keeps_critical_path",
            "independent_local_acceptance",
            "disjoint_write_scope",
            "primary_final_convergence",
            "current_capability_evidence",
        }
        if not isinstance(requirements, dict) or any(
            requirements.get(field) is not True for field in required_guards
        ):
            self.error(
                "DELEGATION_REQUIRED_GUARDS",
                "delegation policy must retain every primary and isolation guard",
                policy_relpath,
            )

        result_policy = policy.get("result_policy")
        expected_result_policy = {
            "accept_out_of_scope_changes": False,
            "accept_unvalidated_changes": False,
            "require_primary_review": True,
            "require_actual_model_or_unverified_status": True,
        }
        if not isinstance(result_policy, dict) or any(
            result_policy.get(field) is not expected
            for field, expected in expected_result_policy.items()
        ):
            self.error(
                "DELEGATION_RESULT_GUARDS",
                "delegation result policy weakens primary review or scope evidence",
                policy_relpath,
            )

        capability_index_relpath = ".ai/assistant/assistant-capabilities.json"
        capability_index = self.load_json_object(
            self.target_path(capability_index_relpath), "DELEGATION_CAPABILITY_INDEX"
        )
        surfaces = (
            capability_index.get("surfaces")
            if isinstance(capability_index, dict)
            else None
        )
        if not isinstance(surfaces, dict) or not surfaces:
            self.error(
                "DELEGATION_CAPABILITY_SURFACES",
                "enabled delegation requires assistant capability surface records",
                capability_index_relpath,
            )
            surfaces = {}

        capability_fields = {
            "route",
            "dispatch_backend",
            "external_dispatcher",
            "native_subagents",
            "model_override",
            "parallel_dispatch",
            "actual_model_evidence",
            "verified_at",
            "client_version",
            "evidence",
            "expires_at",
            "review_triggers",
        }
        capability_records: dict[str, dict[str, Any]] = {}
        ai_router = self.load_json_object(
            self.target_path(".ai/assistant/ai-infrastructure-router.json"),
            "DELEGATION_AI_ROUTER",
        )
        ai_items = ai_router.get("items") if isinstance(ai_router, dict) else []
        ai_item_ids = {
            item.get("id")
            for item in ai_items
            if isinstance(item, dict) and concrete(item.get("id"))
        }
        for surface_id, relpath in surfaces.items():
            if not isinstance(surface_id, str) or not isinstance(relpath, str):
                continue
            record = self.load_json_object(
                self.target_path(relpath), "DELEGATION_SURFACE_CAPABILITY"
            )
            delegation = record.get("subagent_delegation") if record else None
            if not isinstance(delegation, dict):
                self.error(
                    "DELEGATION_CAPABILITY_MISSING",
                    f"assistant surface {surface_id} has no delegation capability",
                    relpath,
                )
                continue
            missing = sorted(capability_fields - set(delegation))
            if missing:
                self.error(
                    "DELEGATION_CAPABILITY_FIELDS",
                    f"assistant surface {surface_id} is missing {missing}",
                    relpath,
                )
            for field in [
                "route",
                "native_subagents",
                "model_override",
                "parallel_dispatch",
                "actual_model_evidence",
            ]:
                value = delegation.get(field)
                if concrete(value) and value not in {
                    "supported",
                    "unsupported",
                    "unknown",
                }:
                    self.error(
                        "DELEGATION_CAPABILITY_VALUE",
                        f"assistant surface {surface_id} {field} is invalid",
                        relpath,
                    )
            backend = delegation.get("dispatch_backend")
            if concrete(backend) and backend not in {
                "native",
                "external",
                "suggestion-only",
                "unsupported",
                "unknown",
            }:
                self.error(
                    "DELEGATION_DISPATCH_BACKEND",
                    f"assistant surface {surface_id} dispatch_backend is invalid",
                    relpath,
                )
            dispatcher = delegation.get("external_dispatcher")
            if backend == "native" and delegation.get("native_subagents") != "supported":
                self.error(
                    "DELEGATION_NATIVE_BACKEND_UNSUPPORTED",
                    f"assistant surface {surface_id} selects native dispatch without native worker evidence",
                    relpath,
                )
            if backend == "external":
                if not concrete(dispatcher) or dispatcher not in ai_item_ids:
                    self.error(
                        "DELEGATION_EXTERNAL_DISPATCHER",
                        f"assistant surface {surface_id} external dispatcher must reference a routed AI-infrastructure item",
                        relpath,
                    )
                if delegation.get("route") != "supported":
                    self.error(
                        "DELEGATION_EXTERNAL_ROUTE_UNSUPPORTED",
                        f"assistant surface {surface_id} external dispatch requires a supported route",
                        relpath,
                    )
            if backend == "unsupported" and delegation.get("route") == "supported":
                self.error(
                    "DELEGATION_UNSUPPORTED_ROUTE_CONFLICT",
                    f"assistant surface {surface_id} cannot claim a supported route with an unsupported backend",
                    relpath,
                )
            capability_records[surface_id] = delegation

        roles = policy.get("roles")
        if not isinstance(roles, list) or not roles:
            self.error(
                "DELEGATION_ROLES_MISSING",
                "enabled delegation requires at least one bounded role",
                policy_relpath,
            )
            roles = []
        role_ids: set[str] = set()
        for index, role in enumerate(roles):
            if not isinstance(role, dict):
                self.error(
                    "DELEGATION_ROLE_SHAPE",
                    f"roles[{index}] must be an object",
                    policy_relpath,
                )
                continue
            role_id = role.get("id")
            if concrete(role_id):
                if role_id in role_ids:
                    self.error(
                        "DELEGATION_ROLE_DUPLICATE",
                        f"duplicate delegation role {role_id}",
                        policy_relpath,
                    )
                role_ids.add(role_id)
            actions = role.get("allowed_actions")
            if isinstance(actions, list):
                self.check_allowed_actions(
                    [value for value in actions if isinstance(value, str)],
                    policy_relpath,
                    f"roles[{index}].allowed_actions",
                )
            else:
                self.error(
                    "DELEGATION_ROLE_ACTIONS",
                    f"roles[{index}].allowed_actions must be a list",
                    policy_relpath,
                )
            binding = role.get("model_binding")
            if not isinstance(binding, dict):
                self.error(
                    "DELEGATION_MODEL_BINDING",
                    f"roles[{index}].model_binding must be an object",
                    policy_relpath,
                )
                continue
            surface_id = binding.get("assistant_surface")
            selection_mode = binding.get("selection_mode")
            if concrete(surface_id) and surface_id not in surfaces:
                self.error(
                    "DELEGATION_MODEL_SURFACE",
                    f"roles[{index}] references unknown surface {surface_id}",
                    policy_relpath,
                )
                continue
            if concrete(selection_mode) and selection_mode not in {
                "explicit-model",
                "inherit",
                "client-default",
            }:
                self.error(
                    "DELEGATION_MODEL_SELECTION_MODE",
                    f"roles[{index}] selection_mode is invalid",
                    policy_relpath,
                )
            capability = capability_records.get(surface_id)
            if (
                capability is not None
                and selection_mode == "explicit-model"
                and capability.get("model_override") != "supported"
            ):
                self.error(
                    "DELEGATION_MODEL_OVERRIDE_UNSUPPORTED",
                    f"roles[{index}] selects a model without supported override evidence",
                    policy_relpath,
                )

        overlay_relpath = (
            ".ai/assistant/context/task-scales/delegated-execution.json"
        )
        overlay = self.load_json_object(
            self.target_path(overlay_relpath), "DELEGATION_OVERLAY"
        )
        if overlay is not None and (
            overlay.get("id") != "delegated-execution"
            or overlay.get("required_module") != "subagent-delegation"
        ):
            self.error(
                "DELEGATION_OVERLAY_CONTRACT",
                "delegated execution overlay identity or module is invalid",
                overlay_relpath,
            )

    def check_discussion_diagrams(self, manifest: ManifestData | None) -> None:
        module_relpath = ".ai/assistant/module-profile.md"
        module_path = self.target_path(module_relpath)
        if not module_path.is_file():
            return
        module_text = self.read_text(module_path)
        module_match = re.search(
            r"^Module: `diagrams`\s*$([\s\S]*?)(?=^Module: `|\Z)",
            module_text,
            flags=re.MULTILINE,
        )
        if module_match is None:
            self.warn(
                "DIAGRAM_MODULE_UNDECLARED",
                "module profile does not declare diagrams state",
                module_relpath,
            )
            return
        state_match = re.search(
            r"^State:\s*`?([^`\n]+)`?\s*$",
            module_match.group(1),
            flags=re.MULTILINE,
        )
        if state_match is None:
            self.warn(
                "DIAGRAM_MODULE_STATE_MISSING",
                "diagrams module has no parseable State field",
                module_relpath,
            )
            return
        state = state_match.group(1).strip().casefold()
        if state not in {"enabled", "required"}:
            return

        required_paths = [
            ".ai/assistant/flows/diagram-discussion.flow.md",
            ".ai/assistant/templates/diagram-presentation.md",
            ".ai/assistant/templates/ascii-diagram.md",
            ".ai/assistant/assistant-capabilities.json",
            ".ai/assistant/bridge-capability-matrix.md",
            ".ai/framework/ascii-diagrams.md",
        ]
        for relpath in required_paths:
            if not self.target_path(relpath).is_file():
                self.error(
                    "DIAGRAM_REQUIRED_FILE_MISSING",
                    "enabled diagrams module is missing a discussion contract",
                    relpath,
                )

        if manifest is not None:
            expected_manifest = {
                (
                    "operations",
                    "diagram_discussion",
                ): ".ai/assistant/flows/diagram-discussion.flow.md",
                (
                    "operations",
                    "diagram_presentation",
                ): ".ai/assistant/templates/diagram-presentation.md",
                (
                    "bridges",
                    "capabilities",
                ): ".ai/assistant/assistant-capabilities.json",
            }
            for key, expected in expected_manifest.items():
                scalar = manifest.scalars.get(key)
                if scalar is None or scalar.value != expected:
                    self.error(
                        "DIAGRAM_MANIFEST_PATH",
                        f"{dotted(key)} must be {expected} when diagrams are enabled",
                        ".ai/alatyr.yaml",
                    )

        catalog = self.load_json_object(
            self.target_path(".ai/assistant/operation-catalog.json"),
            "OPERATION_CATALOG",
        )
        operations = catalog.get("operations") if isinstance(catalog, dict) else None
        operation = None
        if isinstance(operations, list):
            operation = next(
                (
                    item
                    for item in operations
                    if isinstance(item, dict)
                    and item.get("id") == "diagram-discussion"
                ),
                None,
            )
        if not isinstance(operation, dict):
            self.error(
                "DIAGRAM_OPERATION_MISSING",
                "enabled diagrams module requires diagram-discussion operation",
                ".ai/assistant/operation-catalog.json",
            )
        else:
            if operation.get("required_module") != "diagrams":
                self.error(
                    "DIAGRAM_OPERATION_MODULE",
                    "diagram-discussion must require the diagrams module",
                    ".ai/assistant/operation-catalog.json",
                )
            if operation.get("flow") != required_paths[0]:
                self.error(
                    "DIAGRAM_OPERATION_FLOW",
                    f"diagram-discussion must route to {required_paths[0]}",
                    ".ai/assistant/operation-catalog.json",
                )
            if operation.get("allowed_actions") != ["read-only", "docs-only"]:
                self.error(
                    "DIAGRAM_OPERATION_ACTIONS",
                    "diagram-discussion must allow only read-only and docs-only",
                    ".ai/assistant/operation-catalog.json",
                )

        router = self.load_json_object(
            self.target_path(".ai/assistant/context-router.json"), "ROUTER"
        )
        intent_overlays = (
            router.get("intent_overlays") if isinstance(router, dict) else None
        )
        diagram_overlay = (
            intent_overlays.get("diagram-request")
            if isinstance(intent_overlays, dict)
            else None
        )
        routed = isinstance(diagram_overlay, dict) and diagram_overlay.get(
            "operation_candidates"
        ) == ["diagram-discussion"]
        if not routed:
            self.error(
                "DIAGRAM_OPERATION_UNROUTED",
                "enabled diagram-discussion has no diagram-request intent overlay",
                ".ai/assistant/context-router.json",
            )

        matrix_relpath = ".ai/assistant/bridge-capability-matrix.md"
        matrix_text = self.read_text(self.target_path(matrix_relpath))
        matches = list(
            re.finditer(
                r"^### Assistant Surface: `([^`]+)`\s*$",
                matrix_text,
                flags=re.MULTILINE,
            )
        )
        if not matches:
            self.error(
                "DIAGRAM_BRIDGE_CAPABILITY_MISSING",
                "enabled diagrams module has no assistant capability entries",
                matrix_relpath,
            )
        capability_relpath = ".ai/assistant/assistant-capabilities.json"
        capabilities = self.load_json_object(
            self.target_path(capability_relpath), "ASSISTANT_CAPABILITIES"
        )
        capability_surfaces = (
            capabilities.get("surfaces") if isinstance(capabilities, dict) else None
        )
        if isinstance(capabilities, dict):
            if capabilities.get("schema_version") != 2:
                self.error(
                    "DIAGRAM_CAPABILITY_SCHEMA",
                    "capability index schema_version should be 2",
                    capability_relpath,
                )
            if capabilities.get("capability_kind") != (
                "target-assistant-capability-index"
            ):
                self.error(
                    "DIAGRAM_CAPABILITY_KIND",
                    "capability_kind should be target-assistant-capability-index",
                    capability_relpath,
                )
        if not isinstance(capability_surfaces, dict) or not capability_surfaces:
            self.error(
                "DIAGRAM_CAPABILITY_SURFACES",
                "enabled diagrams require assistant capability surface entries",
                capability_relpath,
            )
            capability_surfaces = {}

        required_capability_fields = {
            "route",
            "native_inline_syntaxes",
            "artifact_presentation",
            "readable_fallback",
            "verified_at",
            "expires_at",
            "review_triggers",
            "client_version",
            "evidence",
        }
        for index, match in enumerate(matches):
            end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(matrix_text)
            )
            block = matrix_text[match.end():end]
            surface_id = match.group(1)
            expected_reference = (
                "Diagram capability record: "
                f"`.ai/assistant/assistant-capabilities/{surface_id}.json`"
            )
            if expected_reference not in block:
                self.error(
                    "DIAGRAM_BRIDGE_CAPABILITY_FIELD",
                    f"assistant surface {surface_id} has no compact capability reference",
                    matrix_relpath,
                )
            surface_relpath = (
                f".ai/assistant/assistant-capabilities/{surface_id}.json"
            )
            if capability_surfaces.get(surface_id) != surface_relpath:
                self.error(
                    "DIAGRAM_CAPABILITY_INDEX_PATH",
                    f"assistant surface {surface_id} must route to {surface_relpath}",
                    capability_relpath,
                )
                continue
            surface = self.load_json_object(
                self.target_path(surface_relpath), "ASSISTANT_SURFACE_CAPABILITIES"
            )
            if surface is None:
                continue
            if surface.get("schema_version") != 1:
                self.error(
                    "DIAGRAM_SURFACE_CAPABILITY_SCHEMA",
                    "surface capability schema_version should be 1",
                    surface_relpath,
                )
            if surface.get("capability_kind") != (
                "target-assistant-surface-capabilities"
            ):
                self.error(
                    "DIAGRAM_SURFACE_CAPABILITY_KIND",
                    "surface capability kind is invalid",
                    surface_relpath,
                )
            if surface.get("assistant_surface") != surface_id:
                self.error(
                    "DIAGRAM_SURFACE_CAPABILITY_ID",
                    f"surface capability identity should be {surface_id}",
                    surface_relpath,
                )
            diagram = surface.get("diagram_discussion")
            if not isinstance(diagram, dict):
                self.error(
                    "DIAGRAM_CAPABILITY_MISSING",
                    f"assistant surface {surface_id} has no diagram_discussion capability",
                    surface_relpath,
                )
                continue
            missing_fields = sorted(required_capability_fields - set(diagram))
            if missing_fields:
                self.error(
                    "DIAGRAM_CAPABILITY_FIELDS",
                    f"assistant surface {surface_id} is missing {missing_fields}",
                    surface_relpath,
                )
            if diagram.get("route") not in {"supported", "unsupported", "unknown"}:
                self.error(
                    "DIAGRAM_CAPABILITY_ROUTE",
                    f"assistant surface {surface_id} route must be supported, unsupported, or unknown",
                    surface_relpath,
                )
            if diagram.get("artifact_presentation") not in {
                "link",
                "attachment",
                "both",
                "unsupported",
                "unknown",
            }:
                self.error(
                    "DIAGRAM_CAPABILITY_ARTIFACT",
                    f"assistant surface {surface_id} artifact_presentation has an invalid enum",
                    surface_relpath,
                )
            syntaxes = diagram.get("native_inline_syntaxes")
            if not isinstance(syntaxes, list) or not syntaxes or not all(
                isinstance(value, str) and value for value in syntaxes
            ):
                self.error(
                    "DIAGRAM_CAPABILITY_SYNTAXES",
                    f"assistant surface {surface_id} native_inline_syntaxes must be a string list",
                    surface_relpath,
                )
            for field in [
                "readable_fallback",
                "verified_at",
                "expires_at",
                "client_version",
                "evidence",
            ]:
                value = diagram.get(field)
                if not isinstance(value, str) or not value.strip():
                    self.error(
                        "DIAGRAM_CAPABILITY_EVIDENCE",
                        f"assistant surface {surface_id} {field} must be recorded",
                        surface_relpath,
                    )
            for field in ["readable_fallback", "evidence"]:
                value = diagram.get(field)
                if isinstance(value, str) and value.strip().casefold() in UNRESOLVED_WORDS:
                    self.error(
                        "DIAGRAM_CAPABILITY_EVIDENCE",
                        f"assistant surface {surface_id} {field} is unresolved",
                        surface_relpath,
                    )
            if diagram.get("readable_fallback") != "ascii":
                self.error(
                    "DIAGRAM_CAPABILITY_ASCII_FALLBACK",
                    f"assistant surface {surface_id} readable_fallback must be ascii",
                    surface_relpath,
                )
            verified_at = diagram.get("verified_at")
            if isinstance(verified_at, str) and not (
                re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T[^\s]+)?", verified_at)
                or verified_at.casefold().startswith("unknown:")
            ):
                self.error(
                    "DIAGRAM_CAPABILITY_FRESHNESS",
                    f"assistant surface {surface_id} verified_at must be an ISO date/time or unknown: reason",
                    surface_relpath,
                )
            expires_at = diagram.get("expires_at")
            if isinstance(expires_at, str):
                expiry_is_date = re.fullmatch(
                    r"\d{4}-\d{2}-\d{2}(?:T[^\s]+)?", expires_at
                )
                expiry_is_trigger = expires_at.casefold().startswith(
                    ("review-trigger:", "unknown:")
                )
                if not expiry_is_date and not expiry_is_trigger:
                    self.error(
                        "DIAGRAM_CAPABILITY_EXPIRY",
                        f"assistant surface {surface_id} expires_at needs an ISO date or review-trigger: reason",
                        surface_relpath,
                    )
                elif expiry_is_date:
                    expiry = datetime.strptime(expires_at[:10], "%Y-%m-%d").date()
                    if expiry < datetime.now(timezone.utc).date():
                        self.warn(
                            "DIAGRAM_CAPABILITY_EXPIRED",
                            f"assistant surface {surface_id} capability evidence expired",
                            surface_relpath,
                        )
            review_triggers = diagram.get("review_triggers")
            if not isinstance(review_triggers, list) or not review_triggers or not all(
                isinstance(value, str) and value for value in review_triggers
            ):
                self.error(
                    "DIAGRAM_CAPABILITY_REVIEW_TRIGGERS",
                    f"assistant surface {surface_id} review_triggers must be a string list",
                    surface_relpath,
                )
            client_version = diagram.get("client_version")
            if isinstance(client_version, str) and client_version.casefold() in {
                "unknown",
                "n/a",
            }:
                self.error(
                    "DIAGRAM_CAPABILITY_CLIENT_VERSION",
                    f"assistant surface {surface_id} client_version needs a value or unknown: reason",
                    surface_relpath,
                )

        matrix_surface_ids = {match.group(1) for match in matches}
        extra_capabilities = sorted(set(capability_surfaces) - matrix_surface_ids)
        if extra_capabilities:
            self.error(
                "DIAGRAM_CAPABILITY_SURFACE_DRIFT",
                f"capability projection has surfaces absent from bridge matrix: {extra_capabilities}",
                capability_relpath,
            )

        flow_text = self.read_text(self.target_path(required_paths[0]))
        presentation_text = self.read_text(self.target_path(required_paths[1]))
        for relpath, text, snippets in [
            (
                required_paths[0],
                flow_text,
                [
                    "`read-only`",
                    "current assistant surface record",
                    "portable ASCII view",
                    "hard maximum of 100 columns",
                    "stable diagram ID",
                    "Classify data sensitivity",
                ],
            ),
            (
                required_paths[1],
                presentation_text,
                [
                    "Presentation mode:",
                    "Portable ASCII presentation:",
                    "ASCII readability check:",
                    "Diagram ID:",
                    "Data classification:",
                    "External renderer or network action:",
                    "is not project source of truth",
                ],
            ),
            (
                required_paths[2],
                self.read_text(self.target_path(required_paths[2])),
                [
                    "Hard maximum width: `100`",
                    "printable 7-bit ASCII plus line feeds",
                    "Longest line at most 100 columns",
                ],
            ),
        ]:
            for snippet in snippets:
                if snippet not in text:
                    self.error(
                        "DIAGRAM_CONTRACT_INCOMPLETE",
                        f"discussion contract is missing {snippet}",
                        relpath,
                    )

    def check_architecture_knowledge(
        self, manifest: ManifestData | None
    ) -> None:
        module_relpath = ".ai/assistant/module-profile.md"
        module_path = self.target_path(module_relpath)
        if not module_path.is_file():
            return
        module_match = re.search(
            r"^Module: `architecture-knowledge`\s*$([\s\S]*?)(?=^Module: `|\Z)",
            self.read_text(module_path),
            flags=re.MULTILINE,
        )
        if module_match is None:
            self.warn(
                "ARCHITECTURE_MODULE_UNDECLARED",
                "module profile does not declare architecture-knowledge state",
                module_relpath,
            )
            return
        state_match = re.search(
            r"^State:\s*`?([^`\n]+)`?\s*$",
            module_match.group(1),
            flags=re.MULTILINE,
        )
        if state_match is None:
            self.warn(
                "ARCHITECTURE_MODULE_STATE_MISSING",
                "architecture-knowledge module has no parseable State field",
                module_relpath,
            )
            return
        state = state_match.group(1).strip().casefold()
        if state not in {"enabled", "required"}:
            return

        required_paths = [
            ".ai/project/architecture/README.md",
            ".ai/project/architecture/catalog.json",
            ".ai/assistant/context/intents/architecture-request.json",
            ".ai/assistant/flows/architecture-assistance.flow.md",
            ".ai/assistant/templates/architecture-pattern.md",
            ".ai/assistant/templates/architecture-area.md",
            ".ai/assistant/templates/architecture-discussion-result.md",
            ".ai/framework/architecture-knowledge.md",
        ]
        missing_required = False
        for relpath in required_paths:
            if not self.target_path(relpath).is_file():
                missing_required = True
                self.error(
                    "ARCHITECTURE_REQUIRED_FILE_MISSING",
                    "enabled architecture-knowledge module is missing a contract",
                    relpath,
                )
        if missing_required:
            return

        if manifest is not None:
            expected_manifest = {
                ("source_of_truth", "architecture_index"): required_paths[0],
                ("source_of_truth", "architecture_catalog"): required_paths[1],
                ("operations", "architecture_assistance"): required_paths[3],
                (
                    "operations",
                    "architecture_discussion_result",
                ): required_paths[6],
            }
            for key, expected in expected_manifest.items():
                scalar = manifest.scalars.get(key)
                if scalar is None or scalar.value != expected:
                    self.error(
                        "ARCHITECTURE_MANIFEST_PATH",
                        f"{dotted(key)} must be {expected} when architecture knowledge is enabled",
                        ".ai/alatyr.yaml",
                    )

        catalog_relpath = required_paths[1]
        catalog = self.load_json_object(
            self.target_path(catalog_relpath), "ARCHITECTURE_CATALOG"
        )
        if catalog is None:
            return
        if catalog.get("schema_version") != 1:
            self.error(
                "ARCHITECTURE_CATALOG_SCHEMA",
                "schema_version should be 1",
                catalog_relpath,
            )
        if catalog.get("catalog_kind") != "target-architecture-knowledge-catalog":
            self.error(
                "ARCHITECTURE_CATALOG_KIND",
                "catalog_kind should be target-architecture-knowledge-catalog",
                catalog_relpath,
            )
        if catalog.get("human_index") != required_paths[0]:
            self.error(
                "ARCHITECTURE_CATALOG_INDEX",
                f"human_index should point to {required_paths[0]}",
                catalog_relpath,
            )

        def concrete(value: Any) -> bool:
            return (
                isinstance(value, str)
                and bool(value.strip())
                and not is_placeholder(value)
                and not is_unresolved_value(value)
            )

        def string_list(value: Any, label: str, *, non_empty: bool = True) -> list[str]:
            if not isinstance(value, list) or (non_empty and not value) or not all(
                isinstance(item, str) and item for item in value
            ):
                self.error(
                    "ARCHITECTURE_CATALOG_LIST",
                    f"{label} must be a {'non-empty ' if non_empty else ''}string list",
                    catalog_relpath,
                )
                return []
            return value

        metadata_fields = [
            "project",
            "module_state",
            "architecture_owner",
            "decision_authority",
            "last_reviewed",
            "evidence_revision",
        ]
        for field in metadata_fields:
            value = catalog.get(field)
            if not isinstance(value, str) or not value.strip():
                self.error(
                    "ARCHITECTURE_CATALOG_METADATA",
                    f"{field} must be a non-empty string",
                    catalog_relpath,
                )
        module_state = catalog.get("module_state")
        if concrete(module_state) and module_state not in {
            "enabled",
            "deferred",
            "disabled",
            "not-applicable",
            "blocked",
        }:
            self.error(
                "ARCHITECTURE_MODULE_STATE",
                f"module_state is invalid: {module_state}",
                catalog_relpath,
            )
        if module_state == "enabled":
            for field in [
                "project",
                "architecture_owner",
                "decision_authority",
                "last_reviewed",
                "evidence_revision",
            ]:
                if not concrete(catalog.get(field)):
                    self.error(
                        "ARCHITECTURE_ENABLED_METADATA_UNRESOLVED",
                        f"enabled architecture knowledge requires resolved {field}",
                        catalog_relpath,
                    )

        canonical_sources = string_list(
            catalog.get("canonical_sources"), "canonical_sources"
        )
        decision_sources = string_list(
            catalog.get("decision_sources"), "decision_sources"
        )
        known_gaps = string_list(
            catalog.get("known_gaps"), "known_gaps", non_empty=False
        )
        if module_state == "enabled":
            for label, values in [
                ("canonical_sources", canonical_sources),
                ("decision_sources", decision_sources),
            ]:
                if not any(concrete(item) for item in values):
                    self.error(
                        "ARCHITECTURE_ENABLED_METADATA_UNRESOLVED",
                        f"enabled architecture knowledge requires resolved {label}",
                        catalog_relpath,
                    )
            if any(not concrete(item) for item in known_gaps):
                self.error(
                    "ARCHITECTURE_KNOWN_GAP_UNRESOLVED",
                    "known_gaps must be empty or contain concrete gap records",
                    catalog_relpath,
                )

        statuses = {
            "observed",
            "proposed",
            "accepted",
            "preferred",
            "restricted",
            "deprecated",
            "contradicted",
            "unknown",
        }
        pattern_kinds = {
            "style",
            "boundary",
            "integration",
            "data",
            "security",
            "runtime",
            "operational",
            "other",
        }
        accepted_states = {"accepted", "preferred", "restricted", "deprecated"}
        areas = catalog.get("areas")
        if not isinstance(areas, list):
            self.error(
                "ARCHITECTURE_AREAS_SHAPE",
                "areas must be a list",
                catalog_relpath,
            )
            areas = []
        patterns = catalog.get("patterns")
        if not isinstance(patterns, list):
            self.error(
                "ARCHITECTURE_PATTERNS_SHAPE",
                "patterns must be a list",
                catalog_relpath,
            )
            patterns = []

        area_ids = {
            item.get("id")
            for item in areas
            if isinstance(item, dict) and concrete(item.get("id"))
        }
        concrete_area_count = sum(
            1
            for item in areas
            if isinstance(item, dict) and concrete(item.get("id"))
        )
        if len(area_ids) != concrete_area_count:
            self.error(
                "ARCHITECTURE_AREA_ID_DUPLICATE",
                "concrete area IDs must be unique",
                catalog_relpath,
            )

        pattern_ids = {
            item.get("id")
            for item in patterns
            if isinstance(item, dict) and concrete(item.get("id"))
        }
        concrete_pattern_count = sum(
            1
            for item in patterns
            if isinstance(item, dict) and concrete(item.get("id"))
        )
        if len(pattern_ids) != concrete_pattern_count:
            self.error(
                "ARCHITECTURE_PATTERN_ID_DUPLICATE",
                "concrete pattern IDs must be unique",
                catalog_relpath,
            )

        area_fields = {"id", "name", "status", "owner", "detail", "evidence", "pattern_ids"}
        for index, area in enumerate(areas):
            label = f"areas[{index}]"
            if not isinstance(area, dict):
                self.error("ARCHITECTURE_AREA_SHAPE", f"{label} must be an object", catalog_relpath)
                continue
            missing = sorted(area_fields - set(area))
            if missing:
                self.error("ARCHITECTURE_AREA_FIELDS", f"{label} is missing {missing}", catalog_relpath)
            status = area.get("status")
            if concrete(status) and status not in statuses:
                self.error(
                    "ARCHITECTURE_ITEM_STATUS",
                    f"{label}.status is invalid: {status}",
                    catalog_relpath,
                )
            evidence = string_list(area.get("evidence"), f"{label}.evidence")
            refs = string_list(
                area.get("pattern_ids"),
                f"{label}.pattern_ids",
                non_empty=False,
            )
            for ref in refs:
                if concrete(ref) and ref not in pattern_ids:
                    self.error(
                        "ARCHITECTURE_PATTERN_REFERENCE",
                        f"{label} references unknown pattern {ref}",
                        catalog_relpath,
                    )
            if module_state == "enabled":
                for field in ["id", "name", "status", "owner"]:
                    if not concrete(area.get(field)):
                        self.error(
                            "ARCHITECTURE_ITEM_IDENTITY_UNRESOLVED",
                            f"{label}.{field} must be resolved",
                            catalog_relpath,
                        )
                if not any(concrete(item) for item in evidence):
                    self.error(
                        "ARCHITECTURE_ITEM_EVIDENCE_UNRESOLVED",
                        f"{label} needs concrete evidence",
                        catalog_relpath,
                    )

        pattern_fields = {
            "id", "name", "kind", "status", "scope", "problem",
            "decision_owner", "decision_record", "detail", "evidence",
            "validation", "related_pattern_ids", "last_verified_revision",
        }
        for index, pattern in enumerate(patterns):
            label = f"patterns[{index}]"
            if not isinstance(pattern, dict):
                self.error("ARCHITECTURE_PATTERN_SHAPE", f"{label} must be an object", catalog_relpath)
                continue
            missing = sorted(pattern_fields - set(pattern))
            if missing:
                self.error("ARCHITECTURE_PATTERN_FIELDS", f"{label} is missing {missing}", catalog_relpath)
            status = pattern.get("status")
            if concrete(status) and status not in statuses:
                self.error(
                    "ARCHITECTURE_ITEM_STATUS",
                    f"{label}.status is invalid: {status}",
                    catalog_relpath,
                )
            kind = pattern.get("kind")
            if concrete(kind) and kind not in pattern_kinds:
                self.error(
                    "ARCHITECTURE_PATTERN_KIND",
                    f"{label}.kind is invalid: {kind}",
                    catalog_relpath,
                )
            for field in ["scope", "evidence", "validation"]:
                values = string_list(pattern.get(field), f"{label}.{field}")
                if (
                    module_state == "enabled"
                    and not any(concrete(item) for item in values)
                ):
                    self.error(
                        "ARCHITECTURE_ITEM_FIELD_UNRESOLVED",
                        f"{label}.{field} needs at least one concrete value",
                        catalog_relpath,
                    )
            refs = string_list(
                pattern.get("related_pattern_ids"),
                f"{label}.related_pattern_ids",
                non_empty=False,
            )
            for ref in refs:
                if concrete(ref) and ref not in pattern_ids:
                    self.error(
                        "ARCHITECTURE_PATTERN_REFERENCE",
                        f"{label} references unknown pattern {ref}",
                        catalog_relpath,
                    )
            if module_state == "enabled":
                for field in [
                    "id",
                    "name",
                    "kind",
                    "status",
                    "problem",
                    "decision_owner",
                    "last_verified_revision",
                ]:
                    if not concrete(pattern.get(field)):
                        self.error(
                            "ARCHITECTURE_ITEM_IDENTITY_UNRESOLVED",
                            f"{label}.{field} must be resolved",
                            catalog_relpath,
                        )
            if status in accepted_states:
                for field in ["decision_owner", "decision_record", "last_verified_revision"]:
                    if not concrete(pattern.get(field)):
                        self.error(
                            "ARCHITECTURE_ACCEPTED_EVIDENCE",
                            f"{label} accepted state requires resolved {field}",
                            catalog_relpath,
                        )

        operation_catalog = self.load_json_object(
            self.target_path(".ai/assistant/operation-catalog.json"),
            "OPERATION_CATALOG",
        )
        operations = operation_catalog.get("operations") if isinstance(operation_catalog, dict) else None
        operation = next(
            (
                item for item in operations
                if isinstance(item, dict) and item.get("id") == "architecture-assistance"
            ),
            None,
        ) if isinstance(operations, list) else None
        if not isinstance(operation, dict):
            self.error(
                "ARCHITECTURE_OPERATION_MISSING",
                "enabled architecture knowledge requires architecture-assistance operation",
                ".ai/assistant/operation-catalog.json",
            )
        else:
            if operation.get("required_module") != "architecture-knowledge":
                self.error("ARCHITECTURE_OPERATION_MODULE", "architecture-assistance must require architecture-knowledge", ".ai/assistant/operation-catalog.json")
            if operation.get("flow") != required_paths[3]:
                self.error("ARCHITECTURE_OPERATION_FLOW", f"architecture-assistance must route to {required_paths[3]}", ".ai/assistant/operation-catalog.json")
            if operation.get("allowed_actions") != ["read-only", "docs-only", "full-with-approval"]:
                self.error("ARCHITECTURE_OPERATION_ACTIONS", "architecture-assistance allowed actions are invalid", ".ai/assistant/operation-catalog.json")

        router = self.load_json_object(
            self.target_path(".ai/assistant/context-router.json"), "ROUTER"
        )
        overlays = router.get("intent_overlays") if isinstance(router, dict) else None
        route = overlays.get("architecture-request") if isinstance(overlays, dict) else None
        if not isinstance(route, dict) or route.get("operation_candidates") != ["architecture-assistance"]:
            self.error(
                "ARCHITECTURE_OPERATION_UNROUTED",
                "enabled architecture assistance has no architecture-request intent route",
                ".ai/assistant/context-router.json",
            )

        required_text = {
            required_paths[0]: ["## Status Meanings", "## Architecture Patterns And Items", "Evidence revision:"],
            required_paths[3]: ["## Routing Modes", "no-change baseline", "reuse of an accepted project pattern", "adaptation of an existing pattern", "new pattern", "`docs-only`", "`full-with-approval`"],
            required_paths[4]: ["Pattern ID:", "Problem addressed:", "Rules and invariants:", "Do not use when:", "Last verified revision:"],
            required_paths[5]: ["Area ID:", "Responsibilities:", "Pattern IDs:", "Validation or fitness checks:"],
            required_paths[6]: ["No-change baseline:", "Reuse accepted project pattern:", "Adapt existing project pattern:", "Introduce new pattern:", "Pattern-proliferation result:"],
        }
        for relpath, snippets in required_text.items():
            text = self.read_text(self.target_path(relpath))
            for snippet in snippets:
                if snippet not in text:
                    self.error(
                        "ARCHITECTURE_CONTRACT_INCOMPLETE",
                        f"architecture contract is missing {snippet}",
                        relpath,
                    )

    def check_code_documentation(
        self, manifest: ManifestData | None
    ) -> None:
        module_relpath = ".ai/assistant/module-profile.md"
        module_path = self.target_path(module_relpath)
        if not module_path.is_file():
            return
        module_match = re.search(
            r"^Module: `code-documentation`\s*$([\s\S]*?)(?=^Module: `|\Z)",
            self.read_text(module_path),
            flags=re.MULTILINE,
        )
        if module_match is None:
            self.warn(
                "CODEDOC_MODULE_UNDECLARED",
                "module profile does not declare code-documentation state",
                module_relpath,
            )
            return
        state_match = re.search(
            r"^State:\s*`?([^`\n]+)`?\s*$",
            module_match.group(1),
            flags=re.MULTILINE,
        )
        if state_match is None:
            self.warn(
                "CODEDOC_MODULE_STATE_MISSING",
                "code-documentation module has no parseable State field",
                module_relpath,
            )
            return
        if state_match.group(1).strip().casefold() not in {"enabled", "required"}:
            return

        required_paths = [
            ".ai/project/documentation/README.md",
            ".ai/project/documentation/catalog.json",
            ".ai/project/documentation/profiles.json",
            ".ai/assistant/context/intents/code-documentation.json",
            ".ai/assistant/flows/documentation-sync.flow.md",
            ".ai/assistant/templates/code-documentation-profile-review.md",
            ".ai/assistant/skills/code-documentation/SKILL.md",
            ".ai/framework/code-documentation.md",
        ]
        missing = False
        for relpath in required_paths:
            if not self.target_path(relpath).is_file():
                missing = True
                self.error(
                    "CODEDOC_REQUIRED_FILE_MISSING",
                    "enabled code-documentation module is missing a contract",
                    relpath,
                )
        if missing:
            return

        if manifest is not None:
            expected_manifest = {
                ("source_of_truth", "code_documentation_index"): required_paths[0],
                ("source_of_truth", "code_documentation_catalog"): required_paths[1],
                ("source_of_truth", "code_documentation_profiles"): required_paths[2],
                ("operations", "documentation_sync"): required_paths[4],
                ("operations", "code_documentation_profile_review"): required_paths[5],
                ("code_documentation", "catalog"): required_paths[1],
                ("code_documentation", "profiles"): required_paths[2],
                ("code_documentation", "intent"): required_paths[3],
                ("code_documentation", "flow"): required_paths[4],
                ("code_documentation", "profile_review"): required_paths[5],
                ("code_documentation", "skill"): required_paths[6],
            }
            for key, expected in expected_manifest.items():
                scalar = manifest.scalars.get(key)
                if scalar is None or scalar.value != expected:
                    self.error(
                        "CODEDOC_MANIFEST_PATH",
                        f"{dotted(key)} must be {expected} when code documentation is enabled",
                        ".ai/alatyr.yaml",
                    )

        def concrete(value: Any) -> bool:
            return (
                isinstance(value, str)
                and bool(value.strip())
                and not is_placeholder(value)
                and not is_unresolved_value(value)
            )

        def string_list(
            value: Any, label: str, relpath: str, *, non_empty: bool = True
        ) -> list[str]:
            if not isinstance(value, list) or (non_empty and not value) or not all(
                isinstance(item, str) and item for item in value
            ):
                self.error(
                    "CODEDOC_LIST_SHAPE",
                    f"{label} must be a {'non-empty ' if non_empty else ''}string list",
                    relpath,
                )
                return []
            return value

        catalog_relpath = required_paths[1]
        catalog = self.load_json_object(
            self.target_path(catalog_relpath), "CODEDOC_CATALOG"
        )
        profiles_relpath = required_paths[2]
        profile_data = self.load_json_object(
            self.target_path(profiles_relpath), "CODEDOC_PROFILES"
        )
        if catalog is None or profile_data is None:
            return
        if catalog.get("schema_version") != 1:
            self.error("CODEDOC_CATALOG_SCHEMA", "schema_version should be 1", catalog_relpath)
        if catalog.get("catalog_kind") != "target-code-documentation-catalog":
            self.error("CODEDOC_CATALOG_KIND", "catalog_kind is invalid", catalog_relpath)
        if catalog.get("human_index") != required_paths[0]:
            self.error("CODEDOC_CATALOG_INDEX", "human_index is invalid", catalog_relpath)
        if catalog.get("profiles") != required_paths[2]:
            self.error("CODEDOC_CATALOG_PROFILES", "profiles path is invalid", catalog_relpath)
        for field in [
            "project", "module_state", "documentation_owner",
            "profile_decision_authority", "generation_owner",
            "last_reviewed", "evidence_revision",
        ]:
            if not concrete(catalog.get(field)):
                self.error(
                    "CODEDOC_ENABLED_METADATA_UNRESOLVED",
                    f"enabled code documentation requires resolved {field}",
                    catalog_relpath,
                )

        if profile_data.get("schema_version") != 1:
            self.error("CODEDOC_PROFILE_SCHEMA", "schema_version should be 1", profiles_relpath)
        if profile_data.get("profile_kind") != "target-code-documentation-profiles":
            self.error("CODEDOC_PROFILE_KIND", "profile_kind is invalid", profiles_relpath)
        selection = profile_data.get("selection_policy")
        if not isinstance(selection, dict):
            self.error("CODEDOC_SELECTION_POLICY", "selection_policy must be an object", profiles_relpath)
        else:
            for field in ["order", "on_equal_conflict", "on_no_accepted_match"]:
                if field not in selection:
                    self.error("CODEDOC_SELECTION_POLICY", f"selection_policy missing {field}", profiles_relpath)

        entries = profile_data.get("profiles")
        if not isinstance(entries, list) or not entries:
            self.error("CODEDOC_PROFILES_EMPTY", "enabled module requires profiles", profiles_relpath)
            entries = []
        valid_states = {"proposed", "accepted", "deprecated", "contradicted", "unknown"}
        valid_outputs = {"ci-artifact", "committed-generated", "local-only", "external-publish", "unresolved"}
        profile_ids: set[str] = set()
        accepted_count = 0
        accepted_selectors: dict[tuple[Any, ...], str] = {}
        required_fields = {
            "id", "state", "owner", "priority", "match", "audiences",
            "visibility", "purpose", "evidence", "comment_contract",
            "generation", "validation", "assistant_skill", "migration_scope",
            "approval_needs", "known_gaps",
        }
        for index, profile in enumerate(entries):
            label = f"profiles[{index}]"
            if not isinstance(profile, dict):
                self.error("CODEDOC_PROFILE_SHAPE", f"{label} must be an object", profiles_relpath)
                continue
            missing_fields = sorted(required_fields - set(profile))
            if missing_fields:
                self.error("CODEDOC_PROFILE_FIELDS", f"{label} missing {missing_fields}", profiles_relpath)
            profile_id = profile.get("id")
            if concrete(profile_id):
                if profile_id in profile_ids:
                    self.error("CODEDOC_PROFILE_ID_DUPLICATE", f"duplicate profile ID {profile_id}", profiles_relpath)
                profile_ids.add(profile_id)
            state = profile.get("state")
            if not concrete(state) or state not in valid_states:
                self.error("CODEDOC_PROFILE_STATE", f"{label}.state is invalid or unresolved", profiles_relpath)
            match = profile.get("match")
            if not isinstance(match, dict):
                self.error("CODEDOC_PROFILE_MATCH", f"{label}.match must be an object", profiles_relpath)
                match = {}
            include = string_list(match.get("include"), f"{label}.match.include", profiles_relpath)
            exclude = string_list(match.get("exclude"), f"{label}.match.exclude", profiles_relpath, non_empty=False)
            languages = string_list(match.get("languages"), f"{label}.match.languages", profiles_relpath)
            frameworks = string_list(match.get("frameworks"), f"{label}.match.frameworks", profiles_relpath, non_empty=False)
            audiences = string_list(profile.get("audiences"), f"{label}.audiences", profiles_relpath)
            validation = string_list(profile.get("validation"), f"{label}.validation", profiles_relpath)
            comment = profile.get("comment_contract")
            generation = profile.get("generation")
            if not isinstance(comment, dict):
                self.error("CODEDOC_COMMENT_CONTRACT", f"{label}.comment_contract must be an object", profiles_relpath)
                comment = {}
            if not isinstance(generation, dict):
                self.error("CODEDOC_GENERATION_CONTRACT", f"{label}.generation must be an object", profiles_relpath)
                generation = {}
            if generation.get("direct_edit") != "forbidden":
                self.error("CODEDOC_DIRECT_EDIT", f"{label} must forbid direct generated-output edits", profiles_relpath)
            output_policy = generation.get("output_policy")
            if concrete(output_policy) and output_policy not in valid_outputs:
                self.error("CODEDOC_OUTPUT_POLICY", f"{label}.generation.output_policy is invalid", profiles_relpath)
            if state == "accepted":
                accepted_count += 1
                for field in ["id", "owner", "visibility", "purpose"]:
                    if not concrete(profile.get(field)):
                        self.error("CODEDOC_ACCEPTED_UNRESOLVED", f"{label}.{field} must be resolved", profiles_relpath)
                for field in ["syntax", "uncertainty_policy"]:
                    if not concrete(comment.get(field)):
                        self.error("CODEDOC_ACCEPTED_UNRESOLVED", f"{label}.comment_contract.{field} must be resolved", profiles_relpath)
                for field in ["generator", "entry_point", "output", "output_policy", "publication_boundary"]:
                    if not concrete(generation.get(field)):
                        self.error("CODEDOC_ACCEPTED_UNRESOLVED", f"{label}.generation.{field} must be resolved", profiles_relpath)
                for values, field in [(include, "include"), (languages, "languages"), (audiences, "audiences"), (validation, "validation")]:
                    if not any(concrete(item) for item in values):
                        self.error("CODEDOC_ACCEPTED_UNRESOLVED", f"{label}.{field} needs concrete values", profiles_relpath)
                selector = (
                    tuple(sorted(include)), tuple(sorted(exclude)),
                    tuple(sorted(languages)), tuple(sorted(frameworks)),
                    profile.get("priority"),
                )
                prior = accepted_selectors.get(selector)
                if prior is not None:
                    self.error(
                        "CODEDOC_ACCEPTED_AMBIGUITY",
                        f"accepted profiles {prior} and {profile_id} have equal selectors and priority",
                        profiles_relpath,
                    )
                elif concrete(profile_id):
                    accepted_selectors[selector] = profile_id
        if accepted_count == 0:
            self.error(
                "CODEDOC_NO_ACCEPTED_PROFILE",
                "enabled code-documentation module requires at least one accepted profile",
                profiles_relpath,
            )

        areas = catalog.get("areas")
        if not isinstance(areas, list) or not areas:
            self.error("CODEDOC_AREAS_EMPTY", "enabled catalog requires areas", catalog_relpath)
        else:
            for index, area in enumerate(areas):
                label = f"areas[{index}]"
                if not isinstance(area, dict):
                    self.error("CODEDOC_AREA_SHAPE", f"{label} must be an object", catalog_relpath)
                    continue
                for ref in string_list(area.get("profile_ids"), f"{label}.profile_ids", catalog_relpath):
                    if concrete(ref) and ref not in profile_ids:
                        self.error("CODEDOC_PROFILE_REFERENCE", f"{label} references unknown profile {ref}", catalog_relpath)

        router = self.load_json_object(
            self.target_path(".ai/assistant/context-router.json"), "ROUTER"
        )
        overlays = router.get("intent_overlays") if isinstance(router, dict) else None
        route = overlays.get("code-documentation") if isinstance(overlays, dict) else None
        if not isinstance(route, dict) or route.get("operation_candidates") != ["documentation-sync"]:
            self.error(
                "CODEDOC_OPERATION_UNROUTED",
                "enabled code documentation has no documentation intent route",
                ".ai/assistant/context-router.json",
            )

        required_text = {
            required_paths[0]: ["## Profile States", "## Source-Of-Truth Boundary", "## Documentation Areas"],
            required_paths[4]: ["## Routing Modes", "`propose`", "`document`", "`generate`", "Never edit a configured generated output directly"],
            required_paths[5]: ["Profile state:", "Generator and configuration:", "Approval needs:"],
            required_paths[6]: ["most specific accepted profile", "Never edit generated output directly", "Do not activate this placeholder"],
            required_paths[7]: ["ALATYR-CODEDOC-001", "## Multiple Documentation Profiles", "## Generation And Output Policy"],
        }
        for relpath, snippets in required_text.items():
            text = self.read_text(self.target_path(relpath))
            for snippet in snippets:
                if snippet not in text:
                    self.error("CODEDOC_CONTRACT_INCOMPLETE", f"code-documentation contract is missing {snippet}", relpath)

        self.info(
            "CODEDOC_EVIDENCE_LIMIT",
            "code-documentation structural checks do not prove comment truth, semantic completeness, or generated-reference quality",
        )

    def check_project_vocabulary(
        self, manifest: ManifestData | None
    ) -> None:
        module_relpath = ".ai/assistant/module-profile.md"
        module_path = self.target_path(module_relpath)
        if not module_path.is_file():
            return
        module_match = re.search(
            r"^Module: `project-vocabulary`\s*$([\s\S]*?)(?=^Module: `|\Z)",
            self.read_text(module_path),
            flags=re.MULTILINE,
        )
        if module_match is None:
            self.warn(
                "VOCABULARY_MODULE_UNDECLARED",
                "module profile does not declare project-vocabulary state",
                module_relpath,
            )
            return
        state_match = re.search(
            r"^State:\s*`?([^`\n]+)`?\s*$",
            module_match.group(1),
            flags=re.MULTILINE,
        )
        if state_match is None:
            self.warn(
                "VOCABULARY_MODULE_STATE_MISSING",
                "project-vocabulary module has no parseable State field",
                module_relpath,
            )
            return
        if state_match.group(1).strip().casefold() not in {"enabled", "required"}:
            return

        required_paths = [
            ".ai/project/vocabulary/README.md",
            ".ai/project/vocabulary/catalog.json",
            ".ai/project/vocabulary/terms.json",
            ".ai/project/vocabulary/data-dictionary-links.json",
            ".ai/assistant/context/intents/vocabulary-request.json",
            ".ai/assistant/flows/project-vocabulary.flow.md",
            ".ai/assistant/templates/vocabulary-term-review.md",
            ".ai/assistant/skills/project-vocabulary/SKILL.md",
            ".ai/framework/project-vocabulary.md",
        ]
        missing = False
        for relpath in required_paths:
            if not self.target_path(relpath).is_file():
                missing = True
                self.error(
                    "VOCABULARY_REQUIRED_FILE_MISSING",
                    "enabled project-vocabulary module is missing a contract",
                    relpath,
                )
        if missing:
            return

        if manifest is not None:
            expected_manifest = {
                ("source_of_truth", "vocabulary_index"): required_paths[0],
                ("source_of_truth", "vocabulary_catalog"): required_paths[1],
                ("source_of_truth", "vocabulary_terms"): required_paths[2],
                ("source_of_truth", "vocabulary_data_dictionary_links"): required_paths[3],
                ("operations", "project_vocabulary"): required_paths[5],
                ("operations", "vocabulary_term_review"): required_paths[6],
                ("project_vocabulary", "catalog"): required_paths[1],
                ("project_vocabulary", "terms"): required_paths[2],
                ("project_vocabulary", "data_dictionary_links"): required_paths[3],
                ("project_vocabulary", "intent"): required_paths[4],
                ("project_vocabulary", "flow"): required_paths[5],
                ("project_vocabulary", "term_review"): required_paths[6],
                ("project_vocabulary", "skill"): required_paths[7],
            }
            for key, expected in expected_manifest.items():
                scalar = manifest.scalars.get(key)
                if scalar is None or scalar.value != expected:
                    self.error(
                        "VOCABULARY_MANIFEST_PATH",
                        f"{dotted(key)} must be {expected} when project vocabulary is enabled",
                        ".ai/alatyr.yaml",
                    )

        def concrete(value: Any) -> bool:
            return (
                isinstance(value, str)
                and bool(value.strip())
                and not is_placeholder(value)
                and not is_unresolved_value(value)
            )

        def string_list(
            value: Any, label: str, relpath: str, *, non_empty: bool = True
        ) -> list[str]:
            if not isinstance(value, list) or (non_empty and not value) or not all(
                isinstance(item, str) and item for item in value
            ):
                self.error(
                    "VOCABULARY_STRING_LIST",
                    f"{label} must contain strings" + (" and be non-empty" if non_empty else ""),
                    relpath,
                )
                return []
            return value

        catalog_relpath = required_paths[1]
        terms_relpath = required_paths[2]
        links_relpath = required_paths[3]
        catalog = self.load_json_object(
            self.target_path(catalog_relpath), "VOCABULARY_CATALOG"
        )
        term_data = self.load_json_object(
            self.target_path(terms_relpath), "VOCABULARY_TERMS"
        )
        link_data = self.load_json_object(
            self.target_path(links_relpath), "VOCABULARY_LINKS"
        )
        if catalog is None or term_data is None or link_data is None:
            return

        if catalog.get("schema_version") != 1:
            self.error("VOCABULARY_CATALOG_SCHEMA", "schema_version should be 1", catalog_relpath)
        if catalog.get("catalog_kind") != "target-project-vocabulary-catalog":
            self.error("VOCABULARY_CATALOG_KIND", "catalog_kind is invalid", catalog_relpath)
        expected_catalog = {
            "human_index": required_paths[0],
            "terms": required_paths[2],
            "data_dictionary_links": required_paths[3],
        }
        for field, expected in expected_catalog.items():
            if catalog.get(field) != expected:
                self.error("VOCABULARY_CATALOG_PATH", f"{field} must be {expected}", catalog_relpath)
        for field in [
            "project", "module_state", "vocabulary_owner",
            "term_decision_authority", "normalization_policy",
            "last_reviewed", "evidence_revision",
        ]:
            if not concrete(catalog.get(field)):
                self.error(
                    "VOCABULARY_ENABLED_METADATA_UNRESOLVED",
                    f"enabled project vocabulary requires resolved {field}",
                    catalog_relpath,
                )

        if term_data.get("schema_version") != 1:
            self.error("VOCABULARY_TERM_SCHEMA", "schema_version should be 1", terms_relpath)
        if term_data.get("record_kind") != "target-project-vocabulary-terms":
            self.error("VOCABULARY_TERM_KIND", "record_kind is invalid", terms_relpath)
        valid_states = {
            "observed", "proposed", "accepted", "deprecated", "contradicted", "unknown"
        }
        required_term_fields = {
            "id", "canonical_term", "normalized_term", "kind", "state",
            "domains", "usage_scopes", "audiences", "definition",
            "non_meanings", "aliases", "acronyms", "acronym_expansions",
            "discouraged_synonyms", "replacement_term_id", "owner",
            "decision_authority", "canonical_sources", "evidence",
            "related_term_ids", "data_dictionary_refs", "examples",
            "sensitivity", "validation", "last_verified_revision",
            "contradictions", "known_gaps",
        }
        terms = term_data.get("terms")
        if not isinstance(terms, list) or not terms:
            self.error("VOCABULARY_TERMS_EMPTY", "enabled module requires term records", terms_relpath)
            terms = []
        term_ids: set[str] = set()
        term_by_id: dict[str, dict[str, Any]] = {}
        accepted_count = 0
        accepted_lookup: dict[tuple[str, tuple[str, ...]], str] = {}
        pending_term_refs: list[tuple[str, str, str]] = []
        pending_data_refs: list[tuple[str, str]] = []
        for index, term in enumerate(terms):
            label = f"terms[{index}]"
            if not isinstance(term, dict):
                self.error("VOCABULARY_TERM_SHAPE", f"{label} must be an object", terms_relpath)
                continue
            missing_fields = sorted(required_term_fields - set(term))
            if missing_fields:
                self.error("VOCABULARY_TERM_FIELDS", f"{label} missing {missing_fields}", terms_relpath)
            term_id = term.get("id")
            if concrete(term_id):
                if term_id in term_ids:
                    self.error("VOCABULARY_TERM_ID_DUPLICATE", f"duplicate term ID {term_id}", terms_relpath)
                term_ids.add(term_id)
                term_by_id[term_id] = term
            state = term.get("state")
            if not concrete(state) or state not in valid_states:
                self.error("VOCABULARY_TERM_STATE", f"{label}.state is invalid or unresolved", terms_relpath)
            domains = string_list(term.get("domains"), f"{label}.domains", terms_relpath)
            aliases = string_list(term.get("aliases"), f"{label}.aliases", terms_relpath, non_empty=False)
            acronyms = string_list(term.get("acronyms"), f"{label}.acronyms", terms_relpath, non_empty=False)
            string_list(term.get("acronym_expansions"), f"{label}.acronym_expansions", terms_relpath, non_empty=False)
            related = string_list(term.get("related_term_ids"), f"{label}.related_term_ids", terms_relpath, non_empty=False)
            data_refs = string_list(term.get("data_dictionary_refs"), f"{label}.data_dictionary_refs", terms_relpath, non_empty=False)
            for ref in related:
                if concrete(ref) and concrete(term_id):
                    pending_term_refs.append((term_id, ref, "related_term_ids"))
            for ref in data_refs:
                if concrete(ref) and concrete(term_id):
                    pending_data_refs.append((term_id, ref))
            if state == "accepted":
                accepted_count += 1
                for field in [
                    "id", "canonical_term", "normalized_term", "kind",
                    "definition", "owner", "decision_authority", "sensitivity",
                    "last_verified_revision",
                ]:
                    if not concrete(term.get(field)):
                        self.error("VOCABULARY_ACCEPTED_UNRESOLVED", f"{label}.{field} must be resolved", terms_relpath)
                canonical_sources = string_list(term.get("canonical_sources"), f"{label}.canonical_sources", terms_relpath)
                validation = string_list(term.get("validation"), f"{label}.validation", terms_relpath)
                for values, field in [
                    (domains, "domains"),
                    (canonical_sources, "canonical_sources"),
                    (validation, "validation"),
                ]:
                    if not any(concrete(value) for value in values):
                        self.error("VOCABULARY_ACCEPTED_UNRESOLVED", f"{label}.{field} needs concrete values", terms_relpath)
                lookup_values = [term.get("normalized_term"), *aliases, *acronyms]
                domain_key = tuple(sorted(value.casefold() for value in domains if concrete(value)))
                for lookup in lookup_values:
                    if not concrete(lookup) or not concrete(term_id):
                        continue
                    key = (lookup.casefold(), domain_key)
                    prior = accepted_lookup.get(key)
                    if prior is not None and prior != term_id:
                        self.error(
                            "VOCABULARY_ACCEPTED_AMBIGUITY",
                            f"accepted terms {prior} and {term_id} share lookup {lookup} in the same domains",
                            terms_relpath,
                        )
                    else:
                        accepted_lookup[key] = term_id
        if accepted_count == 0:
            self.error(
                "VOCABULARY_NO_ACCEPTED_TERM",
                "enabled project-vocabulary module requires at least one accepted term",
                terms_relpath,
            )
        for source_id, ref, field in pending_term_refs:
            if ref not in term_ids:
                self.error("VOCABULARY_TERM_REFERENCE", f"{source_id}.{field} references unknown term {ref}", terms_relpath)

        catalog_entries = catalog.get("entries")
        if not isinstance(catalog_entries, list) or not catalog_entries:
            self.error("VOCABULARY_CATALOG_EMPTY", "enabled catalog requires entries", catalog_relpath)
        else:
            catalog_ids: set[str] = set()
            for index, entry in enumerate(catalog_entries):
                label = f"entries[{index}]"
                if not isinstance(entry, dict):
                    self.error("VOCABULARY_CATALOG_ENTRY_SHAPE", f"{label} must be an object", catalog_relpath)
                    continue
                required_catalog_fields = {
                    "term_id", "canonical_term", "normalized_term", "aliases",
                    "acronyms", "domains", "state", "record",
                    "replacement_term_id", "last_verified_revision",
                }
                missing_fields = sorted(required_catalog_fields - set(entry))
                if missing_fields:
                    self.error("VOCABULARY_CATALOG_ENTRY_FIELDS", f"{label} missing {missing_fields}", catalog_relpath)
                term_id = entry.get("term_id")
                if concrete(term_id):
                    if term_id in catalog_ids:
                        self.error("VOCABULARY_CATALOG_ID_DUPLICATE", f"duplicate catalog term ID {term_id}", catalog_relpath)
                    catalog_ids.add(term_id)
                    if term_id not in term_ids:
                        self.error("VOCABULARY_CATALOG_REFERENCE", f"{label} references unknown term {term_id}", catalog_relpath)
                    else:
                        term = term_by_id[term_id]
                        for field in [
                            "canonical_term", "normalized_term", "state",
                            "replacement_term_id", "last_verified_revision",
                        ]:
                            if entry.get(field) != term.get(field):
                                self.error(
                                    "VOCABULARY_CATALOG_DRIFT",
                                    f"{label}.{field} does not match term record {term_id}",
                                    catalog_relpath,
                                )
                        list_pairs = {
                            "aliases": "aliases",
                            "acronyms": "acronyms",
                            "domains": "domains",
                        }
                        for catalog_field, term_field in list_pairs.items():
                            catalog_values = entry.get(catalog_field)
                            term_values = term.get(term_field)
                            if (
                                not isinstance(catalog_values, list)
                                or not isinstance(term_values, list)
                                or sorted(catalog_values) != sorted(term_values)
                            ):
                                self.error(
                                    "VOCABULARY_CATALOG_DRIFT",
                                    f"{label}.{catalog_field} does not match term record {term_id}",
                                    catalog_relpath,
                                )
                        expected_record = f".ai/project/vocabulary/terms.json#{term_id}"
                        if entry.get("record") != expected_record:
                            self.error(
                                "VOCABULARY_CATALOG_RECORD",
                                f"{label}.record must be {expected_record}",
                                catalog_relpath,
                            )
            for term_id in term_ids - catalog_ids:
                self.error("VOCABULARY_TERM_UNINDEXED", f"term {term_id} is missing from compact catalog", catalog_relpath)

        if link_data.get("schema_version") != 1:
            self.error("VOCABULARY_LINK_SCHEMA", "schema_version should be 1", links_relpath)
        if link_data.get("record_kind") != "target-vocabulary-data-dictionary-links":
            self.error("VOCABULARY_LINK_KIND", "record_kind is invalid", links_relpath)
        links = link_data.get("links")
        if not isinstance(links, list):
            self.error("VOCABULARY_LINKS_SHAPE", "links must be a list", links_relpath)
            links = []
        link_ids: set[str] = set()
        required_link_fields = {
            "id", "term_id", "fact_type", "canonical_owner",
            "target_identifier", "relationship", "direction", "evidence",
            "validation", "last_verified_revision", "known_gaps",
        }
        for index, link in enumerate(links):
            label = f"links[{index}]"
            if not isinstance(link, dict):
                self.error("VOCABULARY_LINK_SHAPE", f"{label} must be an object", links_relpath)
                continue
            missing_fields = sorted(required_link_fields - set(link))
            if missing_fields:
                self.error("VOCABULARY_LINK_FIELDS", f"{label} missing {missing_fields}", links_relpath)
            link_id = link.get("id")
            if concrete(link_id):
                if link_id in link_ids:
                    self.error("VOCABULARY_LINK_ID_DUPLICATE", f"duplicate data link ID {link_id}", links_relpath)
                link_ids.add(link_id)
            term_id = link.get("term_id")
            if concrete(term_id) and term_id not in term_ids:
                self.error("VOCABULARY_LINK_TERM_REFERENCE", f"{label} references unknown term {term_id}", links_relpath)
            for field in ["fact_type", "canonical_owner", "target_identifier", "relationship", "direction", "last_verified_revision"]:
                if not concrete(link.get(field)):
                    self.error("VOCABULARY_LINK_UNRESOLVED", f"{label}.{field} must be resolved", links_relpath)
        for term_id, ref in pending_data_refs:
            if ref not in link_ids:
                self.error("VOCABULARY_DATA_REFERENCE", f"term {term_id} references unknown data link {ref}", terms_relpath)

        operation_catalog = self.load_json_object(
            self.target_path(".ai/assistant/operation-catalog.json"),
            "OPERATION_CATALOG",
        )
        operations = operation_catalog.get("operations") if isinstance(operation_catalog, dict) else None
        operation = next(
            (item for item in operations
             if isinstance(item, dict) and item.get("id") == "project-vocabulary"),
            None,
        ) if isinstance(operations, list) else None
        if not isinstance(operation, dict):
            self.error("VOCABULARY_OPERATION_MISSING", "enabled vocabulary requires project-vocabulary operation", ".ai/assistant/operation-catalog.json")
        else:
            if operation.get("required_module") != "project-vocabulary":
                self.error("VOCABULARY_OPERATION_MODULE", "project-vocabulary operation module is invalid", ".ai/assistant/operation-catalog.json")
            if operation.get("flow") != required_paths[5]:
                self.error("VOCABULARY_OPERATION_FLOW", f"project-vocabulary must route to {required_paths[5]}", ".ai/assistant/operation-catalog.json")
            if operation.get("allowed_actions") != ["read-only", "docs-only", "full-with-approval"]:
                self.error("VOCABULARY_OPERATION_ACTIONS", "project-vocabulary allowed actions are invalid", ".ai/assistant/operation-catalog.json")

        router = self.load_json_object(
            self.target_path(".ai/assistant/context-router.json"), "ROUTER"
        )
        overlays = router.get("intent_overlays") if isinstance(router, dict) else None
        route = overlays.get("vocabulary-request") if isinstance(overlays, dict) else None
        if not isinstance(route, dict) or route.get("operation_candidates") != ["project-vocabulary"]:
            self.error("VOCABULARY_OPERATION_UNROUTED", "enabled vocabulary has no vocabulary-request intent route", ".ai/assistant/context-router.json")

        required_text = {
            required_paths[0]: ["## Term States", "## Vocabulary Boundaries", "## Lookup Behavior"],
            required_paths[5]: ["## Routing Modes", "`lookup`", "`terminology-check`", "Do not mark observed or proposed records accepted"],
            required_paths[6]: ["Selected term IDs:", "Data dictionary links:", "Acceptance state:"],
            required_paths[7]: ["Preserve `observed`, `proposed`, `accepted`", "Do not activate this placeholder"],
            required_paths[8]: ["ALATYR-VOCABULARY-001", "## Compact Catalog And Lookup", "## Data Dictionary Links"],
        }
        for relpath, snippets in required_text.items():
            text = self.read_text(self.target_path(relpath))
            for snippet in snippets:
                if snippet not in text:
                    self.error("VOCABULARY_CONTRACT_INCOMPLETE", f"project-vocabulary contract is missing {snippet}", relpath)

        self.info(
            "VOCABULARY_EVIDENCE_LIMIT",
            "project-vocabulary structural checks do not prove term meaning, ownership, relationship, acceptance, or semantic consistency",
        )

    def check_test_first_development(
        self, manifest: ManifestData | None
    ) -> None:
        module_relpath = ".ai/assistant/module-profile.md"
        module_path = self.target_path(module_relpath)
        if not module_path.is_file():
            return
        module_match = re.search(
            r"^Module: `test-first-development`\s*$([\s\S]*?)(?=^Module: `|\Z)",
            self.read_text(module_path),
            flags=re.MULTILINE,
        )
        if module_match is None:
            self.warn(
                "TDD_MODULE_UNDECLARED",
                "module profile does not declare test-first-development state",
                module_relpath,
            )
            return
        state_match = re.search(
            r"^State:\s*`?([^`\n]+)`?\s*$",
            module_match.group(1),
            flags=re.MULTILINE,
        )
        if state_match is None:
            self.warn(
                "TDD_MODULE_STATE_MISSING",
                "test-first-development module has no parseable State field",
                module_relpath,
            )
            return
        if state_match.group(1).strip().casefold() not in {"enabled", "required"}:
            return

        required_paths = [
            ".ai/project/testing/README.md",
            ".ai/project/testing/test-first-policy.json",
            ".ai/assistant/context/intents/test-first-request.json",
            ".ai/assistant/flows/test-first-configuration.flow.md",
            ".ai/assistant/flows/test-first-change.flow.md",
            ".ai/assistant/gates/test-first-development.md",
            ".ai/assistant/templates/test-first-evidence.md",
            ".ai/assistant/skills/test-first-development/SKILL.md",
            ".ai/framework/test-first-development.md",
        ]
        missing = False
        for relpath in required_paths:
            if not self.target_path(relpath).is_file():
                missing = True
                self.error(
                    "TDD_REQUIRED_FILE_MISSING",
                    "enabled test-first-development module is missing a contract",
                    relpath,
                )
        if missing:
            return

        if manifest is not None:
            expected_manifest = {
                ("source_of_truth", "testing_index"): required_paths[0],
                ("source_of_truth", "test_first_policy"): required_paths[1],
                ("operations", "test_first_configuration"): required_paths[3],
                ("operations", "test_first_change"): required_paths[4],
                ("operations", "test_first_evidence"): required_paths[6],
                ("test_first_development", "policy"): required_paths[1],
                ("test_first_development", "intent"): required_paths[2],
                ("test_first_development", "configuration_flow"): required_paths[3],
                ("test_first_development", "change_flow"): required_paths[4],
                ("test_first_development", "gate"): required_paths[5],
                ("test_first_development", "evidence"): required_paths[6],
                ("test_first_development", "skill"): required_paths[7],
            }
            for key, expected in expected_manifest.items():
                scalar = manifest.scalars.get(key)
                if scalar is None or scalar.value != expected:
                    self.error(
                        "TDD_MANIFEST_PATH",
                        f"{dotted(key)} must be {expected} when test-first development is enabled",
                        ".ai/alatyr.yaml",
                    )

        policy_relpath = required_paths[1]
        policy = self.load_json_object(
            self.target_path(policy_relpath), "TDD_POLICY"
        )
        if policy is None:
            return

        def resolved(value: Any) -> bool:
            return (
                isinstance(value, str)
                and bool(value.strip())
                and not is_placeholder(value)
                and not is_unresolved_value(value)
            )

        if policy.get("schema_version") != 1:
            self.error("TDD_POLICY_SCHEMA", "schema_version should be 1", policy_relpath)
        if policy.get("policy_kind") != "target-test-first-development-policy":
            self.error("TDD_POLICY_KIND", "policy_kind is invalid", policy_relpath)
        if str(policy.get("state", "")).casefold() not in {"enabled", "required"}:
            self.error(
                "TDD_POLICY_NOT_ENABLED",
                "enabled module requires enabled or required target policy state",
                policy_relpath,
            )
        for field in ["project", "owner", "decision_authority", "last_reviewed", "evidence_revision"]:
            if not resolved(policy.get(field)):
                self.error(
                    "TDD_POLICY_METADATA_UNRESOLVED",
                    f"enabled test-first policy requires resolved {field}",
                    policy_relpath,
                )

        suggestion = policy.get("suggestion")
        if not isinstance(suggestion, dict):
            self.error("TDD_SUGGESTION_SHAPE", "suggestion must be an object", policy_relpath)
        else:
            if suggestion.get("mode") not in {"off", "advisory"}:
                self.error("TDD_SUGGESTION_MODE", "suggestion.mode must be off or advisory", policy_relpath)
            if suggestion.get("minimum_result") not in {"recommended", "required"}:
                self.error("TDD_SUGGESTION_RESULT", "suggestion.minimum_result is invalid", policy_relpath)
            if suggestion.get("max_per_task") != 1 or suggestion.get("suppress_after_decline") is not True:
                self.error("TDD_SUGGESTION_BOUNDS", "suggestions must be limited to once per task and suppressed after decline", policy_relpath)
            if suggestion.get("cost_statement_required") is not True:
                self.error("TDD_SUGGESTION_COST", "suggestions must state expected cost", policy_relpath)

        valid_modes = {
            "strict-tdd", "regression-first", "characterization-first",
            "contract-first", "test-after-with-reason",
        }
        modes = policy.get("available_modes")
        if not isinstance(modes, list) or not modes or not all(mode in valid_modes for mode in modes):
            self.error("TDD_MODES_INVALID", "available_modes must contain accepted test-first modes", policy_relpath)

        triggers = policy.get("activation_triggers")
        if not isinstance(triggers, list) or not triggers:
            self.error("TDD_TRIGGERS_EMPTY", "enabled policy requires activation triggers", policy_relpath)
        else:
            trigger_ids: set[str] = set()
            for index, trigger in enumerate(triggers):
                if not isinstance(trigger, dict):
                    self.error("TDD_TRIGGER_SHAPE", f"activation_triggers[{index}] must be an object", policy_relpath)
                    continue
                for field in ["id", "state", "mode"]:
                    if not resolved(trigger.get(field)):
                        self.error("TDD_TRIGGER_UNRESOLVED", f"activation_triggers[{index}].{field} must be resolved", policy_relpath)
                trigger_id = trigger.get("id")
                if resolved(trigger_id):
                    if trigger_id in trigger_ids:
                        self.error(
                            "TDD_TRIGGER_DUPLICATE",
                            f"activation_triggers contains duplicate id {trigger_id}",
                            policy_relpath,
                        )
                    trigger_ids.add(trigger_id)
                if trigger.get("state") not in {"required", "recommended", "disabled"}:
                    self.error("TDD_TRIGGER_STATE", f"activation_triggers[{index}].state is invalid", policy_relpath)
                if trigger.get("mode") not in valid_modes:
                    self.error("TDD_TRIGGER_MODE", f"activation_triggers[{index}].mode is invalid", policy_relpath)
                elif isinstance(modes, list) and trigger.get("mode") not in modes:
                    self.error(
                        "TDD_TRIGGER_MODE_UNAVAILABLE",
                        f"activation_triggers[{index}].mode is not in available_modes",
                        policy_relpath,
                    )
                for field in ["changed_fact_classes", "conditions", "test_level_ids"]:
                    value = trigger.get(field)
                    if not isinstance(value, list) or not value or not all(resolved(item) for item in value):
                        self.error("TDD_TRIGGER_LIST", f"activation_triggers[{index}].{field} needs resolved values", policy_relpath)
                exceptions = trigger.get("exceptions")
                if not isinstance(exceptions, list) or not all(
                    resolved(item) for item in exceptions
                ):
                    self.error(
                        "TDD_TRIGGER_EXCEPTIONS",
                        f"activation_triggers[{index}].exceptions must contain resolved IDs",
                        policy_relpath,
                    )

        for field in ["test_levels", "commands", "evidence_requirements"]:
            value = policy.get(field)
            if not isinstance(value, list) or not value:
                self.error("TDD_POLICY_LIST_EMPTY", f"{field} must be non-empty", policy_relpath)
        exceptions = policy.get("exceptions")
        if not isinstance(exceptions, list):
            self.error("TDD_EXCEPTIONS_SHAPE", "exceptions must be a list", policy_relpath)
        evidence_requirements = policy.get("evidence_requirements")
        if isinstance(evidence_requirements, list) and not all(
            resolved(item) for item in evidence_requirements
        ):
            self.error(
                "TDD_EVIDENCE_REQUIREMENTS",
                "evidence_requirements must contain resolved values",
                policy_relpath,
            )
        known_gaps = policy.get("known_gaps")
        if not isinstance(known_gaps, list) or not all(
            resolved(item) for item in known_gaps
        ):
            self.error(
                "TDD_KNOWN_GAPS",
                "known_gaps must be a list of resolved values",
                policy_relpath,
            )

        def indexed_records(field: str) -> tuple[dict[str, dict[str, Any]], bool]:
            records = policy.get(field)
            indexed: dict[str, dict[str, Any]] = {}
            valid = isinstance(records, list)
            if not isinstance(records, list):
                return indexed, False
            for index, record in enumerate(records):
                if not isinstance(record, dict) or not resolved(record.get("id")):
                    self.error(
                        "TDD_RECORD_ID",
                        f"{field}[{index}] requires a resolved id",
                        policy_relpath,
                    )
                    valid = False
                    continue
                record_id = record["id"]
                if record_id in indexed:
                    self.error(
                        "TDD_RECORD_DUPLICATE",
                        f"{field} contains duplicate id {record_id}",
                        policy_relpath,
                    )
                    valid = False
                indexed[record_id] = record
            return indexed, valid

        test_levels, _ = indexed_records("test_levels")
        commands, _ = indexed_records("commands")
        exception_records, _ = indexed_records("exceptions")

        for level_id, level in test_levels.items():
            for field in ["purpose", "feedback_time"]:
                if not resolved(level.get(field)):
                    self.error(
                        "TDD_TEST_LEVEL_UNRESOLVED",
                        f"test level {level_id} requires resolved {field}",
                        policy_relpath,
                    )
            for field in ["paths", "command_ids", "fixtures_and_helpers"]:
                values = level.get(field)
                if not isinstance(values, list) or not values or not all(
                    resolved(item) for item in values
                ):
                    self.error(
                        "TDD_TEST_LEVEL_LIST",
                        f"test level {level_id}.{field} requires resolved values",
                        policy_relpath,
                    )
            for command_id in level.get("command_ids", []):
                if command_id not in commands:
                    self.error(
                        "TDD_COMMAND_REFERENCE",
                        f"test level {level_id} references unknown command {command_id}",
                        policy_relpath,
                    )

        for command_id, command in commands.items():
            for field in ["command", "scope", "live_external_actions"]:
                if not resolved(command.get(field)):
                    self.error(
                        "TDD_COMMAND_UNRESOLVED",
                        f"command {command_id} requires resolved {field}",
                        policy_relpath,
                    )
            if command.get("live_external_actions") not in {
                "forbidden", "allowed-with-approval", "not-applicable",
            }:
                self.error(
                    "TDD_COMMAND_EXTERNAL_ACTIONS",
                    f"command {command_id}.live_external_actions is invalid",
                    policy_relpath,
                )

        for exception_id, exception in exception_records.items():
            for field in ["condition", "approval", "alternative_validation"]:
                if not resolved(exception.get(field)):
                    self.error(
                        "TDD_EXCEPTION_UNRESOLVED",
                        f"exception {exception_id} requires resolved {field}",
                        policy_relpath,
                    )
            if exception.get("required_reason") is not True:
                self.error(
                    "TDD_EXCEPTION_REASON",
                    f"exception {exception_id} must require a reason",
                    policy_relpath,
                )

        for index, trigger in enumerate(triggers if isinstance(triggers, list) else []):
            if not isinstance(trigger, dict):
                continue
            for level_id in trigger.get("test_level_ids", []):
                if level_id not in test_levels:
                    self.error(
                        "TDD_TEST_LEVEL_REFERENCE",
                        f"activation_triggers[{index}] references unknown test level {level_id}",
                        policy_relpath,
                    )
            for exception_id in trigger.get("exceptions", []):
                if exception_id not in exception_records:
                    self.error(
                        "TDD_EXCEPTION_REFERENCE",
                        f"activation_triggers[{index}] references unknown exception {exception_id}",
                        policy_relpath,
                    )
        isolation = policy.get("isolation")
        if not isinstance(isolation, dict):
            self.error("TDD_ISOLATION_SHAPE", "isolation must be an object", policy_relpath)
        else:
            for field in ["clock", "randomness", "database", "queue", "filesystem", "network", "secrets"]:
                if not resolved(isolation.get(field)):
                    self.error("TDD_ISOLATION_UNRESOLVED", f"isolation.{field} must be resolved", policy_relpath)

        catalog = self.load_json_object(
            self.target_path(".ai/assistant/operation-catalog.json"), "OPERATION_CATALOG"
        )
        operations = catalog.get("operations") if isinstance(catalog, dict) else None
        by_id = {
            item.get("id"): item
            for item in operations or []
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        configuration = by_id.get("test-first-configuration")
        execution = by_id.get("test-first-change")
        if not isinstance(configuration, dict) or configuration.get("required_module") != "core-profile":
            self.error("TDD_CONFIGURATION_UNROUTED", "test-first configuration must remain available through core-profile", ".ai/assistant/operation-catalog.json")
        if not isinstance(execution, dict) or execution.get("required_module") != "test-first-development":
            self.error("TDD_EXECUTION_UNROUTED", "test-first execution must require the enabled module", ".ai/assistant/operation-catalog.json")

        router = self.load_json_object(
            self.target_path(".ai/assistant/context-router.json"), "ROUTER"
        )
        overlays = router.get("intent_overlays") if isinstance(router, dict) else None
        route = overlays.get("test-first-request") if isinstance(overlays, dict) else None
        if not isinstance(route, dict) or route.get("operation_candidates") != [
            "test-first-configuration", "test-first-change"
        ]:
            self.error("TDD_INTENT_UNROUTED", "test-first intent must route configuration and execution", ".ai/assistant/context-router.json")

        self.info(
            "TDD_EVIDENCE_LIMIT",
            "test-first structural checks do not prove command execution, expected RED causality, assertion semantics, or changed-contract correctness",
        )

    def check_extensions(self, manifest: ManifestData | None) -> None:
        module_relpath = ".ai/assistant/module-profile.md"
        module_path = self.target_path(module_relpath)
        if not module_path.is_file():
            return
        module_match = re.search(
            r"^Module: `extensions`\s*$([\s\S]*?)(?=^Module: `|\Z)",
            self.read_text(module_path),
            flags=re.MULTILINE,
        )
        if module_match is None:
            self.warn(
                "EXTENSION_MODULE_UNDECLARED",
                "module profile does not declare extensions state",
                module_relpath,
            )
            return
        state_match = re.search(
            r"^State:\s*`?([^`\n]+)`?\s*$",
            module_match.group(1),
            flags=re.MULTILINE,
        )
        if state_match is None:
            self.warn(
                "EXTENSION_MODULE_STATE_MISSING",
                "extensions module has no parseable State field",
                module_relpath,
            )
            return
        if state_match.group(1).strip().casefold() not in {"enabled", "required"}:
            return

        required_paths = [
            ".ai/assistant/extensions/README.md",
            ".ai/assistant/extensions/catalog.json",
            ".ai/assistant/extensions/lock.json",
            ".ai/assistant/context/intents/extension-request.json",
            ".ai/assistant/flows/extension-lifecycle.flow.md",
            ".ai/assistant/gates/extensions.md",
            ".ai/assistant/templates/extension-review.md",
            ".ai/assistant/templates/extension-lifecycle-record.md",
            ".ai/framework/extensions.md",
        ]
        missing = False
        for relpath in required_paths:
            if not self.target_path(relpath).is_file():
                missing = True
                self.error(
                    "EXTENSION_REQUIRED_FILE_MISSING",
                    "enabled extensions module is missing a contract",
                    relpath,
                )
        if missing:
            return

        if manifest is not None:
            expected_manifest = {
                ("extensions", "index"): required_paths[0],
                ("extensions", "catalog"): required_paths[1],
                ("extensions", "lock"): required_paths[2],
                ("extensions", "intent"): required_paths[3],
                ("extensions", "flow"): required_paths[4],
                ("extensions", "gate"): required_paths[5],
                ("extensions", "review"): required_paths[6],
                ("extensions", "lifecycle_record"): required_paths[7],
                ("operations", "extension_management"): required_paths[4],
                ("operations", "extension_review"): required_paths[6],
                ("operations", "extension_lifecycle_record"): required_paths[7],
            }
            for key, expected in expected_manifest.items():
                scalar = manifest.scalars.get(key)
                if scalar is None or scalar.value != expected:
                    self.error(
                        "EXTENSION_MANIFEST_PATH",
                        f"{dotted(key)} must be {expected} when extensions are enabled",
                        ".ai/alatyr.yaml",
                    )

        catalog_relpath = required_paths[1]
        lock_relpath = required_paths[2]
        catalog = self.load_json_object(
            self.target_path(catalog_relpath), "EXTENSION_CATALOG"
        )
        lock = self.load_json_object(self.target_path(lock_relpath), "EXTENSION_LOCK")
        if catalog is None or lock is None:
            return

        if catalog.get("schema_version") != 1:
            self.error("EXTENSION_CATALOG_SCHEMA", "schema_version should be 1", catalog_relpath)
        if catalog.get("catalog_kind") != "target-alatyr-extension-catalog":
            self.error("EXTENSION_CATALOG_KIND", "catalog_kind is invalid", catalog_relpath)
        if catalog.get("extension_api") != 1:
            self.error("EXTENSION_CATALOG_API", "extension_api should be 1", catalog_relpath)
        if lock.get("schema_version") != 1:
            self.error("EXTENSION_LOCK_SCHEMA", "schema_version should be 1", lock_relpath)
        if lock.get("lock_kind") != "target-alatyr-extension-lock":
            self.error("EXTENSION_LOCK_KIND", "lock_kind is invalid", lock_relpath)
        if lock.get("extension_api") != 1:
            self.error("EXTENSION_LOCK_API", "extension_api should be 1", lock_relpath)

        for field in ["owner", "last_reviewed"]:
            value = catalog.get(field)
            if not isinstance(value, str) or is_placeholder(value) or is_unresolved_value(value):
                self.error("EXTENSION_CATALOG_METADATA", f"enabled extension catalog requires resolved {field}", catalog_relpath)

        target_baseline = lock.get("target_baseline")
        if not isinstance(target_baseline, dict):
            self.error("EXTENSION_TARGET_BASELINE", "target_baseline must be an object", lock_relpath)
            target_baseline = {}
        baseline_framework = target_baseline.get("framework_version")
        baseline_schema = target_baseline.get("adapter_schema_version")
        baseline_template = target_baseline.get("template_version")
        baseline_registry = target_baseline.get("rule_registry")
        if not isinstance(baseline_framework, str) or is_placeholder(baseline_framework) or is_unresolved_value(baseline_framework):
            self.error("EXTENSION_TARGET_BASELINE", "target baseline framework version is unresolved", lock_relpath)
        if not isinstance(baseline_schema, int) or isinstance(baseline_schema, bool) or baseline_schema < 1:
            self.error("EXTENSION_TARGET_BASELINE", "target baseline adapter schema must be a positive integer", lock_relpath)
        if not isinstance(baseline_template, int) or isinstance(baseline_template, bool) or baseline_template < 1:
            self.error("EXTENSION_TARGET_BASELINE", "target baseline template version must be a positive integer", lock_relpath)
        if not isinstance(baseline_registry, str) or not is_target_relative_path(baseline_registry):
            self.error("EXTENSION_TARGET_BASELINE", "target baseline rule registry must be target-relative", lock_relpath)
        elif not self.target_path(baseline_registry).is_file():
            self.error("EXTENSION_TARGET_BASELINE", "target baseline rule registry is missing", baseline_registry)
        if manifest is not None:
            expected_baseline = {
                "framework_version": manifest.scalars.get(("framework", "version")),
                "adapter_schema_version": manifest.scalars.get(("schema_version",)),
                "template_version": manifest.scalars.get(("framework", "template_version")),
                "rule_registry": manifest.scalars.get(("framework", "rule_registry")),
            }
            actual_baseline = {
                "framework_version": str(baseline_framework),
                "adapter_schema_version": str(baseline_schema),
                "template_version": str(baseline_template),
                "rule_registry": str(baseline_registry),
            }
            for field, scalar in expected_baseline.items():
                if scalar is None or scalar.value != actual_baseline[field]:
                    self.error("EXTENSION_TARGET_BASELINE_DRIFT", f"target baseline {field} differs from the adapter manifest", lock_relpath)

        catalog_entries = catalog.get("extensions")
        lock_entries = lock.get("extensions")
        if not isinstance(catalog_entries, list):
            self.error("EXTENSION_CATALOG_ENTRIES", "extensions must be a list", catalog_relpath)
            catalog_entries = []
        if not isinstance(lock_entries, list):
            self.error("EXTENSION_LOCK_ENTRIES", "extensions must be a list", lock_relpath)
            lock_entries = []

        extension_id_re = re.compile(r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
        digest_re = re.compile(r"^[0-9a-f]{64}$")

        def resolved(value: Any) -> bool:
            return (
                isinstance(value, str)
                and bool(value.strip())
                and not is_placeholder(value)
                and not is_unresolved_value(value)
            )

        catalog_by_id: dict[str, dict[str, Any]] = {}
        valid_catalog_states = {
            "available", "reviewed", "planned", "active", "blocked",
            "disabled", "deprecated", "removed",
        }
        for index, entry in enumerate(catalog_entries):
            if not isinstance(entry, dict):
                self.error("EXTENSION_CATALOG_ENTRY", f"extensions[{index}] must be an object", catalog_relpath)
                continue
            extension_id = entry.get("id")
            if not isinstance(extension_id, str) or not extension_id_re.fullmatch(extension_id):
                self.error("EXTENSION_ID", f"extensions[{index}].id is invalid", catalog_relpath)
                continue
            if extension_id in catalog_by_id:
                self.error("EXTENSION_CATALOG_DUPLICATE", f"duplicate extension id {extension_id}", catalog_relpath)
            catalog_by_id[extension_id] = entry
            if entry.get("state") not in valid_catalog_states:
                self.error("EXTENSION_CATALOG_STATE", f"extension {extension_id} has invalid state", catalog_relpath)
            for field in ["version", "owner", "lock_id", "manifest", "bindings", "last_reviewed", "evidence_revision"]:
                if not resolved(entry.get(field)):
                    self.error("EXTENSION_CATALOG_UNRESOLVED", f"extension {extension_id} requires resolved {field}", catalog_relpath)
            for field in ["item_ids", "supported_assistants", "known_gaps"]:
                values = entry.get(field)
                if not isinstance(values, list) or not all(resolved(value) for value in values):
                    self.error("EXTENSION_CATALOG_LIST", f"extension {extension_id}.{field} must contain resolved strings", catalog_relpath)

        lock_by_id: dict[str, dict[str, Any]] = {}
        for index, entry in enumerate(lock_entries):
            if not isinstance(entry, dict):
                self.error("EXTENSION_LOCK_ENTRY", f"extensions[{index}] must be an object", lock_relpath)
                continue
            extension_id = entry.get("id")
            if not isinstance(extension_id, str) or not extension_id_re.fullmatch(extension_id):
                self.error("EXTENSION_ID", f"extensions[{index}].id is invalid", lock_relpath)
                continue
            if extension_id in lock_by_id:
                self.error("EXTENSION_LOCK_DUPLICATE", f"duplicate extension id {extension_id}", lock_relpath)
            lock_by_id[extension_id] = entry
            for field in [
                "lock_id", "version", "state", "source_type", "source",
                "source_revision", "license_status", "manifest", "bindings",
                "adaptation_record", "approval_record", "installed_at",
            ]:
                if not resolved(entry.get(field)):
                    self.error("EXTENSION_LOCK_UNRESOLVED", f"extension {extension_id} requires resolved {field}", lock_relpath)
            if entry.get("state") not in {"active", "disabled", "deprecated"}:
                self.error("EXTENSION_LOCK_STATE", f"extension {extension_id} lock state is invalid", lock_relpath)
            if entry.get("source_type") not in {"local-path", "git-url", "https-url", "package", "plugin", "assistant-native", "pasted"}:
                self.error("EXTENSION_SOURCE_TYPE", f"extension {extension_id} source_type is invalid", lock_relpath)
            digest = entry.get("package_digest_sha256")
            if not isinstance(digest, str) or not digest_re.fullmatch(digest):
                self.error("EXTENSION_PACKAGE_DIGEST", f"extension {extension_id} package digest must be lowercase SHA-256", lock_relpath)
            compatibility = entry.get("compatibility")
            if not isinstance(compatibility, dict) or compatibility.get("result") != "compatible":
                self.error("EXTENSION_COMPATIBILITY", f"extension {extension_id} compatibility must be compatible", lock_relpath)
            validation = entry.get("validation")
            if not isinstance(validation, list) or not validation:
                self.error("EXTENSION_VALIDATION", f"extension {extension_id} requires validation evidence", lock_relpath)

            namespace = f".ai/assistant/extensions/{extension_id}/"
            for field in ["manifest", "bindings", "adaptation_record"]:
                value = entry.get(field)
                if not isinstance(value, str) or not value.startswith(namespace):
                    self.error("EXTENSION_NAMESPACE", f"extension {extension_id}.{field} must remain under {namespace}", lock_relpath)
                elif not self.target_path(value).is_file():
                    self.error("EXTENSION_LOCK_PATH_MISSING", f"extension {extension_id}.{field} is missing", value)

            approval_record = entry.get("approval_record")
            if isinstance(approval_record, str):
                if not is_target_relative_path(approval_record):
                    self.error("EXTENSION_APPROVAL_PATH", f"extension {extension_id} approval record must be target-relative", lock_relpath)
                elif not self.target_path(approval_record).is_file():
                    self.error("EXTENSION_APPROVAL_MISSING", f"extension {extension_id} approval record is missing", approval_record)

            installed_files = entry.get("installed_files")
            if not isinstance(installed_files, list) or not installed_files:
                self.error("EXTENSION_INSTALLED_FILES", f"extension {extension_id} requires installed_files", lock_relpath)
                installed_files = []
            seen_paths: set[str] = set()
            for file_index, record in enumerate(installed_files):
                if not isinstance(record, dict):
                    self.error("EXTENSION_FILE_RECORD", f"extension {extension_id} installed_files[{file_index}] must be an object", lock_relpath)
                    continue
                relpath = record.get("path")
                if not isinstance(relpath, str) or not is_target_relative_path(relpath) or not relpath.startswith(namespace):
                    self.error("EXTENSION_FILE_PATH", f"extension {extension_id} has unsafe or out-of-namespace installed path", lock_relpath)
                    continue
                if relpath in seen_paths:
                    self.error("EXTENSION_FILE_DUPLICATE", f"extension {extension_id} repeats installed path {relpath}", lock_relpath)
                seen_paths.add(relpath)
                if record.get("owner") != extension_id:
                    self.error("EXTENSION_FILE_OWNER", f"extension {extension_id} does not own {relpath} exactly", lock_relpath)
                expected_hash = record.get("sha256")
                if not isinstance(expected_hash, str) or not digest_re.fullmatch(expected_hash):
                    self.error("EXTENSION_FILE_HASH", f"extension {extension_id} has invalid hash for {relpath}", lock_relpath)
                    continue
                path = self.target_path(relpath)
                if path.is_symlink():
                    self.error("EXTENSION_FILE_SYMLINK", "installed extension files must not be symlinks", relpath)
                elif not path.is_file():
                    self.error("EXTENSION_FILE_MISSING", "locked installed extension file is missing", relpath)
                elif hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
                    self.error("EXTENSION_FILE_DRIFT", "installed extension file differs from its lock hash", relpath)

            required_binding_ids: set[str] = set()
            normalized_manifest = self.load_json_object(
                self.target_path(str(entry.get("manifest", ""))),
                "EXTENSION_INSTALLED_MANIFEST",
            )
            if normalized_manifest is not None:
                if normalized_manifest.get("package_kind") != "alatyr-extension":
                    self.error("EXTENSION_INSTALLED_MANIFEST_KIND", f"extension {extension_id} normalized manifest kind is invalid", str(entry.get("manifest")))
                if normalized_manifest.get("id") != extension_id or normalized_manifest.get("version") != entry.get("version"):
                    self.error("EXTENSION_INSTALLED_MANIFEST_IDENTITY", f"extension {extension_id} normalized manifest identity differs from the lock", str(entry.get("manifest")))
                provides = normalized_manifest.get("provides")
                provided_ids: list[str] = []
                provided_paths: set[str] = set()
                if not isinstance(provides, list) or not provides:
                    self.error("EXTENSION_INSTALLED_ITEMS", f"extension {extension_id} normalized manifest requires provided items", str(entry.get("manifest")))
                    provides = []
                for item_index, item in enumerate(provides):
                    if not isinstance(item, dict):
                        self.error("EXTENSION_INSTALLED_ITEM", f"extension {extension_id} provides[{item_index}] must be an object", str(entry.get("manifest")))
                        continue
                    item_id = item.get("id")
                    item_relpath = item.get("path")
                    if not resolved(item_id) or item_id in provided_ids:
                        self.error("EXTENSION_INSTALLED_ITEM_ID", f"extension {extension_id} has unresolved or duplicate provided item ID", str(entry.get("manifest")))
                    if isinstance(item_id, str):
                        provided_ids.append(item_id)
                    if (
                        not isinstance(item_relpath, str)
                        or not item_relpath.startswith("items/")
                        or ".." in item_relpath.split("/")
                        or "\\" in item_relpath
                    ):
                        self.error("EXTENSION_INSTALLED_ITEM_PATH", f"extension {extension_id} has unsafe provided item path", str(entry.get("manifest")))
                    elif item_relpath in provided_paths:
                        self.error("EXTENSION_INSTALLED_ITEM_PATH", f"extension {extension_id} repeats provided item path {item_relpath}", str(entry.get("manifest")))
                    else:
                        provided_paths.add(item_relpath)
                        installed_item_path = namespace + item_relpath
                        if installed_item_path not in seen_paths:
                            self.error("EXTENSION_ITEM_UNLOCKED", f"extension {extension_id} item {installed_item_path} is not covered by installed_files", str(entry.get("manifest")))
                catalog_item_ids = catalog_by_id.get(extension_id, {}).get("item_ids")
                if isinstance(catalog_item_ids, list) and sorted(catalog_item_ids) != sorted(provided_ids):
                    self.error("EXTENSION_ITEM_INDEX_DRIFT", f"extension {extension_id} catalog item IDs differ from the normalized manifest", catalog_relpath)
                if normalized_manifest.get("extension_dependencies") not in (None, []):
                    self.error("EXTENSION_INSTALLED_DEPENDENCIES", f"extension {extension_id} normalized manifest must not contain extension dependencies", str(entry.get("manifest")))
                lifecycle = normalized_manifest.get("lifecycle")
                if isinstance(lifecycle, dict) and lifecycle.get("arbitrary_hooks") is not False:
                    self.error("EXTENSION_INSTALLED_HOOK", f"extension {extension_id} normalized manifest must prohibit arbitrary hooks", str(entry.get("manifest")))
                project_bindings = normalized_manifest.get("project_bindings")
                if isinstance(project_bindings, list):
                    required_binding_ids = {
                        binding.get("id")
                        for binding in project_bindings
                        if isinstance(binding, dict)
                        and binding.get("required") is True
                        and isinstance(binding.get("id"), str)
                    }

            bindings = self.load_json_object(
                self.target_path(str(entry.get("bindings", ""))),
                "EXTENSION_BINDINGS",
            )
            if bindings is not None:
                if bindings.get("schema_version") != 1 or bindings.get("binding_kind") != "target-alatyr-extension-bindings":
                    self.error("EXTENSION_BINDING_CONTRACT", f"extension {extension_id} bindings contract is invalid", str(entry.get("bindings")))
                if bindings.get("extension_id") != extension_id:
                    self.error("EXTENSION_BINDING_IDENTITY", f"extension {extension_id} bindings identity differs from the lock", str(entry.get("bindings")))
                binding_entries = bindings.get("bindings")
                if not isinstance(binding_entries, list):
                    self.error("EXTENSION_BINDING_ENTRIES", f"extension {extension_id} bindings must be a list", str(entry.get("bindings")))
                else:
                    seen_bindings: set[str] = set()
                    for binding_index, binding in enumerate(binding_entries):
                        if not isinstance(binding, dict):
                            self.error("EXTENSION_BINDING_ENTRY", f"extension {extension_id} bindings[{binding_index}] must be an object", str(entry.get("bindings")))
                            continue
                        binding_id = binding.get("id")
                        if not resolved(binding_id) or binding_id in seen_bindings:
                            self.error("EXTENSION_BINDING_ID", f"extension {extension_id} has unresolved or duplicate binding ID", str(entry.get("bindings")))
                        if isinstance(binding_id, str):
                            seen_bindings.add(binding_id)
                        for field in ["value", "owner", "source"]:
                            if not resolved(binding.get(field)):
                                self.error("EXTENSION_BINDING_UNRESOLVED", f"extension {extension_id} binding {binding_id} requires resolved {field}", str(entry.get("bindings")))
                    missing_bindings = sorted(required_binding_ids - seen_bindings)
                    if missing_bindings:
                        self.error("EXTENSION_REQUIRED_BINDING_MISSING", f"extension {extension_id} is missing required bindings: {', '.join(missing_bindings)}", str(entry.get("bindings")))

            integration_surfaces = entry.get("integration_surfaces")
            if not isinstance(integration_surfaces, list) or not all(
                isinstance(value, str) and is_target_relative_path(value)
                for value in integration_surfaces
            ):
                self.error("EXTENSION_INTEGRATION_SURFACES", f"extension {extension_id} integration_surfaces must be target-relative paths", lock_relpath)

        for extension_id, entry in catalog_by_id.items():
            if entry.get("state") in {"active", "disabled", "deprecated"}:
                locked = lock_by_id.get(extension_id)
                if locked is None:
                    self.error("EXTENSION_LOCK_MISSING", f"catalog extension {extension_id} has no lock entry", lock_relpath)
                    continue
                for field in ["version", "state", "lock_id", "manifest", "bindings"]:
                    if entry.get(field) != locked.get(field):
                        self.error("EXTENSION_CATALOG_LOCK_DRIFT", f"extension {extension_id}.{field} differs between catalog and lock", catalog_relpath)
        for extension_id in sorted(set(lock_by_id) - set(catalog_by_id)):
            self.error("EXTENSION_CATALOG_MISSING", f"lock extension {extension_id} has no catalog entry", catalog_relpath)

        catalog = self.load_json_object(
            self.target_path(".ai/assistant/operation-catalog.json"),
            "OPERATION_CATALOG",
        )
        operations = catalog.get("operations") if isinstance(catalog, dict) else None
        operation = next(
            (
                item for item in operations or []
                if isinstance(item, dict) and item.get("id") == "extension-management"
            ),
            None,
        )
        if not isinstance(operation, dict) or operation.get("required_module") != "core-profile":
            self.error("EXTENSION_OPERATION_UNROUTED", "extension-management must remain available through core-profile", ".ai/assistant/operation-catalog.json")

        self.info(
            "EXTENSION_EVIDENCE_LIMIT",
            "extension structural checks do not prove source trust, license interpretation, semantic quality, target suitability, or safe runtime behavior",
        )

    def check_dependency_knowledge(self, manifest: ManifestData | None) -> None:
        required_paths = [
            ".ai/framework/dependency-knowledge.md",
            ".ai/project/dependencies/README.md",
            ".ai/project/dependencies/policy.json",
            ".ai/project/dependencies/catalog.json",
            ".ai/project/dependencies/knowledge-lock.json",
            ".ai/project/dependencies/deviations.json",
            ".ai/project/dependencies/snapshots/README.md",
            ".ai/assistant/context/intents/dependency-knowledge-request.json",
            ".ai/assistant/flows/dependency-knowledge-sync.flow.md",
            ".ai/assistant/gates/dependency-knowledge.md",
            ".ai/assistant/templates/dependency-knowledge-sync-report.md",
        ]
        missing = False
        for relpath in required_paths:
            if not self.target_path(relpath).is_file():
                missing = True
                self.error(
                    "DEPENDENCY_KNOWLEDGE_REQUIRED_FILE_MISSING",
                    "enabled dependency-knowledge module is missing a contract",
                    relpath,
                )
        if missing:
            return

        expected_manifest = {
            ("dependency_knowledge", "index"): required_paths[1],
            ("dependency_knowledge", "policy"): required_paths[2],
            ("dependency_knowledge", "catalog"): required_paths[3],
            ("dependency_knowledge", "lock"): required_paths[4],
            ("dependency_knowledge", "deviations"): required_paths[5],
            ("dependency_knowledge", "snapshots"): ".ai/project/dependencies/snapshots",
            ("dependency_knowledge", "intent"): required_paths[7],
            ("dependency_knowledge", "flow"): required_paths[8],
            ("dependency_knowledge", "gate"): required_paths[9],
            ("dependency_knowledge", "report"): required_paths[10],
            ("operations", "dependency_knowledge"): required_paths[8],
            ("operations", "dependency_knowledge_report"): required_paths[10],
        }
        if manifest is not None:
            for key, expected in expected_manifest.items():
                scalar = manifest.scalars.get(key)
                if scalar is None or scalar.value != expected:
                    self.error(
                        "DEPENDENCY_KNOWLEDGE_MANIFEST_PATH",
                        f"{dotted(key)} must be {expected} when dependency knowledge is enabled",
                        ".ai/alatyr.yaml",
                    )

        policy_relpath = required_paths[2]
        catalog_relpath = required_paths[3]
        lock_relpath = required_paths[4]
        deviation_relpath = required_paths[5]
        policy = self.load_json_object(self.target_path(policy_relpath), "DEPENDENCY_KNOWLEDGE_POLICY")
        catalog = self.load_json_object(self.target_path(catalog_relpath), "DEPENDENCY_KNOWLEDGE_CATALOG")
        lock = self.load_json_object(self.target_path(lock_relpath), "DEPENDENCY_KNOWLEDGE_LOCK")
        deviations = self.load_json_object(self.target_path(deviation_relpath), "DEPENDENCY_KNOWLEDGE_DEVIATIONS")
        if any(value is None for value in [policy, catalog, lock, deviations]):
            return

        def resolved(value: Any) -> bool:
            return (
                isinstance(value, str)
                and bool(value.strip())
                and not is_placeholder(value)
                and not is_unresolved_value(value)
            )

        if policy.get("schema_version") != 1 or policy.get("policy_kind") != "target-dependency-knowledge-policy":
            self.error("DEPENDENCY_KNOWLEDGE_POLICY_SCHEMA", "policy schema or kind is invalid", policy_relpath)
        if policy.get("state") not in {"enabled", "required"}:
            self.error("DEPENDENCY_KNOWLEDGE_POLICY_STATE", "enabled module requires enabled or required policy state", policy_relpath)
        if not resolved(policy.get("owner")):
            self.error("DEPENDENCY_KNOWLEDGE_POLICY_OWNER", "enabled policy requires a resolved owner", policy_relpath)
        sources = policy.get("package_sources")
        if not isinstance(sources, list) or not sources:
            self.error("DEPENDENCY_KNOWLEDGE_SOURCES", "enabled policy requires package_sources", policy_relpath)
        else:
            for index, source in enumerate(sources):
                if not isinstance(source, dict):
                    self.error("DEPENDENCY_KNOWLEDGE_SOURCE", f"package_sources[{index}] must be an object", policy_relpath)
                    continue
                for field in ["ecosystem", "manifest", "lockfile", "metadata_locator"]:
                    if not resolved(source.get(field)):
                        self.error("DEPENDENCY_KNOWLEDGE_SOURCE", f"package_sources[{index}].{field} must be resolved", policy_relpath)
                if source.get("metadata_locator_kind") != "native-package-metadata-key":
                    self.error(
                        "DEPENDENCY_KNOWLEDGE_SOURCE_LOCATOR",
                        f"package_sources[{index}].metadata_locator_kind must be native-package-metadata-key",
                        policy_relpath,
                    )
                for field in ["manifest", "lockfile"]:
                    value = source.get(field)
                    if resolved(value) and not is_target_relative_path(value):
                        self.error("DEPENDENCY_KNOWLEDGE_SOURCE_PATH", f"package_sources[{index}].{field} must be target-relative", policy_relpath)
                    elif resolved(value) and not self.target_path(value).is_file():
                        self.error("DEPENDENCY_KNOWLEDGE_SOURCE_MISSING", f"package_sources[{index}].{field} does not exist", policy_relpath)
        discovery = policy.get("discovery")
        expected_discovery = {
            "native_metadata_only": True,
            "recursive_scan": False,
            "execute_package_manager": False,
            "execute_package_hooks": False,
        }
        if not isinstance(discovery, dict) or any(discovery.get(key) is not value for key, value in expected_discovery.items()):
            self.error("DEPENDENCY_KNOWLEDGE_DISCOVERY", "discovery must be native-metadata-only and non-executing", policy_relpath)
        trust = policy.get("trust")
        if not isinstance(trust, dict) or trust.get("raw_content_is_instruction") is not False or trust.get("require_artifact_binding") is not True or trust.get("require_digest") is not True:
            self.error("DEPENDENCY_KNOWLEDGE_TRUST", "trust policy must keep raw content as data and require artifact binding and digest", policy_relpath)
        limits = policy.get("limits")
        if not isinstance(limits, dict):
            self.error("DEPENDENCY_KNOWLEDGE_LIMITS", "limits must be an object", policy_relpath)
        else:
            for field in ["max_manifest_bytes", "max_export_bytes", "max_exports_per_package", "max_graph_depth", "max_graph_instances"]:
                value = limits.get(field)
                if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                    self.error("DEPENDENCY_KNOWLEDGE_LIMIT", f"limits.{field} must be a positive integer", policy_relpath)
        routing = policy.get("routing")
        if not isinstance(routing, dict) or routing.get("routine_bootstrap") is not False or routing.get("load_selected_facts_only") is not True:
            self.error("DEPENDENCY_KNOWLEDGE_ROUTING", "routing must stay outside bootstrap and load selected facts only", policy_relpath)

        if catalog.get("schema_version") != 1 or catalog.get("catalog_kind") != "target-dependency-knowledge-catalog":
            self.error("DEPENDENCY_KNOWLEDGE_CATALOG_SCHEMA", "catalog schema or kind is invalid", catalog_relpath)
        if lock.get("schema_version") != 1 or lock.get("lock_kind") != "target-dependency-knowledge-lock" or lock.get("knowledge_api") != 1:
            self.error("DEPENDENCY_KNOWLEDGE_LOCK_SCHEMA", "knowledge lock schema kind or API is invalid", lock_relpath)
        if deviations.get("schema_version") != 1 or deviations.get("deviation_kind") != "target-dependency-knowledge-deviations":
            self.error("DEPENDENCY_KNOWLEDGE_DEVIATION_SCHEMA", "deviation schema or kind is invalid", deviation_relpath)
        for value, source, field in [
            (catalog.get("owner"), catalog_relpath, "owner"),
            (deviations.get("owner"), deviation_relpath, "owner"),
            (catalog.get("package_lock_fingerprint"), catalog_relpath, "package_lock_fingerprint"),
            (lock.get("package_lock_fingerprint"), lock_relpath, "package_lock_fingerprint"),
        ]:
            if not resolved(value):
                self.error("DEPENDENCY_KNOWLEDGE_METADATA", f"{field} must be resolved", source)
        if catalog.get("package_lock_fingerprint") != lock.get("package_lock_fingerprint"):
            self.error("DEPENDENCY_KNOWLEDGE_FINGERPRINT_DRIFT", "catalog and knowledge lock fingerprints differ", catalog_relpath)
        packages = catalog.get("packages")
        instances = lock.get("instances")
        deviation_entries = deviations.get("deviations")
        catalog_instance_ids: set[str] = set()
        lock_instance_ids: set[str] = set()
        catalog_exports: dict[str, set[str]] = {}
        lock_exports: dict[str, set[str]] = {}
        digest_pattern = re.compile(r"^[0-9a-f]{64}$")

        def dependency_digest(value: Any) -> bool:
            return isinstance(value, str) and digest_pattern.fullmatch(value) is not None

        def dependency_list(value: Any) -> bool:
            return (
                isinstance(value, list)
                and bool(value)
                and all(resolved(item) for item in value)
            )

        def package_relative(value: Any) -> bool:
            if not resolved(value):
                return False
            if "\\" in value:
                return False
            path = Path(value)
            return not path.is_absolute() and ".." not in path.parts

        if not isinstance(packages, list):
            self.error("DEPENDENCY_KNOWLEDGE_PACKAGES", "catalog packages must be a list", catalog_relpath)
        else:
            for index, package in enumerate(packages):
                location = f"{catalog_relpath}:packages[{index}]"
                if not isinstance(package, dict):
                    self.error("DEPENDENCY_KNOWLEDGE_PACKAGE_RECORD", "catalog package must be an object", location)
                    continue
                for field in ["instance_id", "ecosystem", "name", "version"]:
                    if not resolved(package.get(field)):
                        self.error("DEPENDENCY_KNOWLEDGE_PACKAGE_RECORD", f"catalog package {field} must be resolved", location)
                instance_id = package.get("instance_id")
                if resolved(instance_id):
                    if instance_id in catalog_instance_ids:
                        self.error("DEPENDENCY_KNOWLEDGE_INSTANCE_DUPLICATE", f"duplicate catalog instance_id {instance_id}", location)
                    catalog_instance_ids.add(instance_id)
                if package.get("export_status") not in {"available", "unsupported", "blocked", "missing"}:
                    self.error("DEPENDENCY_KNOWLEDGE_EXPORT_STATUS", "export_status must be available, unsupported, blocked, or missing", location)
                if package.get("trust") not in {"unreviewed", "reviewed", "blocked"}:
                    self.error("DEPENDENCY_KNOWLEDGE_TRUST_STATE", "trust must be unreviewed, reviewed, or blocked", location)
                if package.get("freshness") not in {"current", "stale", "missing", "modified"}:
                    self.error("DEPENDENCY_KNOWLEDGE_FRESHNESS", "freshness must be current, stale, missing, or modified", location)
                export_records = package.get("exports")
                package_export_ids: set[str] = set()
                if not isinstance(export_records, list):
                    self.error("DEPENDENCY_KNOWLEDGE_EXPORT_RECORD", "catalog package exports must be a list", location)
                else:
                    for export_index, export in enumerate(export_records):
                        export_location = f"{location}.exports[{export_index}]"
                        if not isinstance(export, dict):
                            self.error("DEPENDENCY_KNOWLEDGE_EXPORT_RECORD", "catalog export must be an object", export_location)
                            continue
                        for field in ["id", "type", "summary"]:
                            if not resolved(export.get(field)):
                                self.error("DEPENDENCY_KNOWLEDGE_EXPORT_RECORD", f"catalog export {field} must be resolved", export_location)
                        export_id = export.get("id")
                        if resolved(export_id):
                            if export_id in package_export_ids:
                                self.error("DEPENDENCY_KNOWLEDGE_EXPORT_DUPLICATE", f"duplicate export ID {export_id} for {instance_id}", export_location)
                            package_export_ids.add(export_id)
                        if not dependency_digest(export.get("content_digest")):
                            self.error("DEPENDENCY_KNOWLEDGE_EXPORT_DIGEST", "catalog export content_digest must be lowercase SHA-256", export_location)
                        if export.get("authority") not in {"upstream-canonical", "upstream-derived", "observed", "third-party", "target-deviation"}:
                            self.error("DEPENDENCY_KNOWLEDGE_AUTHORITY", "catalog export authority is invalid", export_location)
                        if export.get("stability") not in {"stable", "experimental", "deprecated", "internal", "unknown"}:
                            self.error("DEPENDENCY_KNOWLEDGE_STABILITY", "catalog export stability is invalid", export_location)
                        applicability = export.get("applicability")
                        if not isinstance(applicability, dict) or applicability.get("state") not in {"active", "inactive", "conditional", "contradicted"} or not isinstance(applicability.get("conditions"), list) or not all(isinstance(item, str) for item in applicability.get("conditions", [])):
                            self.error("DEPENDENCY_KNOWLEDGE_APPLICABILITY", "catalog export applicability requires a valid independent state and string conditions", export_location)
                        if not dependency_list(export.get("evidence")):
                            self.error("DEPENDENCY_KNOWLEDGE_EXPORT_EVIDENCE", "catalog export evidence must be a non-empty resolved string list", export_location)
                if resolved(instance_id):
                    catalog_exports[instance_id] = package_export_ids
        if not isinstance(instances, list):
            self.error("DEPENDENCY_KNOWLEDGE_INSTANCES", "knowledge lock instances must be a list", lock_relpath)
        else:
            for index, instance in enumerate(instances):
                location = f"{lock_relpath}:instances[{index}]"
                if not isinstance(instance, dict):
                    self.error("DEPENDENCY_KNOWLEDGE_INSTANCE_RECORD", "knowledge-lock instance must be an object", location)
                    continue
                for field in ["instance_id", "ecosystem", "name", "version", "source", "integrity", "revision"]:
                    if not resolved(instance.get(field)):
                        self.error("DEPENDENCY_KNOWLEDGE_INSTANCE_RECORD", f"knowledge-lock instance {field} must be resolved", location)
                instance_id = instance.get("instance_id")
                if resolved(instance_id):
                    if instance_id in lock_instance_ids:
                        self.error("DEPENDENCY_KNOWLEDGE_INSTANCE_DUPLICATE", f"duplicate knowledge-lock instance_id {instance_id}", location)
                    lock_instance_ids.add(instance_id)
                modifications = instance.get("modifications")
                valid_modifications = {"replacement", "fork", "alias", "patch", "path", "workspace", "modified-tree"}
                if not isinstance(modifications, list) or any(item not in valid_modifications for item in modifications):
                    self.error("DEPENDENCY_KNOWLEDGE_MODIFICATIONS", "modifications must contain only supported artifact modification classes", location)
                manifest_record = instance.get("manifest")
                if manifest_record is not None and (
                    not isinstance(manifest_record, dict)
                    or not package_relative(manifest_record.get("path"))
                    or not dependency_digest(manifest_record.get("content_digest"))
                ):
                    self.error("DEPENDENCY_KNOWLEDGE_MANIFEST_RECORD", "manifest requires a contained package-relative path and lowercase SHA-256 digest", location)
                export_records = instance.get("exports")
                instance_export_ids: set[str] = set()
                if not isinstance(export_records, list):
                    self.error("DEPENDENCY_KNOWLEDGE_LOCK_EXPORT", "knowledge-lock exports must be a list", location)
                else:
                    for export_index, export in enumerate(export_records):
                        export_location = f"{location}.exports[{export_index}]"
                        if not isinstance(export, dict) or not resolved(export.get("id")) or not package_relative(export.get("path")) or not dependency_digest(export.get("content_digest")):
                            self.error("DEPENDENCY_KNOWLEDGE_LOCK_EXPORT", "knowledge-lock export requires ID, contained path, and lowercase SHA-256 digest", export_location)
                            continue
                        export_id = export["id"]
                        if export_id in instance_export_ids:
                            self.error("DEPENDENCY_KNOWLEDGE_EXPORT_DUPLICATE", f"duplicate knowledge-lock export ID {export_id} for {instance_id}", export_location)
                        instance_export_ids.add(export_id)
                if manifest_record is None and instance_export_ids:
                    self.error("DEPENDENCY_KNOWLEDGE_MANIFEST_RECORD", "an instance with exports must record its export manifest path and digest", location)
                if resolved(instance_id):
                    lock_exports[instance_id] = instance_export_ids
                graph = instance.get("graph")
                if not isinstance(graph, dict) or not resolved(graph.get("dependency_set")) or not isinstance(graph.get("direct"), bool) or not isinstance(graph.get("public_instance_ids"), list) or not all(resolved(item) for item in graph.get("public_instance_ids", [])):
                    self.error("DEPENDENCY_KNOWLEDGE_GRAPH_RECORD", "graph requires dependency_set, boolean direct, and resolved public_instance_ids", location)
        if not isinstance(deviation_entries, list):
            self.error("DEPENDENCY_KNOWLEDGE_DEVIATIONS", "deviations must be a list", deviation_relpath)
        else:
            deviation_ids: set[str] = set()
            for index, deviation in enumerate(deviation_entries):
                location = f"{deviation_relpath}:deviations[{index}]"
                if not isinstance(deviation, dict):
                    self.error("DEPENDENCY_KNOWLEDGE_DEVIATION_RECORD", "deviation must be an object", location)
                    continue
                for field in ["id", "instance_id", "owner", "source", "effect", "reviewed_at"]:
                    if not resolved(deviation.get(field)):
                        self.error("DEPENDENCY_KNOWLEDGE_DEVIATION_RECORD", f"deviation {field} must be resolved", location)
                if resolved(deviation.get("source")) and not is_target_relative_path(deviation["source"]):
                    self.error("DEPENDENCY_KNOWLEDGE_DEVIATION_SOURCE", "deviation source must be target-relative", location)
                deviation_id = deviation.get("id")
                if resolved(deviation_id):
                    if deviation_id in deviation_ids:
                        self.error("DEPENDENCY_KNOWLEDGE_DEVIATION_DUPLICATE", f"duplicate deviation ID {deviation_id}", location)
                    deviation_ids.add(deviation_id)
                if deviation.get("type") not in {"restriction", "wrapper", "patch", "configuration", "applicability", "conflict"}:
                    self.error("DEPENDENCY_KNOWLEDGE_DEVIATION_TYPE", "deviation type is invalid", location)
                if deviation.get("state") not in {"active", "inactive", "superseded"}:
                    self.error("DEPENDENCY_KNOWLEDGE_DEVIATION_STATE", "deviation state is invalid", location)
                if not isinstance(deviation.get("export_ids"), list) or not all(resolved(item) for item in deviation.get("export_ids", [])):
                    self.error("DEPENDENCY_KNOWLEDGE_DEVIATION_EXPORTS", "deviation export_ids must be a resolved string list", location)

        for instance_id in sorted(catalog_instance_ids - lock_instance_ids):
            self.error("DEPENDENCY_KNOWLEDGE_LOCK_MISSING", f"catalog instance {instance_id} has no knowledge-lock instance", lock_relpath)
        for instance_id in sorted(lock_instance_ids - catalog_instance_ids):
            self.error("DEPENDENCY_KNOWLEDGE_CATALOG_MISSING", f"knowledge-lock instance {instance_id} has no catalog package", catalog_relpath)
        for instance_id in sorted(catalog_instance_ids & lock_instance_ids):
            if catalog_exports.get(instance_id, set()) != lock_exports.get(instance_id, set()):
                self.error("DEPENDENCY_KNOWLEDGE_EXPORT_SET_DRIFT", f"catalog and knowledge-lock export IDs differ for {instance_id}", catalog_relpath)
        if isinstance(instances, list):
            for index, instance in enumerate(instances):
                if not isinstance(instance, dict) or not isinstance(instance.get("graph"), dict):
                    continue
                references = instance["graph"].get("public_instance_ids")
                if not isinstance(references, list):
                    continue
                for reference in references:
                    if resolved(reference) and reference not in lock_instance_ids:
                        self.error("DEPENDENCY_KNOWLEDGE_GRAPH_REFERENCE", f"knowledge-lock graph references unknown instance {reference}", f"{lock_relpath}:instances[{index}]")
        if isinstance(deviation_entries, list):
            for index, deviation in enumerate(deviation_entries):
                if not isinstance(deviation, dict):
                    continue
                instance_id = deviation.get("instance_id")
                if resolved(instance_id) and instance_id not in lock_instance_ids:
                    self.error("DEPENDENCY_KNOWLEDGE_DEVIATION_INSTANCE", f"deviation references unknown instance {instance_id}", f"{deviation_relpath}:deviations[{index}]")
                    continue
                export_ids = deviation.get("export_ids")
                if not isinstance(export_ids, list):
                    continue
                for export_id in export_ids:
                    if resolved(export_id) and export_id not in catalog_exports.get(instance_id, set()):
                        self.error("DEPENDENCY_KNOWLEDGE_DEVIATION_EXPORT", f"deviation references unknown export {export_id} for {instance_id}", f"{deviation_relpath}:deviations[{index}]")

        operations = self.load_json_object(self.target_path(".ai/assistant/operation-catalog.json"), "OPERATION_CATALOG")
        operation = next((item for item in operations.get("operations", []) if isinstance(item, dict) and item.get("id") == "dependency-knowledge"), None) if isinstance(operations, dict) else None
        if not isinstance(operation, dict) or operation.get("required_module") != "dependency-knowledge":
            self.error("DEPENDENCY_KNOWLEDGE_OPERATION_UNROUTED", "dependency-knowledge operation must require the enabled module", ".ai/assistant/operation-catalog.json")
        router = self.load_json_object(self.target_path(".ai/assistant/context-router.json"), "ROUTER")
        overlays = router.get("intent_overlays") if isinstance(router, dict) else None
        route = overlays.get("dependency-knowledge-request") if isinstance(overlays, dict) else None
        if not isinstance(route, dict) or route.get("operation_candidates") != ["dependency-knowledge"]:
            self.error("DEPENDENCY_KNOWLEDGE_INTENT_UNROUTED", "dependency knowledge intent must route the dependency-knowledge operation", ".ai/assistant/context-router.json")

        self.info(
            "DEPENDENCY_KNOWLEDGE_EVIDENCE_LIMIT",
            "dependency knowledge structural checks do not prove publisher identity, semantic correctness, completeness, current applicability, client instruction precedence, or safe runtime behavior",
        )

    def check_workspace_modes(self, manifest: ManifestData | None) -> None:
        required_paths = [
            ".ai/framework/workspace-modes.md",
            ".ai/project/workspace-modes/README.md",
            ".ai/project/workspace-modes/catalog.json",
            ".ai/project/workspace-modes/root/README.md",
            ".ai/project/workspace-modes/root/context.json",
            ".ai/project/workspace-modes/modes/_template/README.md",
            ".ai/project/workspace-modes/modes/_template/mode.json",
            ".ai/assistant/context/intents/workspace-mode-request.json",
            ".ai/assistant/flows/workspace-mode.flow.md",
            ".ai/assistant/gates/workspace-mode.md",
            ".ai/assistant/templates/workspace-mode-suggestion.md",
            ".ai/assistant/templates/workspace-mode-preflight.md",
        ]
        missing = False
        for relpath in required_paths:
            if not self.target_path(relpath).is_file():
                missing = True
                self.error(
                    "WORKSPACE_MODE_REQUIRED_FILE_MISSING",
                    "enabled workspace-modes module is missing a contract",
                    relpath,
                )
        if missing:
            return

        expected_manifest = {
            ("workspace_modes", "index"): required_paths[1],
            ("workspace_modes", "catalog"): required_paths[2],
            ("workspace_modes", "root_context"): required_paths[4],
            ("workspace_modes", "modes"): ".ai/project/workspace-modes/modes",
            ("workspace_modes", "mode_template"): required_paths[6],
            ("workspace_modes", "intent"): required_paths[7],
            ("workspace_modes", "flow"): required_paths[8],
            ("workspace_modes", "gate"): required_paths[9],
            ("workspace_modes", "suggestion"): required_paths[10],
            ("workspace_modes", "preflight"): required_paths[11],
            ("operations", "workspace_mode"): required_paths[8],
            ("operations", "workspace_mode_preflight"): required_paths[11],
        }
        if manifest is not None:
            for key, expected in expected_manifest.items():
                scalar = manifest.scalars.get(key)
                if scalar is None or scalar.value != expected:
                    self.error(
                        "WORKSPACE_MODE_MANIFEST_PATH",
                        f"{dotted(key)} must be {expected} when workspace modes are enabled",
                        ".ai/alatyr.yaml",
                    )

        catalog_relpath = required_paths[2]
        root_relpath = required_paths[4]
        catalog = self.load_json_object(
            self.target_path(catalog_relpath), "WORKSPACE_MODE_CATALOG"
        )
        root_context = self.load_json_object(
            self.target_path(root_relpath), "WORKSPACE_MODE_ROOT_CONTEXT"
        )
        if catalog is None or root_context is None:
            return

        def resolved(value: Any) -> bool:
            return (
                isinstance(value, str)
                and bool(value.strip())
                and not is_placeholder(value)
                and not is_unresolved_value(value)
            )

        def target_path_list(
            value: Any,
            code: str,
            label: str,
            source: str,
            *,
            non_empty: bool = False,
            require_exists: bool = False,
        ) -> list[str]:
            if not isinstance(value, list) or (non_empty and not value):
                self.error(code, f"{label} must be a {'non-empty ' if non_empty else ''}list", source)
                return []
            result: list[str] = []
            for entry in value:
                if not resolved(entry) or not is_target_relative_path(entry):
                    self.error(code, f"{label} must contain target-relative resolved paths", source)
                    continue
                if require_exists and not self.target_path(entry).exists():
                    self.error(code, f"{label} points to missing target evidence {entry}", source)
                    continue
                result.append(entry)
            return result

        if (
            catalog.get("schema_version") != 1
            or catalog.get("catalog_kind") != "target-workspace-mode-catalog"
        ):
            self.error(
                "WORKSPACE_MODE_CATALOG_SCHEMA",
                "catalog schema or kind is invalid",
                catalog_relpath,
            )
        if catalog.get("state") not in {"enabled", "required"}:
            self.error(
                "WORKSPACE_MODE_CATALOG_STATE",
                "enabled module requires enabled or required catalog state",
                catalog_relpath,
            )
        for field in ["owner", "decision_authority"]:
            if not resolved(catalog.get(field)):
                self.error(
                    "WORKSPACE_MODE_CATALOG_OWNER",
                    f"catalog {field} must be resolved",
                    catalog_relpath,
                )

        workspace = catalog.get("workspace")
        workspace_id: str | None = None
        if not isinstance(workspace, dict):
            self.error(
                "WORKSPACE_MODE_WORKSPACE",
                "catalog workspace must be an object",
                catalog_relpath,
            )
        else:
            workspace_id = workspace.get("id") if resolved(workspace.get("id")) else None
            if workspace_id is None:
                self.error("WORKSPACE_MODE_WORKSPACE", "workspace id must be resolved", catalog_relpath)
            if workspace.get("kind") not in {
                "application",
                "framework",
                "library",
                "skeleton",
                "tool",
                "monorepo",
                "mixed",
            }:
                self.error("WORKSPACE_MODE_WORKSPACE", "workspace kind is invalid", catalog_relpath)
            if workspace.get("root") != "." or workspace.get("adapter_role") != "active":
                self.error(
                    "WORKSPACE_MODE_ACTIVE_ROOT",
                    "catalog workspace must identify the selected root '.' and active adapter",
                    catalog_relpath,
                )
            target_path_list(
                workspace.get("evidence"),
                "WORKSPACE_MODE_WORKSPACE_EVIDENCE",
                "workspace.evidence",
                catalog_relpath,
                non_empty=True,
                require_exists=True,
            )

        selection = catalog.get("selection")
        if not isinstance(selection, dict):
            self.error("WORKSPACE_MODE_SELECTION", "selection must be an object", catalog_relpath)
            selection = {}
        expected_selection = {
            "automatic_selection": "accepted-unambiguous-only",
            "ambiguity_behavior": "ask-user",
            "no_match_behavior": "root-read-only",
            "persistence": "per-task",
            "local_preference_allowed": False,
            "show_preflight_before_changes": True,
        }
        for field, expected in expected_selection.items():
            if selection.get(field) != expected:
                self.error(
                    "WORKSPACE_MODE_SELECTION_POLICY",
                    f"selection.{field} must be {expected!r}",
                    catalog_relpath,
                )
        suggestions = catalog.get("suggestions")
        if not isinstance(suggestions, dict):
            self.error("WORKSPACE_MODE_SUGGESTIONS", "suggestions must be an object", catalog_relpath)
        else:
            for field in ["after_installation", "after_framework_update", "after_workspace_change"]:
                if suggestions.get(field) is not True:
                    self.error("WORKSPACE_MODE_SUGGESTIONS", f"suggestions.{field} must be true", catalog_relpath)
            if suggestions.get("automatic_acceptance") is not False:
                self.error("WORKSPACE_MODE_AUTO_ACCEPT", "mode suggestions must never be accepted automatically", catalog_relpath)
        if catalog.get("root_context") != root_relpath:
            self.error("WORKSPACE_MODE_ROOT_REFERENCE", "catalog root_context path is invalid", catalog_relpath)

        if (
            root_context.get("schema_version") != 1
            or root_context.get("descriptor_kind") != "target-workspace-root-context"
        ):
            self.error("WORKSPACE_MODE_ROOT_SCHEMA", "root context schema or kind is invalid", root_relpath)
        root_state = root_context.get("state")
        if root_state not in {"enabled", "disabled"}:
            self.error("WORKSPACE_MODE_ROOT_STATE", "root context state must be enabled or disabled", root_relpath)
        if not resolved(root_context.get("owner")):
            self.error("WORKSPACE_MODE_ROOT_OWNER", "root context owner must be resolved", root_relpath)
        root_required = target_path_list(
            root_context.get("required_context"),
            "WORKSPACE_MODE_ROOT_CONTEXT",
            "required_context",
            root_relpath,
            require_exists=root_state == "enabled",
        )
        root_conditional = root_context.get("conditional_context")
        if not isinstance(root_conditional, list):
            self.error("WORKSPACE_MODE_ROOT_CONTEXT", "conditional_context must be a list", root_relpath)
        else:
            for index, entry in enumerate(root_conditional):
                if (
                    not isinstance(entry, dict)
                    or not resolved(entry.get("path"))
                    or not is_target_relative_path(entry["path"])
                    or not resolved(entry.get("when"))
                ):
                    self.error(
                        "WORKSPACE_MODE_ROOT_CONTEXT",
                        f"conditional_context[{index}] requires target-relative path and condition",
                        root_relpath,
                    )
                elif root_state == "enabled" and not self.target_path(entry["path"]).exists():
                    self.error(
                        "WORKSPACE_MODE_ROOT_CONTEXT",
                        f"conditional_context[{index}] points to missing target context",
                        root_relpath,
                    )
        if root_state == "disabled" and (root_required or root_conditional):
            self.error(
                "WORKSPACE_MODE_ROOT_DISABLED_CONTENT",
                "disabled root context must not route support paths",
                root_relpath,
            )

        modes = catalog.get("modes")
        if not isinstance(modes, list) or not modes:
            self.error(
                "WORKSPACE_MODE_EMPTY",
                "enabled workspace-modes module requires at least one catalog mode",
                catalog_relpath,
            )
            modes = []
        seen_ids: set[str] = set()
        seen_paths: set[str] = set()
        accepted_ids: set[str] = set()
        mode_kinds = {
            "application-development",
            "framework-development",
            "library-development",
            "skeleton-development",
            "dependency-integration",
            "dependency-contribution",
            "skeleton-migration",
            "workspace-coordination",
            "custom",
        }
        states = {"proposed", "accepted", "disabled", "deprecated", "blocked"}
        relationship_types = {
            "workspace-root",
            "workspace-member",
            "dependency",
            "scaffold-origin",
            "vendored-source",
        }
        adapter_roles = {"active", "passive", "provenance-only"}
        ownership_values = {"target", "upstream", "mixed"}

        for index, entry in enumerate(modes):
            location = f"{catalog_relpath}:modes[{index}]"
            if not isinstance(entry, dict):
                self.error("WORKSPACE_MODE_CATALOG_ENTRY", "mode entry must be an object", location)
                continue
            mode_id = entry.get("id")
            state = entry.get("state")
            mode_kind = entry.get("mode_kind")
            path = entry.get("path")
            if not resolved(mode_id) or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", mode_id) is None:
                self.error("WORKSPACE_MODE_ID", "mode ID must be resolved kebab-case", location)
                continue
            if mode_id in seen_ids:
                self.error("WORKSPACE_MODE_DUPLICATE", f"duplicate mode ID {mode_id}", location)
            seen_ids.add(mode_id)
            if state not in states or mode_kind not in mode_kinds:
                self.error("WORKSPACE_MODE_CATALOG_ENTRY", "mode state or kind is invalid", location)
            for field in ["title", "summary", "evidence_revision"]:
                if not resolved(entry.get(field)):
                    self.error("WORKSPACE_MODE_CATALOG_ENTRY", f"mode {field} must be resolved", location)
            expected_path = f".ai/project/workspace-modes/modes/{mode_id}/mode.json"
            if path != expected_path or path in seen_paths or "_template" in str(path):
                self.error("WORKSPACE_MODE_PATH", f"mode path must be unique and equal {expected_path}", location)
            if isinstance(path, str):
                seen_paths.add(path)
            descriptor = self.load_json_object(self.target_path(expected_path), "WORKSPACE_MODE")
            readme_path = f".ai/project/workspace-modes/modes/{mode_id}/README.md"
            if not self.target_path(readme_path).is_file():
                self.error("WORKSPACE_MODE_README_MISSING", "actual mode directory requires README.md", readme_path)
            if descriptor is None:
                self.error("WORKSPACE_MODE_DESCRIPTOR_MISSING", "catalog mode descriptor is missing", expected_path)
                continue
            if descriptor.get("schema_version") != 1 or descriptor.get("descriptor_kind") != "target-workspace-mode":
                self.error("WORKSPACE_MODE_DESCRIPTOR_SCHEMA", "mode descriptor schema or kind is invalid", expected_path)
            if descriptor.get("id") != mode_id or descriptor.get("state") != state or descriptor.get("mode_kind") != mode_kind:
                self.error("WORKSPACE_MODE_DESCRIPTOR_DRIFT", "catalog and descriptor identity state or kind differ", expected_path)
            if state == "accepted":
                accepted_ids.add(mode_id)
            for field in ["title", "purpose", "owner", "decision_authority", "last_reviewed", "evidence_revision"]:
                if not resolved(descriptor.get(field)):
                    self.error("WORKSPACE_MODE_DESCRIPTOR_FIELD", f"mode {field} must be resolved", expected_path)
            scope = descriptor.get("workspace_scope")
            if not isinstance(scope, dict) or not resolved(scope.get("root")) or not is_target_relative_path(scope["root"]):
                self.error("WORKSPACE_MODE_SCOPE", "workspace_scope requires a target-relative root", expected_path)
            else:
                if state == "accepted" and not self.target_path(scope["root"]).exists():
                    self.error(
                        "WORKSPACE_MODE_SCOPE",
                        f"accepted workspace_scope.root points to missing target scope {scope['root']}",
                        expected_path,
                    )
                target_path_list(scope.get("include"), "WORKSPACE_MODE_SCOPE", "workspace_scope.include", expected_path, non_empty=state == "accepted")
                target_path_list(scope.get("exclude"), "WORKSPACE_MODE_SCOPE", "workspace_scope.exclude", expected_path)
            for field in ["use_when", "do_not_use_when"]:
                value = descriptor.get(field)
                if not isinstance(value, list) or not value or not all(resolved(item) for item in value):
                    self.error("WORKSPACE_MODE_SIGNALS", f"{field} must be a non-empty resolved string list", expected_path)
            relationships = descriptor.get("relationships")
            active_roots = 0
            if not isinstance(relationships, list) or not relationships:
                self.error("WORKSPACE_MODE_RELATIONSHIPS", "relationships must be a non-empty list", expected_path)
            else:
                for relationship_index, relationship in enumerate(relationships):
                    rel_location = f"{expected_path}:relationships[{relationship_index}]"
                    if not isinstance(relationship, dict):
                        self.error("WORKSPACE_MODE_RELATIONSHIP", "relationship must be an object", rel_location)
                        continue
                    if not resolved(relationship.get("subject")):
                        self.error("WORKSPACE_MODE_RELATIONSHIP", "relationship subject must be resolved", rel_location)
                    rel_type = relationship.get("relationship")
                    role = relationship.get("adapter_role")
                    if rel_type not in relationship_types or role not in adapter_roles or relationship.get("ownership") not in ownership_values:
                        self.error("WORKSPACE_MODE_RELATIONSHIP", "relationship type adapter role or ownership is invalid", rel_location)
                    target_path_list(
                        relationship.get("evidence"),
                        "WORKSPACE_MODE_RELATIONSHIP_EVIDENCE",
                        "relationship.evidence",
                        rel_location,
                        non_empty=True,
                        require_exists=True,
                    )
                    if role == "active":
                        if rel_type != "workspace-root":
                            self.error("WORKSPACE_MODE_NESTED_ADAPTER", "only workspace-root may have an active adapter role", rel_location)
                        else:
                            active_roots += 1
                            if workspace_id is not None and relationship.get("subject") != workspace_id:
                                self.error("WORKSPACE_MODE_ACTIVE_ROOT", "active root subject must match catalog workspace ID", rel_location)
                    if rel_type in {"dependency", "scaffold-origin"} and role not in {"passive", "provenance-only"}:
                        self.error("WORKSPACE_MODE_NESTED_ADAPTER", "dependency and scaffold adapters must remain passive or provenance-only", rel_location)
            if state == "accepted" and active_roots != 1:
                self.error("WORKSPACE_MODE_ACTIVE_ROOT", "accepted mode must define exactly one active workspace-root relationship", expected_path)
            context = descriptor.get("context")
            if not isinstance(context, dict) or context.get("root_context") not in {"inherit", "required", "skip"}:
                self.error("WORKSPACE_MODE_CONTEXT", "context requires inherit required or skip root_context", expected_path)
            else:
                if (
                    state == "accepted"
                    and context.get("root_context") == "required"
                    and root_state != "enabled"
                ):
                    self.error(
                        "WORKSPACE_MODE_CONTEXT",
                        "accepted mode cannot require disabled shared root context",
                        expected_path,
                    )
                target_path_list(
                    context.get("required_context"),
                    "WORKSPACE_MODE_CONTEXT",
                    "context.required_context",
                    expected_path,
                    require_exists=state == "accepted",
                )
                conditional = context.get("conditional_context")
                if not isinstance(conditional, list):
                    self.error("WORKSPACE_MODE_CONTEXT", "context.conditional_context must be a list", expected_path)
                else:
                    for conditional_index, conditional_entry in enumerate(conditional):
                        if (
                            not isinstance(conditional_entry, dict)
                            or not resolved(conditional_entry.get("path"))
                            or not is_target_relative_path(conditional_entry["path"])
                            or not resolved(conditional_entry.get("when"))
                        ):
                            self.error("WORKSPACE_MODE_CONTEXT", f"conditional context {conditional_index} is invalid", expected_path)
                        elif state == "accepted" and not self.target_path(
                            conditional_entry["path"]
                        ).exists():
                            self.error(
                                "WORKSPACE_MODE_CONTEXT",
                                f"conditional context {conditional_index} points to missing target context",
                                expected_path,
                            )
            for field in ["source_of_truth_ids", "validation_entry_point_ids", "known_gaps"]:
                value = descriptor.get(field)
                if not isinstance(value, list) or not all(resolved(item) for item in value):
                    self.error("WORKSPACE_MODE_DESCRIPTOR_FIELD", f"{field} must be a resolved string list", expected_path)
            constraints = descriptor.get("constraints")
            if not isinstance(constraints, dict):
                self.error("WORKSPACE_MODE_CONSTRAINTS", "constraints must be an object", expected_path)
            else:
                narrowing = constraints.get("narrows_allowed_actions")
                if not isinstance(narrowing, list) or any(item not in ALLOWED_ACTION_MODES for item in narrowing):
                    self.error("WORKSPACE_MODE_CONSTRAINTS", "narrows_allowed_actions contains an invalid mode", expected_path)
                for field in [
                    "grants_write_scope",
                    "grants_approval",
                    "grants_permissions",
                    "grants_authority",
                    "grants_tools",
                    "activates_nested_adapters",
                    "bypasses_gates",
                ]:
                    if constraints.get(field) is not False:
                        self.error("WORKSPACE_MODE_GRANT", f"constraints.{field} must be false", expected_path)

        default_mode = selection.get("default_mode_id")
        if default_mode is not None and default_mode not in accepted_ids:
            self.error("WORKSPACE_MODE_DEFAULT", "default_mode_id must reference an accepted mode", catalog_relpath)

        operations = self.load_json_object(
            self.target_path(".ai/assistant/operation-catalog.json"), "OPERATION_CATALOG"
        )
        operation = next(
            (
                item
                for item in (operations.get("operations", []) if isinstance(operations, dict) else [])
                if isinstance(item, dict) and item.get("id") == "workspace-mode"
            ),
            None,
        )
        if not isinstance(operation, dict) or operation.get("required_module") != "workspace-modes":
            self.error("WORKSPACE_MODE_OPERATION_UNROUTED", "workspace-mode operation must require the enabled module", ".ai/assistant/operation-catalog.json")
        router = self.load_json_object(self.target_path(".ai/assistant/context-router.json"), "ROUTER")
        overlays = router.get("intent_overlays") if isinstance(router, dict) else None
        route = overlays.get("workspace-mode-request") if isinstance(overlays, dict) else None
        mode_routing = router.get("workspace_mode_routing") if isinstance(router, dict) else None
        if not isinstance(route, dict) or route.get("operation_candidates") != ["workspace-mode"]:
            self.error("WORKSPACE_MODE_INTENT_UNROUTED", "workspace mode intent must route the workspace-mode operation", ".ai/assistant/context-router.json")
        if (
            not isinstance(mode_routing, dict)
            or mode_routing.get("catalog") != catalog_relpath
            or mode_routing.get("root_context") != root_relpath
            or mode_routing.get("ambiguity_behavior") != "ask-user-and-remain-read-only"
        ):
            self.error("WORKSPACE_MODE_ROUTER", "workspace mode routing must bind catalog root context and safe ambiguity behavior", ".ai/assistant/context-router.json")

        self.info(
            "WORKSPACE_MODE_EVIDENCE_LIMIT",
            "workspace-mode structural checks do not prove strategic correctness, complete workspace discovery, ownership truth, semantic consistency, or assistant compliance",
        )

    def check_consistency_map(self) -> None:
        relpath = ".ai/project/consistency-map.json"
        path = self.target_path(relpath)
        data = self.load_json_object(path, "CONSISTENCY_MAP")
        if data is None:
            return
        schema_version = data.get("schema_version")
        if schema_version == 1:
            self.warn(
                "CONSISTENCY_MAP_SCHEMA_LEGACY",
                "schema_version 1 should migrate to schema 2 registry-sync policy",
                relpath,
            )
        elif schema_version != 2:
            self.error(
                "CONSISTENCY_MAP_SCHEMA",
                "schema_version should be 1 or 2",
                relpath,
            )
        if data.get("map_kind") != "target-consistency-map":
            self.error(
                "CONSISTENCY_MAP_KIND",
                "map_kind should be target-consistency-map",
                relpath,
            )
        if data.get("human_registry") != ".ai/project/source-of-truth-registry.md":
            self.error(
                "CONSISTENCY_MAP_REGISTRY",
                "human_registry should point to the target source-of-truth registry",
                relpath,
            )
        if schema_version == 2 and data.get("registry_sync_policy") != CONSISTENCY_REGISTRY_SYNC_POLICY:
            self.error(
                "CONSISTENCY_MAP_REGISTRY_SYNC_POLICY",
                "registry_sync_policy must require exact coverage while allowing extra derived nodes",
                relpath,
            )
        if data.get("levels") != CONSISTENCY_LEVELS:
            self.error(
                "CONSISTENCY_MAP_LEVELS",
                "levels must match the portable consistency level order",
                relpath,
            )
        relationships = data.get("relationship_types")
        if (
            not isinstance(relationships, list)
            or not all(isinstance(value, str) for value in relationships)
            or set(relationships) != CONSISTENCY_RELATIONSHIPS
        ):
            self.error(
                "CONSISTENCY_MAP_RELATIONSHIPS",
                "relationship_types must match the portable relationship set",
                relpath,
            )
        policy = data.get("impact_policy")
        if not isinstance(policy, dict):
            self.error(
                "CONSISTENCY_MAP_IMPACT_POLICY",
                "impact_policy must be an object",
                relpath,
            )
        else:
            for field in ["transitive_expand_when", "required_evidence"]:
                expect_string_list(
                    policy.get(field),
                    self,
                    "CONSISTENCY_MAP_IMPACT_POLICY",
                    relpath,
                    label=f"impact_policy.{field}",
                )

        nodes = data.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            self.error("CONSISTENCY_MAP_NODES", "nodes must be a non-empty list", relpath)
            return
        node_ids: set[str] = set()
        nodes_by_id: dict[str, dict[str, Any]] = {}
        edge_ids: set[str] = set()
        for index, node in enumerate(nodes):
            label = f"nodes[{index}]"
            if not isinstance(node, dict):
                self.error("CONSISTENCY_MAP_NODE_SHAPE", f"{label} must be an object", relpath)
                continue
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id:
                self.error("CONSISTENCY_MAP_NODE_ID", f"{label}.id must be a string", relpath)
            elif not is_placeholder(node_id):
                if node_id in node_ids:
                    self.error(
                        "CONSISTENCY_MAP_NODE_DUPLICATE",
                        f"duplicate node id {node_id}",
                        relpath,
                    )
                node_ids.add(node_id)
                nodes_by_id[node_id] = node
            fact_type = node.get("fact_type")
            if not isinstance(fact_type, str) or not fact_type.strip():
                self.error(
                    "CONSISTENCY_MAP_NODE_FACT_TYPE",
                    f"{label}.fact_type must be a non-empty string",
                    relpath,
                )
            elif is_placeholder(fact_type) and not self.allow_placeholders:
                self.error(
                    "CONSISTENCY_MAP_NODE_FACT_TYPE",
                    f"{label}.fact_type must be resolved in an accepted adapter",
                    relpath,
                )
            level = node.get("level")
            if not is_placeholder(level) and level not in CONSISTENCY_LEVELS:
                self.error(
                    "CONSISTENCY_MAP_NODE_LEVEL",
                    f"{label}.level is invalid: {level}",
                    relpath,
                )
            project_area = node.get("project_area")
            if not isinstance(project_area, str) or not project_area.strip():
                self.error(
                    "CONSISTENCY_MAP_NODE_AREA",
                    f"{label}.project_area must be a non-empty string",
                    relpath,
                )
            elif is_placeholder(project_area) and not self.allow_placeholders:
                self.error(
                    "CONSISTENCY_MAP_NODE_AREA",
                    f"{label}.project_area must be resolved in an accepted adapter",
                    relpath,
                )
            owner = node.get("canonical_owner")
            if (
                isinstance(owner, str)
                and not is_placeholder(owner)
                and not is_unresolved_value(owner)
            ):
                if not is_target_relative_path(owner):
                    self.error(
                        "CONSISTENCY_MAP_OWNER_PATH",
                        f"{label}.canonical_owner must be target-relative",
                        relpath,
                    )
                elif not self.target_path(owner).exists():
                    self.warn(
                        "CONSISTENCY_MAP_OWNER_MISSING",
                        f"{label}.canonical_owner is missing: {owner}",
                        relpath,
                    )
            edges = node.get("relationships")
            if not isinstance(edges, list) or not edges:
                self.error(
                    "CONSISTENCY_MAP_EDGES",
                    f"{label}.relationships must be non-empty",
                    relpath,
                )
                continue
            for edge_index, edge in enumerate(edges):
                edge_label = f"{label}.relationships[{edge_index}]"
                if not isinstance(edge, dict):
                    self.error(
                        "CONSISTENCY_MAP_EDGE_SHAPE",
                        f"{edge_label} must be an object",
                        relpath,
                    )
                    continue
                edge_id = edge.get("id")
                if not isinstance(edge_id, str) or not edge_id:
                    self.error(
                        "CONSISTENCY_MAP_EDGE_ID",
                        f"{edge_label}.id must be a string",
                        relpath,
                    )
                elif not is_placeholder(edge_id):
                    if edge_id in edge_ids:
                        self.error(
                            "CONSISTENCY_MAP_EDGE_DUPLICATE",
                            f"duplicate relationship id {edge_id}",
                            relpath,
                        )
                    edge_ids.add(edge_id)
                edge_type = edge.get("type")
                if not is_placeholder(edge_type) and edge_type not in CONSISTENCY_RELATIONSHIPS:
                    self.error(
                        "CONSISTENCY_MAP_EDGE_TYPE",
                        f"{edge_label}.type is invalid: {edge_type}",
                        relpath,
                    )
                target_level = edge.get("target_level")
                if not is_placeholder(target_level) and target_level not in CONSISTENCY_LEVELS:
                    self.error(
                        "CONSISTENCY_MAP_TARGET_LEVEL",
                        f"{edge_label}.target_level is invalid: {target_level}",
                        relpath,
                    )
                if edge.get("direction") != "outbound":
                    self.error(
                        "CONSISTENCY_MAP_DIRECTION",
                        f"{edge_label}.direction must be outbound",
                        relpath,
                    )
                for field in ["required_when", "validation"]:
                    expect_string_list(
                        edge.get(field),
                        self,
                        "CONSISTENCY_MAP_EDGE_FIELD",
                        relpath,
                        label=f"{edge_label}.{field}",
                    )

        registry_relpath = ".ai/project/source-of-truth-registry.md"
        registry_path = self.target_path(registry_relpath)
        if not registry_path.is_file():
            self.error(
                "CONSISTENCY_MAP_REGISTRY_MISSING",
                "enabled consistency map requires the human source-of-truth registry",
                registry_relpath,
            )
            return
        registry_entries = parse_registry_fact_entries(self.read_text(registry_path))
        if not registry_entries:
            self.error(
                "CONSISTENCY_MAP_REGISTRY_EMPTY",
                "source-of-truth registry has no Fact Type entries",
                registry_relpath,
            )
            return

        heading_counts: dict[str, int] = {}
        referenced_nodes: dict[str, str] = {}
        for entry in registry_entries:
            heading_counts[entry.heading_fact_type] = (
                heading_counts.get(entry.heading_fact_type, 0) + 1
            )
            entry_path = f"{registry_relpath}:{entry.line}"
            if entry.declared_fact_type != entry.heading_fact_type:
                self.error(
                    "CONSISTENCY_REGISTRY_FACT_TYPE_DRIFT",
                    "Fact type field must match its Fact Type heading exactly",
                    entry_path,
                )
            node_id = entry.map_node_id
            if (
                not isinstance(node_id, str)
                or is_placeholder(node_id)
                or is_unresolved_value(node_id)
            ):
                report = self.warn if self.allow_placeholders else self.error
                report(
                    "CONSISTENCY_REGISTRY_NODE_UNRESOLVED",
                    f"Fact Type {entry.heading_fact_type!r} needs one resolved consistency-map node ID",
                    entry_path,
                )
                continue
            previous_fact_type = referenced_nodes.get(node_id)
            if previous_fact_type is not None:
                self.error(
                    "CONSISTENCY_REGISTRY_NODE_REUSED",
                    f"node {node_id!r} is referenced by both {previous_fact_type!r} and {entry.heading_fact_type!r}",
                    entry_path,
                )
                continue
            referenced_nodes[node_id] = entry.heading_fact_type
            node = nodes_by_id.get(node_id)
            if node is None:
                self.error(
                    "CONSISTENCY_REGISTRY_NODE_MISSING",
                    f"Fact Type {entry.heading_fact_type!r} references missing node {node_id!r}",
                    entry_path,
                )
                continue
            if node.get("fact_type") != entry.heading_fact_type:
                self.error(
                    "CONSISTENCY_REGISTRY_NODE_FACT_TYPE_DRIFT",
                    f"node {node_id!r} fact_type must exactly match {entry.heading_fact_type!r}",
                    relpath,
                )

        for fact_type, count in sorted(heading_counts.items()):
            if count > 1:
                self.error(
                    "CONSISTENCY_REGISTRY_FACT_TYPE_DUPLICATE",
                    f"registry repeats Fact Type {fact_type!r}",
                    registry_relpath,
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
        relpath = ".ai/assistant/ai-infrastructure-router.json"
        path = self.target_path(relpath)
        data = self.load_json_object(path, "AI_ROUTER")
        if data is None:
            return
        schema_version = data.get("schema_version")
        if schema_version not in {1, 2}:
            self.error("AI_ROUTER_SCHEMA", "schema_version should be 1 or 2", relpath)
        elif schema_version == 1:
            self.warn(
                "AI_ROUTER_LEGACY_SCHEMA",
                "schema_version 1 has no evidence-based recommendation route",
                relpath,
            )
        if data.get("router_kind") != "target-ai-infrastructure-router":
            self.error(
                "AI_ROUTER_KIND",
                "router_kind should be target-ai-infrastructure-router",
                relpath,
            )
        routing_order = expect_string_list(
            data.get("routing_order"), self, "AI_ROUTER_ORDER", relpath
        )
        expected_routes = (
            AI_INFRASTRUCTURE_ROUTES
            if schema_version == 2
            else AI_INFRASTRUCTURE_ROUTES_V1
        )
        if set(routing_order) != expected_routes:
            self.error(
                "AI_ROUTER_ROUTES",
                "routing_order must contain each portable AI infrastructure route",
                relpath,
            )
        item_types = expect_string_list(
            data.get("item_types"), self, "AI_ROUTER_ITEM_TYPES", relpath
        )
        if set(item_types) != AI_INFRASTRUCTURE_ITEM_TYPES:
            self.error(
                "AI_ROUTER_ITEM_TYPES",
                "item_types must match the portable item type set",
                relpath,
            )

        if schema_version == 2:
            recommendation_template = data.get("recommendation_template")
            if not isinstance(recommendation_template, str) or not recommendation_template:
                self.error(
                    "AI_ROUTER_RECOMMENDATION_TEMPLATE",
                    "schema_version 2 requires recommendation_template",
                    relpath,
                )
            else:
                self.check_optional_target_reference(
                    recommendation_template,
                    relpath,
                    "recommendation_template",
                )

        routes = data.get("routes")
        if not isinstance(routes, dict):
            self.error("AI_ROUTER_ROUTE_SHAPE", "routes must be an object", relpath)
            routes = {}
        for route_name in expected_routes:
            route = routes.get(route_name)
            if not isinstance(route, dict):
                self.error("AI_ROUTER_ROUTE_MISSING", f"route is missing: {route_name}", relpath)
                continue
            for field in [
                "use_when",
                "required_context",
                "expand_when",
                "allowed_actions",
                "approval_gates",
                "validation",
                "final_evidence",
            ]:
                values = expect_string_list(
                    route.get(field),
                    self,
                    "AI_ROUTER_ROUTE_FIELD",
                    relpath,
                    label=f"routes.{route_name}.{field}",
                )
                if field == "required_context":
                    for value in values:
                        self.check_optional_target_reference(
                            value, relpath, f"routes.{route_name}.{field}"
                        )
                if field == "allowed_actions":
                    self.check_allowed_actions(
                        values, relpath, f"routes.{route_name}.{field}"
                    )

        items = data.get("items")
        if not isinstance(items, list) or not items:
            self.error("AI_ROUTER_ITEMS", "items must be a non-empty list", relpath)
            return
        item_ids: set[str] = set()
        for index, item in enumerate(items):
            label = f"items[{index}]"
            if not isinstance(item, dict):
                self.error("AI_ROUTER_ITEM_SHAPE", f"{label} must be an object", relpath)
                continue
            item_id = item.get("id")
            if not isinstance(item_id, str) or not item_id:
                self.error("AI_ROUTER_ITEM_ID", f"{label}.id must be a string", relpath)
            elif not is_placeholder(item_id):
                if item_id in item_ids:
                    self.error("AI_ROUTER_ITEM_DUPLICATE", f"duplicate item id {item_id}", relpath)
                item_ids.add(item_id)
            item_type = item.get("type")
            if not is_placeholder(item_type) and item_type not in AI_INFRASTRUCTURE_ITEM_TYPES:
                self.error("AI_ROUTER_ITEM_TYPE", f"{label}.type is invalid: {item_type}", relpath)
            status = item.get("status")
            if not is_placeholder(status) and status not in {
                "active",
                "blocked",
                "deprecated",
                "unresolved",
            }:
                self.error(
                    "AI_ROUTER_ITEM_STATUS",
                    f"{label}.status is invalid: {status}",
                    relpath,
                )
            for field in [
                "activation_triggers",
                "required_context",
                "assistant_surfaces",
                "wrappers",
                "allowed_actions",
                "required_permissions",
                "approval_triggers",
                "gates",
                "validation",
                "conflicts_with",
            ]:
                values = expect_string_list(
                    item.get(field),
                    self,
                    "AI_ROUTER_ITEM_FIELD",
                    relpath,
                    label=f"{label}.{field}",
                )
                if field in {"required_context", "wrappers", "gates"}:
                    for value in values:
                        self.check_optional_target_reference(value, relpath, f"{label}.{field}")
                if field == "allowed_actions":
                    self.check_allowed_actions(values, relpath, f"{label}.{field}")
            for field in ["canonical_source", "output_contract", "adaptation_record"]:
                value = item.get(field)
                if not isinstance(value, str) or not value:
                    self.error("AI_ROUTER_ITEM_FIELD", f"{label}.{field} must be a string", relpath)
                elif field != "output_contract":
                    self.check_optional_target_reference(value, relpath, f"{label}.{field}")

    def check_development_evidence(self, manifest: ManifestData | None) -> None:
        key = ("source_of_truth", "development_evidence")
        scalar = manifest.scalars.get(key) if manifest else None
        relpath = scalar.value if scalar else ".ai/project/development-evidence.json"
        path = self.target_path(relpath)
        if not path.is_file():
            self.warn(
                "DEVELOPMENT_EVIDENCE_MISSING",
                "target has no compact development evidence index; recurring request "
                "and process-pattern recommendations remain conversation-local",
                relpath,
            )
            return

        data = self.load_json_object(path, "DEVELOPMENT_EVIDENCE")
        if data is None:
            return
        if data.get("schema_version") != 1:
            self.error(
                "DEVELOPMENT_EVIDENCE_SCHEMA",
                "schema_version should be 1",
                relpath,
            )
        if data.get("register_kind") != "target-development-evidence":
            self.error(
                "DEVELOPMENT_EVIDENCE_KIND",
                "register_kind should be target-development-evidence",
                relpath,
            )

        for field in ["project", "owner", "retention_policy", "last_reviewed"]:
            value = data.get(field)
            if not isinstance(value, str) or not value.strip():
                self.error(
                    "DEVELOPMENT_EVIDENCE_METADATA",
                    f"{field} must be a non-empty string",
                    relpath,
                )
            elif is_unresolved_value(value):
                report = self.warn if self.allow_placeholders else self.error
                report(
                    "DEVELOPMENT_EVIDENCE_METADATA_UNRESOLVED",
                    f"{field} is unresolved",
                    relpath,
                )

        content_policy = data.get("content_policy")
        if not isinstance(content_policy, str) or not all(
            term in content_policy.lower()
            for term in ["raw chat", "secrets", "credentials", "personal data"]
        ):
            self.error(
                "DEVELOPMENT_EVIDENCE_CONTENT_POLICY",
                "content_policy must exclude raw chat, secrets, credentials, and personal data",
                relpath,
            )

        patterns = data.get("patterns")
        if not isinstance(patterns, list):
            self.error(
                "DEVELOPMENT_EVIDENCE_PATTERNS",
                "patterns must be a list",
                relpath,
            )
            return

        required_strings = [
            "id",
            "category",
            "project_area",
            "source_owner",
            "normalized_problem",
            "first_observed",
            "last_observed",
            "evidence_quality",
            "status",
        ]
        list_fields = ["evidence_refs", "outcome_signals", "existing_ai_item_ids"]
        evidence_qualities = {
            "measured",
            "observed",
            "anecdotal",
            "conflicting",
            "unresolved",
        }
        statuses = {"active", "resolved", "deferred", "unresolved"}
        pattern_ids: set[str] = set()
        for index, pattern in enumerate(patterns):
            label = f"patterns[{index}]"
            if not isinstance(pattern, dict):
                self.error(
                    "DEVELOPMENT_EVIDENCE_PATTERN_SHAPE",
                    f"{label} must be an object",
                    relpath,
                )
                continue
            for field in required_strings:
                value = pattern.get(field)
                if not isinstance(value, str) or not value.strip():
                    self.error(
                        "DEVELOPMENT_EVIDENCE_PATTERN_FIELD",
                        f"{label}.{field} must be a non-empty string",
                        relpath,
                    )
            pattern_id = pattern.get("id")
            if isinstance(pattern_id, str) and pattern_id:
                if pattern_id in pattern_ids:
                    self.error(
                        "DEVELOPMENT_EVIDENCE_PATTERN_DUPLICATE",
                        f"duplicate pattern id {pattern_id}",
                        relpath,
                    )
                pattern_ids.add(pattern_id)
            occurrence_count = pattern.get("occurrence_count")
            if not isinstance(occurrence_count, int) or occurrence_count < 1:
                self.error(
                    "DEVELOPMENT_EVIDENCE_OCCURRENCE_COUNT",
                    f"{label}.occurrence_count must be a positive integer",
                    relpath,
                )
            for field in list_fields:
                values = pattern.get(field)
                if not isinstance(values, list) or not all(
                    isinstance(value, str) and value for value in values
                ):
                    self.error(
                        "DEVELOPMENT_EVIDENCE_PATTERN_LIST",
                        f"{label}.{field} must be a string list",
                        relpath,
                    )
            if not pattern.get("evidence_refs"):
                self.error(
                    "DEVELOPMENT_EVIDENCE_REFERENCE_MISSING",
                    f"{label}.evidence_refs must identify at least one occurrence",
                    relpath,
                )
            if pattern.get("evidence_quality") not in evidence_qualities:
                self.error(
                    "DEVELOPMENT_EVIDENCE_QUALITY",
                    f"{label}.evidence_quality is invalid",
                    relpath,
                )
            if pattern.get("status") not in statuses:
                self.error(
                    "DEVELOPMENT_EVIDENCE_STATUS",
                    f"{label}.status is invalid",
                    relpath,
                )

    def check_team_collaboration(self, manifest: ManifestData | None) -> None:
        policy_key = ("team_collaboration", "policy")
        model_key = ("team_collaboration", "operating_model")
        source_model_key = ("source_of_truth", "team_operating_model")
        registry_key = ("team_collaboration", "work_registry")
        index_key = ("team_collaboration", "active_work_index")
        backend_key = ("team_collaboration", "backend_contract")
        tasks_key = ("team_collaboration", "task_records_directory")
        local_identity_key = ("team_collaboration", "local_identity")
        policy_scalar = manifest.scalars.get(policy_key) if manifest else None
        model_scalar = manifest.scalars.get(model_key) if manifest else None
        if not model_scalar and manifest:
            model_scalar = manifest.scalars.get(source_model_key)
        registry_scalar = manifest.scalars.get(registry_key) if manifest else None
        index_scalar = manifest.scalars.get(index_key) if manifest else None
        backend_scalar = manifest.scalars.get(backend_key) if manifest else None
        tasks_scalar = manifest.scalars.get(tasks_key) if manifest else None
        local_identity_scalar = (
            manifest.scalars.get(local_identity_key) if manifest else None
        )
        policy_relpath = (
            policy_scalar.value if policy_scalar else ".ai/project/team-policy.json"
        )
        model_relpath = (
            model_scalar.value
            if model_scalar
            else ".ai/project/team-operating-model.md"
        )
        registry_relpath = (
            registry_scalar.value
            if registry_scalar
            else ".ai/assistant/team/work-registry.json"
        )
        index_relpath = (
            index_scalar.value
            if index_scalar
            else ".ai/assistant/team/active-work-index.json"
        )
        backend_relpath = (
            backend_scalar.value
            if backend_scalar
            else ".ai/assistant/team/backend-contract.json"
        )
        tasks_relpath = (
            tasks_scalar.value
            if tasks_scalar
            else ".ai/assistant/team/tasks"
        )
        local_identity_relpath = (
            local_identity_scalar.value
            if local_identity_scalar
            else ".ai/local/team-identity.json"
        )
        policy_path = self.target_path(policy_relpath)
        model_path = self.target_path(model_relpath)
        registry_path = self.target_path(registry_relpath)
        index_path = self.target_path(index_relpath)
        backend_path = self.target_path(backend_relpath)
        tasks_path = self.target_path(tasks_relpath)
        local_identity_path = self.target_path(local_identity_relpath)

        if not policy_path.exists() and not model_path.exists() and not registry_path.exists():
            return
        if not policy_path.is_file():
            self.error(
                "TEAM_POLICY_MISSING",
                "team collaboration exists without its structured target policy",
                policy_relpath,
            )
            return
        if not model_path.is_file():
            self.error(
                "TEAM_OPERATING_MODEL_MISSING",
                "team work registry exists without its target-owned operating model",
                model_relpath,
            )
            return
        if not registry_path.is_file():
            self.error(
                "TEAM_REGISTRY_MISSING",
                "team operating model exists without its machine-readable work registry",
                registry_relpath,
            )
            return

        for path, relpath, code, message in [
            (
                index_path,
                index_relpath,
                "TEAM_ACTIVE_INDEX_MISSING",
                "team collaboration requires a compact active-work index",
            ),
            (
                backend_path,
                backend_relpath,
                "TEAM_BACKEND_CONTRACT_MISSING",
                "team collaboration requires a backend capability contract",
            ),
        ]:
            if not path.is_file():
                self.error(code, message, relpath)
                return

        policy = self.load_json_object(policy_path, "TEAM_POLICY")
        active_index = self.load_json_object(index_path, "TEAM_ACTIVE_INDEX")
        backend = self.load_json_object(backend_path, "TEAM_BACKEND")
        if policy is None or active_index is None or backend is None:
            return

        registry = self.load_json_object(registry_path, "TEAM_REGISTRY")
        if registry is None:
            return
        registry_schema = registry.get("schema_version")
        if registry_schema == 1:
            self.error(
                "TEAM_REGISTRY_MIGRATION_REQUIRED",
                "schema-1 monolithic task records must be migrated atomically to "
                "schema-2 per-task records before team writes",
                registry_relpath,
            )
        elif registry_schema != 2:
            self.error(
                "TEAM_REGISTRY_SCHEMA",
                "schema_version should be 2",
                registry_relpath,
            )
        if registry.get("registry_kind") != "target-team-work-registry":
            self.error(
                "TEAM_REGISTRY_KIND",
                "registry_kind should be target-team-work-registry",
                registry_relpath,
            )

        metadata_fields = [
            "project",
            "module_state",
            "coordination_backend",
            "canonical_task_source",
            "synchronization_direction",
            "team_policy",
            "operating_model",
            "backend_contract",
            "active_work_index",
            "task_records_directory",
            "task_record_template",
            "updated_at",
            "evidence_revision",
            "storage_policy",
            "retention_policy",
            "privacy_policy",
        ]
        for field in metadata_fields:
            value = registry.get(field)
            if not isinstance(value, str) or not value.strip():
                self.error(
                    "TEAM_REGISTRY_METADATA",
                    f"{field} must be a non-empty string",
                    registry_relpath,
                )
        module_state = registry.get("module_state")
        if concrete_state := (
            isinstance(module_state, str)
            and not is_placeholder(module_state)
            and not is_unresolved_value(module_state)
        ):
            if module_state not in {
                "enabled",
                "deferred",
                "disabled",
                "not-applicable",
                "blocked",
            }:
                self.error(
                    "TEAM_MODULE_STATE",
                    f"module_state is invalid: {module_state}",
                    registry_relpath,
                )
        if concrete_state and module_state == "enabled":
            for field in [
                "project",
                "coordination_backend",
                "canonical_task_source",
                "synchronization_direction",
                "storage_policy",
                "retention_policy",
                "privacy_policy",
            ]:
                value = registry.get(field)
                if not isinstance(value, str) or is_unresolved_value(value):
                    self.error(
                        "TEAM_ENABLED_METADATA_UNRESOLVED",
                        f"enabled team module requires resolved {field}",
                        registry_relpath,
                    )
        if registry.get("operating_model") != model_relpath:
            self.error(
                "TEAM_REGISTRY_OPERATING_MODEL",
                f"operating_model should point to {model_relpath}",
                registry_relpath,
            )

        for field, expected in [
            ("team_policy", policy_relpath),
            ("backend_contract", backend_relpath),
            ("active_work_index", index_relpath),
            ("task_records_directory", tasks_relpath),
        ]:
            if registry_schema == 2 and registry.get(field) != expected:
                self.error(
                    "TEAM_REGISTRY_PATH",
                    f"{field} should point to {expected}",
                    registry_relpath,
                )
        if registry_schema == 2 and not isinstance(
            registry.get("registry_revision"), int
        ):
            self.error(
                "TEAM_REGISTRY_REVISION",
                "schema-2 registry_revision must be an integer",
                registry_relpath,
            )
        if registry_schema == 2 and "tasks" in registry:
            self.error(
                "TEAM_REGISTRY_MONOLITHIC_TASKS",
                "schema-2 registry must not contain a monolithic tasks array",
                registry_relpath,
            )

        if policy.get("schema_version") != 1:
            self.error("TEAM_POLICY_SCHEMA", "schema_version should be 1", policy_relpath)
        if policy.get("policy_kind") != "target-team-policy":
            self.error(
                "TEAM_POLICY_KIND",
                "policy_kind should be target-team-policy",
                policy_relpath,
            )
        identity_policy = policy.get("identity")
        if not isinstance(identity_policy, dict):
            self.error("TEAM_IDENTITY_POLICY", "identity must be an object", policy_relpath)
            identity_policy = {}
        else:
            if identity_policy.get("local_identity_path") != local_identity_relpath:
                self.error(
                    "TEAM_LOCAL_IDENTITY_PATH",
                    f"local identity path should be {local_identity_relpath}",
                    policy_relpath,
                )
            if identity_policy.get("git_identity_is_authoritative") is not False:
                self.error(
                    "TEAM_GIT_IDENTITY_AUTHORITY",
                    "Git identity must not be authoritative for team actor selection",
                    policy_relpath,
                )

        actors = policy.get("actors")
        if not isinstance(actors, list):
            self.error("TEAM_ACTORS_SHAPE", "actors must be a list", policy_relpath)
            actors = []
        actor_by_id: dict[str, dict[str, Any]] = {}
        actor_aliases: dict[str, set[str]] = {}
        for index, actor in enumerate(actors):
            label = f"actors[{index}]"
            if not isinstance(actor, dict):
                self.error("TEAM_ACTOR_SHAPE", f"{label} must be an object", policy_relpath)
                continue
            actor_id = actor.get("id")
            if not isinstance(actor_id, str) or not actor_id:
                self.error("TEAM_ACTOR_ID", f"{label}.id must be a string", policy_relpath)
                continue
            if is_placeholder(actor_id):
                continue
            if actor_id in actor_by_id:
                self.error("TEAM_ACTOR_DUPLICATE", f"duplicate actor {actor_id}", policy_relpath)
            actor_by_id[actor_id] = actor
            raw_aliases = actor.get("aliases")
            names = [
                actor.get("display_name"),
                *(raw_aliases if isinstance(raw_aliases, list) else []),
            ]
            for name in names:
                if isinstance(name, str) and name and not is_placeholder(name):
                    actor_aliases.setdefault(name.casefold(), set()).add(actor_id)
            for field in [
                "aliases",
                "teams",
                "roles",
                "responsibilities",
                "decision_authority",
                "review_scopes",
                "priority_scopes",
                "external_identity_refs",
            ]:
                values = actor.get(field)
                if not isinstance(values, list) or not all(
                    isinstance(value, str) and value for value in values
                ):
                    self.error(
                        "TEAM_ACTOR_LIST",
                        f"{label}.{field} must be a string list",
                        policy_relpath,
                    )
        actor_ids = set(actor_by_id)

        priorities = policy.get("priorities")
        if not isinstance(priorities, list):
            self.error("TEAM_PRIORITIES_SHAPE", "priorities must be a list", policy_relpath)
            priorities = []
        priority_by_id = {
            item.get("id"): item
            for item in priorities
            if isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and not is_placeholder(item["id"])
        }
        priority_ids = set(priority_by_id)

        if active_index.get("schema_version") != 1:
            self.error("TEAM_ACTIVE_INDEX_SCHEMA", "schema_version should be 1", index_relpath)
        if active_index.get("index_kind") != "target-team-active-work-index":
            self.error(
                "TEAM_ACTIVE_INDEX_KIND",
                "index_kind should be target-team-active-work-index",
                index_relpath,
            )
        if active_index.get("source_registry") != registry_relpath:
            self.error(
                "TEAM_ACTIVE_INDEX_REGISTRY",
                f"source_registry should point to {registry_relpath}",
                index_relpath,
            )
        index_entries = active_index.get("entries")
        if not isinstance(index_entries, list):
            self.error("TEAM_ACTIVE_INDEX_ENTRIES", "entries must be a list", index_relpath)
            index_entries = []

        if backend.get("schema_version") != 1:
            self.error("TEAM_BACKEND_SCHEMA", "schema_version should be 1", backend_relpath)
        if backend.get("contract_kind") != "target-team-backend-contract":
            self.error(
                "TEAM_BACKEND_KIND",
                "contract_kind should be target-team-backend-contract",
                backend_relpath,
            )
        capabilities = backend.get("capabilities")
        if not isinstance(capabilities, list) or not all(
            isinstance(value, str) and value for value in capabilities
        ):
            self.error(
                "TEAM_BACKEND_CAPABILITIES",
                "capabilities must be a string list",
                backend_relpath,
            )
        for field in [
            "backend_id",
            "backend_mode",
            "provider",
            "canonical_task_source",
            "projection_direction",
            "consistency_model",
            "write_strategy",
            "idempotency_policy",
            "conflict_policy",
            "permission_policy",
            "authentication_policy",
            "validation",
        ]:
            value = backend.get(field)
            if not isinstance(value, str) or not value.strip():
                self.error(
                    "TEAM_BACKEND_FIELD",
                    f"{field} must be a non-empty string",
                    backend_relpath,
                )

        tasks: list[Any] = []
        task_sources: list[str] = []
        if registry_schema == 1:
            legacy_tasks = registry.get("tasks")
            if isinstance(legacy_tasks, list):
                tasks = legacy_tasks
                task_sources = [registry_relpath] * len(tasks)
        elif tasks_path.is_dir():
            for task_path in sorted(tasks_path.glob("*.json")):
                task_record = self.load_json_object(task_path, "TEAM_TASK")
                if task_record is not None:
                    tasks.append(task_record)
                    task_sources.append(self.rel(task_path))

        task_statuses = {
            "proposed",
            "ready",
            "claimed",
            "active",
            "blocked",
            "review",
            "merge-ready",
            "complete",
            "cancelled",
            "stale",
        }
        overlap_states = {
            "none",
            "compatible",
            "sequencing-required",
            "conflicting",
            "unresolved",
        }
        claim_states = {
            "unclaimed",
            "active",
            "released",
            "expired",
            "invalidated",
            "unverified",
        }
        validation_states = {"not-run", "passed", "failed", "partial", "unresolved"}
        review_states = {
            "not-required",
            "pending",
            "changes-requested",
            "approved",
            "unresolved",
        }
        handoff_states = {"none", "pending", "accepted", "rejected", "stale"}
        required_strings = [
            "id",
            "record_kind",
            "backend_revision",
            "goal",
            "priority",
            "priority_rationale",
            "priority_decided_by",
            "status",
            "requested_by_actor_id",
            "owner_actor_id",
            "last_updated_by_actor_id",
            "assistant_actor_id",
            "parent_request",
            "coordination_backend_ref",
            "branch_or_worktree",
            "base_revision",
            "evidence_revision",
            "review_state",
            "validation_state",
            "latest_checkpoint",
            "handoff_state",
            "next_action",
            "updated_at",
        ]
        list_fields = [
            "non_goals",
            "reviewer_actor_ids",
            "allowed_actions",
            "context_profiles",
            "project_areas",
            "changed_fact_ids",
            "canonical_owner_refs",
            "expected_surfaces",
            "dependencies",
            "blockers",
            "related_task_ids",
            "approval_records",
            "review_evidence_refs",
            "decision_records",
            "residual_risks",
        ]
        task_ids: set[str] = set()
        current_head = git_head_revision(self.target)

        def concrete(value: Any) -> bool:
            return (
                isinstance(value, str)
                and bool(value.strip())
                and not is_placeholder(value)
                and value.strip().lower()
                not in {"none", "unavailable", "not available", "not recorded"}
            )

        def check_actor(value: Any, label: str) -> None:
            if not concrete(value):
                return
            if value not in actor_ids:
                self.error(
                    "TEAM_ACTOR_UNKNOWN",
                    f"{label} references actor {value!r} absent from the operating model",
                    registry_relpath,
                )

        for index, task in enumerate(tasks):
            label = f"tasks[{index}]"
            task_source = (
                task_sources[index]
                if index < len(task_sources)
                else registry_relpath
            )
            if not isinstance(task, dict):
                self.error(
                    "TEAM_TASK_SHAPE",
                    f"{label} must be an object",
                    registry_relpath,
                )
                continue
            if registry_schema == 2:
                if task.get("schema_version") != 2:
                    self.error(
                        "TEAM_TASK_SCHEMA",
                        f"{label}.schema_version should be 2",
                        task_source,
                    )
                if task.get("record_kind") != "target-team-task":
                    self.error(
                        "TEAM_TASK_KIND",
                        f"{label}.record_kind should be target-team-task",
                        task_source,
                    )
                record_revision = task.get("record_revision")
                expected_revision = task.get("expected_revision")
                if not isinstance(record_revision, int) or record_revision < 0:
                    self.error(
                        "TEAM_TASK_RECORD_REVISION",
                        f"{label}.record_revision must be a non-negative integer",
                        task_source,
                    )
                if not isinstance(expected_revision, int) or expected_revision < 0:
                    self.error(
                        "TEAM_TASK_EXPECTED_REVISION",
                        f"{label}.expected_revision must be a non-negative integer",
                        task_source,
                    )
                if (
                    isinstance(record_revision, int)
                    and isinstance(expected_revision, int)
                    and expected_revision != record_revision
                ):
                    self.error(
                        "TEAM_TASK_REVISION_CONFLICT",
                        f"{label} expected revision does not match current record revision",
                        task_source,
                    )
            for field in required_strings:
                value = task.get(field)
                if not isinstance(value, str) or not value.strip():
                    self.error(
                        "TEAM_TASK_FIELD",
                        f"{label}.{field} must be a non-empty string",
                        registry_relpath,
                    )
            for field in list_fields:
                values = task.get(field)
                if not isinstance(values, list) or not all(
                    isinstance(value, str) and value for value in values
                ):
                    self.error(
                        "TEAM_TASK_LIST",
                        f"{label}.{field} must be a string list",
                        registry_relpath,
                    )
                    continue
                if field == "allowed_actions":
                    self.check_allowed_actions(
                        values,
                        registry_relpath,
                        f"{label}.{field}",
                    )

            task_id = task.get("id")
            if concrete(task_id):
                if task_id in task_ids:
                    self.error(
                        "TEAM_TASK_DUPLICATE",
                        f"duplicate task id {task_id}",
                        registry_relpath,
                    )
                task_ids.add(task_id)

            status = task.get("status")
            if concrete(status) and status not in task_statuses:
                self.error(
                    "TEAM_TASK_STATUS",
                    f"{label}.status is invalid: {status}",
                    registry_relpath,
                )
            priority = task.get("priority")
            if concrete(priority) and priority not in priority_ids:
                self.error(
                    "TEAM_PRIORITY_UNKNOWN",
                    f"{label}.priority references {priority!r} absent from the operating model",
                    registry_relpath,
                )
            review_state = task.get("review_state")
            if concrete(review_state) and review_state not in review_states:
                self.error(
                    "TEAM_REVIEW_STATE",
                    f"{label}.review_state is invalid: {review_state}",
                    registry_relpath,
                )
            validation_state = task.get("validation_state")
            if concrete(validation_state) and validation_state not in validation_states:
                self.error(
                    "TEAM_VALIDATION_STATE",
                    f"{label}.validation_state is invalid: {validation_state}",
                    registry_relpath,
                )
            handoff_state = task.get("handoff_state")
            if concrete(handoff_state) and handoff_state not in handoff_states:
                self.error(
                    "TEAM_HANDOFF_STATE",
                    f"{label}.handoff_state is invalid: {handoff_state}",
                    registry_relpath,
                )

            check_actor(task.get("owner_actor_id"), f"{label}.owner_actor_id")
            check_actor(
                task.get("requested_by_actor_id"),
                f"{label}.requested_by_actor_id",
            )
            check_actor(
                task.get("last_updated_by_actor_id"),
                f"{label}.last_updated_by_actor_id",
            )
            check_actor(
                task.get("assistant_actor_id"),
                f"{label}.assistant_actor_id",
            )
            check_actor(task.get("priority_decided_by"), f"{label}.priority_decided_by")
            reviewers = task.get("reviewer_actor_ids")
            if isinstance(reviewers, list):
                for reviewer_index, reviewer in enumerate(reviewers):
                    check_actor(
                        reviewer,
                        f"{label}.reviewer_actor_ids[{reviewer_index}]",
                    )

            priority_decider = task.get("priority_decided_by")
            priority_policy = priority_by_id.get(priority)
            if isinstance(priority_policy, dict) and concrete(priority_decider):
                assigners = priority_policy.get("assigner_actor_ids")
                if isinstance(assigners, list) and any(concrete(item) for item in assigners):
                    if priority_decider not in assigners:
                        self.error(
                            "TEAM_PRIORITY_AUTHORITY",
                            f"{label}.priority_decided_by lacks authority for {priority}",
                            task_source,
                        )

            review_policy = policy.get("review_policy")
            if isinstance(review_policy, dict) and review_policy.get(
                "implementer_reviewer_separation"
            ) == "required":
                owner = task.get("owner_actor_id")
                if concrete(owner) and isinstance(reviewers, list) and owner in reviewers:
                    self.error(
                        "TEAM_REVIEWER_SEPARATION",
                        f"{label} assigns its implementer as reviewer",
                        task_source,
                    )

            overlap = task.get("overlap")
            overlap_state: Any = None
            if not isinstance(overlap, dict):
                self.error(
                    "TEAM_OVERLAP_SHAPE",
                    f"{label}.overlap must be an object",
                    registry_relpath,
                )
            else:
                overlap_state = overlap.get("state")
                for field in ["state", "checked_at", "checked_revision", "resolution"]:
                    value = overlap.get(field)
                    if not isinstance(value, str) or not value.strip():
                        self.error(
                            "TEAM_OVERLAP_FIELD",
                            f"{label}.overlap.{field} must be a non-empty string",
                            registry_relpath,
                        )
                for field in [
                    "fact_ids",
                    "contract_or_dependency_refs",
                    "file_or_surface_refs",
                ]:
                    values = overlap.get(field)
                    if not isinstance(values, list) or not all(
                        isinstance(value, str) and value for value in values
                    ):
                        self.error(
                            "TEAM_OVERLAP_LIST",
                            f"{label}.overlap.{field} must be a string list",
                            registry_relpath,
                        )
                if concrete(overlap_state) and overlap_state not in overlap_states:
                    self.error(
                        "TEAM_OVERLAP_STATE",
                        f"{label}.overlap.state is invalid: {overlap_state}",
                        registry_relpath,
                    )

            claim = task.get("claim")
            claim_state: Any = None
            if not isinstance(claim, dict):
                self.error(
                    "TEAM_CLAIM_SHAPE",
                    f"{label}.claim must be an object",
                    registry_relpath,
                )
            else:
                claim_state = claim.get("state")
                for field in [
                    "mode",
                    "actor_id",
                    "claimed_at",
                    "expires_at",
                    "base_revision",
                    "state",
                    *(
                        ["lease_id", "heartbeat_at", "backend_revision"]
                        if registry_schema == 2
                        else []
                    ),
                ]:
                    value = claim.get(field)
                    if not isinstance(value, str) or not value.strip():
                        self.error(
                            "TEAM_CLAIM_FIELD",
                            f"{label}.claim.{field} must be a non-empty string",
                            registry_relpath,
                        )
                if concrete(claim_state) and claim_state not in claim_states:
                    self.error(
                        "TEAM_CLAIM_STATE",
                        f"{label}.claim.state is invalid: {claim_state}",
                        registry_relpath,
                    )
                claim_mode = claim.get("mode")
                if concrete(claim_mode) and claim_mode not in {
                    "advisory",
                    "target-enforced",
                }:
                    self.error(
                        "TEAM_CLAIM_MODE",
                        f"{label}.claim.mode is invalid: {claim_mode}",
                        registry_relpath,
                    )
                check_actor(claim.get("actor_id"), f"{label}.claim.actor_id")
                if claim_state == "active":
                    for field in [
                        "actor_id",
                        "claimed_at",
                        "base_revision",
                        *(["lease_id"] if registry_schema == 2 else []),
                    ]:
                        if not concrete(claim.get(field)):
                            self.error(
                                "TEAM_ACTIVE_CLAIM_INCOMPLETE",
                                f"{label}.claim.{field} is required for an active claim",
                                registry_relpath,
                            )

            if registry_schema == 2:
                transition = task.get("transition")
                if not isinstance(transition, dict):
                    self.error(
                        "TEAM_TRANSITION_SHAPE",
                        f"{label}.transition must be an object",
                        task_source,
                    )
                else:
                    transition_from = transition.get("from")
                    transition_to = transition.get("to")
                    transition_actor = transition.get("changed_by_actor_id")
                    check_actor(
                        transition_actor,
                        f"{label}.transition.changed_by_actor_id",
                    )
                    if concrete(transition_to) and transition_to != status:
                        self.error(
                            "TEAM_TRANSITION_STATUS",
                            f"{label}.transition.to must match task status",
                            task_source,
                        )
                    transitions = policy.get("state_transitions")
                    if (
                        concrete(transition_from)
                        and concrete(transition_to)
                        and isinstance(transitions, list)
                    ):
                        matching = [
                            item
                            for item in transitions
                            if isinstance(item, dict)
                            and item.get("from") == transition_from
                            and item.get("to") == transition_to
                        ]
                        if not matching:
                            self.error(
                                "TEAM_TRANSITION_NOT_ALLOWED",
                                f"{label} transition {transition_from} -> {transition_to} "
                                "is absent from the team policy",
                                task_source,
                            )

            if status in {"claimed", "active"} and claim_state != "active":
                self.warn(
                    "TEAM_ACTIVE_TASK_WITHOUT_CLAIM",
                    f"{label} is {status} without an active claim",
                    registry_relpath,
                )
            if status in {"complete", "cancelled"} and claim_state == "active":
                self.warn(
                    "TEAM_TERMINAL_TASK_ACTIVE_CLAIM",
                    f"{label} is {status} but still has an active claim",
                    registry_relpath,
                )
            if status in {"claimed", "active", "review", "merge-ready"} and overlap_state in {
                "conflicting",
                "unresolved",
            }:
                report = self.error if status == "merge-ready" else self.warn
                report(
                    "TEAM_ACTIVE_OVERLAP_BLOCKED",
                    f"{label} is {status} with {overlap_state} overlap",
                    registry_relpath,
                )

            task_revision = task.get("evidence_revision")
            if status == "merge-ready":
                if review_state not in {"approved", "not-required"}:
                    self.error(
                        "TEAM_MERGE_READY_REVIEW",
                        f"{label} is merge-ready without approved or explicitly "
                        "not-required review state",
                        registry_relpath,
                    )
                review_evidence = task.get("review_evidence_refs")
                if not isinstance(review_evidence, list) or not any(
                    concrete(reference) for reference in review_evidence
                ):
                    self.error(
                        "TEAM_MERGE_READY_REVIEW_EVIDENCE",
                        f"{label} is merge-ready without review evidence",
                        registry_relpath,
                    )
                if validation_state != "passed":
                    self.error(
                        "TEAM_MERGE_READY_VALIDATION",
                        f"{label} is merge-ready without passed validation",
                        registry_relpath,
                    )
                if overlap_state not in {"none", "compatible"}:
                    self.error(
                        "TEAM_MERGE_READY_OVERLAP",
                        f"{label} is merge-ready without resolved overlap",
                        registry_relpath,
                    )
                if review_state == "approved" and (
                    not isinstance(reviewers, list)
                    or not any(concrete(reviewer) for reviewer in reviewers)
                ):
                    self.error(
                        "TEAM_MERGE_READY_REVIEWERS",
                        f"{label} has approved review state without a recorded reviewer",
                        registry_relpath,
                    )
                for field in ["base_revision", "evidence_revision"]:
                    if not concrete(task.get(field)):
                        self.error(
                            "TEAM_MERGE_READY_REVISION",
                            f"{label}.{field} is required for merge-ready evidence",
                            registry_relpath,
                        )
                if registry_schema == 2:
                    reviewed_head = task.get("reviewed_head_revision")
                    reviewed_base = task.get("reviewed_base_revision")
                    if not concrete(reviewed_head) or not concrete(reviewed_base):
                        self.error(
                            "TEAM_MERGE_READY_REVIEW_REVISIONS",
                            f"{label} must record reviewed head and base revisions",
                            task_source,
                        )
                    elif reviewed_head != task_revision or reviewed_base != task.get(
                        "base_revision"
                    ):
                        self.error(
                            "TEAM_MERGE_READY_REVIEW_STALE",
                            f"{label} review revisions do not match task evidence",
                            task_source,
                        )
                if (
                    current_head
                    and concrete(task_revision)
                    and not refs_match(self.target, str(task_revision), current_head)
                ):
                    self.warn(
                        "TEAM_MERGE_READY_STALE",
                        f"{label} evidence revision does not match this checkout's "
                        "HEAD; confirm its selected branch or worktree before merge",
                        registry_relpath,
                    )

        for alias, matching_ids in actor_aliases.items():
            if len(matching_ids) > 1:
                self.warn(
                    "TEAM_ACTOR_ALIAS_AMBIGUOUS",
                    f"actor name or alias {alias!r} resolves to multiple actor IDs",
                    policy_relpath,
                )

        index_ids: set[str] = set()
        for index, entry in enumerate(index_entries):
            label = f"entries[{index}]"
            if not isinstance(entry, dict):
                self.error(
                    "TEAM_ACTIVE_INDEX_ENTRY",
                    f"{label} must be an object",
                    index_relpath,
                )
                continue
            entry_id = entry.get("task_id")
            if not concrete(entry_id):
                self.error(
                    "TEAM_ACTIVE_INDEX_TASK_ID",
                    f"{label}.task_id must be a concrete string",
                    index_relpath,
                )
                continue
            if entry_id in index_ids:
                self.error(
                    "TEAM_ACTIVE_INDEX_DUPLICATE",
                    f"duplicate active task {entry_id}",
                    index_relpath,
                )
            index_ids.add(str(entry_id))
            for field in [
                "task_record",
                "status",
                "owner_actor_id",
                "branch_or_worktree",
                "record_revision",
                "backend_revision",
            ]:
                if field not in entry:
                    self.error(
                        "TEAM_ACTIVE_INDEX_FIELD",
                        f"{label} missing {field}",
                        index_relpath,
                    )
            for field in [
                "project_areas",
                "changed_fact_ids",
                "canonical_owner_refs",
                "contract_or_dependency_refs",
                "expected_surfaces",
            ]:
                values = entry.get(field)
                if not isinstance(values, list) or not all(
                    isinstance(value, str) and value for value in values
                ):
                    self.error(
                        "TEAM_ACTIVE_INDEX_LIST",
                        f"{label}.{field} must be a string list",
                        index_relpath,
                    )

        active_statuses = {
            "ready",
            "claimed",
            "active",
            "blocked",
            "review",
            "merge-ready",
            "stale",
        }
        local_active_ids = {
            str(task.get("id"))
            for task in tasks
            if isinstance(task, dict)
            and concrete(task.get("id"))
            and task.get("status") in active_statuses
        }
        backend_mode = backend.get("backend_mode")
        if registry_schema == 2 and backend_mode in {"repository", "both"}:
            missing_from_index = sorted(local_active_ids - index_ids)
            extra_in_index = sorted(index_ids - local_active_ids)
            if missing_from_index:
                self.error(
                    "TEAM_ACTIVE_INDEX_INCOMPLETE",
                    f"active-work index misses task records {missing_from_index}",
                    index_relpath,
                )
            if extra_in_index:
                self.error(
                    "TEAM_ACTIVE_INDEX_STALE",
                    f"active-work index references absent or inactive tasks {extra_in_index}",
                    index_relpath,
                )

        if local_identity_path.is_file():
            local_identity = self.load_json_object(
                local_identity_path,
                "TEAM_LOCAL_IDENTITY",
            )
            if local_identity is not None:
                if local_identity.get("schema_version") != 1:
                    self.error(
                        "TEAM_LOCAL_IDENTITY_SCHEMA",
                        "schema_version should be 1",
                        local_identity_relpath,
                    )
                if local_identity.get("identity_kind") != "local-team-identity":
                    self.error(
                        "TEAM_LOCAL_IDENTITY_KIND",
                        "identity_kind should be local-team-identity",
                        local_identity_relpath,
                    )
                selected_actor = local_identity.get("actor_id")
                if concrete(selected_actor):
                    if selected_actor not in actor_by_id:
                        self.error(
                            "TEAM_LOCAL_IDENTITY_UNKNOWN",
                            f"selected actor {selected_actor!r} is absent from team policy",
                            local_identity_relpath,
                        )
                    elif actor_by_id[selected_actor].get("status") != "active":
                        self.error(
                            "TEAM_LOCAL_IDENTITY_INACTIVE",
                            f"selected actor {selected_actor!r} is not active",
                            local_identity_relpath,
                        )
                selected_policy_revision = local_identity.get("policy_revision")
                current_policy_revision = policy.get("policy_revision")
                if (
                    concrete(selected_policy_revision)
                    and concrete(current_policy_revision)
                    and selected_policy_revision != current_policy_revision
                ):
                    self.warn(
                        "TEAM_LOCAL_IDENTITY_STALE",
                        "local actor selection was made against another policy revision",
                        local_identity_relpath,
                    )
                if local_identity.get("selected_by") != "explicit-user-request":
                    self.error(
                        "TEAM_LOCAL_IDENTITY_SELECTION",
                        "local actor selection must record an explicit user request",
                        local_identity_relpath,
                    )
            ignore_path = self.target_path(".ai/.gitignore")
            if not ignore_path.is_file() or "local/" not in self.read_text(ignore_path):
                self.error(
                    "TEAM_LOCAL_IDENTITY_NOT_IGNORED",
                    ".ai/local must be ignored before storing local identity",
                    ".ai/.gitignore",
                )

        registry_revision = registry.get("evidence_revision")
        if (
            current_head
            and concrete(registry_revision)
            and not refs_match(self.target, str(registry_revision), current_head)
        ):
            self.warn(
                "TEAM_REGISTRY_REVISION_STALE",
                "team work registry evidence revision does not match current HEAD",
                registry_relpath,
            )

        router_path = self.target_path(".ai/assistant/context-router.json")
        router = self.load_json_object(router_path, "ROUTER")
        overlay_route = (
            router.get("task_scale_overlays", {}).get("team-active")
            if isinstance(router, dict)
            and isinstance(router.get("task_scale_overlays"), dict)
            else None
        )
        if not isinstance(overlay_route, dict):
            self.error(
                "TEAM_CONTEXT_OVERLAY_MISSING",
                "enabled team artifacts require the team-active context overlay",
                ".ai/assistant/context-router.json",
            )
            return
        descriptor = overlay_route.get("descriptor")
        if not isinstance(descriptor, str) or not descriptor:
            self.error(
                "TEAM_CONTEXT_OVERLAY_DESCRIPTOR",
                "team-active must identify its lazy descriptor",
                ".ai/assistant/context-router.json",
            )
            return
        overlay = self.load_json_object(
            self.target_path(descriptor),
            "TEAM_CONTEXT_OVERLAY",
        )
        if overlay is not None:
            if overlay.get("schema_version") != 2:
                self.error(
                    "TEAM_CONTEXT_OVERLAY_SCHEMA",
                    "schema_version should be 2",
                    descriptor,
                )
            if overlay.get("overlay_kind") != "target-team-context-overlay":
                self.error(
                    "TEAM_CONTEXT_OVERLAY_KIND",
                    "overlay_kind should be target-team-context-overlay",
                    descriptor,
                )
            if overlay.get("overlay_id") != "team-active":
                self.error(
                    "TEAM_CONTEXT_OVERLAY_ID",
                    "overlay_id should be team-active",
                    descriptor,
                )
            required_context = overlay.get("required_context")
            if not isinstance(required_context, list):
                self.error(
                    "TEAM_CONTEXT_OVERLAY_SHAPE",
                    "team-active required_context must be a list",
                    descriptor,
                )
            else:
                if required_context != [index_relpath]:
                    self.error(
                        "TEAM_CONTEXT_OVERLAY_PREFLIGHT",
                        "team-active required_context should contain only the "
                        "compact active-work index",
                        descriptor,
                    )
            conditional_context = overlay.get("conditional_context")
            if not isinstance(conditional_context, list):
                self.error(
                    "TEAM_CONTEXT_OVERLAY_CONDITIONAL",
                    "team-active conditional_context must be a list",
                    descriptor,
                )
            else:
                conditional_paths = {
                    entry.get("path")
                    for entry in conditional_context
                    if isinstance(entry, dict)
                }
                for required_path in [
                    ".ai/framework/team-collaboration.md",
                    policy_relpath,
                    model_relpath,
                    registry_relpath,
                    backend_relpath,
                    ".ai/assistant/gates/team-collaboration.md",
                ]:
                    if required_path not in conditional_paths:
                        self.error(
                            "TEAM_CONTEXT_OVERLAY_PATH",
                            f"team-active conditional context is missing {required_path}",
                            descriptor,
                        )

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
        text = path.read_text(encoding="utf-8")
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

    def check_placeholders(self) -> None:
        if self.allow_placeholders:
            self.info("PLACEHOLDERS_ALLOWED", "placeholder checks were downgraded by option")
            return

        paths = [
            self.target_path(".ai/alatyr.yaml"),
            self.target_path(".ai/README.md"),
            self.target_path(".ai/project/contour.md"),
            self.target_path(".ai/project/source-of-truth-registry.md"),
            self.target_path(".ai/assistant/contour.md"),
            self.target_path(".ai/assistant/context-profiles.md"),
            self.target_path(".ai/assistant/help.md"),
            self.target_path(".ai/assistant/help-reference.md"),
            self.target_path(".ai/assistant/module-profile.md"),
            self.target_path(".ai/assistant/maturity-profile.md"),
            self.target_path(".ai/assistant/gates/checklist.md"),
            self.target_path(".ai/assistant/operation-catalog.json"),
            self.target_path(".ai/project/team-policy.json"),
            self.target_path(".ai/project/team-operating-model.md"),
            self.target_path(".ai/assistant/team/context-overlay.json"),
            self.target_path(".ai/assistant/team/work-registry.json"),
            self.target_path(".ai/assistant/team/active-work-index.json"),
            self.target_path(".ai/assistant/team/backend-contract.json"),
            self.target_path(".ai/assistant/team/task-record-template.json"),
            self.target_path(".ai/assistant/gates/team-collaboration.md"),
            self.target_path(".ai/assistant/templates/team-checkpoint.md"),
            self.target_path(".ai/assistant/templates/team-handoff.md"),
            self.target_path(".ai/assistant/templates/team-decision-record.md"),
            self.target_path(".ai/assistant/templates/team-identity.example.json"),
            self.target_path(".ai/assistant/templates/team-collaboration-review.md"),
            self.target_path(".ai/project/blueprint.md"),
        ]
        flows = self.target_path(".ai/assistant/flows")
        if flows.is_dir():
            paths.extend(sorted(flows.glob("*.md")))
        paths.extend(self.target_path(relpath) for relpath in ["AGENTS.md", *BRIDGE_FILES])

        for path in paths:
            if not path.is_file():
                continue
            text = self.read_text(path)
            for line_number, line in enumerate(text.splitlines(), start=1):
                if PLACEHOLDER_RE.search(line):
                    self.error(
                        "PLACEHOLDER_UNRESOLVED",
                        "unresolved template placeholder remains in accepted adapter surface",
                        f"{self.rel(path)}:{line_number}",
                    )
                if "not defined" in line.lower():
                    self.warn(
                        "UNRESOLVED_NOT_DEFINED",
                        "unresolved 'not defined' marker remains",
                        f"{self.rel(path)}:{line_number}",
                    )

    def check_local_paths(self) -> None:
        scan_paths = self.scan_text_files()
        target_string = str(self.target)
        patterns = [UNIX_LOCAL_PATH_RE, WINDOWS_LOCAL_PATH_RE]
        for path in scan_paths:
            text = self.read_text(path)
            for line_number, line in enumerate(text.splitlines(), start=1):
                raw_matches = [
                    match.group(0)
                    for pattern in patterns
                    for match in pattern.finditer(line)
                ]
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
        roots = [self.target_path(".ai")]
        files = [self.target_path(relpath) for relpath in ["AGENTS.md", *BRIDGE_FILES]]
        for root in roots:
            if not root.is_dir():
                continue
            for path in root.rglob("*"):
                if path.is_file() and not should_skip_path(path):
                    files.append(path)
        return sorted({path for path in files if path.is_file()})

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
            try:
                package = json.loads(package_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
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
            self.error(
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
        directory = self.target_path(".ai/assistant/approvals")
        return sorted(
            path
            for pattern in ("*.md", "*.json")
            for path in directory.glob(pattern)
            if path.name not in {"approval-template.md", "approval-record-template.json"}
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
                except json.JSONDecodeError:
                    continue
                if not isinstance(data, dict):
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

    def check_approval_hash_evidence(self, approval_records: list[Path]) -> None:
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
                    elif sha256(plan_path).lower() != plan_hash:
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
            if not self.diff_ref:
                self.info(
                    "APPROVAL_PATCH_HASH_SKIPPED",
                    "patch hash recorded but --diff-ref was not provided",
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
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.error("PACKAGE_INDEX_JSON", f"invalid change-package index: {exc}", relpath)
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

    def package_snapshot_digest(self, paths: list[str], source: str) -> str | None:
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
                self.change_package_finding(
                    "PACKAGE_SNAPSHOT_FILE",
                    f"snapshot path is not a file: {relpath}",
                    source,
                )
                return None
            digest.update(relpath.replace("\\", "/").encode("utf-8"))
            digest.update(b"\0")
            try:
                digest.update(path.read_bytes())
            except OSError as exc:
                self.change_package_finding(
                    "PACKAGE_SNAPSHOT_READ",
                    f"cannot read snapshot path {relpath}: {exc}",
                    source,
                )
                return None
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
            try:
                index_data = json.loads(index_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
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
        for package in packages:
            source = self.rel(package)
            if self.enforce_change_package and source not in indexed_records:
                self.error(
                    "PACKAGE_NOT_INDEXED",
                    "strictly selected change package is not present in the compact index",
                    source,
                )
            try:
                data = json.loads(package.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self.change_package_finding(
                    "PACKAGE_INVALID_JSON", f"invalid change package: {exc}", source
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
                    elif plan_hash and sha256(plan_path) != plan_hash:
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
                try:
                    approval = json.loads(approval_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    self.change_package_finding(
                        "PACKAGE_APPROVAL_RECORD", f"cannot load approval {relpath}: {exc}", source
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
                if git_resolve_ref(self.target, before) is None:
                    self.change_package_finding(
                        "PACKAGE_BEFORE_REF", f"before revision does not resolve: {before}", source
                    )
                if git_resolve_ref(self.target, after) is None:
                    self.change_package_finding(
                        "PACKAGE_AFTER_REF", f"after revision does not resolve: {after}", source
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
                computed_digest = self.package_snapshot_digest(snapshot_paths, source)
                if computed_digest and recorded_digest != computed_digest:
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

            self.info(
                "PACKAGE_CHECKED",
                f"checked change package {package_id or source}; structural checks do not prove semantic completeness or architecture correctness",
                source,
            )

    def check_framework_baseline(self) -> None:
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

        manifest = parse_manifest(self.target_path(".ai/alatyr.yaml"))
        pack_scalar = manifest.scalars.get(("framework", "pack"))
        framework_pack = pack_scalar.value if pack_scalar else "complete"
        if framework_pack in {"core", "standard"}:
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
                if (
                    not isinstance(relpath, str)
                    or not relpath.startswith("framework/")
                    or Path(relpath).name != relpath[len("framework/") :]
                    or not isinstance(digest, str)
                    or len(digest) != 64
                ):
                    self.error(
                        "FRAMEWORK_PACK_INVENTORY_ENTRY",
                        f"framework pack inventory entry {index} is invalid",
                        ".ai/framework/file-inventory.json",
                    )
                    continue
                expected[Path(relpath).name] = entry
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
                path.name
                for path in target_framework.iterdir()
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
                actual_digest = sha256(target_path)
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
                and sha256(inventory_path) != source_inventory_digest
            ):
                self.framework_drift_detected = True
                self.warn(
                    "FRAMEWORK_PACK_INVENTORY_CONTENT_DRIFT",
                    "installed framework pack inventory differs from source projection",
                    ".ai/framework/file-inventory.json",
                )
            return

        source_files = {
            path.name: path
            for path in source_framework.iterdir()
            if path.is_file() and path.suffix in {".md", ".json"}
        }
        target_files = {
            path.name: path
            for path in target_framework.iterdir()
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
            if sha256(source_files[name]) != sha256(target_files[name]):
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

        text = self.read_text(self.migration_diff)
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


def adapter_health_state(findings: list[Finding]) -> str:
    if any(finding.code in {"TARGET_MISSING", "TARGET_NOT_DIRECTORY"} for finding in findings):
        return "unverified"
    if any(is_blocking_finding(finding) for finding in findings):
        return "blocked"
    if any(finding.level == "warning" for finding in findings):
        return "attention"
    return "ready"


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


def render_summary(findings: list[Finding], *, strict_warnings: bool) -> int:
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
    health = adapter_health_state(findings)
    print(
        f"\nSummary: errors={errors} warnings={warnings} "
        f"blocking_warnings={blocking_warnings} info={infos}"
    )
    print(f"Alatyr adapter health: {health}")
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
    observed_at = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": 2,
        "tool": "validate_target_adapter",
        "target": str(target),
        "evidence": {
            "basis": "current-state-structural",
            "observed_at": observed_at,
            "observed_revision": observed_revision,
            "historical_actions_verified": False,
            "limitation": (
                "Current files do not prove historical installation, update, "
                "approval, or validation actions without dated records."
            ),
        },
        "status": "failed" if exit_code else "passed",
        "adapter_health": {
            "state": adapter_health_state(findings),
            "observed_at": observed_at,
            "observed_revision": observed_revision,
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
        "--config",
        type=Path,
        help=(
            "Optional validator config JSON. Defaults to "
            ".ai/assistant/validator-config.json when that file exists."
        ),
    )
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="Do not fail on unresolved placeholders in adapter surfaces.",
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
        allow_placeholders=args.allow_placeholders,
        allow_local_paths=args.allow_local_path,
        config=config,
        initial_findings=config_findings,
    )
    findings = validator.run()
    payload = findings_payload(
        findings,
        target=args.target.resolve(),
        strict_warnings=args.strict_warnings,
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
    return render_summary(findings, strict_warnings=args.strict_warnings)


if __name__ == "__main__":
    raise SystemExit(main())
