# Task Decomposition

Plan ID: `{PLAN_ID}`
Parent operation ID: `{OPERATION_ID}`
Base revision: `{BASE_REVISION}`
Primary assistant/session: `{PRIMARY_ASSISTANT_REFERENCE}`
Policy: `.ai/assistant/task-decomposition.json`
Current logical scope: `{CURRENT_LOGICAL_SCOPE}`
Current user authorization: `{CURRENT_AUTHORIZED_PHASES}`
Allowed actions ceiling: `{ALLOWED_ACTIONS}`
Delegation preference: `{AUTO_ALLOW_FORBID_REQUIRE_SUPPORTED_OR_NONE}`

## Request Classification

Requested action: `{USER_REQUEST_SUMMARY}`
Task profile: `{SELECTED_PROFILE_OR_UNRESOLVED}`
Task scale: `{SMALL_STANDARD_LARGE_PROTECTED_OR_UNRESOLVED}`
Changed facts: `{FACT_IDS_OR_NONE}`
Project areas: `{AREA_IDS_OR_NONE}`
Risk: `{RISK_CLASSES_OR_NONE}`
Approval state: `{NOT_REQUIRED_REQUIRED_PRESENT_BLOCKED_OR_UNRESOLVED}`

## Task Graph

Use one task when the request is small and locally provable. Use multiple
tasks only when semantic owners, dependencies, validation, or support surfaces
justify the coordination cost.

Task ID: `{TASK_ID}`
Status: `{PLANNED_BLOCKED_READY_RUNNING_REVIEW_REQUIRED_DONE_FAILED_CANCELLED}`
Goal: `{ONE_BOUNDED_GOAL}`
Implementation level: `{L0_L1_L2_L3_L4_L5_L6_OR_L7}`
Why this level: `{LEVEL_SELECTION_REASON}`
Dependencies: `{TASK_IDS_OR_NONE}`
Changed facts: `{FACT_IDS_OR_NONE}`
Canonical owners: `{OWNER_PATHS_OR_NONE}`
Allowed files or surfaces: `{PATHS_SURFACES_OR_NONE}`
Required context: `{PATHS_AND_REASONS}`
Intentionally omitted context: `{PATHS_AND_REASONS_OR_NONE}`
Acceptance criteria: `{OBJECTIVE_LOCAL_CRITERIA}`
Validation: `{TARGET_VALIDATION_OR_MANUAL_REVIEW}`
Executor decision: `{PRIMARY_WORKER_SUGGESTION_ONLY_OR_BLOCKED}`
Selected worker role: `{ROLE_ID_OR_NONE}`
Why this executor: `{EXECUTOR_SELECTION_REASON}`
Delegation packet: `{PACKET_ID_OR_NONE}`
Result: `{RESULT_ID_OR_NONE}`
Blocker or readiness evidence: `{EVIDENCE_OR_NONE}`

## Dependency And Scope Review

Dependency cycles: `{NONE_OR_DETAILS}`
Shared semantic owners: `{NONE_OR_PRIMARY_CONVERGENCE_TASK}`
Overlapping write scopes: `{NONE_OR_REJECTED_TASKS}`
New relationships discovered: `{NONE_OR_ESCALATION_DETAILS}`
Escalations: `{NONE_OR_TASK_IDS_AND_REASONS}`

## Primary Convergence

Tasks completed locally: `{TASK_IDS_OR_NONE}`
Delegated packets accepted: `{PACKET_OR_RESULT_IDS_OR_NONE}`
Delegated packets rejected: `{PACKET_OR_RESULT_IDS_AND_REASONS_OR_NONE}`
Combined validation: `{RESULT_OR_NOT_RUN_WITH_REASON}`
Changed-fact reconciliation: `{RESULT_OR_NOT_APPLICABLE}`
Approval and authorization reconciliation: `{RESULT_OR_NOT_APPLICABLE}`
Documentation diagram and support sync: `{RESULT_OR_NOT_APPLICABLE}`
Final logical integrity result: `{PASSED_FAILED_BLOCKED_OR_UNVERIFIED}`
Residual risk: `{RESIDUAL_RISK}`
