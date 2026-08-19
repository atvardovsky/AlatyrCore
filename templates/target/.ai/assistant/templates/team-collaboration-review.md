# Team Collaboration Review

- Review ID: `{TEAM_REVIEW_ID}`
- Period or operation scope: `{BOUNDED_REVIEW_SCOPE}`
- Policy revision: `{TARGET_TEAM_POLICY_REVISION}`
- Registry/backend evidence revision: `{TEAM_EVIDENCE_REVISION}`
- Reviewed by actor: `{ACTOR_ID}`
- Evidence quality: `{MEASURED_OBSERVED_ANECDOTAL_CONFLICTING_OR_UNRESOLVED}`

## Aggregate Signals

- Active and stale claim counts: `{ACTIVE_AND_STALE_CLAIM_COUNTS}`
- Revision conflicts rejected before overwrite:
  `{REJECTED_CONCURRENT_WRITE_COUNT_OR_UNKNOWN}`
- Logical overlaps found before edits and after edits:
  `{PRECHANGE_AND_LATE_OVERLAP_COUNTS_OR_UNKNOWN}`
- Handoffs pending, accepted, rejected, or stale:
  `{HANDOFF_STATE_COUNTS}`
- Review or merge evidence invalidated by later changes:
  `{REVIEW_INVALIDATION_COUNT_OR_UNKNOWN}`
- Repeated missing actor, owner, authority, or backend evidence:
  `{MISSING_COORDINATION_EVIDENCE_PATTERNS_OR_NONE}`
- Team context files and approximate volume:
  `{TEAM_CONTEXT_COST_EVIDENCE_OR_UNKNOWN}`

Do not rank individuals or infer productivity from these signals. Use bounded
team-process evidence and target privacy/retention policy.

## Improvement Candidates

For each repeated or high-impact pattern, record the project owner, evidence
references, current workflow or AI item, proposed gate/checker/skill/flow/tool
change, expected quality and context-cost effect, acceptance criteria,
maintenance owner, and next read-only recommendation operation.

## Decisions

- Keep: `{SUPPORTED_EXISTING_ITEMS_OR_PROCESS}`
- Improve: `{ACCEPTED_IMPROVEMENT_CANDIDATES_OR_NONE}`
- Add: `{ACCEPTED_NEW_ITEM_CANDIDATES_OR_NONE}`
- Retire: `{RETIREMENT_CANDIDATES_OR_NONE}`
- Unresolved: `{UNRESOLVED_EVIDENCE_OR_AUTHORITY}`

This review does not modify project facts, AI infrastructure, permissions,
framework files, or team policy. Accepted changes use their normal target
operation, authority, approval, validation, and rollback path.
