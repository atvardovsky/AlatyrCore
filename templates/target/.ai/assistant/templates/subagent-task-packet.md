# Subagent Task Packet

Packet ID: `{PACKET_ID}`
Parent operation ID: `{OPERATION_ID}`
Parent workstream ID: `{WORKSTREAM_ID_OR_NONE}`
Primary assistant/session reference: `{PRIMARY_ASSISTANT_REFERENCE}`
Status: `{PLANNED_DISPATCHED_RETURNED_ACCEPTED_REJECTED_BLOCKED_OR_CANCELLED}`

## Goal And Scope

Goal: `{ONE_BOUNDED_GOAL}`
Non-goals: `{EXPLICIT_NON_GOALS}`
Expected output: `{PATCH_EVIDENCE_FINDINGS_OR_OTHER}`
Changed fact IDs: `{CHANGED_FACT_IDS_OR_NONE}`
Semantic fact owner: `{PRIMARY_OWNED_OWNER_OR_NONE}`
Local acceptance criteria: `{OBJECTIVE_ACCEPTANCE_CRITERIA}`
Dependency state: `{READY_DEPENDENCIES_OR_BLOCKER}`

## Context Boundary

Required context:

- `{REQUIRED_CONTEXT_PATH_AND_REASON}`

Excluded context:

- `{EXCLUDED_CONTEXT_OR_NOT_NEEDED}`

Context budget: `{TARGET_PACKET_CONTEXT_BUDGET}`

## Authority Boundary

Allowed actions: `{READ_ONLY_DOCS_ONLY_ADAPTER_ONLY_OR_CODE_AND_TESTS}`
Allowed files or surfaces:

- `{ALLOWED_PATH_OR_SURFACE}`

Allowed tools:

- `{ALLOWED_TOOL_OR_NONE}`

Prohibited actions:

- approval or project decision authority
- permission, network, destructive, production, spend, migration, or external
  actions unless the packet explicitly references valid target approval
- files, facts, tools, or surfaces outside this packet
- `{TARGET_ADDITIONAL_PROHIBITED_ACTION}`

Concurrent packets and write-isolation decision:
`{PACKET_IDS_AND_DISJOINT_SCOPE_EVIDENCE_OR_READ_ONLY}`

## Delegation Selection

Assistant surface: `{ASSISTANT_SURFACE}`
Dispatch backend: `{NATIVE_EXTERNAL_SUGGESTION_ONLY_OR_UNSUPPORTED}`
External dispatcher item: `{TARGET_AI_INFRASTRUCTURE_ITEM_ID_NONE_OR_UNKNOWN}`
Role: `{TARGET_DELEGATION_ROLE}`
Requested model or selection mode: `{MODEL_ID_INHERIT_OR_CLIENT_DEFAULT}`
Capability evidence: `{CAPABILITY_RECORD_PATH_AND_FRESHNESS}`
Selection rationale: `{LATENCY_CONTEXT_OR_PARALLELISM_REASON}`
Fallback: `{CONTINUE_PRIMARY_USE_STRONGER_VERIFIED_MODEL_OR_STOP}`

## Validation And Return

Delegate validation:

- `{TARGET_FOCUSED_VALIDATION_OR_MANUAL_REVIEW}`

Return format:

- summary and packet status
- files or surfaces touched
- commands or tools used and results
- requested versus actual model, or `unverified`
- acceptance-criteria result
- unresolved findings and residual risk

## Returned Result

Actual assistant surface: `{ACTUAL_SURFACE_OR_UNVERIFIED}`
Actual role/model: `{ACTUAL_ROLE_AND_MODEL_OR_UNVERIFIED}`
Files or surfaces touched: `{TOUCHED_SURFACES_OR_NONE}`
Validation result: `{RESULT_OR_NOT_RUN_WITH_REASON}`
Acceptance result: `{PASS_FAIL_OR_BLOCKED}`
Unexpected scope or conflicts: `{DETAILS_OR_NONE}`
Residual risk: `{RESIDUAL_RISK}`

## Primary Review

Scope review: `{ACCEPTED_REJECTED_OR_REWORK_REQUIRED}`
Patch/evidence review: `{PRIMARY_REVIEW_RESULT}`
Repeated or combined validation: `{RESULT_OR_NOT_RUN_WITH_REASON}`
Changed-fact and approval reconciliation: `{RESULT_OR_NOT_APPLICABLE}`
Final disposition: `{INTEGRATED_REWORKED_DISCARDED_OR_BLOCKED}`
Measured latency or cost evidence: `{MEASUREMENT_OR_NOT_CAPTURED}`
