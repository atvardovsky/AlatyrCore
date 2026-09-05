"""Validate target-owned team collaboration support."""

from __future__ import annotations

from typing import Any

from target_adapter_validation.capability import (
    CapabilityValidationContext,
    FunctionCapabilityModule,
)
from target_validation_support import (
    ManifestData,
    is_placeholder,
    is_unresolved_value,
)


def validate_team_collaboration(
    context: CapabilityValidationContext,
    manifest: ManifestData | None,
) -> None:
    policy_key = ("team_collaboration", "policy")
    model_key = ("team_collaboration", "operating_model")
    source_model_key = ("source_of_truth", "team_operating_model")
    registry_key = ("team_collaboration", "work_registry")
    index_key = ("team_collaboration", "active_work_index")
    backend_key = ("team_collaboration", "backend_contract")
    tasks_key = ("team_collaboration", "task_records_directory")
    local_identity_key = ("team_collaboration", "local_identity")
    policy_scalar = manifest.scalars.get(policy_key) if manifest else None
    model_scalar = manifest.scalars.get(model_key) if manifest else None
    if not model_scalar and manifest:
        model_scalar = manifest.scalars.get(source_model_key)
    registry_scalar = manifest.scalars.get(registry_key) if manifest else None
    index_scalar = manifest.scalars.get(index_key) if manifest else None
    backend_scalar = manifest.scalars.get(backend_key) if manifest else None
    tasks_scalar = manifest.scalars.get(tasks_key) if manifest else None
    local_identity_scalar = (
        manifest.scalars.get(local_identity_key) if manifest else None
    )
    policy_relpath = (
        policy_scalar.value if policy_scalar else ".ai/project/team-policy.json"
    )
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
    index_relpath = (
        index_scalar.value
        if index_scalar
        else ".ai/assistant/team/active-work-index.json"
    )
    backend_relpath = (
        backend_scalar.value
        if backend_scalar
        else ".ai/assistant/team/backend-contract.json"
    )
    tasks_relpath = (
        tasks_scalar.value
        if tasks_scalar
        else ".ai/assistant/team/tasks"
    )
    local_identity_relpath = (
        local_identity_scalar.value
        if local_identity_scalar
        else ".ai/local/team-identity.json"
    )
    policy_path = context.target_path(policy_relpath)
    model_path = context.target_path(model_relpath)
    registry_path = context.target_path(registry_relpath)
    index_path = context.target_path(index_relpath)
    backend_path = context.target_path(backend_relpath)
    tasks_path = context.target_path(tasks_relpath)
    local_identity_path = context.target_path(local_identity_relpath)

    if not policy_path.exists() and not model_path.exists() and not registry_path.exists():
        return
    if not policy_path.is_file():
        context.error(
            "TEAM_POLICY_MISSING",
            "team collaboration exists without its structured target policy",
            policy_relpath,
        )
        return
    if not model_path.is_file():
        context.error(
            "TEAM_OPERATING_MODEL_MISSING",
            "team work registry exists without its target-owned operating model",
            model_relpath,
        )
        return
    if not registry_path.is_file():
        context.error(
            "TEAM_REGISTRY_MISSING",
            "team operating model exists without its machine-readable work registry",
            registry_relpath,
        )
        return

    for path, relpath, code, message in [
        (
            index_path,
            index_relpath,
            "TEAM_ACTIVE_INDEX_MISSING",
            "team collaboration requires a compact active-work index",
        ),
        (
            backend_path,
            backend_relpath,
            "TEAM_BACKEND_CONTRACT_MISSING",
            "team collaboration requires a backend capability contract",
        ),
    ]:
        if not path.is_file():
            context.error(code, message, relpath)
            return

    policy = context.load_json_object(policy_path, "TEAM_POLICY")
    active_index = context.load_json_object(index_path, "TEAM_ACTIVE_INDEX")
    backend = context.load_json_object(backend_path, "TEAM_BACKEND")
    if policy is None or active_index is None or backend is None:
        return

    registry = context.load_json_object(registry_path, "TEAM_REGISTRY")
    if registry is None:
        return
    registry_schema = registry.get("schema_version")
    if registry_schema == 1:
        context.error(
            "TEAM_REGISTRY_MIGRATION_REQUIRED",
            "schema-1 monolithic task records must be migrated atomically to "
            "schema-2 per-task records before team writes",
            registry_relpath,
        )
    elif registry_schema != 2:
        context.error(
            "TEAM_REGISTRY_SCHEMA",
            "schema_version should be 2",
            registry_relpath,
        )
    if registry.get("registry_kind") != "target-team-work-registry":
        context.error(
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
        "team_policy",
        "operating_model",
        "backend_contract",
        "active_work_index",
        "task_records_directory",
        "task_record_template",
        "updated_at",
        "evidence_revision",
        "storage_policy",
        "retention_policy",
        "privacy_policy",
    ]
    for field in metadata_fields:
        value = registry.get(field)
        if not isinstance(value, str) or not value.strip():
            context.error(
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
            context.error(
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
                context.error(
                    "TEAM_ENABLED_METADATA_UNRESOLVED",
                    f"enabled team module requires resolved {field}",
                    registry_relpath,
                )
    if registry.get("operating_model") != model_relpath:
        context.error(
            "TEAM_REGISTRY_OPERATING_MODEL",
            f"operating_model should point to {model_relpath}",
            registry_relpath,
        )

    for field, expected in [
        ("team_policy", policy_relpath),
        ("backend_contract", backend_relpath),
        ("active_work_index", index_relpath),
        ("task_records_directory", tasks_relpath),
    ]:
        if registry_schema == 2 and registry.get(field) != expected:
            context.error(
                "TEAM_REGISTRY_PATH",
                f"{field} should point to {expected}",
                registry_relpath,
            )
    if registry_schema == 2 and not isinstance(
        registry.get("registry_revision"), int
    ):
        context.error(
            "TEAM_REGISTRY_REVISION",
            "schema-2 registry_revision must be an integer",
            registry_relpath,
        )
    if registry_schema == 2 and "tasks" in registry:
        context.error(
            "TEAM_REGISTRY_MONOLITHIC_TASKS",
            "schema-2 registry must not contain a monolithic tasks array",
            registry_relpath,
        )

    if policy.get("schema_version") != 1:
        context.error("TEAM_POLICY_SCHEMA", "schema_version should be 1", policy_relpath)
    if policy.get("policy_kind") != "target-team-policy":
        context.error(
            "TEAM_POLICY_KIND",
            "policy_kind should be target-team-policy",
            policy_relpath,
        )
    identity_policy = policy.get("identity")
    if not isinstance(identity_policy, dict):
        context.error("TEAM_IDENTITY_POLICY", "identity must be an object", policy_relpath)
        identity_policy = {}
    else:
        if identity_policy.get("local_identity_path") != local_identity_relpath:
            context.error(
                "TEAM_LOCAL_IDENTITY_PATH",
                f"local identity path should be {local_identity_relpath}",
                policy_relpath,
            )
        if identity_policy.get("git_identity_is_authoritative") is not False:
            context.error(
                "TEAM_GIT_IDENTITY_AUTHORITY",
                "Git identity must not be authoritative for team actor selection",
                policy_relpath,
            )

    actors = policy.get("actors")
    if not isinstance(actors, list):
        context.error("TEAM_ACTORS_SHAPE", "actors must be a list", policy_relpath)
        actors = []
    actor_by_id: dict[str, dict[str, Any]] = {}
    actor_aliases: dict[str, set[str]] = {}
    for index, actor in enumerate(actors):
        label = f"actors[{index}]"
        if not isinstance(actor, dict):
            context.error("TEAM_ACTOR_SHAPE", f"{label} must be an object", policy_relpath)
            continue
        actor_id = actor.get("id")
        if not isinstance(actor_id, str) or not actor_id:
            context.error("TEAM_ACTOR_ID", f"{label}.id must be a string", policy_relpath)
            continue
        if is_placeholder(actor_id):
            continue
        if actor_id in actor_by_id:
            context.error("TEAM_ACTOR_DUPLICATE", f"duplicate actor {actor_id}", policy_relpath)
        actor_by_id[actor_id] = actor
        raw_aliases = actor.get("aliases")
        names = [
            actor.get("display_name"),
            *(raw_aliases if isinstance(raw_aliases, list) else []),
        ]
        for name in names:
            if isinstance(name, str) and name and not is_placeholder(name):
                actor_aliases.setdefault(name.casefold(), set()).add(actor_id)
        for field in [
            "aliases",
            "teams",
            "roles",
            "responsibilities",
            "decision_authority",
            "review_scopes",
            "priority_scopes",
            "external_identity_refs",
        ]:
            values = actor.get(field)
            if not isinstance(values, list) or not all(
                isinstance(value, str) and value for value in values
            ):
                context.error(
                    "TEAM_ACTOR_LIST",
                    f"{label}.{field} must be a string list",
                    policy_relpath,
                )
    actor_ids = set(actor_by_id)

    priorities = policy.get("priorities")
    if not isinstance(priorities, list):
        context.error("TEAM_PRIORITIES_SHAPE", "priorities must be a list", policy_relpath)
        priorities = []
    priority_by_id = {
        item.get("id"): item
        for item in priorities
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and not is_placeholder(item["id"])
    }
    priority_ids = set(priority_by_id)

    if active_index.get("schema_version") != 1:
        context.error("TEAM_ACTIVE_INDEX_SCHEMA", "schema_version should be 1", index_relpath)
    if active_index.get("index_kind") != "target-team-active-work-index":
        context.error(
            "TEAM_ACTIVE_INDEX_KIND",
            "index_kind should be target-team-active-work-index",
            index_relpath,
        )
    if active_index.get("source_registry") != registry_relpath:
        context.error(
            "TEAM_ACTIVE_INDEX_REGISTRY",
            f"source_registry should point to {registry_relpath}",
            index_relpath,
        )
    index_entries = active_index.get("entries")
    if not isinstance(index_entries, list):
        context.error("TEAM_ACTIVE_INDEX_ENTRIES", "entries must be a list", index_relpath)
        index_entries = []

    if backend.get("schema_version") != 1:
        context.error("TEAM_BACKEND_SCHEMA", "schema_version should be 1", backend_relpath)
    if backend.get("contract_kind") != "target-team-backend-contract":
        context.error(
            "TEAM_BACKEND_KIND",
            "contract_kind should be target-team-backend-contract",
            backend_relpath,
        )
    capabilities = backend.get("capabilities")
    if not isinstance(capabilities, list) or not all(
        isinstance(value, str) and value for value in capabilities
    ):
        context.error(
            "TEAM_BACKEND_CAPABILITIES",
            "capabilities must be a string list",
            backend_relpath,
        )
    for field in [
        "backend_id",
        "backend_mode",
        "provider",
        "canonical_task_source",
        "projection_direction",
        "consistency_model",
        "write_strategy",
        "idempotency_policy",
        "conflict_policy",
        "permission_policy",
        "authentication_policy",
        "validation",
    ]:
        value = backend.get(field)
        if not isinstance(value, str) or not value.strip():
            context.error(
                "TEAM_BACKEND_FIELD",
                f"{field} must be a non-empty string",
                backend_relpath,
            )

    tasks: list[Any] = []
    task_sources: list[str] = []
    if registry_schema == 1:
        legacy_tasks = registry.get("tasks")
        if isinstance(legacy_tasks, list):
            tasks = legacy_tasks
            task_sources = [registry_relpath] * len(tasks)
    elif tasks_path.is_dir():
        for task_path in sorted(tasks_path.glob("*.json")):
            task_record = context.load_json_object(task_path, "TEAM_TASK")
            if task_record is not None:
                tasks.append(task_record)
                task_sources.append(context.rel(task_path))

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
        "record_kind",
        "backend_revision",
        "goal",
        "priority",
        "priority_rationale",
        "priority_decided_by",
        "status",
        "requested_by_actor_id",
        "owner_actor_id",
        "last_updated_by_actor_id",
        "assistant_actor_id",
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
    current_head = context.git.head_revision()

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
            context.error(
                "TEAM_ACTOR_UNKNOWN",
                f"{label} references actor {value!r} absent from the operating model",
                registry_relpath,
            )

    for index, task in enumerate(tasks):
        label = f"tasks[{index}]"
        task_source = (
            task_sources[index]
            if index < len(task_sources)
            else registry_relpath
        )
        if not isinstance(task, dict):
            context.error(
                "TEAM_TASK_SHAPE",
                f"{label} must be an object",
                registry_relpath,
            )
            continue
        if registry_schema == 2:
            if task.get("schema_version") != 2:
                context.error(
                    "TEAM_TASK_SCHEMA",
                    f"{label}.schema_version should be 2",
                    task_source,
                )
            if task.get("record_kind") != "target-team-task":
                context.error(
                    "TEAM_TASK_KIND",
                    f"{label}.record_kind should be target-team-task",
                    task_source,
                )
            record_revision = task.get("record_revision")
            expected_revision = task.get("expected_revision")
            if not isinstance(record_revision, int) or record_revision < 0:
                context.error(
                    "TEAM_TASK_RECORD_REVISION",
                    f"{label}.record_revision must be a non-negative integer",
                    task_source,
                )
            if not isinstance(expected_revision, int) or expected_revision < 0:
                context.error(
                    "TEAM_TASK_EXPECTED_REVISION",
                    f"{label}.expected_revision must be a non-negative integer",
                    task_source,
                )
            if (
                isinstance(record_revision, int)
                and isinstance(expected_revision, int)
                and expected_revision != record_revision
            ):
                context.error(
                    "TEAM_TASK_REVISION_CONFLICT",
                    f"{label} expected revision does not match current record revision",
                    task_source,
                )
        for field in required_strings:
            value = task.get(field)
            if not isinstance(value, str) or not value.strip():
                context.error(
                    "TEAM_TASK_FIELD",
                    f"{label}.{field} must be a non-empty string",
                    registry_relpath,
                )
        for field in list_fields:
            values = task.get(field)
            if not isinstance(values, list) or not all(
                isinstance(value, str) and value for value in values
            ):
                context.error(
                    "TEAM_TASK_LIST",
                    f"{label}.{field} must be a string list",
                    registry_relpath,
                )
                continue
            if field == "allowed_actions":
                context.check_allowed_actions(
                    values,
                    registry_relpath,
                    f"{label}.{field}",
                )

        task_id = task.get("id")
        if concrete(task_id):
            if task_id in task_ids:
                context.error(
                    "TEAM_TASK_DUPLICATE",
                    f"duplicate task id {task_id}",
                    registry_relpath,
                )
            task_ids.add(task_id)

        status = task.get("status")
        if concrete(status) and status not in task_statuses:
            context.error(
                "TEAM_TASK_STATUS",
                f"{label}.status is invalid: {status}",
                registry_relpath,
            )
        priority = task.get("priority")
        if concrete(priority) and priority not in priority_ids:
            context.error(
                "TEAM_PRIORITY_UNKNOWN",
                f"{label}.priority references {priority!r} absent from the operating model",
                registry_relpath,
            )
        review_state = task.get("review_state")
        if concrete(review_state) and review_state not in review_states:
            context.error(
                "TEAM_REVIEW_STATE",
                f"{label}.review_state is invalid: {review_state}",
                registry_relpath,
            )
        validation_state = task.get("validation_state")
        if concrete(validation_state) and validation_state not in validation_states:
            context.error(
                "TEAM_VALIDATION_STATE",
                f"{label}.validation_state is invalid: {validation_state}",
                registry_relpath,
            )
        handoff_state = task.get("handoff_state")
        if concrete(handoff_state) and handoff_state not in handoff_states:
            context.error(
                "TEAM_HANDOFF_STATE",
                f"{label}.handoff_state is invalid: {handoff_state}",
                registry_relpath,
            )

        check_actor(task.get("owner_actor_id"), f"{label}.owner_actor_id")
        check_actor(
            task.get("requested_by_actor_id"),
            f"{label}.requested_by_actor_id",
        )
        check_actor(
            task.get("last_updated_by_actor_id"),
            f"{label}.last_updated_by_actor_id",
        )
        check_actor(
            task.get("assistant_actor_id"),
            f"{label}.assistant_actor_id",
        )
        check_actor(task.get("priority_decided_by"), f"{label}.priority_decided_by")
        reviewers = task.get("reviewer_actor_ids")
        if isinstance(reviewers, list):
            for reviewer_index, reviewer in enumerate(reviewers):
                check_actor(
                    reviewer,
                    f"{label}.reviewer_actor_ids[{reviewer_index}]",
                )

        priority_decider = task.get("priority_decided_by")
        priority_policy = priority_by_id.get(priority)
        if isinstance(priority_policy, dict) and concrete(priority_decider):
            assigners = priority_policy.get("assigner_actor_ids")
            if isinstance(assigners, list) and any(concrete(item) for item in assigners):
                if priority_decider not in assigners:
                    context.error(
                        "TEAM_PRIORITY_AUTHORITY",
                        f"{label}.priority_decided_by lacks authority for {priority}",
                        task_source,
                    )

        review_policy = policy.get("review_policy")
        if isinstance(review_policy, dict) and review_policy.get(
            "implementer_reviewer_separation"
        ) == "required":
            owner = task.get("owner_actor_id")
            if concrete(owner) and isinstance(reviewers, list) and owner in reviewers:
                context.error(
                    "TEAM_REVIEWER_SEPARATION",
                    f"{label} assigns its implementer as reviewer",
                    task_source,
                )

        overlap = task.get("overlap")
        overlap_state: Any = None
        if not isinstance(overlap, dict):
            context.error(
                "TEAM_OVERLAP_SHAPE",
                f"{label}.overlap must be an object",
                registry_relpath,
            )
        else:
            overlap_state = overlap.get("state")
            for field in ["state", "checked_at", "checked_revision", "resolution"]:
                value = overlap.get(field)
                if not isinstance(value, str) or not value.strip():
                    context.error(
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
                    context.error(
                        "TEAM_OVERLAP_LIST",
                        f"{label}.overlap.{field} must be a string list",
                        registry_relpath,
                    )
            if concrete(overlap_state) and overlap_state not in overlap_states:
                context.error(
                    "TEAM_OVERLAP_STATE",
                    f"{label}.overlap.state is invalid: {overlap_state}",
                    registry_relpath,
                )

        claim = task.get("claim")
        claim_state: Any = None
        if not isinstance(claim, dict):
            context.error(
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
                *(
                    ["lease_id", "heartbeat_at", "backend_revision"]
                    if registry_schema == 2
                    else []
                ),
            ]:
                value = claim.get(field)
                if not isinstance(value, str) or not value.strip():
                    context.error(
                        "TEAM_CLAIM_FIELD",
                        f"{label}.claim.{field} must be a non-empty string",
                        registry_relpath,
                    )
            if concrete(claim_state) and claim_state not in claim_states:
                context.error(
                    "TEAM_CLAIM_STATE",
                    f"{label}.claim.state is invalid: {claim_state}",
                    registry_relpath,
                )
            claim_mode = claim.get("mode")
            if concrete(claim_mode) and claim_mode not in {
                "advisory",
                "target-enforced",
            }:
                context.error(
                    "TEAM_CLAIM_MODE",
                    f"{label}.claim.mode is invalid: {claim_mode}",
                    registry_relpath,
                )
            check_actor(claim.get("actor_id"), f"{label}.claim.actor_id")
            if claim_state == "active":
                for field in [
                    "actor_id",
                    "claimed_at",
                    "base_revision",
                    *(["lease_id"] if registry_schema == 2 else []),
                ]:
                    if not concrete(claim.get(field)):
                        context.error(
                            "TEAM_ACTIVE_CLAIM_INCOMPLETE",
                            f"{label}.claim.{field} is required for an active claim",
                            registry_relpath,
                        )

        if registry_schema == 2:
            transition = task.get("transition")
            if not isinstance(transition, dict):
                context.error(
                    "TEAM_TRANSITION_SHAPE",
                    f"{label}.transition must be an object",
                    task_source,
                )
            else:
                transition_from = transition.get("from")
                transition_to = transition.get("to")
                transition_actor = transition.get("changed_by_actor_id")
                check_actor(
                    transition_actor,
                    f"{label}.transition.changed_by_actor_id",
                )
                if concrete(transition_to) and transition_to != status:
                    context.error(
                        "TEAM_TRANSITION_STATUS",
                        f"{label}.transition.to must match task status",
                        task_source,
                    )
                transitions = policy.get("state_transitions")
                if (
                    concrete(transition_from)
                    and concrete(transition_to)
                    and isinstance(transitions, list)
                ):
                    matching = [
                        item
                        for item in transitions
                        if isinstance(item, dict)
                        and item.get("from") == transition_from
                        and item.get("to") == transition_to
                    ]
                    if not matching:
                        context.error(
                            "TEAM_TRANSITION_NOT_ALLOWED",
                            f"{label} transition {transition_from} -> {transition_to} "
                            "is absent from the team policy",
                            task_source,
                        )

        if status in {"claimed", "active"} and claim_state != "active":
            context.warn(
                "TEAM_ACTIVE_TASK_WITHOUT_CLAIM",
                f"{label} is {status} without an active claim",
                registry_relpath,
            )
        if status in {"complete", "cancelled"} and claim_state == "active":
            context.warn(
                "TEAM_TERMINAL_TASK_ACTIVE_CLAIM",
                f"{label} is {status} but still has an active claim",
                registry_relpath,
            )
        if status in {"claimed", "active", "review", "merge-ready"} and overlap_state in {
            "conflicting",
            "unresolved",
        }:
            report = context.error if status == "merge-ready" else context.warn
            report(
                "TEAM_ACTIVE_OVERLAP_BLOCKED",
                f"{label} is {status} with {overlap_state} overlap",
                registry_relpath,
            )

        task_revision = task.get("evidence_revision")
        if status == "merge-ready":
            if review_state not in {"approved", "not-required"}:
                context.error(
                    "TEAM_MERGE_READY_REVIEW",
                    f"{label} is merge-ready without approved or explicitly "
                    "not-required review state",
                    registry_relpath,
                )
            review_evidence = task.get("review_evidence_refs")
            if not isinstance(review_evidence, list) or not any(
                concrete(reference) for reference in review_evidence
            ):
                context.error(
                    "TEAM_MERGE_READY_REVIEW_EVIDENCE",
                    f"{label} is merge-ready without review evidence",
                    registry_relpath,
                )
            if validation_state != "passed":
                context.error(
                    "TEAM_MERGE_READY_VALIDATION",
                    f"{label} is merge-ready without passed validation",
                    registry_relpath,
                )
            if overlap_state not in {"none", "compatible"}:
                context.error(
                    "TEAM_MERGE_READY_OVERLAP",
                    f"{label} is merge-ready without resolved overlap",
                    registry_relpath,
                )
            if review_state == "approved" and (
                not isinstance(reviewers, list)
                or not any(concrete(reviewer) for reviewer in reviewers)
            ):
                context.error(
                    "TEAM_MERGE_READY_REVIEWERS",
                    f"{label} has approved review state without a recorded reviewer",
                    registry_relpath,
                )
            for field in ["base_revision", "evidence_revision"]:
                if not concrete(task.get(field)):
                    context.error(
                        "TEAM_MERGE_READY_REVISION",
                        f"{label}.{field} is required for merge-ready evidence",
                        registry_relpath,
                    )
            if registry_schema == 2:
                reviewed_head = task.get("reviewed_head_revision")
                reviewed_base = task.get("reviewed_base_revision")
                if not concrete(reviewed_head) or not concrete(reviewed_base):
                    context.error(
                        "TEAM_MERGE_READY_REVIEW_REVISIONS",
                        f"{label} must record reviewed head and base revisions",
                        task_source,
                    )
                elif reviewed_head != task_revision or reviewed_base != task.get(
                    "base_revision"
                ):
                    context.error(
                        "TEAM_MERGE_READY_REVIEW_STALE",
                        f"{label} review revisions do not match task evidence",
                        task_source,
                    )
            if (
                current_head
                and concrete(task_revision)
                and not context.git.refs_match(str(task_revision), current_head)
            ):
                context.warn(
                    "TEAM_MERGE_READY_STALE",
                    f"{label} evidence revision does not match this checkout's "
                    "HEAD; confirm its selected branch or worktree before merge",
                    registry_relpath,
                )

    for alias, matching_ids in actor_aliases.items():
        if len(matching_ids) > 1:
            context.warn(
                "TEAM_ACTOR_ALIAS_AMBIGUOUS",
                f"actor name or alias {alias!r} resolves to multiple actor IDs",
                policy_relpath,
            )

    index_ids: set[str] = set()
    for index, entry in enumerate(index_entries):
        label = f"entries[{index}]"
        if not isinstance(entry, dict):
            context.error(
                "TEAM_ACTIVE_INDEX_ENTRY",
                f"{label} must be an object",
                index_relpath,
            )
            continue
        entry_id = entry.get("task_id")
        if not concrete(entry_id):
            context.error(
                "TEAM_ACTIVE_INDEX_TASK_ID",
                f"{label}.task_id must be a concrete string",
                index_relpath,
            )
            continue
        if entry_id in index_ids:
            context.error(
                "TEAM_ACTIVE_INDEX_DUPLICATE",
                f"duplicate active task {entry_id}",
                index_relpath,
            )
        index_ids.add(str(entry_id))
        for field in [
            "task_record",
            "status",
            "owner_actor_id",
            "branch_or_worktree",
            "record_revision",
            "backend_revision",
        ]:
            if field not in entry:
                context.error(
                    "TEAM_ACTIVE_INDEX_FIELD",
                    f"{label} missing {field}",
                    index_relpath,
                )
        for field in [
            "project_areas",
            "changed_fact_ids",
            "canonical_owner_refs",
            "contract_or_dependency_refs",
            "expected_surfaces",
        ]:
            values = entry.get(field)
            if not isinstance(values, list) or not all(
                isinstance(value, str) and value for value in values
            ):
                context.error(
                    "TEAM_ACTIVE_INDEX_LIST",
                    f"{label}.{field} must be a string list",
                    index_relpath,
                )

    active_statuses = {
        "ready",
        "claimed",
        "active",
        "blocked",
        "review",
        "merge-ready",
        "stale",
    }
    local_active_ids = {
        str(task.get("id"))
        for task in tasks
        if isinstance(task, dict)
        and concrete(task.get("id"))
        and task.get("status") in active_statuses
    }
    backend_mode = backend.get("backend_mode")
    if registry_schema == 2 and backend_mode in {"repository", "both"}:
        missing_from_index = sorted(local_active_ids - index_ids)
        extra_in_index = sorted(index_ids - local_active_ids)
        if missing_from_index:
            context.error(
                "TEAM_ACTIVE_INDEX_INCOMPLETE",
                f"active-work index misses task records {missing_from_index}",
                index_relpath,
            )
        if extra_in_index:
            context.error(
                "TEAM_ACTIVE_INDEX_STALE",
                f"active-work index references absent or inactive tasks {extra_in_index}",
                index_relpath,
            )

    if local_identity_path.is_file():
        local_identity = context.load_json_object(
            local_identity_path,
            "TEAM_LOCAL_IDENTITY",
        )
        if local_identity is not None:
            if local_identity.get("schema_version") != 1:
                context.error(
                    "TEAM_LOCAL_IDENTITY_SCHEMA",
                    "schema_version should be 1",
                    local_identity_relpath,
                )
            if local_identity.get("identity_kind") != "local-team-identity":
                context.error(
                    "TEAM_LOCAL_IDENTITY_KIND",
                    "identity_kind should be local-team-identity",
                    local_identity_relpath,
                )
            selected_actor = local_identity.get("actor_id")
            if concrete(selected_actor):
                if selected_actor not in actor_by_id:
                    context.error(
                        "TEAM_LOCAL_IDENTITY_UNKNOWN",
                        f"selected actor {selected_actor!r} is absent from team policy",
                        local_identity_relpath,
                    )
                elif actor_by_id[selected_actor].get("status") != "active":
                    context.error(
                        "TEAM_LOCAL_IDENTITY_INACTIVE",
                        f"selected actor {selected_actor!r} is not active",
                        local_identity_relpath,
                    )
            selected_policy_revision = local_identity.get("policy_revision")
            current_policy_revision = policy.get("policy_revision")
            if (
                concrete(selected_policy_revision)
                and concrete(current_policy_revision)
                and selected_policy_revision != current_policy_revision
            ):
                context.warn(
                    "TEAM_LOCAL_IDENTITY_STALE",
                    "local actor selection was made against another policy revision",
                    local_identity_relpath,
                )
            if local_identity.get("selected_by") != "explicit-user-request":
                context.error(
                    "TEAM_LOCAL_IDENTITY_SELECTION",
                    "local actor selection must record an explicit user request",
                    local_identity_relpath,
                )
        ignore_path = context.target_path(".ai/.gitignore")
        if not ignore_path.is_file() or "local/" not in context.read_text(ignore_path):
            context.error(
                "TEAM_LOCAL_IDENTITY_NOT_IGNORED",
                ".ai/local must be ignored before storing local identity",
                ".ai/.gitignore",
            )

    registry_revision = registry.get("evidence_revision")
    if (
        current_head
        and concrete(registry_revision)
        and not context.git.refs_match(str(registry_revision), current_head)
    ):
        context.warn(
            "TEAM_REGISTRY_REVISION_STALE",
            "team work registry evidence revision does not match current HEAD",
            registry_relpath,
        )

    router_path = context.target_path(".ai/assistant/context-router.json")
    router = context.load_json_object(router_path, "ROUTER")
    overlay_route = (
        router.get("task_scale_overlays", {}).get("team-active")
        if isinstance(router, dict)
        and isinstance(router.get("task_scale_overlays"), dict)
        else None
    )
    if not isinstance(overlay_route, dict):
        context.error(
            "TEAM_CONTEXT_OVERLAY_MISSING",
            "enabled team artifacts require the team-active context overlay",
            ".ai/assistant/context-router.json",
        )
        return
    descriptor = overlay_route.get("descriptor")
    if not isinstance(descriptor, str) or not descriptor:
        context.error(
            "TEAM_CONTEXT_OVERLAY_DESCRIPTOR",
            "team-active must identify its lazy descriptor",
            ".ai/assistant/context-router.json",
        )
        return
    overlay = context.load_json_object(
        context.target_path(descriptor),
        "TEAM_CONTEXT_OVERLAY",
    )
    if overlay is not None:
        if overlay.get("schema_version") != 2:
            context.error(
                "TEAM_CONTEXT_OVERLAY_SCHEMA",
                "schema_version should be 2",
                descriptor,
            )
        if overlay.get("overlay_kind") != "target-team-context-overlay":
            context.error(
                "TEAM_CONTEXT_OVERLAY_KIND",
                "overlay_kind should be target-team-context-overlay",
                descriptor,
            )
        if overlay.get("overlay_id") != "team-active":
            context.error(
                "TEAM_CONTEXT_OVERLAY_ID",
                "overlay_id should be team-active",
                descriptor,
            )
        required_context = overlay.get("required_context")
        if not isinstance(required_context, list):
            context.error(
                "TEAM_CONTEXT_OVERLAY_SHAPE",
                "team-active required_context must be a list",
                descriptor,
            )
        else:
            if required_context != [index_relpath]:
                context.error(
                    "TEAM_CONTEXT_OVERLAY_PREFLIGHT",
                    "team-active required_context should contain only the "
                    "compact active-work index",
                    descriptor,
                )
        conditional_context = overlay.get("conditional_context")
        if not isinstance(conditional_context, list):
            context.error(
                "TEAM_CONTEXT_OVERLAY_CONDITIONAL",
                "team-active conditional_context must be a list",
                descriptor,
            )
        else:
            conditional_paths = {
                entry.get("path")
                for entry in conditional_context
                if isinstance(entry, dict)
            }
            for required_path in [
                ".ai/framework/team-collaboration.md",
                policy_relpath,
                model_relpath,
                registry_relpath,
                backend_relpath,
                ".ai/assistant/gates/team-collaboration.md",
            ]:
                if required_path not in conditional_paths:
                    context.error(
                        "TEAM_CONTEXT_OVERLAY_PATH",
                        f"team-active conditional context is missing {required_path}",
                        descriptor,
                    )


TEAM_COLLABORATION_MODULE = FunctionCapabilityModule(
    check_id="check_team_collaboration",
    validator=validate_team_collaboration,
)
