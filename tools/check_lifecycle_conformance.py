#!/usr/bin/env python3
"""Exercise accepted profile installs, approval scope, drift, and update cycles."""

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

from bootstrap_index import BOOTSTRAP_PATH, build_from_target, render
from plan_target_upgrade import add_validation_impact
from scaffold_target_structure import plan as scaffold_plan
from render_context_catalogs import build_framework_catalog_contents
from render_installed_context_catalogs import expected_outputs as installed_context_outputs
from support_state import STATE_PATH, build_support_state, render_state
from target_adapter_validation.framework_baseline import (
    source_pack_projection,
)
from validate_target_adapter import (
    AdapterValidatorConfig,
    Validator,
    findings_payload,
    result_code,
)


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "conformance" / "golden" / "lifecycle" / "accepted-profiles.json"
PROFILE_PACKS = {
    "kernel": "kernel",
    "core": "core",
    "standard": "standard",
    "full": "complete",
}
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
        "KERNEL_CORE_STANDARD_OR_COMPLETE": "core",
        "CORE_STANDARD_OR_FULL": "core",
        "KERNEL_CORE_STANDARD_OR_FULL": "core",
        "COMPLETE_OR_MISSING_GAPS": "complete",
        "SUPPORTED_ASSISTANT": "codex",
        "SUPPORTED_UNSUPPORTED_OR_UNKNOWN": "unknown",
        "TARGET_VALIDATION_COMMAND_OR_MANUAL_REVIEW": "manual review",
        "TASK_PROFILE": "docs-local",
        "CODEOWNERS_OR_EQUIVALENT_OWNER_MAP": "CODEOWNERS",
        "NEW_INSTALL_OR_UPGRADE": "new-install",
        "READ_ONLY_DOCS_ONLY_ADAPTER_ONLY_CODE_AND_TESTS_OR_FULL_WITH_APPROVAL": "adapter-only",
        "SELECTED_ITEM_ALLOWED_ACTIONS": "read-only",
        "TARGET_ITEM_ALLOWED_ACTION": "read-only",
        "SKILL_PROMPT_GATE_CHECKER_FLOW_TOOL_MCP_BRIDGE_WRAPPER_RULE_TEMPLATE_OR_OTHER": "skill",
        "ACTIVE_BLOCKED_DEPRECATED_OR_UNRESOLVED": "blocked",
        "TARGET_UPGRADE_IMPACT_REPORT": ".ai/assistant/migrations/upgrade-impact.json",
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


def resolve_adapter(repo: Path, support_profile: str = "core") -> None:
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

    upgrade_impact_path = (
        repo / ".ai" / "assistant" / "migrations" / "upgrade-impact.json"
    )
    upgrade_impact_path.parent.mkdir(parents=True, exist_ok=True)
    upgrade_impact_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "impact_kind": "alatyr-upgrade-impact",
                "status": "fixture-no-update-pending",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    manifest_path = repo / ".ai" / "alatyr.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["framework"]["pack"] = PROFILE_PACKS[support_profile]
    manifest["installation"]["support_profile"] = support_profile
    manifest["installation"]["state"] = "staged"
    manifest["modules"]["enabled"] = []
    manifest["modules"]["deferred"] = ["all optional modules: fixture does not require them"]
    manifest["modules"]["blocked"] = []
    manifest["source_of_truth"]["project_sources"] = ["README.md"]
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    state_path = repo / ".ai" / "assistant" / "installation-state.json"
    state_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "record_kind": "alatyr-installation-state",
                "current_state": "staged",
                "transitions": [
                    {
                        "sequence": 1,
                        "previous_state": None,
                        "next_state": "scaffolded",
                        "reason": "initial-scaffold",
                        "operation_id": "scaffold-target-adapter",
                        "repository_revision": run_git(repo, "rev-parse", "HEAD"),
                        "current_user_authorization": "fixture adapter-only modify",
                        "approval_evidence": None,
                        "validation": {
                            "status": "not-run",
                            "evidence": "scaffolding does not accept installation",
                        },
                        "recorded_at": "2026-01-01T00:00:00Z",
                    },
                    {
                        "sequence": 2,
                        "previous_state": "scaffolded",
                        "next_state": "staged",
                        "reason": "adaptation-started",
                        "operation_id": "fixture-install",
                        "repository_revision": run_git(repo, "rev-parse", "HEAD"),
                        "current_user_authorization": "fixture adapter-only modify",
                        "approval_evidence": "fixture-install",
                        "validation": {
                            "status": "not-run",
                            "evidence": "repository-aware adaptation in progress",
                        },
                        "recorded_at": "2026-01-01T00:01:00Z",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    refresh_context_and_bootstrap(repo)


def transition_installation_state(
    repo: Path,
    *,
    next_state: str,
    reason: str,
    operation_id: str,
    validation_status: str,
    validation_evidence: str,
) -> None:
    manifest_path = repo / ".ai" / "alatyr.yaml"
    state_path = repo / ".ai" / "assistant" / "installation-state.json"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    record = json.loads(state_path.read_text(encoding="utf-8"))
    previous_state = record["current_state"]
    record["transitions"].append(
        {
            "sequence": len(record["transitions"]) + 1,
            "previous_state": previous_state,
            "next_state": next_state,
            "reason": reason,
            "operation_id": operation_id,
            "repository_revision": run_git(repo, "rev-parse", "HEAD"),
            "current_user_authorization": "fixture adapter-only modify",
            "approval_evidence": "fixture-install",
            "validation": {
                "status": validation_status,
                "evidence": validation_evidence,
            },
            "recorded_at": "2026-01-01T00:02:00Z",
        }
    )
    record["current_state"] = next_state
    state_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    manifest["installation"]["state"] = next_state
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    refresh_context_and_bootstrap(repo)


def refresh_bootstrap(repo: Path) -> None:
    output = repo / BOOTSTRAP_PATH
    output.write_bytes(render(build_from_target(repo)).encode("utf-8"))


def refresh_context_and_bootstrap(repo: Path) -> None:
    for path, content in installed_context_outputs(repo).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))
    refresh_bootstrap(repo)
    support_state = build_support_state(repo)
    (repo / STATE_PATH).write_bytes(render_state(support_state).encode("utf-8"))


def approval_record(base: str, support_profile: str) -> dict[str, Any]:
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
            "allowed_protected_changes": [
                f"install {support_profile} target adapter support profile"
            ],
            "allowed_changed_fact_ids": ["adapter-installation"],
            "allowed_architecture_areas": ["none"],
            "allowed_behavior_categories": ["adapter-only"],
            "excluded_semantic_effects": ["project behavior changes"],
            "permitted_external_effects": ["none"],
            "allowed_files_or_surfaces": [
                ".ai/**",
                ".agents/**",
                ".cursor/**",
                ".cursorrules",
                ".junie/**",
                ".cline/**",
                ".clinerules",
                ".roo/**",
                ".roorules",
                ".roomodes",
                ".kiro/**",
                ".rules",
                ".zed/**",
                ".opencode/**",
                "opencode.json",
                "opencode.jsonc",
                "AGENT.md",
                ".devin/**",
                ".github/**",
                ".windsurf/**",
                ".windsurfrules",
                "AGENTS.md",
                "AI_ASSISTANTS.md",
                "CLAUDE.md",
                "CODEOWNERS",
                "GEMINI.md",
            ],
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


def apply_synthetic_framework_update(repo: Path, source: Path, pack: str) -> None:
    target_framework = repo / ".ai" / "framework"
    expected_names, _registry, expected_contents = source_pack_projection(
        source / "framework", pack
    )
    if set(expected_contents) != expected_names:
        raise ValueError("synthetic update inventory does not match source pack")
    for name, content in expected_contents.items():
        destination = target_framework / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    inventory = json.loads(
        (target_framework / "file-inventory.json").read_text(encoding="utf-8")
    )
    manifest_path = repo / ".ai" / "alatyr.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["framework"]["version"] = inventory["framework_version"]
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False), encoding="utf-8"
    )
    refresh_context_and_bootstrap(repo)


def exercise_profile(
    root: Path,
    support_profile: str,
    expected_pack: str,
    failures: list[str],
) -> None:
    repo = root / f"target-{support_profile}"
    repo.mkdir()
    run_git(repo, "init", "-q")
    run_git(repo, "config", "user.email", "alatyr@example.invalid")
    run_git(repo, "config", "user.name", "Alatyr Conformance")
    (repo / "README.md").write_text("# Lifecycle Fixture\n", encoding="utf-8")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-q", "-m", "seed fixture")
    base = run_git(repo, "rev-parse", "HEAD")
    branch = f"adapter-support-{support_profile}"
    run_git(repo, "branch", "-m", branch)
    if run_git(repo, "branch", "--show-current") != branch:
        failures.append(
            f"{support_profile} lifecycle fixture did not preserve the non-main target branch"
        )

    impact_path = root / f"upgrade-impact-{support_profile}.json"
    report_path = root / f"adapter-validation-{support_profile}.json"
    impact_path.write_text(
            json.dumps({"routing": {"candidate_context": [".ai/alatyr.yaml"]}}),
            encoding="utf-8",
        )
    report_path.write_text(
            json.dumps(
                {
                    "findings": [
                        {
                            "level": "error",
                            "code": "DEBUG_MODE_TEMPLATE_VERSION",
                            "path": ".ai/assistant/templates/debug-session-record.json",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
    add_validation_impact(impact_path, report_path)
    routed_impact = json.loads(impact_path.read_text(encoding="utf-8"))
    if ".ai/assistant/templates/debug-session-record.json" not in routed_impact["routing"]["candidate_context"]:
        failures.append("upgrade impact did not route installed validator findings")

    actions, blocked = scaffold_plan(
            SimpleNamespace(
                target=repo,
                write=True,
                overwrite_existing=False,
                profile=support_profile,
                framework_pack="matched",
                enable_module=[],
            )
        )
    if not actions or blocked:
        failures.append(f"{support_profile} scaffold failed: {blocked}")
    resolve_adapter(repo, support_profile)
    manifest = yaml.safe_load((repo / ".ai" / "alatyr.yaml").read_text(encoding="utf-8"))
    if manifest.get("framework", {}).get("pack") != expected_pack:
        failures.append(f"{support_profile} scaffold resolved unexpected framework pack")
    if manifest.get("installation", {}).get("support_profile") != support_profile:
        failures.append(f"{support_profile} scaffold lost its support profile")
    approval_path = repo / ".ai" / "assistant" / "approvals" / "fixture-install.json"
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text(
            json.dumps(approval_record(base, support_profile), indent=2) + "\n",
            encoding="utf-8",
        )
    refresh_context_and_bootstrap(repo)

    approval_validator = make_validator(repo, ROOT, diff_ref=base, approval=approval_path)
    approval_validator.check_approval_scope()
    approval_errors = [
        finding for finding in approval_validator.findings if finding.level == "error"
    ]
    if approval_errors:
        failures.append(
            f"{support_profile} installation approval scope failed: "
            + ", ".join(finding.code for finding in approval_errors)
        )

    staged = make_validator(repo, ROOT)
    staged_findings = staged.run()
    staged_payload = findings_payload(
        staged_findings,
        target=repo,
        strict_warnings=False,
        installation_state=staged.installation_state,
    )
    if result_code(staged_findings, strict_warnings=False):
        failures.append(
            f"staged {support_profile} strict validation failed before acceptance"
        )
    if staged_payload["adapter_health"]["state"] != "unverified" or staged_payload[
        "placeholder_validation"
    ]["acceptance_eligible"]:
        failures.append(f"staged {support_profile} adapter incorrectly claimed acceptance")

    transition_installation_state(
        repo,
        next_state="accepted",
        reason="strict-acceptance",
        operation_id="fixture-install",
        validation_status="passed",
        validation_evidence="strict target adapter validation passed",
    )
    accepted = make_validator(repo, ROOT)
    accepted_findings = accepted.run()
    accepted_errors = [finding for finding in accepted_findings if finding.level == "error"]
    if accepted_errors or result_code(accepted_findings, strict_warnings=False):
        failures.append(
            f"accepted {support_profile} installation failed: "
            + ", ".join(
                finding.code + ":" + finding.message
                for finding in accepted_findings
                if finding.level in {"error", "warning"}
            )
        )
    accepted_payload = findings_payload(
        accepted_findings,
        target=repo,
        strict_warnings=False,
        installation_state=accepted.installation_state,
    )
    if accepted_payload["adapter_health"]["state"] not in {"ready", "attention"} or not accepted_payload[
        "placeholder_validation"
    ]["acceptance_eligible"]:
        failures.append(
            f"accepted {support_profile} adapter did not report acceptance-eligible health"
        )
    if any(
        PLACEHOLDER.search(path.read_text(encoding="utf-8"))
        for path in repo.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and ".ai/framework" not in path.as_posix()
    ):
        failures.append(f"accepted {support_profile} adapter retains target placeholders")

    run_git(repo, "add", ".")
    run_git(repo, "commit", "-q", "-m", f"install accepted {support_profile} adapter")

    source = root / f"next-source-{support_profile}"
    (source / "framework").parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "framework", source / "framework")
    for name in ["VERSION", "ADAPTER_SCHEMA_VERSION", "TEMPLATE_VERSION"]:
        shutil.copy2(ROOT / name, source / name)
    (source / "VERSION").write_text("0.1.0-lifecycle-fixture\n", encoding="utf-8")
    context_path = source / "framework" / "context-profiles.md"
    context_path.write_bytes(
        context_path.read_bytes() + b"\nLifecycle fixture update.\n"
    )
    for relpath, content in build_framework_catalog_contents(
        root=source / "framework"
    ).items():
        destination = source / "framework" / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content.encode("utf-8"))
    source_inventory_path = source / "framework" / "file-inventory.json"
    source_inventory = json.loads(source_inventory_path.read_text(encoding="utf-8"))
    source_inventory["framework_version"] = "0.1.0-lifecycle-fixture"
    for entry in source_inventory.get("files", []):
        entry_path = entry.get("path")
        if not isinstance(entry_path, str):
            continue
        framework_path = source / entry_path
        if framework_path.is_file():
            entry["sha256"] = hashlib.sha256(framework_path.read_bytes()).hexdigest()
    source_inventory_path.write_bytes(
        (json.dumps(source_inventory, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
    )

    drift = make_validator(repo, source)
    drift.check_framework_baseline()
    drift.check_migration_diff_evidence()
    if result_code(drift.findings, strict_warnings=False) != 1:
        failures.append(
            f"{support_profile} synthetic framework drift did not block validation"
        )

    transition_installation_state(
        repo,
        next_state="degraded",
        reason="blocking-drift",
        operation_id="fixture-update",
        validation_status="failed",
        validation_evidence="framework baseline drift detected",
    )
    transition_installation_state(
        repo,
        next_state="staged",
        reason="repair-started",
        operation_id="fixture-update",
        validation_status="not-run",
        validation_evidence="controlled repair started",
    )

    apply_synthetic_framework_update(repo, source, expected_pack)
    staged_update = make_validator(repo, source)
    staged_update_findings = staged_update.run()
    if result_code(staged_update_findings, strict_warnings=False):
        failures.append(
            f"staged {support_profile} framework update failed validation: "
            + ", ".join(
                finding.code + ":" + finding.message
                for finding in staged_update_findings
                if finding.level in {"error", "warning"}
            )
        )
    transition_installation_state(
        repo,
        next_state="accepted",
        reason="strict-acceptance",
        operation_id="fixture-update",
        validation_status="passed",
        validation_evidence="strict post-update validation passed",
    )
    updated = make_validator(repo, source)
    updated_findings = updated.run()
    updated_errors = [finding for finding in updated_findings if finding.level == "error"]
    if updated_errors or result_code(updated_findings, strict_warnings=False):
        failures.append(
            f"{support_profile} post-update adapter validation failed: "
            + ", ".join(
                finding.code + ":" + finding.message
                for finding in updated_findings
                if finding.level in {"error", "warning"}
            )
        )

def main() -> int:
    failures: list[str] = []
    try:
        golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
        expected_phases = golden["phases"]
        profile_contracts = golden["support_profiles"]
        if expected_phases[-1] != "accepted-post-update-validation":
            failures.append("lifecycle golden contract is invalid")
        if profile_contracts != {
            profile: {"framework_pack": pack, "enabled_optional_modules": []}
            for profile, pack in PROFILE_PACKS.items()
        }:
            failures.append("lifecycle profile and framework-pack matrix drifted")
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="alatyr-lifecycle-") as directory:
        root = Path(directory)
        for support_profile, expected_pack in PROFILE_PACKS.items():
            exercise_profile(root, support_profile, expected_pack, failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: accepted kernel, core, standard, and full profile installation, "
        "approval scope, drift, and update cycles passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
