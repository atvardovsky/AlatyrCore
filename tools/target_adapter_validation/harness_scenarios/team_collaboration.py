"""Target-validator scenarios for team collaboration."""

from __future__ import annotations

from .common import (
    extract_list_field,
    scope_entries_cover,
    validator,
    write_json,
)


def run(target: Path, failures: list[str]) -> None:
    router_path = target / ".ai" / "assistant" / "context-router.json"
    team_model = target / ".ai" / "project" / "team-operating-model.md"
    team_model.write_text(
        (
            "# Team Operating Model\n\n"
            "### Actor `actor-owner`\n\n"
            "### Priority `normal`\n"
        ),
        encoding="utf-8",
    )
    write_json(
        target / ".ai" / "project" / "team-policy.json",
        {
            "schema_version": 1,
            "policy_kind": "target-team-policy",
            "policy_revision": "policy-1",
            "identity": {
                "local_identity_path": ".ai/local/team-identity.json",
                "git_identity_is_authoritative": False,
            },
            "actors": [
                {
                    "id": "actor-owner",
                    "display_name": "Owner",
                    "aliases": [],
                    "status": "active",
                    "teams": [],
                    "roles": ["owner"],
                    "responsibilities": [],
                    "decision_authority": [],
                    "review_scopes": [],
                    "priority_scopes": ["normal"],
                    "external_identity_refs": [],
                }
            ],
            "priorities": [
                {"id": "normal", "assigner_actor_ids": ["actor-owner"]}
            ],
            "review_policy": {
                "implementer_reviewer_separation": "required"
            },
            "state_transitions": [],
        },
    )
    write_json(
        target / ".ai" / "assistant" / "team" / "active-work-index.json",
        {
            "schema_version": 1,
            "index_kind": "target-team-active-work-index",
            "source_registry": ".ai/assistant/team/work-registry.json",
            "entries": [],
        },
    )
    write_json(
        target / ".ai" / "assistant" / "team" / "backend-contract.json",
        {
            "schema_version": 1,
            "contract_kind": "target-team-backend-contract",
            "backend_id": "repository",
            "backend_mode": "repository",
            "provider": "repository",
            "canonical_task_source": "registry",
            "projection_direction": "manual",
            "consistency_model": "manual",
            "write_strategy": "compare-and-swap",
            "capabilities": ["read-tasks"],
            "idempotency_policy": "task revision",
            "conflict_policy": "stop",
            "permission_policy": "adapter-only",
            "authentication_policy": "target",
            "validation": "fixture",
        },
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
