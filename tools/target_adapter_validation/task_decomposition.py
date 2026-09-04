"""Task-decomposition contract validation."""

from __future__ import annotations

from typing import Any

from target_adapter_validation.files import missing_target_files
from target_validation_support import expect_string_list


POLICY_RELPATH = ".ai/assistant/task-decomposition.json"
PLAN_RELPATH = ".ai/assistant/templates/task-decomposition.md"
ROUTER_RELPATH = ".ai/assistant/context-router.json"
OPERATION_REQUEST_RELPATH = ".ai/assistant/templates/operation-request.md"
OPERATION_COMPLETION_RELPATH = (
    ".ai/assistant/templates/operation-completion-evidence.json"
)
OPERATION_ROUTING_RELPATH = ".ai/assistant/flows/operation-routing.flow.md"
DELEGATION_POLICY_RELPATH = ".ai/assistant/delegation-policy.json"
ROLE_CATALOG_RELPATH = ".ai/assistant/workers/role-catalog.json"

REQUIRED_PATHS = (
    ".ai/framework/task-decomposition.md",
    POLICY_RELPATH,
    PLAN_RELPATH,
)
LEVEL_IDS = ["L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7"]
LEVEL_REQUIRED_FIELDS = {
    "id",
    "name",
    "use_when",
    "allowed_actions",
    "default_executor",
    "worker_roles",
    "delegation",
    "quality_gate",
}
WORKER_ELIGIBLE_LEVELS = {"L1", "L2", "L3", "L4", "L5"}
PRIMARY_ONLY_LEVELS = {"L0", "L6", "L7"}
KNOWN_WORKER_ROLES = {
    "explorer",
    "implementer",
    "test-runner",
    "documentation-worker",
    "reviewer",
    "fast-focused-worker",
}
REQUIRED_ROUTER_RECEIPT = "task decomposition id and implementation levels"
REQUIRED_QUALITY_GATES = {
    "one_level_per_task",
    "reject_dependency_cycles",
    "reject_overlapping_parallel_writes",
    "primary_owns_semantic_decisions",
    "primary_owns_final_convergence",
    "delegation_cannot_broaden_authorization",
    "escalate_on_new_relationship",
    "escalate_on_failed_validation",
    "escalation_loads_only_triggering_context",
}


def validate_task_decomposition(validator: Any, manifest: Any) -> None:
    """Validate installed decomposition routing, policy, and evidence surfaces."""

    self = validator
    for relpath in missing_target_files(self, REQUIRED_PATHS):
        self.error(
            "TASK_DECOMPOSITION_REQUIRED_FILE_MISSING",
            "installed adapter is missing a required task-decomposition contract",
            relpath,
        )

    policy = self.load_json_object(
        self.target_path(POLICY_RELPATH), "TASK_DECOMPOSITION_POLICY"
    )
    if isinstance(policy, dict):
        _validate_policy(self, policy)

    router = self.load_json_object(self.target_path(ROUTER_RELPATH), "CONTEXT_ROUTER")
    if isinstance(router, dict):
        _validate_router(self, router)

    _require_template_text(
        self,
        PLAN_RELPATH,
        [
            "Implementation level:",
            "Executor decision:",
            "Selected worker role:",
            "Dependency cycles:",
            "## Primary Convergence",
        ],
    )
    _require_template_text(
        self,
        OPERATION_REQUEST_RELPATH,
        [
            "Task decomposition preference:",
            "Existing task decomposition plan:",
            ".ai/assistant/task-decomposition.json",
        ],
    )
    if self.target_path(OPERATION_COMPLETION_RELPATH).is_file():
        completion = self.load_json_object(
            self.target_path(OPERATION_COMPLETION_RELPATH),
            "OPERATION_COMPLETION_EVIDENCE",
        )
        if not isinstance(completion, dict) or not isinstance(
            completion.get("task_decomposition"), dict
        ):
            self.error(
                "TASK_DECOMPOSITION_COMPLETION_EVIDENCE",
                "operation completion evidence must record task decomposition",
                OPERATION_COMPLETION_RELPATH,
            )
    _require_template_text(
        self,
        OPERATION_ROUTING_RELPATH,
        [
            ".ai/assistant/templates/task-decomposition.md",
            "implementation level",
            "decomposition plan",
        ],
        required=False,
    )

    if self.target_path(DELEGATION_POLICY_RELPATH).is_file():
        _validate_delegation_composition(self)


def _validate_policy(self: Any, policy: dict[str, Any]) -> None:
    if policy.get("schema_version") != 1:
        self.error(
            "TASK_DECOMPOSITION_POLICY_SCHEMA",
            "task-decomposition policy schema_version must be 1",
            POLICY_RELPATH,
        )
    if policy.get("policy_kind") != "target-task-decomposition-policy":
        self.error(
            "TASK_DECOMPOSITION_POLICY_KIND",
            "task-decomposition policy kind is invalid",
            POLICY_RELPATH,
        )
    if policy.get("portable_rule") != ".ai/framework/task-decomposition.md":
        self.error(
            "TASK_DECOMPOSITION_PORTABLE_RULE",
            "task-decomposition policy must reference the portable rule owner",
            POLICY_RELPATH,
        )
    if policy.get("plan_template") != PLAN_RELPATH:
        self.error(
            "TASK_DECOMPOSITION_PLAN_TEMPLATE",
            "task-decomposition policy must reference the canonical plan template",
            POLICY_RELPATH,
        )
    if "non-trivial" not in str(policy.get("default_behavior", "")):
        self.error(
            "TASK_DECOMPOSITION_DEFAULT_BEHAVIOR",
            "task-decomposition policy must name non-trivial request behavior",
            POLICY_RELPATH,
        )
    expect_string_list(
        policy.get("decomposition_order"),
        self,
        "TASK_DECOMPOSITION_ORDER",
        POLICY_RELPATH,
        label="task_decomposition.decomposition_order",
    )

    levels = policy.get("levels")
    if not isinstance(levels, list):
        self.error(
            "TASK_DECOMPOSITION_LEVELS",
            "task-decomposition policy levels must be a list",
            POLICY_RELPATH,
        )
        return
    level_ids = [
        level.get("id")
        for level in levels
        if isinstance(level, dict) and isinstance(level.get("id"), str)
    ]
    if level_ids != LEVEL_IDS:
        self.error(
            "TASK_DECOMPOSITION_LEVEL_ORDER",
            "task-decomposition levels must be exactly L0 through L7",
            POLICY_RELPATH,
        )
    for level in levels:
        if not isinstance(level, dict):
            self.error(
                "TASK_DECOMPOSITION_LEVEL_SHAPE",
                "each task-decomposition level must be an object",
                POLICY_RELPATH,
            )
            continue
        missing = sorted(LEVEL_REQUIRED_FIELDS - set(level))
        if missing:
            self.error(
                "TASK_DECOMPOSITION_LEVEL_FIELDS",
                f"task-decomposition level {level.get('id', '<unknown>')} missing {missing}",
                POLICY_RELPATH,
            )
        level_id = level.get("id")
        roles = level.get("worker_roles")
        if not isinstance(roles, list):
            self.error(
                "TASK_DECOMPOSITION_WORKER_ROLES",
                f"task-decomposition level {level_id} worker_roles must be a list",
                POLICY_RELPATH,
            )
            roles = []
        role_set = {role for role in roles if isinstance(role, str)}
        unknown_roles = sorted(role_set - KNOWN_WORKER_ROLES)
        if unknown_roles:
            self.error(
                "TASK_DECOMPOSITION_WORKER_ROLE_UNKNOWN",
                f"task-decomposition level {level_id} references unknown worker roles {unknown_roles}",
                POLICY_RELPATH,
            )
        if level_id in PRIMARY_ONLY_LEVELS and role_set:
            self.error(
                "TASK_DECOMPOSITION_PRIMARY_ONLY_LEVEL",
                f"task-decomposition level {level_id} must remain primary-only",
                POLICY_RELPATH,
            )
        if level_id in {"L6", "L7"} and "not-allowed" not in str(
            level.get("delegation", "")
        ):
            self.error(
                "TASK_DECOMPOSITION_PROTECTED_DELEGATION",
                f"task-decomposition level {level_id} must not allow delegation",
                POLICY_RELPATH,
            )
        if level_id in PRIMARY_ONLY_LEVELS and level.get("default_executor") != "primary":
            self.error(
                "TASK_DECOMPOSITION_DEFAULT_EXECUTOR",
                f"task-decomposition level {level_id} default executor must be primary",
                POLICY_RELPATH,
            )
        if level_id in WORKER_ELIGIBLE_LEVELS and not isinstance(
            level.get("quality_gate"), str
        ):
            self.error(
                "TASK_DECOMPOSITION_QUALITY_GATE",
                f"task-decomposition level {level_id} must define a quality gate",
                POLICY_RELPATH,
            )

    quality = policy.get("quality_gates")
    if not isinstance(quality, dict):
        self.error(
            "TASK_DECOMPOSITION_QUALITY_GATES",
            "task-decomposition policy must define quality_gates",
            POLICY_RELPATH,
        )
    else:
        for gate in sorted(REQUIRED_QUALITY_GATES):
            if quality.get(gate) is not True:
                self.error(
                    "TASK_DECOMPOSITION_QUALITY_GATE",
                    f"task-decomposition quality gate {gate} must be true",
                    POLICY_RELPATH,
                )


def _validate_router(self: Any, router: dict[str, Any]) -> None:
    decomposition = router.get("task_decomposition")
    if not isinstance(decomposition, dict):
        self.error(
            "ROUTER_TASK_DECOMPOSITION_MISSING",
            "context router must define task_decomposition routing",
            ROUTER_RELPATH,
        )
        return
    if decomposition.get("schema_version") != 1:
        self.error(
            "ROUTER_TASK_DECOMPOSITION_SCHEMA",
            "task_decomposition.schema_version must be 1",
            ROUTER_RELPATH,
        )
    if decomposition.get("policy") != POLICY_RELPATH:
        self.error(
            "ROUTER_TASK_DECOMPOSITION_POLICY",
            "task_decomposition.policy must point to the target policy",
            ROUTER_RELPATH,
        )
    if decomposition.get("plan_template") != PLAN_RELPATH:
        self.error(
            "ROUTER_TASK_DECOMPOSITION_TEMPLATE",
            "task_decomposition.plan_template must point to the target template",
            ROUTER_RELPATH,
        )
    for field in ["load_after", "use_when"]:
        expect_string_list(
            decomposition.get(field),
            self,
            "ROUTER_TASK_DECOMPOSITION_FIELD",
            ROUTER_RELPATH,
            label=f"task_decomposition.{field}",
        )
    receipt = router.get("context_receipt")
    fields = receipt.get("fields") if isinstance(receipt, dict) else None
    if not isinstance(fields, list) or REQUIRED_ROUTER_RECEIPT not in fields:
        self.error(
            "ROUTER_TASK_DECOMPOSITION_RECEIPT",
            "context receipt must record task decomposition id and levels",
            ROUTER_RELPATH,
        )


def _validate_delegation_composition(self: Any) -> None:
    policy = self.load_json_object(
        self.target_path(DELEGATION_POLICY_RELPATH), "DELEGATION_POLICY"
    )
    if isinstance(policy, dict) and policy.get("decomposition_policy") != POLICY_RELPATH:
        self.error(
            "TASK_DECOMPOSITION_DELEGATION_POLICY",
            "delegation policy must point to the task-decomposition policy",
            DELEGATION_POLICY_RELPATH,
        )

    catalog = self.load_json_object(
        self.target_path(ROLE_CATALOG_RELPATH), "WORKER_ROLE_CATALOG"
    )
    if not isinstance(catalog, dict):
        return
    if catalog.get("decomposition_policy") != POLICY_RELPATH:
        self.error(
            "TASK_DECOMPOSITION_ROLE_CATALOG",
            "worker role catalog must point to the task-decomposition policy",
            ROLE_CATALOG_RELPATH,
        )
    roles = catalog.get("roles")
    if not isinstance(roles, list):
        return
    for role in roles:
        if not isinstance(role, dict):
            continue
        levels = role.get("implementation_levels")
        if not isinstance(levels, list) or not levels:
            self.error(
                "TASK_DECOMPOSITION_ROLE_LEVELS",
                f"worker role {role.get('id', '<unknown>')} must declare implementation levels",
                ROLE_CATALOG_RELPATH,
            )
            continue
        unsupported = sorted(
            level
            for level in levels
            if not isinstance(level, str) or level not in WORKER_ELIGIBLE_LEVELS
        )
        if unsupported:
            self.error(
                "TASK_DECOMPOSITION_ROLE_LEVEL",
                f"worker role {role.get('id', '<unknown>')} has invalid implementation levels {unsupported}",
                ROLE_CATALOG_RELPATH,
            )


def _require_template_text(
    self: Any,
    relpath: str,
    required_text: list[str],
    *,
    required: bool = True,
) -> None:
    path = self.target_path(relpath)
    if not path.is_file():
        if required:
            self.error(
                "TASK_DECOMPOSITION_REQUIRED_FILE_MISSING",
                "task-decomposition evidence surface is missing",
                relpath,
            )
        return
    text = self.read_text(path)
    for value in required_text:
        if value not in text:
            self.error(
                "TASK_DECOMPOSITION_TEXT",
                f"{relpath} missing {value}",
                relpath,
            )
