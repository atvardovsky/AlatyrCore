# Worker Result

Result ID: `{RESULT_ID}`
Task ID: `{TASK_ID}`
Packet ID: `{PACKET_ID}`
Parent operation ID: `{OPERATION_ID}`
Status: `{SUCCEEDED_FAILED_BLOCKED_CANCELLED_OR_SCOPE_VIOLATION}`
Base revision observed: `{BASE_REVISION}`

## Execution Evidence

Actual assistant surface: `{SURFACE_OR_UNVERIFIED}`
Actual role: `{ROLE_ID_OR_UNVERIFIED}`
Actual model: `{MODEL_ID_OR_UNVERIFIED}`
Capability evidence: `{CAPABILITY_RECORD_AND_REVISION}`
Summary: `{BOUNDED_RESULT_SUMMARY}`
Files or surfaces touched: `{TOUCHED_SURFACES_OR_NONE}`
Commands or tools used: `{COMMANDS_TOOLS_AND_RESULTS_OR_NONE}`
Validation: `{RESULT_OR_NOT_RUN_WITH_REASON}`
Acceptance criteria: `{PASS_FAIL_OR_BLOCKED_BY_CRITERION}`

## Boundary Evidence

Scope violation: `{NONE_OR_DETAILS}`
Architecture or semantic deviation: `{NONE_OR_DETAILS}`
Unexpected repository state: `{NONE_OR_DETAILS}`
Authorization or approval concern: `{NONE_OR_DETAILS}`
Unresolved findings: `{NONE_OR_DETAILS}`
Suggested follow-up: `{NONE_OR_PRIMARY_OWNED_ACTION}`
Residual risk: `{RESIDUAL_RISK}`

This result is evidence for primary review. It is not approval, integration,
commit, publication, or final operation completion.
