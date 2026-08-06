#!/usr/bin/env python3
"""Validate an installed Alatyr target adapter.

This is an optional helper. It checks structural adapter consistency in a
target repository; it does not install Alatyr Core, approve changes, validate
project business facts, or replace assistant logical integrity review.

The implementation uses only Python standard-library APIs so it can run on
Linux, macOS, and Windows with Python 3.
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


ROOT = Path(__file__).resolve().parents[1]

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
    ".ai/project/contour.md",
    ".ai/project/source-of-truth-registry.md",
    ".ai/assistant/contour.md",
    ".ai/assistant/context-router.json",
    ".ai/assistant/context-profiles.md",
    ".ai/assistant/module-profile.md",
    ".ai/assistant/maturity-profile.md",
    ".ai/assistant/gates/checklist.md",
    ".ai/assistant/approvals/approval-record-template.json",
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
    ".ai/alatyr.yaml",
    ".ai/README.md",
    ".ai/assistant/context-router.json",
]

DEFERRED_BOOTSTRAP = {
    "AGENTS.md",
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
    ("source_of_truth", "context_profiles"),
    ("source_of_truth", "module_profile"),
    ("operations", "help"),
    ("operations", "operation_request"),
    ("operations", "output_contracts"),
    ("maturity", "profile"),
    ("approvals", "directory"),
    ("approvals", "template"),
    ("approvals", "machine_template"),
    ("policies", "source_access"),
    ("policies", "prompt_injection"),
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
        self.check_router()
        if support_profile in {"standard", "full"} or self.target_path(
            ".ai/assistant/operation-catalog.json"
        ).is_file():
            self.check_operation_catalog()
        self.check_discussion_diagrams(manifest)
        self.check_architecture_knowledge(manifest)
        self.check_code_documentation(manifest)
        self.check_consistency_map()
        self.check_ai_infrastructure_router()
        self.check_development_evidence(manifest)
        self.check_team_collaboration(manifest)
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
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ""
        except OSError:
            return ""

    def manifest_support_profile(self, manifest: ManifestData | None) -> str:
        if manifest is None:
            return "full"
        scalar = manifest.scalars.get(("installation", "support_profile"))
        if scalar and scalar.value in SUPPORT_PROFILES:
            return scalar.value
        return "full"

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

    def check_router(self) -> None:
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
                "context router schema 1 should migrate to lazy routing schema 3",
                ".ai/assistant/context-router.json",
            )
        elif schema_version not in {2, 3}:
            self.error(
                "ROUTER_SCHEMA",
                "context router schema_version should be 2 or 3",
                ".ai/assistant/context-router.json",
            )
        if router.get("human_reference") != ".ai/assistant/context-profiles.md":
            self.error(
                "ROUTER_HUMAN_REFERENCE",
                "human_reference should be .ai/assistant/context-profiles.md",
                ".ai/assistant/context-router.json",
            )

        if schema_version in {2, 3}:
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
            for required in REQUIRED_BOOTSTRAP:
                if required not in bootstrap:
                    self.error(
                        "ROUTER_BOOTSTRAP_MISSING",
                        f"bootstrap_context missing {required}",
                        ".ai/assistant/context-router.json",
                    )
            deferred = sorted(set(bootstrap) & DEFERRED_BOOTSTRAP)
            if deferred:
                self.warn(
                    "ROUTER_BOOTSTRAP_BROAD",
                    "bootstrap contains context routed after task selection: "
                    + ", ".join(deferred),
                    ".ai/assistant/context-router.json",
                )

            if not isinstance(router.get("context_budgets"), dict):
                self.error(
                    "ROUTER_BUDGETS_MISSING",
                    "schema 2 or 3 router must define context_budgets",
                    ".ai/assistant/context-router.json",
                )
            if not isinstance(router.get("context_receipt"), dict):
                self.error(
                    "ROUTER_RECEIPT_MISSING",
                    "schema 2 or 3 router must define context_receipt",
                    ".ai/assistant/context-router.json",
                )
            migration_entry = router.get("migration_routing")
            migration = migration_entry
            if schema_version == 3 and isinstance(migration_entry, dict):
                migration = self.load_context_descriptor(
                    migration_entry,
                    "target-migration-routing",
                    "migration_routing",
                )
            if not isinstance(migration, dict):
                self.error(
                    "ROUTER_MIGRATION_MISSING",
                    "schema 2 or 3 router must define migration-first routing",
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

        for profile in CANONICAL_PROFILES:
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
        if router.get("schema_version") != 3:
            profiles = router.get("profiles")
            return profiles if isinstance(profiles, dict) else {}
        index = router.get("profile_index")
        if not isinstance(index, dict):
            self.error(
                "ROUTER_PROFILE_INDEX",
                "schema 3 router must define profile_index",
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

    def check_consistency_map(self) -> None:
        relpath = ".ai/project/consistency-map.json"
        path = self.target_path(relpath)
        data = self.load_json_object(path, "CONSISTENCY_MAP")
        if data is None:
            return
        if data.get("schema_version") != 1:
            self.error("CONSISTENCY_MAP_SCHEMA", "schema_version should be 1", relpath)
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
            level = node.get("level")
            if not is_placeholder(level) and level not in CONSISTENCY_LEVELS:
                self.error(
                    "CONSISTENCY_MAP_NODE_LEVEL",
                    f"{label}.level is invalid: {level}",
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
        model_key = ("team_collaboration", "operating_model")
        source_model_key = ("source_of_truth", "team_operating_model")
        registry_key = ("team_collaboration", "work_registry")
        model_scalar = manifest.scalars.get(model_key) if manifest else None
        if not model_scalar and manifest:
            model_scalar = manifest.scalars.get(source_model_key)
        registry_scalar = manifest.scalars.get(registry_key) if manifest else None
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
        model_path = self.target_path(model_relpath)
        registry_path = self.target_path(registry_relpath)

        if not model_path.exists() and not registry_path.exists():
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

        registry = self.load_json_object(registry_path, "TEAM_REGISTRY")
        if registry is None:
            return
        if registry.get("schema_version") != 1:
            self.error(
                "TEAM_REGISTRY_SCHEMA",
                "schema_version should be 1",
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
            "operating_model",
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

        model_text = self.read_text(model_path)
        actor_ids = {
            match.group(1)
            for match in re.finditer(r"^### Actor `([^`]+)`$", model_text, re.MULTILINE)
            if not is_placeholder(match.group(1))
        }
        priority_ids = {
            match.group(1)
            for match in re.finditer(
                r"^### Priority `([^`]+)`$",
                model_text,
                re.MULTILINE,
            )
            if not is_placeholder(match.group(1))
        }

        tasks = registry.get("tasks")
        if not isinstance(tasks, list):
            self.error(
                "TEAM_REGISTRY_TASKS",
                "tasks must be a list",
                registry_relpath,
            )
            return

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
            "goal",
            "priority",
            "priority_rationale",
            "priority_decided_by",
            "status",
            "owner_actor_id",
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
            if not isinstance(task, dict):
                self.error(
                    "TEAM_TASK_SHAPE",
                    f"{label} must be an object",
                    registry_relpath,
                )
                continue
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
            check_actor(task.get("priority_decided_by"), f"{label}.priority_decided_by")
            reviewers = task.get("reviewer_actor_ids")
            if isinstance(reviewers, list):
                for reviewer_index, reviewer in enumerate(reviewers):
                    check_actor(
                        reviewer,
                        f"{label}.reviewer_actor_ids[{reviewer_index}]",
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
                    for field in ["actor_id", "claimed_at", "base_revision"]:
                        if not concrete(claim.get(field)):
                            self.error(
                                "TEAM_ACTIVE_CLAIM_INCOMPLETE",
                                f"{label}.claim.{field} is required for an active claim",
                                registry_relpath,
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
            if overlay.get("schema_version") != 1:
                self.error(
                    "TEAM_CONTEXT_OVERLAY_SCHEMA",
                    "schema_version should be 1",
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
                for required_path in [
                    ".ai/framework/team-collaboration.md",
                    model_relpath,
                    registry_relpath,
                    ".ai/assistant/gates/team-collaboration.md",
                ]:
                    if required_path not in required_context:
                        self.error(
                            "TEAM_CONTEXT_OVERLAY_PATH",
                            f"team-active required_context is missing {required_path}",
                            descriptor,
                        )

    def load_json_object(self, path: Path, code_prefix: str) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.error(f"{code_prefix}_INVALID_JSON", str(exc), self.rel(path))
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
            if ".ai/assistant/context-router.json" not in text:
                level = self.error if relpath == "AGENTS.md" else self.warn
                level(
                    "BOOTSTRAP_CONTEXT_ROUTER_MISSING",
                    "bootstrap references do not include .ai/assistant/context-router.json",
                    relpath,
                )
            if ".ai/README.md" not in text:
                level = self.error if relpath == "AGENTS.md" else self.warn
                level(
                    "BOOTSTRAP_AREA_MAP_MISSING",
                    "bootstrap references do not include .ai/README.md",
                    relpath,
                )

        gates = self.target_path(".ai/assistant/gates/checklist.md")
        if gates.is_file() and ".ai/assistant/context-router.json" not in self.read_text(gates):
            self.error(
                "GATE_CONTEXT_ROUTER_MISSING",
                "gate checklist bootstrap does not mention context-router.json",
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
            self.target_path(".ai/assistant/module-profile.md"),
            self.target_path(".ai/assistant/maturity-profile.md"),
            self.target_path(".ai/assistant/gates/checklist.md"),
            self.target_path(".ai/assistant/operation-catalog.json"),
            self.target_path(".ai/project/team-operating-model.md"),
            self.target_path(".ai/assistant/team/context-overlay.json"),
            self.target_path(".ai/assistant/team/work-registry.json"),
            self.target_path(".ai/assistant/gates/team-collaboration.md"),
            self.target_path(".ai/assistant/templates/team-checkpoint.md"),
            self.target_path(".ai/assistant/templates/team-handoff.md"),
            self.target_path(".ai/assistant/templates/team-decision-record.md"),
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
    if any(finding.level == "error" for finding in findings):
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
    health = adapter_health_state(findings)
    print(f"\nSummary: errors={errors} warnings={warnings} info={infos}")
    print(f"Alatyr adapter health: {health}")
    repairs = prioritized_repair_operations(findings)
    if repairs:
        print("Suggested repair operations: " + ", ".join(repairs))

    if errors:
        return 1
    if strict_warnings and warnings:
        return 1
    return 0


def result_code(findings: list[Finding], *, strict_warnings: bool) -> int:
    errors = sum(1 for finding in findings if finding.level == "error")
    warnings = sum(1 for finding in findings if finding.level == "warning")
    if errors:
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
            "machine-readable JSON approval records bound to --diff-ref."
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
    validator = Validator(
        args.target,
        framework_source=args.framework_source,
        diff_ref=args.diff_ref,
        approval_records=args.approval_record,
        enforce_approval_scope=args.enforce_approval_scope,
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
