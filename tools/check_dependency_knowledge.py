#!/usr/bin/env python3
"""Validate dependency knowledge framework, template, route, and tool contracts."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from validate_dependency_knowledge_export import validate_export


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(read(path))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return value


def require(path: Path, snippets: list[str], failures: list[str]) -> None:
    text = " ".join(read(path).split())
    for snippet in snippets:
        if " ".join(snippet.split()) not in text:
            failures.append(f"{path.relative_to(ROOT)} missing {snippet}")


def fixture_manifest(digest: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "package_kind": "alatyr-dependency-knowledge",
        "knowledge_api": 1,
        "package": {
            "ecosystem": "fixture",
            "name": "example/library",
            "version": "1.0.0",
            "source": "https://example.invalid/library",
            "release_profile": "consumer",
            "license": "Apache-2.0",
        },
        "compatibility": {"required_capabilities": ["dependency-knowledge:v1"]},
        "export_root": "exports",
        "exports": [
            {
                "id": "fixture:example/library.public-contract",
                "type": "public-contract",
                "path": "exports/contracts.json",
                "content_digest": digest,
                "authority": "upstream-canonical",
                "stability": "stable",
                "summary": "Fixture public contract",
                "applicability": {"state": "active", "conditions": []},
                "evidence": ["exports/contracts.json"],
            }
        ],
        "public_dependencies": [],
        "prohibited_surfaces": sorted(
            {
                "assistant-bridges",
                "prompts",
                "skills",
                "gates",
                "tools",
                "permissions",
                "lifecycle-hooks",
                "executable-commands",
            }
        ),
    }


def main() -> int:
    failures: list[str] = []
    paths = {
        "rule": ROOT / "framework/dependency-knowledge.md",
        "schema": ROOT / "schemas/alatyr-dependency-knowledge.schema.json",
        "package": ROOT / "templates/dependency-knowledge/alatyr-dependency.json",
        "package_readme": ROOT / "templates/dependency-knowledge/README.md",
        "index": TARGET / ".ai/project/dependencies/README.md",
        "policy": TARGET / ".ai/project/dependencies/policy.json",
        "catalog": TARGET / ".ai/project/dependencies/catalog.json",
        "lock": TARGET / ".ai/project/dependencies/knowledge-lock.json",
        "deviations": TARGET / ".ai/project/dependencies/deviations.json",
        "snapshots": TARGET / ".ai/project/dependencies/snapshots/README.md",
        "intent": TARGET / ".ai/assistant/context/intents/dependency-knowledge-request.json",
        "flow": TARGET / ".ai/assistant/flows/dependency-knowledge-sync.flow.md",
        "gate": TARGET / ".ai/assistant/gates/dependency-knowledge.md",
        "report": TARGET / ".ai/assistant/templates/dependency-knowledge-sync-report.md",
        "modules": TARGET / ".ai/assistant/module-profile.md",
        "manifest": TARGET / ".ai/alatyr.yaml",
        "operations": TARGET / ".ai/assistant/operation-catalog.json",
        "router": TARGET / ".ai/assistant/context-router.json",
        "help": TARGET / ".ai/assistant/help-reference.md",
        "install": ROOT / "INSTALL.md",
        "install_flow": ROOT / "installer/assistant-installation.flow.md",
        "readiness": ROOT / "installer/readiness-checklist.md",
        "plan": ROOT / "installer/installation-plan-template.md",
        "validator": ROOT / "tools/validate_dependency_knowledge_export.py",
    }
    for path in paths.values():
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    for path in [paths["schema"], paths["package"], paths["policy"], paths["catalog"], paths["lock"], paths["deviations"], paths["intent"], paths["operations"], paths["router"]]:
        try:
            load(path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"{path.relative_to(ROOT)} invalid JSON: {exc}")

    require(paths["rule"], [
        "ALATYR-DEPENDENCY-001",
        "## Activation And Scope",
        "## Trust Boundary",
        "## Identity",
        "## Fact Ownership",
        "## Synchronization Procedure",
        "Do not collapse these axes into one `accepted` state",
        "Do not recursively scan dependency directories",
        "Do not automatically accept a semantic change",
    ], failures)
    require(paths["flow"], [
        "Do not activate nested dependency adapters",
        "Do not execute package managers",
        "Record trust, freshness, authority, and applicability independently",
        "A hash difference shows change only",
        "Never edit dependency files",
    ], failures)
    require(paths["gate"], [
        "Nested dependency adapters",
        "exact resolved package instance",
        "Digest or structural validity is not treated as semantic proof",
        "visited-set",
        "Structural validation does not prove",
    ], failures)
    require(paths["index"], [
        "## Normalized Record Contract",
        '"instance_id"',
        '"export_status"',
        '"public_instance_ids"',
        '"export_ids"',
        "Keep these axes independent",
    ], failures)
    for name in ["install", "install_flow", "readiness", "plan"]:
        require(paths[name], ["dependency knowledge"], failures)

    capabilities = load(ROOT / "framework/capabilities.json")
    module = capabilities.get("modules", {}).get("dependency-knowledge")
    if not isinstance(module, dict) or module.get("check_ids") != ["dependency-knowledge"]:
        failures.append("framework/capabilities.json missing dependency-knowledge check closure")

    operations = load(paths["operations"]).get("operations", [])
    operation = next((item for item in operations if item.get("id") == "dependency-knowledge"), None)
    if not isinstance(operation, dict) or operation.get("required_module") != "dependency-knowledge":
        failures.append("operation catalog does not gate dependency-knowledge by module")
    router = load(paths["router"]).get("intent_overlays", {}).get("dependency-knowledge-request")
    if not isinstance(router, dict) or router.get("operation_candidates") != ["dependency-knowledge"]:
        failures.append("context router does not select dependency-knowledge operation")

    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory)
        exports = source / "exports"
        exports.mkdir()
        content = b'{"contract":"fixture"}\n'
        contract = exports / "contracts.json"
        contract.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        manifest = fixture_manifest(digest)
        (source / "alatyr-dependency.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        findings = validate_export(source)
        if findings:
            failures.append(f"valid dependency export fixture rejected: {findings}")
        manifest["exports"][0]["path"] = "../escape.md"
        (source / "alatyr-dependency.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        codes = {finding["code"] for finding in validate_export(source)}
        if "EXPORT_PATH" not in codes:
            failures.append("dependency export validator did not reject path traversal")
        manifest = fixture_manifest(digest)
        manifest["commands"] = []
        (source / "alatyr-dependency.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        codes = {finding["code"] for finding in validate_export(source)}
        if "SCHEMA_CONTRACT" not in codes:
            failures.append(
                "dependency export validator did not reject an undeclared surface"
            )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("Dependency knowledge contracts are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
