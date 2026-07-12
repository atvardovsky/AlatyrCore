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

REQUIRED_BOOTSTRAP = [
    "AGENTS.md",
    ".ai/alatyr.yaml",
    ".ai/README.md",
    ".ai/assistant/context-router.json",
    ".ai/assistant/context-profiles.md",
    ".ai/assistant/module-profile.md",
    ".ai/project/contour.md",
    ".ai/project/source-of-truth-registry.md",
    ".ai/assistant/contour.md",
]

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
        allow_placeholders: bool,
        allow_local_paths: list[str],
    ) -> None:
        self.target = target.resolve()
        self.framework_source = framework_source.resolve() if framework_source else None
        self.diff_ref = diff_ref
        self.allow_placeholders = allow_placeholders
        self.allow_local_paths = allow_local_paths
        self.findings: list[Finding] = []

    def error(self, code: str, message: str, path: str | None = None) -> None:
        self.findings.append(Finding("error", code, message, path))

    def warn(self, code: str, message: str, path: str | None = None) -> None:
        self.findings.append(Finding("warning", code, message, path))

    def info(self, code: str, message: str, path: str | None = None) -> None:
        self.findings.append(Finding("info", code, message, path))

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
        self.check_bootstrap_references()
        self.check_placeholders()
        self.check_local_paths()
        checker_files, checker_commands = self.discover_checkers(manifest)
        self.check_checker_claims(checker_files, checker_commands)
        self.check_approval_scope()
        self.check_framework_baseline()
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
        if router.get("human_reference") != ".ai/assistant/context-profiles.md":
            self.error(
                "ROUTER_HUMAN_REFERENCE",
                "human_reference should be .ai/assistant/context-profiles.md",
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
            if ".ai/assistant/context-profiles.md" not in text:
                level = self.error if relpath == "AGENTS.md" else self.warn
                level(
                    "BOOTSTRAP_CONTEXT_PROFILES_MISSING",
                    "bootstrap references do not include .ai/assistant/context-profiles.md",
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
        coverage_terms = {
            "context-router": "context-router coverage",
            "placeholder": "placeholder coverage",
            "local path": "local path leakage coverage",
            "stale": "stale checker-claim coverage",
            "manifest": "manifest coverage",
        }
        for term, label in coverage_terms.items():
            if term not in checker_text.lower():
                self.warn(
                    "TARGET_CHECKER_COVERAGE_GAP",
                    f"target-local checker may be missing {label}",
                )

    def check_approval_scope(self) -> None:
        if not self.diff_ref:
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

        approval_records = sorted(self.target_path(".ai/assistant/approvals").glob("*.md"))
        if not approval_records:
            self.warn(
                "APPROVAL_RECORD_MISSING",
                "protected adapter surfaces changed but no approval records exist",
            )
            return

        approval_text = "\n".join(self.read_text(path) for path in approval_records)
        for required in ["Plan hash:", "Allowed files or surfaces:"]:
            if required not in approval_text:
                self.warn(
                    "APPROVAL_RECORD_FIELD_MISSING",
                    f"approval records do not include {required}",
                    ".ai/assistant/approvals",
                )
        for changed in protected:
            if changed in approval_text or covers_with_wildcard(changed, approval_text):
                continue
            self.warn(
                "APPROVAL_SCOPE_MISMATCH",
                f"changed protected file not named in approval records: {changed}",
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
            self.warn(
                "FRAMEWORK_FILE_MISSING",
                f"installed framework is missing source file {name}",
                f".ai/framework/{name}",
            )
        for name in sorted(set(target_files) - set(source_files)):
            self.warn(
                "FRAMEWORK_FILE_EXTRA",
                f"installed framework has file not present in source baseline: {name}",
                f".ai/framework/{name}",
            )
        for name in sorted(set(source_files) & set(target_files)):
            if sha256(source_files[name]) != sha256(target_files[name]):
                self.warn(
                    "FRAMEWORK_FILE_DRIFT",
                    f"installed framework file differs from source baseline: {name}",
                    f".ai/framework/{name}",
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


def is_placeholder(value: str) -> bool:
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


def covers_with_wildcard(path: str, approval_text: str) -> bool:
    if ".ai/*" in approval_text and path.startswith(".ai/"):
        return True
    parts = path.split("/")
    for index in range(1, len(parts)):
        prefix = "/".join(parts[:index])
        if f"{prefix}/*" in approval_text:
            return True
    return False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    args = parser.parse_args()

    validator = Validator(
        args.target,
        framework_source=args.framework_source,
        diff_ref=args.diff_ref,
        allow_placeholders=args.allow_placeholders,
        allow_local_paths=args.allow_local_path,
    )
    findings = validator.run()
    return render_summary(findings, strict_warnings=args.strict_warnings)


if __name__ == "__main__":
    raise SystemExit(main())
