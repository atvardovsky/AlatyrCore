# Team Handoff Flow

Use this flow in `{PROJECT_NAME}` to hand a task between humans, assistants, or
roles when the `team-collaboration` module is enabled.

With `read-only`, return draft checkpoint and handoff evidence without
persisting it. Writing records requires `adapter-only` and target backend
permission.

## Target Sources

- Team operating model: `.ai/project/team-operating-model.md`
- Work registry: `.ai/assistant/team/work-registry.json`
- Checkpoint template: `.ai/assistant/templates/team-checkpoint.md`
- Handoff template: `.ai/assistant/templates/team-handoff.md`
- Team gate: `.ai/assistant/gates/team-collaboration.md`
- Target handoff storage policy: `{TARGET_TEAM_RECORD_STORAGE_POLICY}`

## Steps

1. Resolve the task, source actor, destination actor or role, current
   repository revision, and canonical task backend.
2. Verify that the source actor and destination reference exist in the target
   operating model or record the missing target fact.
3. Re-run active-task overlap and invalidate stale claim, dependency,
   approval, or validation assumptions.
4. Create or refresh a checkpoint before the handoff.
5. Create a handoff record from
   `.ai/assistant/templates/team-handoff.md`.
6. Include completed work, changed facts and owners, decisions, current diff,
   validation, approvals, unresolved questions, residual risk, required
   context, and exact next action.
7. Mark the handoff `pending`; do not silently accept it for the receiver.
8. On acceptance, the receiver compares the record with current repository,
   registry, backend, and owner evidence before recording `accepted`.
9. When evidence changed materially, mark the handoff `stale` and refresh it.

## Final Evidence

Report source and destination actors, task ID, checkpoint and handoff paths,
evidence revision, acceptance state, changed facts, invalidated assumptions,
approval and validation state, unresolved questions, next action, and residual
risk.

## Rejection Criteria

Reject or revise a handoff that:

- lacks a current checkpoint or repository revision
- copies project source-of-truth prose instead of owner references
- treats destination assignment as acceptance or approval
- hides unresolved validation, approvals, conflicts, or residual risk
- requires the receiver to reload unrelated team history
