# Team Operating Model

Use this file to record target-owned team roles, decision authority, priority,
review, coordination, storage, and privacy facts for `{PROJECT_NAME}`.

Replace every placeholder from target evidence before enabling the
`team-collaboration` module. This file is not a roster copied from Alatyr Core.

## Ownership

- Responsible team: `{RESPONSIBLE_TEAM}`
- Technical owner: `{TEAM_COORDINATION_TECHNICAL_OWNER}`
- Backup owner: `{TEAM_COORDINATION_BACKUP_OWNER}`
- Escalation owner: `{TEAM_ESCALATION_OWNER}`
- Last reviewed: `{LAST_REVIEW_DATE}`
- Review cadence: `{TEAM_OPERATING_MODEL_REVIEW_CADENCE}`

## Coordination Backend

- Backend: `{REPOSITORY_EXTERNAL_TRACKER_BOTH_OR_OTHER}`
- Canonical task source: `{TARGET_TASK_SOURCE_OF_TRUTH}`
- Registry synchronization direction:
  `{BACKEND_TO_REGISTRY_REGISTRY_TO_BACKEND_BIDIRECTIONAL_OR_MANUAL}`
- Branch or worktree convention: `{TARGET_BRANCH_OR_WORKTREE_POLICY}`
- Claim enforcement: `{ADVISORY_OR_TARGET_ENFORCED}`
- Claim staleness policy: `{TARGET_CLAIM_STALENESS_POLICY}`
- Record storage: `{TARGET_TEAM_RECORD_STORAGE_POLICY}`
- Retention policy: `{TARGET_TEAM_RECORD_RETENTION_POLICY}`
- Privacy policy: `{TARGET_TEAM_RECORD_PRIVACY_POLICY}`

## Actors And Roles

Repeat for every stable actor or role that the module may reference. Prefer
role IDs over personal details when the target does not need a person-level
record.

### Actor `{ACTOR_ID}`

- Display name or role: `{ACTOR_DISPLAY_NAME_OR_ROLE}`
- Actor type:
  `{HUMAN_IMPLEMENTER_HUMAN_REVIEWER_AI_ASSISTANT_AUTOMATION_CI_OR_DECISION_OWNER}`
- Status: `{ACTIVE_INACTIVE_OR_EXTERNAL}`
- Team: `{TARGET_TEAM_OR_NONE}`
- Responsibilities: `{RESPONSIBILITIES}`
- Decision authority: `{DECISION_TYPES_OR_NONE}`
- Required review scopes: `{REVIEW_SCOPES_OR_NONE}`
- Escalation target: `{ESCALATION_ACTOR_ID}`
- External identity reference: `{TARGET_IDENTITY_REFERENCE_OR_NONE}`

Assignment, task claim, review participation, or commit authorship does not
grant protected-change approval.

## Priority Policy

Repeat for every target priority class.

### Priority `{PRIORITY_ID}`

- Rank or ordering: `{TARGET_PRIORITY_ORDER}`
- Meaning: `{TARGET_PRIORITY_MEANING}`
- Who may assign it: `{PRIORITY_DECISION_ACTOR_IDS}`
- Required rationale: `{PRIORITY_RATIONALE_REQUIREMENT}`
- Deadline or dependency evidence: `{DEADLINE_OR_DEPENDENCY_POLICY}`
- Preemption rule: `{TARGET_PREEMPTION_RULE}`
- Escalation rule: `{TARGET_PRIORITY_ESCALATION_RULE}`

Priority controls scheduling and tradeoff discussion. It does not bypass
correctness, source-of-truth ownership, safety, validation, review, or
approval.

## Review And Decision Policy

- Required implementer/reviewer separation:
  `{TARGET_IMPLEMENTER_REVIEWER_SEPARATION}`
- CODEOWNERS or equivalent owner map: `{TARGET_OWNER_MAP}`
- Business decision owner: `{TARGET_BUSINESS_DECISION_OWNER}`
- Architecture decision owner: `{TARGET_ARCHITECTURE_DECISION_OWNER}`
- Data decision owner: `{TARGET_DATA_DECISION_OWNER}`
- Security decision owner: `{TARGET_SECURITY_DECISION_OWNER}`
- Adapter decision owner: `{TARGET_ADAPTER_DECISION_OWNER}`
- Canonical decision record location: `{TARGET_DECISION_RECORD_DIRECTORY}`
- Merge authority: `{TARGET_MERGE_AUTHORITY}`
- Merge-readiness validation: `{TARGET_MERGE_READINESS_VALIDATION_OR_REVIEW}`

## Concurrent Work Policy

- Fact overlap source: `.ai/project/source-of-truth-registry.md`
- Consistency map: `.ai/project/consistency-map.json` when enabled
- Active work registry: `.ai/assistant/team/work-registry.json`
- Shared contract policy: `{TARGET_SHARED_CONTRACT_COORDINATION_POLICY}`
- Migration or generated-artifact sequencing:
  `{TARGET_SEQUENCING_POLICY}`
- File overlap role: secondary evidence after facts, owners, contracts, and
  dependencies
- Unresolved overlap action: `{COORDINATE_SEQUENCE_MERGE_TASKS_OR_BLOCK}`

## Known Gaps

- `{TEAM_OPERATING_MODEL_GAP}`

Do not claim the module is enabled while required actors, authority,
coordination backend, storage/privacy policy, or conflict handling remain
unknown.
