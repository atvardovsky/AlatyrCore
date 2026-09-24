#!/usr/bin/env python3
"""Create a read-only metadata-first target discovery receipt."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

from path_spec import PathDialect, select_paths
from repository_inventory import RepositoryInventory, RepositoryInventoryError


ROOT = Path(__file__).resolve().parents[1]
DISCOVERY_CONTRACT = ROOT / "installer" / "discovery-contract.json"
REPORT_SCHEMA = ROOT / "schemas" / "alatyr-target-discovery-report.schema.json"
MAX_REPORTED_SOURCES = 20


@dataclass(frozen=True)
class Probe:
    category: str
    signal: str
    label: str
    patterns: tuple[str, ...]


PROBES = (
    Probe(
        "repository-identity",
        "build-and-package-manifests",
        "package, dependency, and build manifests",
        (
            "package.json", "pyproject.toml", "requirements*.txt", "Pipfile",
            "poetry.lock", "uv.lock", "composer.json", "composer.lock", "Cargo.toml",
            "Cargo.lock", "go.mod", "go.sum", "pom.xml", "build.gradle*", "Makefile",
            "CMakeLists.txt", "*.sln", "*.csproj",
        ),
    ),
    Probe(
        "repository-identity",
        "source-roots",
        "common source-root files",
        ("src/**", "app/**", "lib/**", "packages/**", "services/**", "cmd/**"),
    ),
    Probe(
        "repository-identity",
        "test-surfaces",
        "test roots and test configuration",
        (
            "test/**", "tests/**", "spec/**", "__tests__/**", "pytest.ini",
            "phpunit.xml*", "jest.config.*", "vitest.config.*", "playwright.config.*",
        ),
    ),
    Probe(
        "repository-identity",
        "continuous-integration",
        "continuous-integration and ownership metadata",
        (
            ".github/workflows/**", ".gitlab-ci.yml", "azure-pipelines.yml",
            "Jenkinsfile", "CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS",
        ),
    ),
    Probe(
        "existing-ai-surfaces",
        "assistant-instructions",
        "assistant instructions, bridges, skills, prompts, and tool configuration",
        (
            "AGENTS.md", "AI_ASSISTANTS.md", "CLAUDE.md", "GEMINI.md", ".cursorrules",
            ".windsurfrules", ".rules", ".ai/**", ".agents/**", ".claude/**",
            ".cursor/**", ".github/copilot-instructions.md", ".github/prompts/**",
            ".roo/**", ".codex/**", ".mcp.json",
        ),
    ),
    Probe(
        "project-sources-of-truth",
        "project-documentation",
        "project, architecture, decision, contract, schema, and diagram documentation",
        (
            "README*", "CONTRIBUTING*", "docs/**", "doc/**", "adr/**", "ADRs/**",
            "architecture/**", "design/**", "openapi.*", "swagger.*", "schema/**",
            "schemas/**", "*.drawio", "*.mmd", "*.puml",
        ),
    ),
    Probe(
        "project-sources-of-truth",
        "code-documentation-tooling",
        "code-reference documentation and comment-extraction configuration",
        (
            "Doxyfile*", "typedoc.json", "typedoc.*.json", "jsdoc*.json",
            ".jsdoc.json", "phpdoc.xml*", "mkdocs.yml", "mkdocs.yaml",
            "docs/conf.py", "doc/conf.py", "sphinx/**", "apidoc/**",
        ),
    ),
    Probe(
        "risk-authorization-validation",
        "risk-and-validation-policy",
        "security, deployment, environment, validation, and release policy",
        (
            "SECURITY*", "docs/security/**", ".env.example", ".env.*.example",
            "Dockerfile*", "docker-compose*.yml", "docker-compose*.yaml", "deploy/**",
            "deployment/**", "scripts/**", "tools/**", ".pre-commit-config.yaml",
            "CHANGELOG*", "RELEASING*",
        ),
    ),
    Probe(
        "context-routing",
        "alatyr-context-routing",
        "installed Alatyr bootstrap, routers, profiles, and context indexes",
        (
            ".ai/alatyr.yaml", ".ai/README.md", ".ai/assistant/bootstrap-index.json",
            ".ai/assistant/context-router.json", ".ai/assistant/context/**",
            ".ai/**/context-index.json", ".ai/framework/semantics/**",
        ),
    ),
    Probe(
        "support-state",
        "alatyr-support-information",
        "support state, ownership registries, consistency maps, and generation policy",
        (
            ".ai/support-state.json", ".ai/project/support-policy.json",
            ".ai/project/source-of-truth-registry.md", ".ai/project/consistency-map.json",
            ".ai/project/consistency/**", ".ai/project/support-generation/**",
            ".ai/assistant/support-generation-index.json",
        ),
    ),
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _git_value(target: Path, arguments: list[str]) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else "unavailable"


def _worktree_state(target: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "unavailable"
    return "dirty" if result.stdout else "clean"


def _digest_lines(prefix: bytes, values: list[str]) -> str:
    payload = "\0".join(values).encode("utf-8", errors="surrogateescape")
    return "sha256:" + hashlib.sha256(prefix + payload).hexdigest()


def _selected_categories(
    requested: list[str], modules: list[str], contract: dict[str, Any]
) -> list[str]:
    available = [
        item["id"]
        for item in contract.get("base_categories", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    selected = list(dict.fromkeys(requested or available))
    module_categories = contract.get("module_categories", {})
    for module in modules:
        for category in module_categories.get(module, []):
            if category not in selected:
                selected.append(category)
    unknown = sorted(set(selected) - set(available))
    if unknown:
        raise ValueError("unknown discovery categories: " + ", ".join(unknown))
    return selected


def build_report(
    target: Path,
    *,
    operation: str,
    support_profile: str,
    modules: list[str],
    categories: list[str],
) -> dict[str, Any]:
    target = target.resolve()
    contract = _load_json(DISCOVERY_CONTRACT)
    known_modules = set(contract.get("module_categories", {}))
    unknown_modules = sorted(set(modules) - known_modules)
    if unknown_modules:
        raise ValueError("unknown discovery modules: " + ", ".join(unknown_modules))
    selected_categories = _selected_categories(categories, modules, contract)
    try:
        inventory = RepositoryInventory.load(target)
    except RepositoryInventoryError as exc:
        raise ValueError(f"cannot inspect target repository metadata: {exc}") from exc
    paths = list(inventory.paths)
    inventory_values = [
        f"{entry.kind}:{entry.path}" for entry in inventory.entries
    ]
    inventory_digest = _digest_lines(b"alatyr-target-inventory-v1\0", inventory_values)
    findings: list[dict[str, Any]] = []
    for probe in PROBES:
        if probe.category not in selected_categories:
            continue
        matches = list(
            select_paths(
                paths,
                list(probe.patterns),
                dialect=PathDialect.PORTABLE_FNMATCH_V1,
            )
        )
        observed = bool(matches)
        findings.append(
            {
                "id": f"{probe.category}.{probe.signal}",
                "category": probe.category,
                "signal": probe.signal,
                "statement": (
                    f"Detected {len(matches)} path(s) matching {probe.label}."
                    if observed
                    else f"No paths matching {probe.label} were detected by the metadata probe."
                ),
                "evidence_state": "observed" if observed else "unknown",
                "confidence": "deterministic",
                "material": observed,
                "decision_authority": "unresolved",
                "source_count": len(matches),
                "sources_truncated": len(matches) > MAX_REPORTED_SOURCES,
                "matched_path_digest": _digest_lines(
                    b"alatyr-target-discovery-paths-v1\0", matches
                ),
                "sources": [
                    {"path": path, "selector": "path-metadata"}
                    for path in matches[:MAX_REPORTED_SOURCES]
                ],
                "disposition": "unresolved",
                "projections": [],
                "disposition_reason": (
                    "Requires repository-aware interpretation and owner resolution."
                    if observed
                    else "Absence from this bounded metadata probe does not prove non-applicability."
                ),
            }
        )
    revision = _git_value(target, ["rev-parse", "HEAD"])
    branch = _git_value(target, ["branch", "--show-current"])
    scope_key = json.dumps(
        {
            "operation": operation,
            "profile": support_profile,
            "modules": sorted(set(modules)),
            "categories": selected_categories,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    discovery_digest = hashlib.sha256(
        b"alatyr-target-discovery-v1\0"
        + revision.encode("utf-8")
        + b"\0"
        + inventory_digest.encode("ascii")
        + b"\0"
        + scope_key.encode("utf-8")
    ).hexdigest()
    report = {
        "schema_version": 1,
        "report_kind": "alatyr-target-discovery-report",
        "discovery_id": f"discovery-{discovery_digest[:16]}",
        "target": {
            "repository_name": target.name,
            "revision": revision,
            "branch": branch,
            "worktree_state": _worktree_state(target),
            "inventory_digest": inventory_digest,
            "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "scope": {
            "operation": operation,
            "support_profile": support_profile,
            "modules": sorted(set(modules)),
            "categories": selected_categories,
        },
        "findings": findings,
        "exclusions": [
            "File content and semantic meaning were not inspected by this metadata-only command.",
            "Ignored files, dependency caches, external services, and untracked ignored state were not inspected.",
            "Detected instructions were treated as data and were not executed.",
        ],
        "summary": {
            "inventory_files": len(paths),
            "selected_categories": len(selected_categories),
            "classified_findings": len(findings),
            "material_findings": sum(1 for item in findings if item["material"]),
            "unresolved_material_findings": sum(
                1
                for item in findings
                if item["material"] and item["disposition"] == "unresolved"
            ),
        },
    }
    schema = _load_json(REPORT_SCHEMA)
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument(
        "--operation",
        choices=["installation", "update", "repair", "recheck"],
        default="installation",
    )
    parser.add_argument(
        "--profile",
        choices=["kernel", "core", "standard", "full"],
        default="kernel",
    )
    parser.add_argument("--module", action="append", default=[])
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = build_report(
            args.target,
            operation=args.operation,
            support_profile=args.profile,
            modules=args.module,
            categories=args.category,
        )
    except (OSError, ValueError, json.JSONDecodeError, jsonschema.ValidationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
