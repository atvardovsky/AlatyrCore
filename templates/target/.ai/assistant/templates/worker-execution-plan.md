# Worker Execution Plan

Plan ID: `{PLAN_ID}`
Parent operation ID: `{OPERATION_ID}`
Base revision: `{BASE_REVISION}`
Primary assistant/session: `{PRIMARY_ASSISTANT_REFERENCE}`
Current logical scope: `{CURRENT_LOGICAL_SCOPE}`
Authorized action phases: `{CURRENT_AUTHORIZED_PHASES}`
Delegation policy revision: `{POLICY_REVISION_OR_HASH}`

## Task Graph

Use statuses `PLANNED`, `BLOCKED`, `READY`, `RUNNING`, `REVIEW_REQUIRED`,
`DONE`, `FAILED`, or `CANCELLED`. Only the primary assistant computes readiness.

Task ID: `{TASK_ID}`
Status: `{TASK_STATUS}`
Goal: `{ONE_BOUNDED_GOAL}`
Dependencies: `{TASK_IDS_OR_NONE}`
Changed facts: `{FACT_IDS_OR_NONE}`
Expected write scope: `{DISJOINT_PATHS_SURFACES_OR_NONE}`
Role: `{ENABLED_ROLE_ID_OR_PRIMARY}`
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

## Primary Convergence

Accepted results: `{RESULT_IDS_OR_NONE}`
Rejected or retried results: `{RESULT_IDS_REASONS_OR_NONE}`
Combined validation: `{RESULT_OR_NOT_RUN_WITH_REASON}`
Logical integrity and approval reconciliation: `{RESULT}`
Residual risk: `{RESIDUAL_RISK}`
