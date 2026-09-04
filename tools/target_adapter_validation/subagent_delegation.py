"""Subagent delegation capability validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from target_validation_support import is_placeholder
from target_adapter_validation.files import missing_target_files
from target_adapter_validation.capability import FunctionCapabilityModule
from target_adapter_validation.values import is_resolved_string


REQUIRED_PATHS = (
    ".ai/framework/task-decomposition.md",
    ".ai/framework/subagent-delegation.md",
    ".ai/assistant/task-decomposition.json",
    ".ai/assistant/delegation-policy.json",
    ".ai/assistant/context/task-scales/delegated-execution.json",
    ".ai/assistant/flows/subagent-delegation.flow.md",
    ".ai/assistant/prompts/worker-orchestration.md",
    ".ai/assistant/templates/subagent-task-packet.md",
    ".ai/assistant/templates/native-worker-binding.md",
    ".ai/assistant/templates/worker-execution-plan.md",
    ".ai/assistant/templates/worker-result.md",
    ".ai/assistant/workers/role-catalog.json",
    ".ai/assistant/workers/roles/explorer.md",
    ".ai/assistant/workers/roles/implementer.md",
    ".ai/assistant/workers/roles/test-runner.md",
    ".ai/assistant/workers/roles/documentation-worker.md",
    ".ai/assistant/workers/roles/reviewer.md",
    ".ai/assistant/workers/roles/fast-focused-worker.md",
    ".ai/assistant/assistant-capabilities.json",
    ".ai/assistant/bridge-capability-matrix.md",
)

POLICY_RELPATH = ".ai/assistant/delegation-policy.json"
TASK_DECOMPOSITION_RELPATH = ".ai/assistant/task-decomposition.json"
ROLE_CATALOG_RELPATH = ".ai/assistant/workers/role-catalog.json"
CAPABILITY_INDEX_RELPATH = ".ai/assistant/assistant-capabilities.json"
AI_ROUTER_RELPATH = ".ai/assistant/ai-infrastructure-router.json"
OVERLAY_RELPATH = ".ai/assistant/context/task-scales/delegated-execution.json"

CAPABILITY_FIELDS = {
    "route",
    "dispatch_backend",
    "external_dispatcher",
    "client_product",
    "runtime_variant",
    "native_subagents",
    "automatic_delegation",
    "explicit_delegation",
    "project_worker_definitions",
    "worker_definition_format",
    "worker_definition_paths",
    "tool_restrictions",
    "write_isolation",
    "background_execution",
    "nested_delegation",
    "model_override",
    "parallel_dispatch",
    "actual_model_evidence",
    "role_bindings",
    "verified_at",
    "client_version",
    "evidence",
    "expires_at",
    "review_triggers",
}

CAPABILITY_SUPPORT_FIELDS = {
    "route",
    "native_subagents",
    "automatic_delegation",
    "explicit_delegation",
    "project_worker_definitions",
    "tool_restrictions",
    "background_execution",
    "nested_delegation",
    "model_override",
    "parallel_dispatch",
    "actual_model_evidence",
}

SUPPORT_VALUES = {"supported", "unsupported", "unknown"}
DISPATCH_BACKENDS = {
    "native",
    "external",
    "suggestion-only",
    "unsupported",
    "unknown",
}
WRITE_ISOLATION_VALUES = {
    "shared-workspace",
    "native-isolated",
    "external-isolated",
    "unsupported",
    "unknown",
}
ROLE_ACTION_CEILINGS = {"read-only", "docs-only", "adapter-only", "code-and-tests"}
ROLE_STATES = {"enabled", "disabled", "blocked"}
ROLE_WRITE_MODES = {"none", "bounded"}
WORKER_ELIGIBLE_LEVELS = {"L1", "L2", "L3", "L4", "L5"}
SELECTION_MODES = {"explicit-model", "inherit", "client-default"}
EXPECTED_CONFLICTS = {
    "overlapping_writes": "reject-concurrent-dispatch",
    "contradictory_results": "return-to-primary",
    "stale_baseline": "revalidate-before-integration",
    "scope_violation": "reject-result",
}
REQUIRED_GUARDS = {
    "primary_keeps_critical_path",
    "independent_local_acceptance",
    "disjoint_write_scope",
    "primary_final_convergence",
    "current_capability_evidence",
}
EXPECTED_RESULT_POLICY = {
    "accept_out_of_scope_changes": False,
    "accept_unvalidated_changes": False,
    "require_primary_review": True,
    "require_actual_model_or_unverified_status": True,
    "require_normalized_worker_result": True,
}
CANONICAL_WORKER_REFERENCES = (
    ".ai/assistant/task-decomposition.json",
    ".ai/assistant/delegation-policy.json",
    ".ai/assistant/prompts/worker-orchestration.md",
    ".ai/assistant/workers/role-catalog.json",
)
REQUIRED_WORKER_CONTEXT = {
    ".ai/assistant/task-decomposition.json",
    ".ai/assistant/delegation-policy.json",
    ".ai/assistant/workers/role-catalog.json",
    ".ai/assistant/prompts/worker-orchestration.md",
    ".ai/assistant/templates/worker-execution-plan.md",
    ".ai/assistant/templates/subagent-task-packet.md",
    ".ai/assistant/templates/worker-result.md",
}


def validate_subagent_delegation(validator: Any, manifest: Any) -> None:
    self = validator
    if manifest is None or not _manifest_enables_delegation(manifest):
        return

    _validate_required_files(self)
    policy = self.load_json_object(
        self.target_path(POLICY_RELPATH), "DELEGATION_POLICY"
    )
    if policy is None:
        return

    concrete_enabled_roles = _validate_policy(self, policy)
    catalog_roles = _load_and_validate_role_catalog(self)
    surfaces = _load_capability_surfaces(self)
    ai_item_ids = _load_ai_item_ids(self)
    capability_records = _validate_surface_capabilities(self, surfaces, ai_item_ids)
    role_ids, writable_role_ids, role_states = _validate_roles(self, catalog_roles)
    _validate_enabled_roles(self, concrete_enabled_roles, role_ids, role_states)
    _validate_role_bindings(
        self,
        surfaces,
        capability_records,
        role_ids,
        writable_role_ids,
        concrete_enabled_roles,
    )
    _validate_overlay(self)


SUBAGENT_DELEGATION_MODULE = FunctionCapabilityModule(
    "check_subagent_delegation", validate_subagent_delegation
)


def _manifest_enables_delegation(manifest: Any) -> bool:
    enabled = {scalar.value for scalar in manifest.lists.get(("modules", "enabled"), [])}
    return "subagent-delegation" in enabled


def _validate_required_files(self: Any) -> None:
    for relpath in missing_target_files(self, REQUIRED_PATHS):
        self.error(
            "DELEGATION_REQUIRED_FILE_MISSING",
            "enabled subagent delegation is missing a required contract",
            relpath,
        )


def _validate_policy(self: Any, policy: dict[str, Any]) -> list[str]:
    _validate_policy_identity(self, policy)
    concrete_enabled_roles = _validate_policy_roles(self, policy)
    _validate_retry_policy(self, policy)
    _validate_conflict_policy(self, policy)
    _validate_required_guards(self, policy)
    _validate_result_policy(self, policy)
    return concrete_enabled_roles


def _validate_policy_identity(self: Any, policy: dict[str, Any]) -> None:
    if policy.get("schema_version") != 2:
        self.error(
            "DELEGATION_POLICY_SCHEMA",
            "delegation policy schema_version must be 2",
            POLICY_RELPATH,
        )
    if policy.get("policy_kind") != "target-subagent-delegation-policy":
        self.error(
            "DELEGATION_POLICY_KIND",
            "delegation policy kind is invalid",
            POLICY_RELPATH,
        )
    state = policy.get("state")
    if is_resolved_string(state) and state not in {"enabled", "suggest-only"}:
        self.error(
            "DELEGATION_POLICY_STATE",
            "enabled module requires enabled or suggest-only policy state",
            POLICY_RELPATH,
        )
    decision_mode = policy.get("decision_mode")
    if is_resolved_string(decision_mode) and decision_mode not in {"automatic", "suggest-only"}:
        self.error(
            "DELEGATION_DECISION_MODE",
            "enabled delegation decision_mode must be automatic or suggest-only",
            POLICY_RELPATH,
        )
    preference = policy.get("default_preference")
    if is_resolved_string(preference) and preference not in {
        "auto",
        "allow",
        "forbid",
        "require-supported",
    }:
        self.error(
            "DELEGATION_DEFAULT_PREFERENCE",
            "delegation default_preference is invalid",
            POLICY_RELPATH,
        )
    parallel = policy.get("max_parallel_delegates")
    if not is_placeholder(parallel) and (
        not isinstance(parallel, int) or isinstance(parallel, bool) or parallel < 1
    ):
        self.error(
            "DELEGATION_PARALLEL_LIMIT",
            "max_parallel_delegates must be a positive integer",
            POLICY_RELPATH,
        )
    if policy.get("role_catalog") != ROLE_CATALOG_RELPATH:
        self.error(
            "DELEGATION_ROLE_CATALOG_PATH",
            "delegation policy must select the canonical target role catalog",
            POLICY_RELPATH,
        )
    if policy.get("decomposition_policy") != TASK_DECOMPOSITION_RELPATH:
        self.error(
            "DELEGATION_DECOMPOSITION_POLICY",
            "delegation policy must reference the task-decomposition policy",
            POLICY_RELPATH,
        )


def _validate_policy_roles(self: Any, policy: dict[str, Any]) -> list[str]:
    enabled_role_ids = policy.get("enabled_role_ids")
    if not isinstance(enabled_role_ids, list) or not enabled_role_ids:
        self.error(
            "DELEGATION_ENABLED_ROLES",
            "enabled delegation requires a non-empty enabled_role_ids list",
            POLICY_RELPATH,
        )
        enabled_role_ids = []
    concrete_enabled_roles = [value for value in enabled_role_ids if is_resolved_string(value)]
    if len(concrete_enabled_roles) != len(set(concrete_enabled_roles)):
        self.error(
            "DELEGATION_ENABLED_ROLE_DUPLICATE",
            "enabled_role_ids contains duplicates",
            POLICY_RELPATH,
        )
    return concrete_enabled_roles


def _validate_retry_policy(self: Any, policy: dict[str, Any]) -> None:
    retry_policy = policy.get("retry_policy")
    if not isinstance(retry_policy, dict):
        self.error(
            "DELEGATION_RETRY_POLICY",
            "enabled delegation requires a retry policy",
            POLICY_RELPATH,
        )
        return
    attempts = retry_policy.get("max_attempts_per_task")
    if not is_placeholder(attempts) and (
        not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 0
    ):
        self.error(
            "DELEGATION_RETRY_LIMIT",
            "max_attempts_per_task must be zero or a positive integer",
            POLICY_RELPATH,
        )
    if retry_policy.get("retry_only_when_scope_unchanged") is not True:
        self.error(
            "DELEGATION_RETRY_SCOPE",
            "retry policy must forbid scope expansion",
            POLICY_RELPATH,
        )


def _validate_conflict_policy(self: Any, policy: dict[str, Any]) -> None:
    conflict_policy = policy.get("conflict_policy")
    if not isinstance(conflict_policy, dict) or any(
        conflict_policy.get(field) != expected
        for field, expected in EXPECTED_CONFLICTS.items()
    ):
        self.error(
            "DELEGATION_CONFLICT_GUARDS",
            "delegation conflict policy weakens portable rejection rules",
            POLICY_RELPATH,
        )


def _validate_required_guards(self: Any, policy: dict[str, Any]) -> None:
    requirements = policy.get("requirements")
    if not isinstance(requirements, dict) or any(
        requirements.get(field) is not True for field in REQUIRED_GUARDS
    ):
        self.error(
            "DELEGATION_REQUIRED_GUARDS",
            "delegation policy must retain every primary and isolation guard",
            POLICY_RELPATH,
        )


def _validate_result_policy(self: Any, policy: dict[str, Any]) -> None:
    result_policy = policy.get("result_policy")
    if not isinstance(result_policy, dict) or any(
        result_policy.get(field) is not expected
        for field, expected in EXPECTED_RESULT_POLICY.items()
    ):
        self.error(
            "DELEGATION_RESULT_GUARDS",
            "delegation result policy weakens primary review or scope evidence",
            POLICY_RELPATH,
        )


def _load_and_validate_role_catalog(self: Any) -> list[Any]:
    catalog = self.load_json_object(
        self.target_path(ROLE_CATALOG_RELPATH), "DELEGATION_ROLE_CATALOG"
    )
    catalog_roles = catalog.get("roles") if isinstance(catalog, dict) else None
    if not isinstance(catalog_roles, list) or not catalog_roles:
        self.error(
            "DELEGATION_ROLES_MISSING",
            "enabled delegation requires a non-empty target worker role catalog",
            ROLE_CATALOG_RELPATH,
        )
        catalog_roles = []
    if isinstance(catalog, dict) and (
        catalog.get("schema_version") != 1
        or catalog.get("catalog_kind") != "target-worker-role-catalog"
    ):
        self.error(
            "DELEGATION_ROLE_CATALOG_SCHEMA",
            "worker role catalog identity or schema is invalid",
            ROLE_CATALOG_RELPATH,
        )
    if isinstance(catalog, dict) and catalog.get("decomposition_policy") != TASK_DECOMPOSITION_RELPATH:
        self.error(
            "DELEGATION_ROLE_CATALOG_DECOMPOSITION_POLICY",
            "worker role catalog must reference the task-decomposition policy",
            ROLE_CATALOG_RELPATH,
        )
    return catalog_roles


def _load_capability_surfaces(self: Any) -> dict[str, str]:
    capability_index = self.load_json_object(
        self.target_path(CAPABILITY_INDEX_RELPATH), "DELEGATION_CAPABILITY_INDEX"
    )
    surfaces = capability_index.get("surfaces") if isinstance(capability_index, dict) else None
    if not isinstance(surfaces, dict) or not surfaces:
        self.error(
            "DELEGATION_CAPABILITY_SURFACES",
            "enabled delegation requires assistant capability surface records",
            CAPABILITY_INDEX_RELPATH,
        )
        return {}
    return {
        key: value
        for key, value in surfaces.items()
        if isinstance(key, str) and isinstance(value, str)
    }


def _load_ai_item_ids(self: Any) -> set[str]:
    ai_router = self.load_json_object(
        self.target_path(AI_ROUTER_RELPATH), "DELEGATION_AI_ROUTER"
    )
    ai_items = ai_router.get("items") if isinstance(ai_router, dict) else []
    return {
        item.get("id")
        for item in ai_items
        if isinstance(item, dict) and is_resolved_string(item.get("id"))
    }


def _validate_surface_capabilities(
    self: Any, surfaces: dict[str, str], ai_item_ids: set[str]
) -> dict[str, dict[str, Any]]:
    capability_records: dict[str, dict[str, Any]] = {}
    for surface_id, relpath in surfaces.items():
        record = self.load_json_object(
            self.target_path(relpath), "DELEGATION_SURFACE_CAPABILITY"
        )
        delegation = record.get("subagent_delegation") if record else None
        if not isinstance(delegation, dict):
            self.error(
                "DELEGATION_CAPABILITY_MISSING",
                f"assistant surface {surface_id} has no delegation capability",
                relpath,
            )
            continue
        _validate_surface_capability(self, surface_id, relpath, delegation, ai_item_ids)
        capability_records[surface_id] = delegation
    return capability_records


def _validate_surface_capability(
    self: Any,
    surface_id: str,
    relpath: str,
    delegation: dict[str, Any],
    ai_item_ids: set[str],
) -> None:
    missing = sorted(CAPABILITY_FIELDS - set(delegation))
    if missing:
        self.error(
            "DELEGATION_CAPABILITY_FIELDS",
            f"assistant surface {surface_id} is missing {missing}",
            relpath,
        )
    for field in CAPABILITY_SUPPORT_FIELDS:
        value = delegation.get(field)
        if is_resolved_string(value) and value not in SUPPORT_VALUES:
            self.error(
                "DELEGATION_CAPABILITY_VALUE",
                f"assistant surface {surface_id} {field} is invalid",
                relpath,
            )
    _validate_backend(self, surface_id, relpath, delegation, ai_item_ids)
    _validate_write_isolation(self, surface_id, relpath, delegation)
    _validate_worker_definition_paths(self, surface_id, relpath, delegation)


def _validate_backend(
    self: Any,
    surface_id: str,
    relpath: str,
    delegation: dict[str, Any],
    ai_item_ids: set[str],
) -> None:
    backend = delegation.get("dispatch_backend")
    if is_resolved_string(backend) and backend not in DISPATCH_BACKENDS:
        self.error(
            "DELEGATION_DISPATCH_BACKEND",
            f"assistant surface {surface_id} dispatch_backend is invalid",
            relpath,
        )
    dispatcher = delegation.get("external_dispatcher")
    if backend == "native":
        _validate_native_backend(self, surface_id, relpath, delegation)
    if backend == "external":
        if not is_resolved_string(dispatcher) or dispatcher not in ai_item_ids:
            self.error(
                "DELEGATION_EXTERNAL_DISPATCHER",
                f"assistant surface {surface_id} external dispatcher must reference a routed AI-infrastructure item",
                relpath,
            )
        if delegation.get("route") != "supported":
            self.error(
                "DELEGATION_EXTERNAL_ROUTE_UNSUPPORTED",
                f"assistant surface {surface_id} external dispatch requires a supported route",
                relpath,
            )
    if backend == "unsupported" and delegation.get("route") == "supported":
        self.error(
            "DELEGATION_UNSUPPORTED_ROUTE_CONFLICT",
            f"assistant surface {surface_id} cannot claim a supported route with an unsupported backend",
            relpath,
        )


def _validate_native_backend(
    self: Any, surface_id: str, relpath: str, delegation: dict[str, Any]
) -> None:
    if delegation.get("route") != "supported":
        self.error(
            "DELEGATION_NATIVE_ROUTE_UNSUPPORTED",
            f"assistant surface {surface_id} native dispatch requires a supported route",
            relpath,
        )
    if delegation.get("native_subagents") != "supported":
        self.error(
            "DELEGATION_NATIVE_BACKEND_UNSUPPORTED",
            f"assistant surface {surface_id} selects native dispatch without native worker evidence",
            relpath,
        )
    if not any(
        delegation.get(field) == "supported"
        for field in ["automatic_delegation", "explicit_delegation"]
    ):
        self.error(
            "DELEGATION_NATIVE_INVOCATION_UNSUPPORTED",
            f"assistant surface {surface_id} selects native dispatch without a verified invocation mode",
            relpath,
        )


def _validate_write_isolation(
    self: Any, surface_id: str, relpath: str, delegation: dict[str, Any]
) -> None:
    write_isolation = delegation.get("write_isolation")
    if is_resolved_string(write_isolation) and write_isolation not in WRITE_ISOLATION_VALUES:
        self.error(
            "DELEGATION_WRITE_ISOLATION",
            f"assistant surface {surface_id} write_isolation is invalid",
            relpath,
        )


def _validate_worker_definition_paths(
    self: Any, surface_id: str, relpath: str, delegation: dict[str, Any]
) -> None:
    definition_paths = delegation.get("worker_definition_paths")
    if not isinstance(definition_paths, list):
        self.error(
            "DELEGATION_WORKER_DEFINITION_PATHS",
            f"assistant surface {surface_id} worker_definition_paths must be a list",
            relpath,
        )
        definition_paths = []
    concrete_definition_paths = [value for value in definition_paths if is_resolved_string(value)]
    if delegation.get("project_worker_definitions") == "supported":
        if not is_resolved_string(delegation.get("worker_definition_format")):
            self.error(
                "DELEGATION_WORKER_DEFINITION_FORMAT",
                f"assistant surface {surface_id} supports project worker definitions but has no format",
                relpath,
            )
        if not concrete_definition_paths:
            self.error(
                "DELEGATION_WORKER_DEFINITION_PATHS",
                f"assistant surface {surface_id} supports project worker definitions but has no target paths",
                relpath,
            )
    elif concrete_definition_paths:
        self.error(
            "DELEGATION_WORKER_DEFINITION_STATE_CONFLICT",
            f"assistant surface {surface_id} records native worker paths without supported project definitions",
            relpath,
        )
    for definition_path in concrete_definition_paths:
        _validate_worker_definition_path(self, surface_id, relpath, delegation, definition_path)


def _validate_worker_definition_path(
    self: Any,
    surface_id: str,
    relpath: str,
    delegation: dict[str, Any],
    definition_path: str,
) -> None:
    candidate = Path(definition_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        self.error(
            "DELEGATION_WORKER_DEFINITION_PATH",
            f"assistant surface {surface_id} has an unsafe native worker definition path",
            relpath,
        )
    elif (
        delegation.get("project_worker_definitions") == "supported"
        and not self.target_path(definition_path).is_file()
    ):
        self.error(
            "DELEGATION_WORKER_DEFINITION_MISSING",
            f"assistant surface {surface_id} native worker definition is missing",
            definition_path,
        )
    elif delegation.get("project_worker_definitions") == "supported":
        native_text = self.read_text(self.target_path(definition_path))
        for canonical_reference in CANONICAL_WORKER_REFERENCES:
            if canonical_reference not in native_text:
                self.error(
                    "DELEGATION_WORKER_DEFINITION_NOT_THIN",
                    f"assistant surface {surface_id} native worker definition does not route to {canonical_reference}",
                    definition_path,
                )


def _validate_roles(
    self: Any, catalog_roles: list[Any]
) -> tuple[set[str], set[str], dict[str, str]]:
    role_ids: set[str] = set()
    writable_role_ids: set[str] = set()
    role_states: dict[str, str] = {}
    for index, role in enumerate(catalog_roles):
        if not isinstance(role, dict):
            self.error(
                "DELEGATION_ROLE_SHAPE",
                f"roles[{index}] must be an object",
                ROLE_CATALOG_RELPATH,
            )
            continue
        _validate_role(self, index, role, role_ids, writable_role_ids, role_states)
    return role_ids, writable_role_ids, role_states


def _validate_role(
    self: Any,
    index: int,
    role: dict[str, Any],
    role_ids: set[str],
    writable_role_ids: set[str],
    role_states: dict[str, str],
) -> None:
    role_id = role.get("id")
    if is_resolved_string(role_id):
        if role_id in role_ids:
            self.error(
                "DELEGATION_ROLE_DUPLICATE",
                f"duplicate delegation role {role_id}",
                ROLE_CATALOG_RELPATH,
            )
        role_ids.add(role_id)
    state_value = role.get("state")
    if is_resolved_string(state_value) and state_value not in ROLE_STATES:
        self.error(
            "DELEGATION_ROLE_STATE",
            f"roles[{index}].state is invalid",
            ROLE_CATALOG_RELPATH,
        )
    if is_resolved_string(role_id) and is_resolved_string(state_value):
        role_states[role_id] = state_value
    action_ceiling = role.get("action_ceiling")
    if is_resolved_string(action_ceiling) and action_ceiling not in ROLE_ACTION_CEILINGS:
        self.error(
            "DELEGATION_ROLE_ACTION_CEILING",
            f"roles[{index}].action_ceiling is invalid",
            ROLE_CATALOG_RELPATH,
        )
    write_mode = role.get("write_mode")
    if is_resolved_string(write_mode) and write_mode not in ROLE_WRITE_MODES:
        self.error(
            "DELEGATION_ROLE_WRITE_MODE",
            f"roles[{index}].write_mode is invalid",
            ROLE_CATALOG_RELPATH,
        )
    if write_mode == "bounded" and is_resolved_string(role_id):
        writable_role_ids.add(role_id)
    if _role_write_ceiling_conflicts(action_ceiling, write_mode):
        self.error(
            "DELEGATION_ROLE_WRITE_CEILING_CONFLICT",
            f"roles[{index}] action ceiling and write mode disagree",
            ROLE_CATALOG_RELPATH,
        )
    _validate_role_prompt(self, index, role)
    if role.get("required_output") != "normalized-worker-result":
        self.error(
            "DELEGATION_ROLE_RESULT_CONTRACT",
            f"roles[{index}] must require normalized-worker-result",
            ROLE_CATALOG_RELPATH,
        )
    levels = role.get("implementation_levels")
    if not isinstance(levels, list) or not levels:
        self.error(
            "DELEGATION_ROLE_IMPLEMENTATION_LEVELS",
            f"roles[{index}] must declare worker-eligible implementation levels",
            ROLE_CATALOG_RELPATH,
        )
    else:
        invalid_levels = sorted(
            {
                level
                for level in levels
                if not isinstance(level, str) or level not in WORKER_ELIGIBLE_LEVELS
            }
        )
        if invalid_levels:
            self.error(
                "DELEGATION_ROLE_IMPLEMENTATION_LEVEL",
                f"roles[{index}] has invalid implementation levels {invalid_levels}",
                ROLE_CATALOG_RELPATH,
            )


def _role_write_ceiling_conflicts(action_ceiling: Any, write_mode: Any) -> bool:
    return (
        is_resolved_string(action_ceiling)
        and is_resolved_string(write_mode)
        and (
            (action_ceiling == "read-only" and write_mode != "none")
            or (action_ceiling != "read-only" and write_mode != "bounded")
        )
    )


def _validate_role_prompt(self: Any, index: int, role: dict[str, Any]) -> None:
    prompt = role.get("prompt")
    if not is_resolved_string(prompt):
        return
    prompt_path = Path(prompt)
    if (
        prompt_path.is_absolute()
        or ".." in prompt_path.parts
        or not self.target_path(prompt).is_file()
    ):
        self.error(
            "DELEGATION_ROLE_PROMPT",
            f"roles[{index}] prompt is unsafe or missing",
            ROLE_CATALOG_RELPATH,
        )


def _validate_enabled_roles(
    self: Any,
    concrete_enabled_roles: list[str],
    role_ids: set[str],
    role_states: dict[str, str],
) -> None:
    for role_id in concrete_enabled_roles:
        if role_id not in role_ids:
            self.error(
                "DELEGATION_ENABLED_ROLE_UNKNOWN",
                f"enabled role {role_id} is absent from the role catalog",
                POLICY_RELPATH,
            )
        elif role_states.get(role_id) != "enabled":
            self.error(
                "DELEGATION_ENABLED_ROLE_INACTIVE",
                f"enabled role {role_id} is not enabled in the role catalog",
                POLICY_RELPATH,
            )


def _validate_role_bindings(
    self: Any,
    surfaces: dict[str, str],
    capability_records: dict[str, dict[str, Any]],
    role_ids: set[str],
    writable_role_ids: set[str],
    concrete_enabled_roles: list[str],
) -> None:
    for surface_id, capability in capability_records.items():
        relpath = surfaces.get(surface_id, CAPABILITY_INDEX_RELPATH)
        bindings = capability.get("role_bindings")
        if not isinstance(bindings, list):
            self.error(
                "DELEGATION_ROLE_BINDINGS",
                f"assistant surface {surface_id} role_bindings must be a list",
                relpath,
            )
            continue
        bound_roles: set[str] = set()
        for index, binding in enumerate(bindings):
            _validate_role_binding(
                self, surface_id, relpath, capability, index, binding, role_ids, bound_roles
            )
        _validate_required_bindings(
            self,
            surface_id,
            relpath,
            capability,
            concrete_enabled_roles,
            bound_roles,
            writable_role_ids,
        )


def _validate_role_binding(
    self: Any,
    surface_id: str,
    relpath: str,
    capability: dict[str, Any],
    index: int,
    binding: Any,
    role_ids: set[str],
    bound_roles: set[str],
) -> None:
    if not isinstance(binding, dict):
        self.error(
            "DELEGATION_ROLE_BINDING_SHAPE",
            f"assistant surface {surface_id} role_bindings[{index}] must be an object",
            relpath,
        )
        return
    role_id = binding.get("role_id")
    if is_resolved_string(role_id):
        if role_id not in role_ids:
            self.error(
                "DELEGATION_ROLE_BINDING_UNKNOWN",
                f"assistant surface {surface_id} binds unknown role {role_id}",
                relpath,
            )
        if role_id in bound_roles:
            self.error(
                "DELEGATION_ROLE_BINDING_DUPLICATE",
                f"assistant surface {surface_id} binds role {role_id} more than once",
                relpath,
            )
        bound_roles.add(role_id)
    _validate_role_binding_mode(self, surface_id, relpath, capability, binding)


def _validate_role_binding_mode(
    self: Any,
    surface_id: str,
    relpath: str,
    capability: dict[str, Any],
    binding: dict[str, Any],
) -> None:
    selection_mode = binding.get("selection_mode")
    if is_resolved_string(selection_mode) and selection_mode not in SELECTION_MODES:
        self.error(
            "DELEGATION_MODEL_SELECTION_MODE",
            f"assistant surface {surface_id} role binding selection_mode is invalid",
            relpath,
        )
    availability = binding.get("availability")
    if is_resolved_string(availability) and availability not in SUPPORT_VALUES:
        self.error(
            "DELEGATION_ROLE_BINDING_AVAILABILITY",
            f"assistant surface {surface_id} role binding availability is invalid",
            relpath,
        )
    if selection_mode == "explicit-model" and capability.get("model_override") != "supported":
        self.error(
            "DELEGATION_MODEL_OVERRIDE_UNSUPPORTED",
            f"assistant surface {surface_id} selects a model without supported override evidence",
            relpath,
        )
    if availability == "supported" and capability.get("route") != "supported":
        self.error(
            "DELEGATION_ROLE_BINDING_ROUTE_CONFLICT",
            f"assistant surface {surface_id} has an available role binding on an unsupported route",
            relpath,
        )
    if selection_mode == "explicit-model" and not is_resolved_string(binding.get("model")):
        self.error(
            "DELEGATION_EXPLICIT_MODEL_MISSING",
            f"assistant surface {surface_id} explicit role binding has no model",
            relpath,
        )


def _validate_required_bindings(
    self: Any,
    surface_id: str,
    relpath: str,
    capability: dict[str, Any],
    concrete_enabled_roles: list[str],
    bound_roles: set[str],
    writable_role_ids: set[str],
) -> None:
    if (
        capability.get("dispatch_backend") in {"native", "external"}
        and capability.get("route") == "supported"
        and concrete_enabled_roles
        and not set(concrete_enabled_roles).intersection(bound_roles)
    ):
        self.error(
            "DELEGATION_ENABLED_ROLE_UNBOUND",
            f"assistant surface {surface_id} has no binding for an enabled worker role",
            relpath,
        )
    if (
        capability.get("parallel_dispatch") == "supported"
        and capability.get("write_isolation") == "shared-workspace"
        and writable_role_ids.intersection(bound_roles)
    ):
        self.warn(
            "DELEGATION_SHARED_WRITE_ISOLATION",
            f"assistant surface {surface_id} can parallelize writable roles only with packet-level disjoint-write enforcement",
            relpath,
        )


def _validate_overlay(self: Any) -> None:
    overlay = self.load_json_object(
        self.target_path(OVERLAY_RELPATH), "DELEGATION_OVERLAY"
    )
    if overlay is not None and (
        overlay.get("id") != "delegated-execution"
        or overlay.get("required_module") != "subagent-delegation"
    ):
        self.error(
            "DELEGATION_OVERLAY_CONTRACT",
            "delegated execution overlay identity or module is invalid",
            OVERLAY_RELPATH,
        )
    overlay_context = overlay.get("required_context") if overlay else None
    if not isinstance(overlay_context, list) or not REQUIRED_WORKER_CONTEXT.issubset(
        set(overlay_context)
    ):
        self.error(
            "DELEGATION_OVERLAY_CONTEXT",
            "delegated execution overlay does not load the portable worker contracts",
            OVERLAY_RELPATH,
        )
