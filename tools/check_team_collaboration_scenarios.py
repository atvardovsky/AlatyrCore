#!/usr/bin/env python3
"""Exercise multi-actor and concurrent-update team collaboration scenarios."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from validate_target_adapter import AdapterValidatorConfig, Validator


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def validator(target: Path) -> Validator:
    return Validator(
        target,
        framework_source=None,
        diff_ref=None,
        approval_records=[],
        enforce_approval_scope=False,
        change_packages=[],
        enforce_change_package=False,
        migration_diff=None,
        allow_placeholders=False,
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
    )


def policy() -> dict[str, object]:
    actors = []
    for actor_id, display_name, roles in [
        ("alice", "Alice", ["implementer", "decision-owner"]),
        ("bob", "Bob", ["reviewer"]),
        ("codex", "Codex", ["assistant"]),
    ]:
        actors.append(
            {
                "id": actor_id,
                "display_name": display_name,
                "aliases": [display_name.casefold()],
                "actor_type": "ai-assistant" if actor_id == "codex" else "human",
                "status": "active",
                "teams": ["engineering"],
                "roles": roles,
                "responsibilities": ["fixture"],
                "decision_authority": ["delivery"] if actor_id == "alice" else [],
                "review_scopes": ["code"] if actor_id == "bob" else [],
                "priority_scopes": ["normal"] if actor_id == "alice" else [],
                "escalation_actor_id": "alice",
                "external_identity_refs": [],
            }
        )
    return {
        "schema_version": 1,
        "policy_kind": "target-team-policy",
        "project": "fixture",
        "module_state": "enabled",
        "policy_revision": "policy-1",
        "owner_actor_id": "alice",
        "last_reviewed": "2026-08-19",
        "review_cadence": "quarterly",
        "identity": {
            "local_identity_path": ".ai/local/team-identity.json",
            "selection_mode": "explicit-user-or-verified-provider",
            "unknown_actor_action": "propose-enrollment",
            "git_identity_is_authoritative": False,
            "authentication_boundary": "local-selection-is-attribution-not-authentication",
            "identity_proof_required_for": [],
        },
        "coordination_backend": {
            "mode": "repository",
            "canonical_task_source": "repository task records",
            "synchronization_direction": "manual",
            "branch_or_worktree_policy": "one branch per task",
            "claim_enforcement": "advisory",
            "claim_staleness_policy": "one day",
            "storage_policy": "repository",
            "retention_policy": "retain completed records",
            "privacy_policy": "no raw chat or secrets",
        },
        "actors": actors,
        "priorities": [
            {
                "id": "normal",
                "rank": "1",
                "meaning": "normal delivery",
                "assigner_actor_ids": ["alice"],
                "required_rationale": "required",
                "deadline_or_dependency_policy": "record dependencies",
                "preemption_rule": "owner decision",
                "escalation_rule": "alice",
            }
        ],
        "review_policy": {
            "implementer_reviewer_separation": "required",
            "owner_map": "repository owner map",
            "required_review_scopes": ["code"],
            "merge_authority_actor_ids": ["bob"],
            "merge_readiness_validation": "fixture validation",
        },
        "decision_owners": {
            "business": ["alice"],
            "architecture": ["alice"],
            "data": ["alice"],
            "security": ["alice"],
            "adapter": ["alice"],
        },
        "state_transitions": [
            {
                "from": "ready",
                "to": "active",
                "allowed_roles": ["implementer"],
                "required_evidence": ["active claim"],
            },
            {
                "from": "review",
                "to": "merge-ready",
                "allowed_roles": ["reviewer"],
                "required_evidence": ["review and validation"],
            },
        ],
        "conflict_policy": {
            "fact_overlap_source": ".ai/project/source-of-truth-registry.md",
            "consistency_map": ".ai/project/consistency-map.json",
            "shared_contract_policy": "coordinate",
            "sequencing_policy": "block unresolved overlap",
            "unresolved_overlap_action": "block",
        },
        "known_gaps": [],
    }


def backend() -> dict[str, object]:
    return {
        "schema_version": 1,
        "contract_kind": "target-team-backend-contract",
        "project": "fixture",
        "backend_id": "repository",
        "backend_mode": "repository",
        "provider": "repository",
        "canonical_task_source": "repository task records",
        "projection_direction": "task-records-to-index",
        "consistency_model": "strong",
        "write_strategy": "compare-and-swap",
        "capabilities": [
            "read-tasks",
            "create-task",
            "claim",
            "release",
            "checkpoint",
            "handoff",
            "review",
            "sync-status",
        ],
        "idempotency_policy": "task ID and expected revision",
        "conflict_policy": "reject revision mismatch",
        "unavailable_evidence_policy": "partial-or-unverified",
        "permission_policy": "adapter-only records",
        "authentication_policy": "local selection is not authentication",
        "extension_id": "none",
        "validation": "target adapter validator",
    }


def task() -> dict[str, object]:
    return {
        "schema_version": 2,
        "record_kind": "target-team-task",
        "id": "task-1",
        "record_revision": 1,
        "expected_revision": 1,
        "backend_revision": "backend-1",
        "goal": "Change fact-1 safely",
        "non_goals": [],
        "priority": "normal",
        "priority_rationale": "fixture",
        "priority_decided_by": "alice",
        "status": "active",
        "requested_by_actor_id": "alice",
        "owner_actor_id": "alice",
        "reviewer_actor_ids": ["bob"],
        "last_updated_by_actor_id": "alice",
        "assistant_actor_id": "codex",
        "parent_request": "fixture",
        "coordination_backend_ref": "task-1",
        "branch_or_worktree": "task-1",
        "base_revision": "base-1",
        "evidence_revision": "head-1",
        "allowed_actions": ["code-and-tests"],
        "context_profiles": ["code-local"],
        "project_areas": ["api"],
        "changed_fact_ids": ["fact-1"],
        "canonical_owner_refs": ["owner-1"],
        "expected_surfaces": ["src/api"],
        "dependencies": [],
        "blockers": [],
        "related_task_ids": [],
        "overlap": {
            "state": "none",
            "checked_at": "2026-08-19",
            "checked_revision": "head-1",
            "fact_ids": [],
            "contract_or_dependency_refs": [],
            "file_or_surface_refs": [],
            "resolution": "none",
        },
        "claim": {
            "mode": "advisory",
            "lease_id": "lease-1",
            "actor_id": "alice",
            "claimed_at": "2026-08-19T10:00:00Z",
            "heartbeat_at": "2026-08-19T10:05:00Z",
            "expires_at": "2026-08-20T10:00:00Z",
            "base_revision": "base-1",
            "backend_revision": "backend-1",
            "state": "active",
        },
        "transition": {
            "from": "ready",
            "to": "active",
            "changed_by_actor_id": "alice",
            "changed_at": "2026-08-19T10:00:00Z",
            "reason": "implementation started",
        },
        "approval_records": [],
        "review_state": "pending",
        "review_evidence_refs": [],
        "reviewed_head_revision": "none",
        "reviewed_base_revision": "none",
        "validation_state": "not-run",
        "latest_checkpoint": "none",
        "handoff_state": "none",
        "decision_records": [],
        "residual_risks": [],
        "next_action": "implement",
        "updated_at": "2026-08-19T10:00:00Z",
    }


def index_entry(task_record: dict[str, object]) -> dict[str, object]:
    return {
        "task_id": task_record["id"],
        "task_record": ".ai/assistant/team/tasks/task-1.json",
        "status": task_record["status"],
        "owner_actor_id": task_record["owner_actor_id"],
        "branch_or_worktree": task_record["branch_or_worktree"],
        "priority": task_record["priority"],
        "project_areas": task_record["project_areas"],
        "changed_fact_ids": task_record["changed_fact_ids"],
        "canonical_owner_refs": task_record["canonical_owner_refs"],
        "contract_or_dependency_refs": [],
        "expected_surfaces": task_record["expected_surfaces"],
        "record_revision": task_record["record_revision"],
        "backend_revision": task_record["backend_revision"],
    }


def write_fixture(target: Path, task_record: dict[str, object]) -> None:
    (target / ".ai/project").mkdir(parents=True, exist_ok=True)
    (target / ".ai/project/team-operating-model.md").write_text(
        "# Team Operating Model\n", encoding="utf-8"
    )
    write_json(target / ".ai/project/team-policy.json", policy())
    write_json(target / ".ai/assistant/team/backend-contract.json", backend())
    write_json(
        target / ".ai/assistant/team/work-registry.json",
        {
            "schema_version": 2,
            "registry_kind": "target-team-work-registry",
            "project": "fixture",
            "module_state": "enabled",
            "coordination_backend": "repository",
            "canonical_task_source": "repository task records",
            "synchronization_direction": "manual",
            "team_policy": ".ai/project/team-policy.json",
            "operating_model": ".ai/project/team-operating-model.md",
            "backend_contract": ".ai/assistant/team/backend-contract.json",
            "active_work_index": ".ai/assistant/team/active-work-index.json",
            "task_records_directory": ".ai/assistant/team/tasks",
            "task_record_template": ".ai/assistant/team/task-record-template.json",
            "registry_revision": 1,
            "updated_at": "2026-08-19T10:00:00Z",
            "evidence_revision": "unavailable",
            "storage_policy": "repository",
            "retention_policy": "retain completed records",
            "privacy_policy": "no raw chat or secrets",
        },
    )
    write_json(
        target / ".ai/assistant/team/active-work-index.json",
        {
            "schema_version": 1,
            "index_kind": "target-team-active-work-index",
            "project": "fixture",
            "module_state": "enabled",
            "source_registry": ".ai/assistant/team/work-registry.json",
            "source_revision": "1",
            "generated_at": "2026-08-19T10:00:00Z",
            "entries": [index_entry(task_record)],
        },
    )
    write_json(target / ".ai/assistant/team/tasks/task-1.json", task_record)
    write_json(
        target / ".ai/assistant/team/context-overlay.json",
        {
            "schema_version": 2,
            "overlay_kind": "target-team-context-overlay",
            "overlay_id": "team-active",
            "required_context": [".ai/assistant/team/active-work-index.json"],
            "conditional_context": [
                {"path": ".ai/framework/team-collaboration.md"},
                {"path": ".ai/project/team-policy.json"},
                {"path": ".ai/project/team-operating-model.md"},
                {"path": ".ai/assistant/team/work-registry.json"},
                {"path": ".ai/assistant/team/backend-contract.json"},
                {"path": ".ai/assistant/gates/team-collaboration.md"},
            ],
        },
    )
    write_json(
        target / ".ai/assistant/context-router.json",
        {
            "task_scale_overlays": {
                "team-active": {
                    "descriptor": ".ai/assistant/team/context-overlay.json"
                }
            }
        },
    )


def codes(target: Path) -> set[str]:
    check = validator(target)
    check.check_team_collaboration(None)
    return {finding.code for finding in check.findings}


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="alatyr-team-scenarios-") as directory:
        root = Path(directory)

        valid_target = root / "valid"
        valid_task = task()
        write_fixture(valid_target, valid_task)
        valid_codes = codes(valid_target)
        if valid_codes:
            failures.append(f"valid team fixture produced findings {sorted(valid_codes)}")

        revision_target = root / "revision-conflict"
        revision_task = copy.deepcopy(valid_task)
        revision_task["expected_revision"] = 0
        write_fixture(revision_target, revision_task)
        if "TEAM_TASK_REVISION_CONFLICT" not in codes(revision_target):
            failures.append("revision mismatch was not rejected")

        review_target = root / "self-review"
        review_task = copy.deepcopy(valid_task)
        review_task["reviewer_actor_ids"] = ["alice"]
        write_fixture(review_target, review_task)
        if "TEAM_REVIEWER_SEPARATION" not in codes(review_target):
            failures.append("required implementer/reviewer separation was not enforced")

        index_target = root / "stale-index"
        write_fixture(index_target, valid_task)
        index_path = index_target / ".ai/assistant/team/active-work-index.json"
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
        index_data["entries"] = []
        write_json(index_path, index_data)
        if "TEAM_ACTIVE_INDEX_INCOMPLETE" not in codes(index_target):
            failures.append("active task missing from compact index was not rejected")

        identity_target = root / "unknown-identity"
        write_fixture(identity_target, valid_task)
        (identity_target / ".ai/.gitignore").write_text("local/\n", encoding="utf-8")
        write_json(
            identity_target / ".ai/local/team-identity.json",
            {
                "schema_version": 1,
                "identity_kind": "local-team-identity",
                "actor_id": "unknown",
                "selected_at": "2026-08-19T10:00:00Z",
                "selected_by": "explicit-user-request",
                "policy_revision": "policy-1",
                "verification": "unverified-local-selection",
                "external_identity_ref": "none",
            },
        )
        if "TEAM_LOCAL_IDENTITY_UNKNOWN" not in codes(identity_target):
            failures.append("unknown local actor selection was not rejected")

        merge_target = root / "stale-review"
        merge_task = copy.deepcopy(valid_task)
        merge_task.update(
            {
                "status": "merge-ready",
                "review_state": "approved",
                "review_evidence_refs": ["review-1"],
                "validation_state": "passed",
                "reviewed_head_revision": "old-head",
                "reviewed_base_revision": "base-1",
                "transition": {
                    "from": "review",
                    "to": "merge-ready",
                    "changed_by_actor_id": "bob",
                    "changed_at": "2026-08-19T11:00:00Z",
                    "reason": "review complete",
                },
            }
        )
        write_fixture(merge_target, merge_task)
        if "TEAM_MERGE_READY_REVIEW_STALE" not in codes(merge_target):
            failures.append("merge-ready evidence with stale reviewed head was not rejected")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(
        "OK: checked valid collaboration plus revision conflict, self-review, "
        "stale index, unknown identity, and stale merge-review scenarios"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
