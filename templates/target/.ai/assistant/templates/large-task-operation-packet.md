# Large-Task Operation Packet

Use this template in `{PROJECT_NAME}` only for large, cross-boundary,
multi-workstream, or resumable operations. The completed packet is coordination
evidence, not a source of truth for project facts.

## Operation

- Operation ID: `{OPERATION_ID}`
- Parent request or issue: `{PARENT_REQUEST_OR_ISSUE}`
- Goal: `{GOAL}`
- Non-goals: `{NON_GOALS}`
- Allowed actions: `{ALLOWED_ACTIONS}`
- Activation reason: `{LARGE_TASK_ACTIVATION_REASON}`
- Current phase: `{DISCOVERY_PLANNING_EXECUTION_CONVERGENCE_OR_COMPLETE}`
- Packet status: `{ACTIVE_BLOCKED_COMPLETE_OR_ARCHIVED}`
- Packet owner: `{TARGET_OPERATION_OWNER}`
- Storage and retention policy: `{TARGET_OPERATION_PACKET_POLICY}`

## Routed Context

- Selected task profile: `{TASK_PROFILE}`
- Task-scale overlay: `large-or-resumable`
- Selected project areas: `{PROJECT_AREA_OVERLAYS}`
- Context budget: `{CONTEXT_BUDGET}`
- Loaded files and reasons: `{LOADED_FILES_AND_REASONS}`
- Approximate context volume: `{APPROXIMATE_CONTEXT_VOLUME}`
- Expansion triggers: `{CONTEXT_EXPANSION_TRIGGERS}`
- Intentionally omitted context: `{INTENTIONALLY_OMITTED_CONTEXT}`
- Residual context risk: `{RESIDUAL_CONTEXT_RISK}`

## Changed Facts

Repeat this block for each changed or disputed fact.

### Fact `{FACT_ID}`

- Statement: `{CHANGED_FACT}`
- Canonical owner: `{CANONICAL_SOURCE_OF_TRUTH_OR_MISSING}`
- Risk class: `{RISK_CLASS}`
- Affected surfaces: `{AFFECTED_SURFACES}`
- Approval state: `{APPROVAL_RECORD_OR_NOT_REQUIRED_OR_MISSING}`
- Owning workstream: `{WORKSTREAM_ID}`
- Reconciliation state: `{PENDING_CONSISTENT_CONFLICT_OR_UNRESOLVED}`

## Workstreams

Repeat this block for each coherent workstream.

### Workstream `{WORKSTREAM_ID}`

- Goal: `{WORKSTREAM_GOAL}`
- Project area: `{PROJECT_AREA}`
- Changed facts: `{FACT_IDS}`
- Dependencies: `{WORKSTREAM_DEPENDENCIES_OR_NONE}`
- Blocking decisions: `{BLOCKING_DECISIONS_OR_NONE}`
- Required context: `{MINIMUM_REQUIRED_CONTEXT}`
- Deferred context: `{INTENTIONALLY_DEFERRED_CONTEXT}`
- Allowed surfaces: `{ALLOWED_FILES_OR_SURFACES}`
- Expected outputs: `{EXPECTED_OUTPUTS}`
- Validation: `{TARGET_VALIDATION_OR_MANUAL_REVIEW}`
- Status: `{READY_ACTIVE_BLOCKED_LOCALLY_VALIDATED_OR_COMPLETE}`
- Evidence: `{WORKSTREAM_EVIDENCE}`
- Unresolved risk: `{WORKSTREAM_RESIDUAL_RISK}`
- Handoff state: `{NEXT_ACTION_AND_REQUIRED_CONTEXT}`

## Checkpoints

Repeat after local validation, an approval boundary, a handoff, or before a
context reset.

### Checkpoint `{CHECKPOINT_ID}`

- Recorded at: `{CHECKPOINT_TIME_OR_COMMIT}`
- Completed work: `{COMPLETED_WORK}`
- Decisions and evidence: `{DECISIONS_AND_EVIDENCE}`
- Approval state: `{APPROVAL_STATE}`
- Validation state: `{VALIDATION_STATE}`
- Invalidated assumptions: `{INVALIDATED_ASSUMPTIONS_OR_NONE}`
- Context receipt delta: `{NEW_FILES_REASONS_AND_VOLUME}`
- Unresolved items: `{UNRESOLVED_ITEMS}`
- Next ready action: `{NEXT_READY_ACTION}`
- Resume context: `{MINIMUM_RESUME_CONTEXT}`

## Final Convergence

- Completed workstreams: `{COMPLETED_WORKSTREAMS}`
- Unresolved workstreams: `{UNRESOLVED_WORKSTREAMS_OR_NONE}`
- Changed-fact reconciliation: `{FACT_RECONCILIATION_RESULT}`
- Source-of-truth synchronization: `{SOURCE_OF_TRUTH_SYNC_RESULT}`
- Cross-workstream conflicts: `{CONFLICTS_AND_REPAIRS_OR_NONE}`
- Approval scope versus applied changes: `{APPROVAL_COVERAGE_RESULT}`
- Combined validation: `{TARGET_VALIDATION_RESULT_OR_UNRESOLVED}`
- Global logical integrity review: `{GLOBAL_LOGICAL_INTEGRITY_RESULT}`
- Skipped checks: `{SKIPPED_CHECKS}`
- Final residual risk: `{FINAL_RESIDUAL_RISK}`
- Packet disposition: `{CLOSE_ARCHIVE_RETAIN_OR_DELETE_PER_TARGET_POLICY}`

## Resume Rule

On resume, load the compact adapter bootstrap, this packet, the active
workstream's minimum context, its changed-fact owners, and dependencies. Check
packet claims against current repository evidence before continuing. Do not
load completed workstream context again unless evidence changed.
