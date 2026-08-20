#!/usr/bin/env python3
"""Exercise an accepted core install, approval scope, drift, and update cycle."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

from scaffold_target_structure import plan as scaffold_plan
from target_adapter_validation.framework_baseline import source_pack_expectation
from validate_target_adapter import (
    AdapterValidatorConfig,
    Validator,
    result_code,
)


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "conformance" / "golden" / "lifecycle" / "accepted-core.json"
PLACEHOLDER = re.compile(r"\{[A-Z0-9_]+(?:_[A-Z0-9_]+)*\}")


def run_git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def replacement(name: str) -> str:
    exact = {
        "ALATYR_ADAPTER_SCHEMA_VERSION": (ROOT / "ADAPTER_SCHEMA_VERSION").read_text(encoding="utf-8").strip(),
        "ALATYR_CORE_VERSION": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "ALATYR_TEMPLATE_VERSION": (ROOT / "TEMPLATE_VERSION").read_text(encoding="utf-8").strip(),
        "CORE_STANDARD_OR_COMPLETE": "core",
        "CORE_STANDARD_OR_FULL": "core",
        "COMPLETE_OR_MISSING_GAPS": "complete",
        "SUPPORTED_ASSISTANT": "codex",
        "TARGET_VALIDATION_COMMAND_OR_MANUAL_REVIEW": "manual review",
        "TASK_PROFILE": "docs-local",
        "CODEOWNERS_OR_EQUIVALENT_OWNER_MAP": "CODEOWNERS",
        "NEW_INSTALL_OR_UPGRADE": "new-install",
        "READ_ONLY_DOCS_ONLY_ADAPTER_ONLY_CODE_AND_TESTS_OR_FULL_WITH_APPROVAL": "adapter-only",
        "SELECTED_ITEM_ALLOWED_ACTIONS": "read-only",
        "TARGET_ITEM_ALLOWED_ACTION": "read-only",
        "SKILL_PROMPT_GATE_CHECKER_FLOW_TOOL_MCP_BRIDGE_WRAPPER_RULE_TEMPLATE_OR_OTHER": "skill",
        "ACTIVE_BLOCKED_DEPRECATED_OR_UNRESOLVED": "blocked",
    }
    if name in exact:
        return exact[name]
    if "ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED" in name:
        return "deferred"
    if "REQUIRED_ENABLED_OR_BLOCKED" in name:
        return "required"
    if name.endswith("_DATE") or name.endswith("_AT"):
        return "2026-01-01"
    if "YES_NO" in name:
        return "no"
    if "PATH" in name or "FILE" in name or "SOURCE_OF_TRUTH" in name:
        return "README.md"
    return "fixture-value"


def resolve_adapter(repo: Path) -> None:
    framework_root = repo / ".ai" / "framework"
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        if framework_root in path.parents:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        resolved = PLACEHOLDER.sub(lambda match: replacement(match.group(0)[1:-1]), text)
        path.write_text(resolved, encoding="utf-8")

    manifest_path = repo / ".ai" / "alatyr.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["framework"]["pack"] = "core"
    manifest["installation"]["support_profile"] = "core"
    manifest["modules"]["enabled"] = []
    manifest["modules"]["deferred"] = ["all optional modules: fixture does not require them"]
    manifest["modules"]["blocked"] = []
    manifest["source_of_truth"]["project_sources"] = ["README.md"]
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def approval_record(base: str) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "record_kind": "alatyr-approval-record",
        "evidence_classification": "historical-record",
        "approval_id": "fixture-install",
        "operation": {"id": "fixture-install", "type": "installation"},
        "plan": {"version": "1", "sha256": "not available with reason", "file": "not available with reason"},
        "diff": {
            "base": base,
            "patch_sha256": "not available with reason",
            "repository_revision_at_approval": base,
        },
        "scope": {
            "allowed_protected_changes": ["install core target adapter"],
            "allowed_changed_fact_ids": ["adapter-installation"],
            "allowed_architecture_areas": ["none"],
            "allowed_behavior_categories": ["adapter-only"],
            "excluded_semantic_effects": ["project behavior changes"],
            "permitted_external_effects": ["none"],
            "allowed_files_or_surfaces": [".ai/**", "AGENTS.md", "CODEOWNERS"],
            "excluded_files_or_surfaces": ["src/**"],
            "excluded_actions": ["project source changes"],
            "allowed_actions_mode": "adapter-only",
            "invalidation_rule": "scope or plan changes require new approval",
        },
        "approval": {
            "requested_by": "fixture",
            "approved_by": "fixture-owner",
            "approved_at": "2026-01-01",
            "source_or_message": "deterministic conformance fixture",
            "expires_at_or_reuse_policy": "single use",
        },
        "use_result": {
            "used_by": "fixture-install",
            "patch_changed_after_approval": "no",
            "implementation_within_scope": "yes",
            "declared_semantic_scope_within_approval": "yes",
            "validation": "lifecycle conformance",
            "result_evidence": "current fixture run",
            "residual_risk": "does not execute an AI assistant",
        },
    }


def make_validator(
    repo: Path,
    framework_source: Path,
    *,
    diff_ref: str | None = None,
    approval: Path | None = None,
) -> Validator:
    return Validator(
        repo,
        framework_source=framework_source,
        diff_ref=diff_ref,
        approval_records=[approval] if approval else [],
        enforce_approval_scope=approval is not None,
        change_packages=[],
        enforce_change_package=False,
        migration_diff=None,
        allow_placeholders=False,
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
    )


def apply_synthetic_framework_update(repo: Path, source: Path) -> None:
    target_framework = repo / ".ai" / "framework"
    shutil.copy2(source / "framework" / "context-profiles.md", target_framework / "context-profiles.md")
    expected_names, _registry, expected_hashes = source_pack_expectation(
        source / "framework", "core"
    )
    inventory_path = target_framework / "file-inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["framework_version"] = (source / "VERSION").read_text(encoding="utf-8").strip()
    entries = {Path(item["path"]).name: item for item in inventory["files"]}
    if set(entries) | {"file-inventory.json"} != expected_names:
        raise ValueError("synthetic update inventory does not match source pack")
    for name, entry in entries.items():
        entry["sha256"] = expected_hashes[name]
    inventory_path.write_bytes(
        (json.dumps(inventory, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    manifest_path = repo / ".ai" / "alatyr.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["framework"]["version"] = inventory["framework_version"]
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False), encoding="utf-8"
    )


def main() -> int:
    failures: list[str] = []
    try:
        golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
        expected_phases = golden["phases"]
        if expected_phases[-1] != "accepted-post-update-validation":
            failures.append("lifecycle golden contract is invalid")
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="alatyr-lifecycle-") as directory:
        repo = Path(directory) / "target"
        repo.mkdir()
        run_git(repo, "init", "-q")
        run_git(repo, "config", "user.email", "alatyr@example.invalid")
        run_git(repo, "config", "user.name", "Alatyr Conformance")
        (repo / "README.md").write_text("# Lifecycle Fixture\n", encoding="utf-8")
        run_git(repo, "add", ".")
        run_git(repo, "commit", "-q", "-m", "seed fixture")
        base = run_git(repo, "rev-parse", "HEAD")

        actions, blocked = scaffold_plan(
            SimpleNamespace(
                target=repo,
                write=True,
                overwrite_existing=False,
                profile="core",
            )
        )
        if not actions or blocked:
            failures.append(f"core scaffold failed: {blocked}")
        resolve_adapter(repo)
        approval_path = repo / ".ai" / "assistant" / "approvals" / "fixture-install.json"
        approval_path.write_text(
            json.dumps(approval_record(base), indent=2) + "\n", encoding="utf-8"
        )

        approval_validator = make_validator(
            repo, ROOT, diff_ref=base, approval=approval_path
        )
        approval_validator.check_approval_scope()
        approval_errors = [
            finding for finding in approval_validator.findings if finding.level == "error"
        ]
        if approval_errors:
            failures.append(
                "installation approval scope failed: "
                + ", ".join(finding.code for finding in approval_errors)
            )

        accepted = make_validator(repo, ROOT)
        accepted_findings = accepted.run()
        accepted_errors = [finding for finding in accepted_findings if finding.level == "error"]
        if accepted_errors or result_code(accepted_findings, strict_warnings=False):
            failures.append(
                "accepted core installation failed: "
                + ", ".join(
                    finding.code
                    for finding in accepted_findings
                    if finding.level in {"error", "warning"}
                )
            )
        if any(PLACEHOLDER.search(path.read_text(encoding="utf-8")) for path in repo.rglob("*") if path.is_file() and ".git" not in path.parts and ".ai/framework" not in path.as_posix()):
            failures.append("accepted adapter retains target placeholders")

        run_git(repo, "add", ".")
        run_git(repo, "commit", "-q", "-m", "install accepted core adapter")

        source = Path(directory) / "next-source"
        (source / "framework").parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ROOT / "framework", source / "framework")
        for name in ["VERSION", "ADAPTER_SCHEMA_VERSION", "TEMPLATE_VERSION"]:
            shutil.copy2(ROOT / name, source / name)
        (source / "VERSION").write_text("0.1.0-lifecycle-fixture\n", encoding="utf-8")
        context_path = source / "framework" / "context-profiles.md"
        context_path.write_text(
            context_path.read_text(encoding="utf-8") + "\nLifecycle fixture update.\n",
            encoding="utf-8",
        )

        drift = make_validator(repo, source)
        drift.check_framework_baseline()
        drift.check_migration_diff_evidence()
        if result_code(drift.findings, strict_warnings=False) != 1:
            failures.append("synthetic framework drift did not block validation")

        apply_synthetic_framework_update(repo, source)
        updated = make_validator(repo, source)
        updated_findings = updated.run()
        updated_errors = [finding for finding in updated_findings if finding.level == "error"]
        if updated_errors or result_code(updated_findings, strict_warnings=False):
            failures.append(
                "post-update adapter validation failed: "
                + ", ".join(
                    finding.code
                    for finding in updated_findings
                    if finding.level in {"error", "warning"}
                )
            )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: accepted core installation, approval scope, drift, and update cycle passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
