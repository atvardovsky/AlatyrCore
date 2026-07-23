# Team Handoff

- Handoff ID: `{HANDOFF_ID}`
- Task ID: `{TASK_ID}`
- Source actor: `{SOURCE_ACTOR_ID}`
- Destination actor or role: `{DESTINATION_ACTOR_ID_OR_ROLE}`
- Reason: `{HANDOFF_REASON}`
- State: `{PENDING_ACCEPTED_REJECTED_OR_STALE}`
- Created at: `{OBSERVATION_TIME}`
- Accepted or rejected at: `{ACCEPTANCE_TIME_OR_NONE}`
- Repository revision: `{HEAD_REVISION_OR_UNAVAILABLE}`
- Checkpoint reference: `{CHECKPOINT_PATH_OR_ID}`

## Scope And Evidence

- Goal and accepted scope: `{GOAL_AND_SCOPE}`
- Completed work: `{COMPLETED_WORK}`
- Changed fact IDs: `{FACT_IDS}`
- Canonical owner references: `{CANONICAL_OWNER_REFS}`
- Decisions and decision records: `{DECISIONS_AND_RECORDS}`
- Current diff or change reference: `{DIFF_OR_CHANGE_REFERENCE}`
- Validation state: `{VALIDATION_RESULT_OR_UNRESOLVED}`
- Review state and evidence: `{REVIEW_STATE_AND_EVIDENCE_OR_UNRESOLVED}`
- Approval state: `{APPROVAL_RECORDS_OR_NOT_REQUIRED_OR_MISSING}`
- Concurrent overlap state: `{OVERLAP_RESULT}`

## Receiver Context

- Required context: `{MINIMUM_REQUIRED_CONTEXT}`
- Intentionally omitted context: `{INTENTIONALLY_OMITTED_CONTEXT}`
- Invalidated assumptions: `{INVALIDATED_ASSUMPTIONS_OR_NONE}`
- Unresolved questions: `{UNRESOLVED_QUESTIONS_OR_NONE}`
- Blockers: `{BLOCKERS_OR_NONE}`
- Residual risks: `{RESIDUAL_RISKS_OR_NONE}`
- Exact next action: `{NEXT_ACTION}`

The destination actor must compare this handoff with current evidence before
acceptance. Acceptance does not grant protected-change approval.
