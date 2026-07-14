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
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple


ROOT = Path(__file__).resolve().parents[1]

PathKey = Tuple[str, ...]

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

REQUIRED_FILES = [
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
    ".ai/assistant/flows/adapter-recheck.flow.md",
    ".ai/assistant/flows/operation-routing.flow.md",
    ".ai/assistant/templates/adapter-output-contracts.md",
]

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
    ("bridges", "capability_matrix"),
    ("approvals", "directory"),
    ("approvals", "template"),
    ("policies", "source_access"),
    ("policies", "prompt_injection"),
}

MANIFEST_PATH_SCALARS: set[PathKey] = {
    ("framework", "rule_registry"),
    ("source_of_truth", "project_contour"),
    ("source_of_truth", "registry"),
    ("source_of_truth", "consistency_map"),
    ("source_of_truth", "assistant_contour"),
    ("source_of_truth", "context_router"),
    ("source_of_truth", "context_profiles"),
    ("source_of_truth", "module_profile"),
    ("operations", "help"),
    ("operations", "operation_request"),
    ("operations", "output_contracts"),
    ("ai_infrastructure", "router"),
    ("ai_infrastructure", "inventory"),
    ("ai_infrastructure", "adaptation_record"),
    ("maturity", "profile"),
    ("bridges", "capability_matrix"),
    ("approvals", "directory"),
    ("approvals", "template"),
    ("policies", "source_access"),
    ("policies", "prompt_injection"),
}

UNRESOLVED_WORDS = {
    "",
    "not defined",
    "undefined",
    "unknown",
    "todo",
    "tbd",
    "n/a",
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
SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
UNAVAILABLE_HASH_MARKERS = {
    "not available",
    "not available with reason",
    "unavailable",
    "not recorded",
    "none",
}
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
AI_INFRASTRUCTURE_ROUTES = {
    "inventory",
    "use-existing",
    "adapt-import",
    "gate-checker-change",
    "tool-mcp-change",
    "bridge-wrapper-change",
}
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

    def to_json(self) -> dict[str, str]:
        payload = {
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }
        if self.path:
            payload["path"] = self.path
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
class Frame:
    indent: int
    key: str


@dataclass(frozen=True)
class Scalar:
    value: str
    line: int


@dataclass
class ManifestData:
    scalars: dict[PathKey, Scalar]
    lists: dict[PathKey, list[Scalar]]
    parse_failures: list[str]


class Validator:
    def __init__(
        self,
        target: Path,
        *,
        framework_source: Path | None,
        diff_ref: str | None,
        approval_records: list[Path],
        migration_diff: Path | None,
        allow_placeholders: bool,
        allow_local_paths: list[str],
        config: AdapterValidatorConfig,
        initial_findings: list[Finding] | None = None,
    ) -> None:
        self.target = target.resolve()
        self.framework_source = framework_source.resolve() if framework_source else None
        self.diff_ref = diff_ref
        self.approval_records = [
            path.resolve() if path.is_absolute() else (self.target / path).resolve()
            for path in approval_records
        ]
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

        self.check_required_files()
        manifest = self.check_manifest()
        self.check_router()
        self.check_consistency_map()
        self.check_ai_infrastructure_router()
        self.check_bootstrap_references()
        self.check_placeholders()
        self.check_local_paths()
        checker_files, checker_commands = self.discover_checkers(manifest)
        self.check_checker_claims(checker_files, checker_commands)
        self.check_approval_scope()
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

    def check_required_files(self) -> None:
        for relpath in REQUIRED_FILES:
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

        for key in sorted(MANIFEST_REQUIRED_SCALARS):
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
                "context router schema 1 should migrate to compact routing schema 2",
                ".ai/assistant/context-router.json",
            )
        elif schema_version != 2:
            self.error(
                "ROUTER_SCHEMA",
                "context router schema_version should be 2",
                ".ai/assistant/context-router.json",
            )
        if router.get("human_reference") != ".ai/assistant/context-profiles.md":
            self.error(
                "ROUTER_HUMAN_REFERENCE",
                "human_reference should be .ai/assistant/context-profiles.md",
                ".ai/assistant/context-router.json",
            )

        if schema_version == 2:
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
                    "schema 2 router must define context_budgets",
                    ".ai/assistant/context-router.json",
                )
            if not isinstance(router.get("context_receipt"), dict):
                self.error(
                    "ROUTER_RECEIPT_MISSING",
                    "schema 2 router must define context_receipt",
                    ".ai/assistant/context-router.json",
                )

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

        profiles = router.get("profiles")
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
        if data.get("schema_version") != 1:
            self.error("AI_ROUTER_SCHEMA", "schema_version should be 1", relpath)
        if data.get("router_kind") != "target-ai-infrastructure-router":
            self.error(
                "AI_ROUTER_KIND",
                "router_kind should be target-ai-infrastructure-router",
                relpath,
            )
        routing_order = expect_string_list(
            data.get("routing_order"), self, "AI_ROUTER_ORDER", relpath
        )
        if set(routing_order) != AI_INFRASTRUCTURE_ROUTES:
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

        routes = data.get("routes")
        if not isinstance(routes, dict):
            self.error("AI_ROUTER_ROUTE_SHAPE", "routes must be an object", relpath)
            routes = {}
        for route_name in AI_INFRASTRUCTURE_ROUTES:
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
            broad_marker = "`.ai/framework`,\n   `.ai/project`"
            if broad_marker in text or "all `.ai/framework`" in text:
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
        adapter_text_files = self.scan_text_files()
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
        protected = [path for path in changed_files if is_protected_surface(path)]
        if not protected:
            self.info("DIFF_SCOPE_CLEAN", "no protected adapter surfaces changed")
            return
        if not approval_records:
            self.warn(
                "APPROVAL_RECORD_MISSING",
                "protected adapter surfaces changed but no approval records were supplied or found",
            )
            return

        applicable: list[Path] = []
        for record in approval_records:
            text = self.read_text(record)
            allowed = extract_list_field(text, "Allowed files or surfaces:")
            excluded = extract_list_field(text, "Excluded files or surfaces:")
            covered = [path for path in protected if scope_entries_cover(path, allowed)]
            if covered:
                applicable.append(record)
            for changed in protected:
                if scope_entries_cover(changed, excluded):
                    self.warn(
                        "APPROVAL_SCOPE_EXCLUDED",
                        f"changed protected file is explicitly excluded: {changed}",
                        self.rel(record),
                    )

        self.check_approval_hash_evidence(applicable)
        for changed in protected:
            if any(
                scope_entries_cover(
                    changed,
                    extract_list_field(self.read_text(record), "Allowed files or surfaces:"),
                )
                for record in applicable
            ):
                continue
            self.warn(
                "APPROVAL_SCOPE_MISMATCH",
                f"changed protected file is not covered by an explicit approval scope: {changed}",
            )

    def resolve_approval_records(self) -> list[Path]:
        if self.approval_records:
            records: list[Path] = []
            for record in self.approval_records:
                try:
                    record.relative_to(self.target)
                except ValueError:
                    self.warn(
                        "APPROVAL_RECORD_OUTSIDE_TARGET",
                        "supplied approval record must be inside the target repository",
                        str(record),
                    )
                    continue
                if not record.is_file():
                    self.warn(
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
            for path in directory.glob("*.md")
            if path.name != "approval-template.md"
        )

    def check_approval_record_shape(self, approval_records: list[Path]) -> None:
        for record in approval_records:
            text = self.read_text(record)
            relpath = self.rel(record)
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
                    self.warn(
                        "APPROVAL_RECORD_FIELD_MISSING",
                        f"approval record does not include {required}",
                        relpath,
                    )
            if "Evidence classification: `historical-record`" not in text:
                self.warn(
                    "APPROVAL_RECORD_EVIDENCE_CLASS",
                    "approval record must identify itself as historical-record evidence",
                    relpath,
                )
            for field in ["Allowed files or surfaces:"]:
                values = extract_list_field(text, field)
                if not values:
                    self.warn(
                        "APPROVAL_RECORD_SCOPE_EMPTY",
                        f"approval record has no explicit entries under {field}",
                        relpath,
                    )
                for value in values:
                    if is_placeholder(value) or not is_target_scope_pattern(value):
                        self.warn(
                            "APPROVAL_RECORD_SCOPE_INVALID",
                            f"{field} contains an unresolved or unsafe target pattern: {value}",
                            relpath,
                        )

    def check_approval_hash_evidence(self, approval_records: list[Path]) -> None:
        for record in approval_records:
            text = self.read_text(record)
            relpath = self.rel(record)
            plan_hash = normalize_hash_field(extract_field(text, "Plan hash:"))
            plan_file = extract_field(text, "Approved plan file:")
            patch_hash = normalize_hash_field(extract_field(text, "Patch hash:"))

            if "Patch changed after approval:" in text:
                patch_changed = extract_field(text, "Patch changed after approval:").lower()
                if patch_changed.startswith("yes"):
                    self.warn(
                        "APPROVAL_PATCH_CHANGED",
                        "approval record says the patch changed after approval",
                        relpath,
                    )
            if "Implementation stayed within approved scope:" in text:
                within_scope = extract_field(
                    text, "Implementation stayed within approved scope:"
                ).lower()
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
            elif "Plan hash:" in text:
                self.info(
                    "APPROVAL_PLAN_HASH_NOT_VERIFIABLE",
                    "plan hash is unavailable or non-deterministic",
                    relpath,
                )

            if not patch_hash:
                if "Patch hash:" in text:
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


def parse_manifest(path: Path) -> ManifestData:
    scalars: dict[PathKey, Scalar] = {}
    lists: dict[PathKey, list[Scalar]] = {}
    failures: list[str] = []
    stack: list[Frame] = []

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line:
            failures.append(f"line {line_number}: tabs are not allowed")
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2:
            failures.append(f"line {line_number}: indentation should use two spaces")
            continue

        content = raw_line[indent:]
        stack = [frame for frame in stack if frame.indent < indent]
        parent = tuple(frame.key for frame in stack)
        try:
            if content.startswith("- "):
                item = content[2:].strip()
                lists.setdefault(parent, [])
                if ":" in item:
                    key, value = parse_key_value(item, line_number)
                    lists[parent].append(Scalar("<mapping>", line_number))
                    stack.append(Frame(indent, "[]"))
                    child_path = parent + ("[]", key)
                    if value:
                        scalars[child_path] = Scalar(value, line_number)
                    else:
                        stack.append(Frame(indent, key))
                else:
                    lists[parent].append(Scalar(strip_quotes(item), line_number))
                continue
            key, value = parse_key_value(content, line_number)
            current_path = parent + (key,)
            if value:
                scalars[current_path] = Scalar(value, line_number)
            else:
                stack.append(Frame(indent, key))
        except AssertionError as exc:
            failures.append(str(exc))

    return ManifestData(scalars=scalars, lists=lists, parse_failures=failures)


def parse_key_value(content: str, line_number: int) -> tuple[str, str]:
    if ":" not in content:
        raise AssertionError(f"line {line_number}: expected key/value syntax")
    key, value = content.split(":", 1)
    key = key.strip()
    if not key:
        raise AssertionError(f"line {line_number}: empty key")
    return key, strip_quotes(value)


def strip_quotes(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in "'\"":
        return stripped[1:-1]
    return stripped


def dotted(path: PathKey) -> str:
    return ".".join(path)


def is_unresolved_value(value: str) -> bool:
    normalized = value.strip().strip("\"'").lower()
    return normalized in UNRESOLVED_WORDS or is_placeholder(value)


def is_placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    return stripped.startswith("{") and stripped.endswith("}")


def expect_string_list(
    value: Any,
    validator: Validator,
    code: str,
    path: str,
    *,
    label: str = "value",
) -> list[str]:
    if not isinstance(value, list) or not value:
        validator.error(code, f"{label} must be a non-empty list", path)
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            validator.error(code, f"{label}[{index}] must be a non-empty string", path)
            continue
        result.append(item)
    return result


def duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return sorted(repeated)


def should_skip_path(path: Path) -> bool:
    skip_parts = {".git", "node_modules", "__pycache__", "dist", "build"}
    return any(part in skip_parts for part in path.parts)


def is_target_relative_path(value: str) -> bool:
    path = Path(value)
    if path.is_absolute():
        return False
    return ".." not in path.parts


def extract_field(text: str, label: str) -> str:
    for line in text.splitlines():
        if line.startswith(label):
            return strip_backticks(line[len(label) :].strip())
    return ""


def strip_backticks(value: str) -> str:
    stripped = strip_quotes(value)
    if len(stripped) >= 2 and stripped[0] == stripped[-1] == "`":
        return stripped[1:-1]
    return stripped


def normalize_hash_field(value: str) -> str:
    normalized = strip_backticks(value).strip()
    if not normalized or is_placeholder(normalized):
        return ""
    lowered = normalized.lower()
    if any(marker in lowered for marker in UNAVAILABLE_HASH_MARKERS):
        return ""
    if SHA256_RE.match(normalized):
        return normalized.lower()
    return ""


def git_changed_files(target: Path, diff_ref: str) -> list[str] | None:
    commands = [
        ["git", "diff", "--name-only", f"{diff_ref}...HEAD"],
        ["git", "diff", "--name-only", diff_ref],
    ]
    for command in commands:
        result = subprocess.run(
            command,
            cwd=target,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return None


def git_diff_patch(target: Path, diff_ref: str) -> str | None:
    commands = [
        ["git", "diff", "--binary", f"{diff_ref}...HEAD"],
        ["git", "diff", "--binary", diff_ref],
    ]
    for command in commands:
        result = subprocess.run(
            command,
            cwd=target,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            return result.stdout
    return None


def is_protected_surface(path: str) -> bool:
    protected_prefixes = [
        ".ai/",
        ".github/copilot-instructions.md",
        ".github/prompts/",
        ".cursor/",
        ".devin/",
        ".windsurf/",
        ".agents/",
    ]
    protected_files = {
        "AGENTS.md",
        "AI_ASSISTANTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        "CODEOWNERS",
        ".cursorrules",
        ".windsurfrules",
    }
    return path in protected_files or any(path.startswith(prefix) for prefix in protected_prefixes)


def extract_list_field(text: str, label: str) -> list[str]:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != label:
            continue
        values: list[str] = []
        for candidate in lines[index + 1 :]:
            stripped = candidate.strip()
            if not stripped:
                if values:
                    break
                continue
            if not stripped.startswith("- "):
                break
            value = strip_backticks(stripped[2:].strip())
            if value.lower() not in {"none", "not applicable", "not-applicable"}:
                values.append(value)
        return values
    return []


def is_target_scope_pattern(value: str) -> bool:
    if not value or value.startswith(("/", "\\")):
        return False
    if re.match(r"^[A-Za-z]:[\\/]", value):
        return False
    normalized = value.replace("\\", "/")
    return ".." not in normalized.split("/")


def scope_entries_cover(path: str, entries: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    for entry in entries:
        if is_placeholder(entry) or not is_target_scope_pattern(entry):
            continue
        pattern = entry.replace("\\", "/")
        if normalized == pattern or fnmatch.fnmatchcase(normalized, pattern):
            return True
    return False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head_revision(target: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=target,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    revision = result.stdout.strip()
    return revision or None


def markdown_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            current = heading.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return sections


def section_items(lines: list[str]) -> list[str]:
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        value = stripped[2:].strip()
        if value in {"none", "`none`"}:
            continue
        items.append(value.strip("`"))
    return items


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


def render_summary(findings: list[Finding], *, strict_warnings: bool) -> int:
    order = {"error": 0, "warning": 1, "info": 2}
    for finding in sorted(findings, key=lambda item: (order[item.level], item.code, item.path or "")):
        print(finding.render())

    errors = sum(1 for finding in findings if finding.level == "error")
    warnings = sum(1 for finding in findings if finding.level == "warning")
    infos = sum(1 for finding in findings if finding.level == "info")
    print(f"\nSummary: errors={errors} warnings={warnings} info={infos}")

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
    return {
        "schema_version": 2,
        "tool": "validate_target_adapter",
        "target": str(target),
        "evidence": {
            "basis": "current-state-structural",
            "observed_revision": git_head_revision(target),
            "historical_actions_verified": False,
            "limitation": (
                "Current files do not prove historical installation, update, "
                "approval, or validation actions without dated records."
            ),
        },
        "status": "failed" if exit_code else "passed",
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
            "Optional git ref used to compare protected changed files with "
            "approval-record scope."
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
