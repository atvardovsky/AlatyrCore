#!/usr/bin/env python3
"""Exercise stable contracts of the portable target adapter validator."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_target_adapter import (
    AdapterValidatorConfig,
    Finding,
    Validator,
    extract_list_field,
    findings_payload,
    git_changed_files,
    scope_entries_cover,
)


def validator(target: Path) -> Validator:
    return Validator(
        target,
        framework_source=None,
        diff_ref=None,
        approval_records=[],
        enforce_approval_scope=False,
        migration_diff=None,
        allow_placeholders=True,
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
    )


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory)
        router_path = target / ".ai" / "assistant" / "context-router.json"
        profiles_path = target / ".ai" / "assistant" / "context-profiles.md"
        profiles_path.parent.mkdir(parents=True, exist_ok=True)
        profiles_path.write_text("# Profiles\n", encoding="utf-8")
        write_json(
            router_path,
            {
                "schema_version": 1,
                "router_kind": "target-context-router",
                "human_reference": ".ai/assistant/context-profiles.md",
                "routing_order": ["docs-local"],
                "profiles": {},
            },
        )
        legacy = validator(target)
        legacy.check_router()
        legacy_codes = {finding.code for finding in legacy.findings}
        if "ROUTER_SCHEMA_LEGACY" not in legacy_codes:
            failures.append("schema-1 router must produce a migration warning")
        for forbidden in [
            "ROUTER_PRELOADED",
            "ROUTER_BOOTSTRAP",
            "ROUTER_BUDGETS_MISSING",
            "ROUTER_RECEIPT_MISSING",
        ]:
            if forbidden in legacy_codes:
                failures.append(
                    f"schema-1 router must not receive schema-2 finding {forbidden}"
                )

        write_json(
            router_path,
            {
                "schema_version": 2,
                "router_kind": "target-context-router",
                "human_reference": ".ai/assistant/context-profiles.md",
                "preloaded_context": ["AGENTS.md"],
                "bootstrap_context": [
                    ".ai/alatyr.yaml",
                    ".ai/README.md",
                    ".ai/assistant/context-router.json",
                ],
                "context_budgets": {},
                "context_receipt": {},
                "routing_order": ["docs-local"],
                "profiles": {},
            },
        )
        migration = validator(target)
        migration.check_router()
        migration_codes = {finding.code for finding in migration.findings}
        if "ROUTER_MIGRATION_MISSING" not in migration_codes:
            failures.append("schema-2 router must require migration-first routing")

        catalog_path = target / ".ai" / "assistant" / "operation-catalog.json"
        write_json(
            catalog_path,
            {
                "schema_version": 1,
                "catalog_kind": "target-operation-catalog",
                "fallback_operation": "help",
                "compact_help": ".ai/assistant/help.md",
                "human_reference": ".ai/assistant/help-reference.md",
                "routing_flow": ".ai/assistant/flows/operation-routing.flow.md",
                "health_flow": ".ai/assistant/flows/adapter-health.flow.md",
                "pre_change_preview": ".ai/assistant/templates/pre-change-preview.md",
                "module_profile": ".ai/assistant/module-profile.md",
                "operations": [
                    {
                        "id": operation_id,
                        "title": operation_id,
                        "summary": "fixture operation",
                        "use_when": ["fixture"],
                        "context_profiles": ["docs-local"],
                        "required_module": "core-profile",
                        "flow": ".ai/assistant/flows/operation-routing.flow.md",
                        "minimum_inputs": ["fixture"],
                        "allowed_actions": ["read-only"],
                        "preview": "never",
                        "aliases": [alias],
                        "final_evidence": ["fixture evidence"],
                    }
                    for operation_id, alias in [
                        ("help", "Alatyr"),
                        ("adapter-health", "Alatyr status"),
                    ]
                ],
            },
        )
        write_json(
            router_path,
            {
                "schema_version": 2,
                "router_kind": "target-context-router",
                "human_reference": ".ai/assistant/context-profiles.md",
                "bootstrap_context": [
                    ".ai/alatyr.yaml",
                    ".ai/README.md",
                    ".ai/assistant/context-router.json",
                ],
                "operation_routing": {
                    "catalog": ".ai/assistant/operation-catalog.json",
                    "health_operation": "adapter-health",
                },
                "profiles": {
                    "docs-local": {
                        "operation_candidates": ["unknown-operation"]
                    }
                },
            },
        )
        catalog_validator = validator(target)
        catalog_validator.check_operation_catalog()
        catalog_codes = {finding.code for finding in catalog_validator.findings}
        if "OPERATION_CANDIDATE_UNKNOWN" not in catalog_codes:
            failures.append("operation catalog must reject unknown profile candidates")

        routing_path = (
            target / ".ai" / "assistant" / "flows" / "operation-routing.flow.md"
        )
        routing_path.parent.mkdir(parents=True, exist_ok=True)
        routing_path.write_text(
            "Load bootstrap context only. Do not load all `.ai/framework` files.\n",
            encoding="utf-8",
        )
        bounded_routing = validator(target)
        bounded_routing.check_bootstrap_references()
        if "ROUTING_LOADS_BROAD_CONTEXT" in {
            finding.code for finding in bounded_routing.findings
        }:
            failures.append("negative broad-load guidance must not fail routing checks")
        routing_path.write_text(
            "Load bootstrap context only. Load all `.ai/framework` files.\n",
            encoding="utf-8",
        )
        broad_routing = validator(target)
        broad_routing.check_bootstrap_references()
        if "ROUTING_LOADS_BROAD_CONTEXT" not in {
            finding.code for finding in broad_routing.findings
        }:
            failures.append("positive broad-load guidance must fail routing checks")

        framework_tool_reference = target / ".ai" / "framework" / "migration-diff.md"
        framework_tool_reference.parent.mkdir(parents=True, exist_ok=True)
        framework_tool_reference.write_text(
            "The source may provide `tools/validate_target_adapter.py`.\n",
            encoding="utf-8",
        )
        checker_claims = validator(target)
        checker_claims.check_checker_claims([], [])
        if "STALE_CHECKER_REFERENCE" in {
            finding.code for finding in checker_claims.findings
        }:
            failures.append(
                "portable source-tool guidance must not become a target-local checker claim"
            )

        map_path = target / ".ai" / "project" / "consistency-map.json"
        write_json(
            map_path,
            {
                "schema_version": 1,
                "map_kind": "target-consistency-map",
                "levels": ["fact"],
                "relationship_types": ["implements"],
                "nodes": [],
            },
        )
        consistency = validator(target)
        consistency.check_consistency_map()
        consistency_codes = {finding.code for finding in consistency.findings}
        for required in [
            "CONSISTENCY_MAP_LEVELS",
            "CONSISTENCY_MAP_RELATIONSHIPS",
            "CONSISTENCY_MAP_NODES",
        ]:
            if required not in consistency_codes:
                failures.append(f"broken consistency map missing finding {required}")

        ai_router_path = target / ".ai" / "assistant" / "ai-infrastructure-router.json"
        write_json(
            ai_router_path,
            {
                "schema_version": 1,
                "router_kind": "target-ai-infrastructure-router",
                "item_types": ["skill"],
                "routing_order": ["inventory"],
                "routes": {},
                "items": [],
            },
        )
        ai_router = validator(target)
        ai_router.check_ai_infrastructure_router()
        ai_codes = {finding.code for finding in ai_router.findings}
        for required in ["AI_ROUTER_ROUTES", "AI_ROUTER_ITEM_TYPES", "AI_ROUTER_ITEMS"]:
            if required not in ai_codes:
                failures.append(f"broken AI router missing finding {required}")

        development_evidence_path = (
            target / ".ai" / "project" / "development-evidence.json"
        )
        write_json(
            development_evidence_path,
            {
                "schema_version": 1,
                "register_kind": "target-development-evidence",
                "project": "fixture",
                "owner": "fixture-owner",
                "retention_policy": "keep bounded references",
                "last_reviewed": "2026-07-17",
                "content_policy": (
                    "no raw chat, secrets, credentials, or personal data"
                ),
                "patterns": [
                    {
                        "id": "pattern-1",
                        "category": "review-rework",
                        "project_area": "api",
                        "source_owner": "api-contract",
                        "normalized_problem": "companion contract updates are missed",
                        "occurrence_count": 0,
                        "first_observed": "operation-1",
                        "last_observed": "operation-1",
                        "evidence_quality": "invented",
                        "evidence_refs": [],
                        "outcome_signals": ["rework"],
                        "existing_ai_item_ids": [],
                        "status": "unknown",
                    }
                ],
            },
        )
        development_evidence = validator(target)
        development_evidence.check_development_evidence(None)
        development_codes = {
            finding.code for finding in development_evidence.findings
        }
        for required in [
            "DEVELOPMENT_EVIDENCE_OCCURRENCE_COUNT",
            "DEVELOPMENT_EVIDENCE_REFERENCE_MISSING",
            "DEVELOPMENT_EVIDENCE_QUALITY",
            "DEVELOPMENT_EVIDENCE_STATUS",
        ]:
            if required not in development_codes:
                failures.append(
                    f"broken development evidence missing finding {required}"
                )

        team_model = target / ".ai" / "project" / "team-operating-model.md"
        team_model.write_text(
            (
                "# Team Operating Model\n\n"
                "### Actor `actor-owner`\n\n"
                "### Priority `normal`\n"
            ),
            encoding="utf-8",
        )
        team_overlay_path = (
            target / ".ai" / "assistant" / "team" / "context-overlay.json"
        )
        write_json(
            team_overlay_path,
            {
                "schema_version": 1,
                "overlay_kind": "target-team-context-overlay",
                "overlay_id": "team-active",
                "operation_candidates": ["team-status"],
                "required_context": [
                    ".ai/framework/team-collaboration.md",
                    ".ai/project/team-operating-model.md",
                    ".ai/assistant/team/work-registry.json",
                    ".ai/assistant/gates/team-collaboration.md",
                ],
            },
        )
        write_json(
            router_path,
            {
                "task_scale_overlays": {
                    "team-active": {
                        "use_when": ["team request"],
                        "descriptor": ".ai/assistant/team/context-overlay.json",
                    }
                }
            },
        )
        team_registry_path = (
            target / ".ai" / "assistant" / "team" / "work-registry.json"
        )
        write_json(
            team_registry_path,
            {
                "schema_version": 1,
                "registry_kind": "target-team-work-registry",
                "project": "fixture",
                "module_state": "enabled",
                "coordination_backend": "repository",
                "canonical_task_source": "registry",
                "synchronization_direction": "manual",
                "operating_model": ".ai/project/team-operating-model.md",
                "updated_at": "2026-07-23",
                "evidence_revision": "unavailable",
                "storage_policy": "repository",
                "retention_policy": "target policy",
                "privacy_policy": "no sensitive content",
                "tasks": [
                    {
                        "id": "task-1",
                        "goal": "fixture goal",
                        "non_goals": [],
                        "priority": "normal",
                        "priority_rationale": "fixture",
                        "priority_decided_by": "actor-owner",
                        "status": "merge-ready",
                        "owner_actor_id": "actor-missing",
                        "reviewer_actor_ids": [],
                        "parent_request": "fixture",
                        "coordination_backend_ref": "task-1",
                        "branch_or_worktree": "fixture",
                        "base_revision": "unavailable",
                        "evidence_revision": "unavailable",
                        "allowed_actions": ["code-and-tests"],
                        "context_profiles": ["code-local"],
                        "project_areas": ["fixture"],
                        "changed_fact_ids": ["fact-1"],
                        "canonical_owner_refs": ["owner-1"],
                        "expected_surfaces": ["src"],
                        "dependencies": [],
                        "blockers": [],
                        "related_task_ids": [],
                        "overlap": {
                            "state": "conflicting",
                            "checked_at": "2026-07-23",
                            "checked_revision": "unavailable",
                            "fact_ids": ["fact-1"],
                            "contract_or_dependency_refs": [],
                            "file_or_surface_refs": [],
                            "resolution": "none",
                        },
                        "claim": {
                            "mode": "advisory",
                            "actor_id": "none",
                            "claimed_at": "none",
                            "expires_at": "none",
                            "base_revision": "none",
                            "state": "unclaimed",
                        },
                        "approval_records": [],
                        "review_state": "approved",
                        "review_evidence_refs": [],
                        "validation_state": "failed",
                        "latest_checkpoint": "none",
                        "handoff_state": "none",
                        "decision_records": [],
                        "residual_risks": [],
                        "next_action": "repair",
                        "updated_at": "2026-07-23",
                    }
                ],
            },
        )
        team = validator(target)
        team.check_team_collaboration(None)
        team_codes = {finding.code for finding in team.findings}
        for required in [
            "TEAM_ACTOR_UNKNOWN",
            "TEAM_ACTIVE_OVERLAP_BLOCKED",
            "TEAM_MERGE_READY_VALIDATION",
            "TEAM_MERGE_READY_REVIEW_EVIDENCE",
            "TEAM_MERGE_READY_OVERLAP",
            "TEAM_MERGE_READY_REVIEWERS",
            "TEAM_MERGE_READY_REVISION",
        ]:
            if required not in team_codes:
                failures.append(f"broken team registry missing finding {required}")

        approval = """Allowed files or surfaces:

- `.ai/assistant/help.md`

Excluded files or surfaces:

- `.ai/assistant/private/*`
"""
        allowed = extract_list_field(approval, "Allowed files or surfaces:")
        excluded = extract_list_field(approval, "Excluded files or surfaces:")
        if not scope_entries_cover(".ai/assistant/help.md", allowed):
            failures.append("exact approval scope should cover its named file")
        if scope_entries_cover(".ai/assistant/help.md.backup", allowed):
            failures.append("approval scope must not match path substrings")
        if not scope_entries_cover(".ai/assistant/private/item.md", excluded):
            failures.append("approval scope glob should cover nested target files")

        git_target = target / "approval-diff"
        git_target.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=git_target, check=True)
        subprocess.run(
            ["git", "config", "user.email", "alatyr@example.invalid"],
            cwd=git_target,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Alatyr Check"],
            cwd=git_target,
            check=True,
        )
        source = git_target / "src"
        source.mkdir()
        (source / "allowed.txt").write_text("before\n", encoding="utf-8")
        (source / "outside.txt").write_text("before\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=git_target, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "fixture"],
            cwd=git_target,
            check=True,
        )
        (source / "allowed.txt").write_text("after\n", encoding="utf-8")
        (source / "outside.txt").write_text("after\n", encoding="utf-8")
        (source / "untracked.txt").write_text("new\n", encoding="utf-8")
        approval_path = (
            git_target
            / ".ai"
            / "assistant"
            / "approvals"
            / "approval.json"
        )
        approval_data = {
            "schema_version": 1,
            "record_kind": "alatyr-approval-record",
            "evidence_classification": "historical-record",
            "approval_id": "approval-test",
            "operation": {"id": "operation-test", "type": "code-change"},
            "plan": {"version": "1", "sha256": "none", "file": "none"},
            "diff": {
                "base": "HEAD",
                "patch_sha256": "none",
                "repository_revision_at_approval": "HEAD",
            },
            "scope": {
                "allowed_protected_changes": ["test change"],
                "allowed_files_or_surfaces": [
                    "src/allowed.txt",
                    ".ai/assistant/approvals/approval.json",
                ],
                "excluded_files_or_surfaces": [],
                "excluded_actions": ["live actions"],
                "allowed_actions_mode": "code-and-tests",
                "invalidation_rule": "any scope change invalidates approval",
            },
            "approval": {
                "approved_by": "tester",
                "approved_at": "2026-07-14",
            },
            "use_result": {},
        }
        write_json(approval_path, approval_data)
        changed = git_changed_files(git_target, "HEAD")
        expected_changed = {
            ".ai/assistant/approvals/approval.json",
            "src/allowed.txt",
            "src/outside.txt",
            "src/untracked.txt",
        }
        if changed is None or set(changed) != expected_changed:
            failures.append(
                "approval diff collection must include tracked and untracked paths"
            )

        strict = Validator(
            git_target,
            framework_source=None,
            diff_ref="HEAD",
            approval_records=[approval_path],
            enforce_approval_scope=True,
            migration_diff=None,
            allow_placeholders=True,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
        )
        strict.check_approval_scope()
        mismatch_messages = [
            finding.message
            for finding in strict.findings
            if finding.code == "APPROVAL_SCOPE_MISMATCH" and finding.level == "error"
        ]
        if not any("src/outside.txt" in message for message in mismatch_messages):
            failures.append("strict approval scope must reject tracked out-of-scope files")
        if not any("src/untracked.txt" in message for message in mismatch_messages):
            failures.append("strict approval scope must reject untracked out-of-scope files")

        approval_data["scope"]["allowed_files_or_surfaces"] = [
            "src/*",
            ".ai/assistant/approvals/approval.json",
        ]
        write_json(approval_path, approval_data)
        covered = Validator(
            git_target,
            framework_source=None,
            diff_ref="HEAD",
            approval_records=[approval_path],
            enforce_approval_scope=True,
            migration_diff=None,
            allow_placeholders=True,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
        )
        covered.check_approval_scope()
        if any(
            finding.level == "error" and finding.code.startswith("APPROVAL_")
            for finding in covered.findings
        ):
            failures.append("covered strict approval scope should pass")

        payload = findings_payload([], target=target, strict_warnings=False)
        evidence = payload.get("evidence", {})
        if payload.get("schema_version") != 2:
            failures.append("validator JSON schema must expose evidence schema 2")
        if evidence.get("basis") != "current-state-structural":
            failures.append("validator JSON must classify current-state evidence")
        if evidence.get("historical_actions_verified") is not False:
            failures.append("validator JSON must not imply historical actions were verified")

        health_payload = findings_payload(
            [
                Finding(
                    "warning",
                    "OPERATION_CATALOG_MISSING",
                    "catalog missing",
                    ".ai/assistant/operation-catalog.json",
                )
            ],
            target=target,
            strict_warnings=False,
        )
        if health_payload.get("adapter_health", {}).get("state") != "attention":
            failures.append("validator warning must produce attention health state")
        if health_payload.get("adapter_health", {}).get("repair_operations") != [
            "recheck-after-installation"
        ]:
            failures.append("validator health must return prioritized repair routes")
        health_finding = health_payload.get("findings", [{}])[0]
        if health_finding.get("automatic_repair") is not False:
            failures.append("validator findings must not imply automatic repair")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("OK: checked target adapter validator routing, scope, and evidence contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
