# Worker Execution Plan

Plan ID: `{PLAN_ID}`
Parent operation ID: `{OPERATION_ID}`
Base revision: `{BASE_REVISION}`
Primary assistant/session: `{PRIMARY_ASSISTANT_REFERENCE}`
Current logical scope: `{CURRENT_LOGICAL_SCOPE}`
Authorized action phases: `{CURRENT_AUTHORIZED_PHASES}`
Delegation policy revision: `{POLICY_REVISION_OR_HASH}`
Task decomposition policy revision: `{TASK_DECOMPOSITION_POLICY_REVISION_OR_HASH}`

## Delegation Tree Budget

Dispatch owner: `primary-assistant`
Worker child behavior: `propose-only`
Maximum depth: `{TARGET_MAX_DEPTH_NOT_ABOVE_HARD_LIMIT}`
Maximum total delegates: `{TARGET_MAX_TOTAL_DELEGATES}`
Maximum children per parent: `{TARGET_MAX_CHILDREN_PER_PARENT}`
Maximum total context words: `{TARGET_MAX_CONTEXT_WORDS_TOTAL}`
Maximum retries: `{TARGET_MAX_RETRIES_TOTAL}`
Used delegates/context/retries: `{CURRENT_BUDGET_USAGE}`

## Task Graph

Use statuses `PLANNED`, `BLOCKED`, `READY`, `RUNNING`, `REVIEW_REQUIRED`,
`DONE`, `FAILED`, or `CANCELLED`. Only the primary assistant computes readiness.

Task ID: `{TASK_ID}`
Parent task or packet ID: `{PARENT_ID_OR_NONE}`
Depth: `{NON_NEGATIVE_INTEGER}`
Coverage key: `{UNIQUE_BOUNDED_COVERAGE_KEY}`
Status: `{TASK_STATUS}`
Goal: `{ONE_BOUNDED_GOAL}`
Implementation level: `{L1_L2_L3_L4_OR_L5_FOR_WORKER_ELIGIBLE_TASKS}`
Dependencies: `{TASK_IDS_OR_NONE}`
Changed facts: `{FACT_IDS_OR_NONE}`
Expected write scope: `{DISJOINT_PATHS_SURFACES_OR_NONE}`
Role: `{ENABLED_ROLE_ID_OR_PRIMARY}`
Executor decision: `{PRIMARY_WORKER_SUGGESTION_ONLY_OR_BLOCKED}`
Required context: `{PATHS_AND_REASONS}`
Acceptance criteria: `{OBJECTIVE_LOCAL_CRITERIA}`
Validation: `{TARGET_VALIDATION_OR_MANUAL_REVIEW}`
Dispatch backend: `{NATIVE_EXTERNAL_SUGGESTION_ONLY_PRIMARY_OR_UNRESOLVED}`
Packet ID: `{PACKET_ID_OR_NONE}`
Result ID: `{RESULT_ID_OR_NONE}`
Blocker or readiness evidence: `{EVIDENCE}`

## Conflict Review

Dependency cycles: `{NONE_OR_DETAILS}`
Overlapping write scopes: `{NONE_OR_REJECTED_TASKS}`
Shared semantic owners: `{NONE_OR_PRIMARY_CONVERGENCE_TASK}`
Stale baseline handling: `{REVALIDATION_DECISION}`
Duplicate coverage keys: `{NONE_OR_REJECTED_TASKS}`
Tree budget result: `{WITHIN_LIMITS_OR_STOP_REASON_ID}`

## Primary Convergence

Accepted results: `{RESULT_IDS_OR_NONE}`
Rejected or retried results: `{RESULT_IDS_REASONS_OR_NONE}`
Combined validation: `{RESULT_OR_NOT_RUN_WITH_REASON}`
Logical integrity and approval reconciliation: `{RESULT}`
Residual risk: `{RESIDUAL_RISK}`
Tree stop reason: `{TARGET_STOP_REASON_ID}`
