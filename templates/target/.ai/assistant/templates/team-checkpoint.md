# Team Checkpoint

- Checkpoint ID: `{CHECKPOINT_ID}`
- Task ID: `{TASK_ID}`
- Recorded by actor: `{ACTOR_ID}`
- Recorded at: `{OBSERVATION_TIME}`
- Repository revision: `{HEAD_REVISION_OR_UNAVAILABLE}`
- Base revision: `{BASE_REVISION_OR_UNAVAILABLE}`
- Branch or worktree: `{TARGET_BRANCH_WORKTREE_OR_NONE}`
- Task status: `{TASK_STATUS}`
- Claim state: `{CLAIM_STATE}`

## Work State

- Completed work: `{COMPLETED_WORK}`
- Current diff or change reference: `{DIFF_OR_CHANGE_REFERENCE}`
- Changed fact IDs: `{FACT_IDS}`
- Canonical owner references: `{CANONICAL_OWNER_REFS}`
- Decisions and decision records: `{DECISIONS_AND_RECORDS}`
- Active-task overlap result: `{OVERLAP_RESULT}`
- Validation state: `{VALIDATION_RESULT_OR_UNRESOLVED}`
- Review state and evidence: `{REVIEW_STATE_AND_EVIDENCE_OR_UNRESOLVED}`
- Approval state: `{APPROVAL_RECORDS_OR_NOT_REQUIRED_OR_MISSING}`

## Resume Evidence

- Invalidated assumptions: `{INVALIDATED_ASSUMPTIONS_OR_NONE}`
- Blockers: `{BLOCKERS_OR_NONE}`
- Unresolved questions: `{UNRESOLVED_QUESTIONS_OR_NONE}`
- Residual risks: `{RESIDUAL_RISKS_OR_NONE}`
- Minimum resume context: `{MINIMUM_RESUME_CONTEXT}`
- Exact next action: `{NEXT_ACTION}`
- Next responsible actor or role: `{NEXT_ACTOR_ID_OR_ROLE}`

This checkpoint is coordination evidence. Compare it with current repository,
registry, backend, approval, and source-of-truth evidence before resuming.
