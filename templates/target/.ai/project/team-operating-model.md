# Team Operating Model

This is the human-oriented explanation of team collaboration for
`{PROJECT_NAME}`. Canonical actor, authority, priority, review, transition,
backend, storage, and privacy fields live in `.ai/project/team-policy.json`.

Replace every placeholder from target evidence before enabling the
`team-collaboration` module. Do not maintain a second actor roster here.

## Ownership

- Canonical policy: `.ai/project/team-policy.json`
- Responsible team: `{RESPONSIBLE_TEAM}`
- Technical owner: `{TEAM_COORDINATION_TECHNICAL_OWNER}`
- Backup owner: `{TEAM_COORDINATION_BACKUP_OWNER}`
- Escalation owner: `{TEAM_ESCALATION_OWNER}`
- Last reviewed: `{LAST_REVIEW_DATE}`
- Review cadence: `{TEAM_OPERATING_MODEL_REVIEW_CADENCE}`

## Identity And Attribution

Users may select their current actor through `Alatyr set actor {ACTOR_ID_OR_NAME}`.
The selection is written to ignored `.ai/local/team-identity.json` and must
resolve to one active actor in the canonical team policy.

Local selection supports attribution; it is not authentication, approval, or
decision authority. Git author, OS username, assistant account, task ownership,
or commit authorship must not be treated as proof of identity. Protected target
actions use the verification and approval rules named by the canonical policy.

## Coordination Backend

- Backend contract: `.ai/assistant/team/backend-contract.json`
- Work registry metadata: `.ai/assistant/team/work-registry.json`
- Compact active projection: `.ai/assistant/team/active-work-index.json`
- Per-task records: `.ai/assistant/team/tasks/{TASK_ID}.json` for repository
  storage, or a deterministic target projection for an external backend
- Synchronization notes: `{TARGET_BACKEND_SYNCHRONIZATION_NOTES}`

Task writes use the target backend's compare-and-swap or equivalent conflict
rule. A revision mismatch stops the write and refreshes the selected task.

## Roles And Authority

Human-readable role guidance: `{TARGET_ROLE_AND_AUTHORITY_EXPLANATION}`

Assignment, task claim, review participation, selected local identity, or
commit authorship does not grant protected-change approval. Accepted decisions
must still be written by an authorized owner to their canonical project source.

## Priority, Review, And Decisions

- Priority interpretation: `{TARGET_PRIORITY_EXPLANATION}`
- Review separation: `{TARGET_IMPLEMENTER_REVIEWER_SEPARATION}`
- Canonical decision records: `{TARGET_DECISION_RECORD_DIRECTORY}`
- Merge authority: `{TARGET_MERGE_AUTHORITY}`

Priority controls scheduling and tradeoff discussion. It does not bypass
correctness, source-of-truth ownership, safety, validation, review, or approval.

## Concurrent Work

- Fact overlap source: `.ai/project/source-of-truth-registry.md`
- Consistency map: `.ai/project/consistency-map.json` when enabled
- File overlap role: secondary evidence after facts, owners, contracts, and
  dependencies
- Unresolved overlap action: `{COORDINATE_SEQUENCE_MERGE_TASKS_OR_BLOCK}`

Every state-changing operation in an enabled team project runs the compact
active-work preflight. The full team context is loaded only when the current
task or proposed facts may overlap active work.

## Known Gaps

- `{TEAM_OPERATING_MODEL_GAP}`

Do not claim the module is enabled while required actors, authority,
coordination backend, storage/privacy policy, or conflict handling remain
unknown.
