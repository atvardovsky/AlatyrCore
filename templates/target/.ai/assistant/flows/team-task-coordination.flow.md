# Team Task Coordination Flow

Use this flow in `{PROJECT_NAME}` for team status, task start, claim, conflict
review, checkpoint, or release requests when the `team-collaboration` module is
enabled.

Record-changing variants update coordination evidence only. Status and
conflict review remain read-only. When the selected mode is `read-only`,
return the proposed registry/backend delta without persisting it. Persistence
requires `adapter-only` and target backend permission. No variant grants
approval, accepts project facts, or authorizes implementation.

## Target Sources

- Team operating model: `.ai/project/team-operating-model.md`
- Work registry: `.ai/assistant/team/work-registry.json`
- Source-of-truth registry: `.ai/project/source-of-truth-registry.md`
- Consistency map: `.ai/project/consistency-map.json` when enabled
- Team gate: `.ai/assistant/gates/team-collaboration.md`
- Context router: `.ai/assistant/context-router.json`
- Target task backend: `{TARGET_TASK_SOURCE_OF_TRUTH}`
- Target validation or manual review: `{TARGET_TEAM_REGISTRY_VALIDATION}`

## Status

For `Alatyr team status`:

1. Keep allowed actions `read-only`.
2. Read the operating model and compact active-task projection.
3. Report evidence time and revision, module/backend state, active tasks,
   blocked tasks, stale claims, unresolved overlaps, pending handoffs, and
   review or merge-ready tasks.
4. Show no more than three highest-priority actions requiring attention.
5. Mark unavailable external tracker evidence as partial or unverified.

Do not update timestamps merely to make status evidence look fresh.

## Start

For `Alatyr start {TASK}`:

1. Confirm the task goal, non-goals, priority evidence, owner, reviewers,
   allowed actions, selected base profile, and project areas.
2. Resolve changed-fact IDs and canonical owners as far as current evidence
   permits.
3. Compare the proposed task with active registry entries before assigning
   `ready` or `claimed`.
4. Record unresolved facts, dependencies, approval needs, and overlap state.
5. Create the task in the canonical backend or registry according to the
   configured synchronization direction.

Do not invent actors, priority, authority, active history, or external tracker
state.

## Claim

For `Alatyr claim {TASK_ID}`:

1. Check the task, current revision, actor ID, claim policy, and existing claim.
2. Re-run changed-fact, contract, dependency, generated-artifact, migration,
   and secondary file/surface overlap review.
3. Stop or sequence when overlap is conflicting or unresolved.
4. Record claim actor, mode, time, expiry/staleness evidence, and base revision.
5. Keep claims advisory unless the target backend explicitly enforces them.

Claiming a task does not approve its changes or mark implementation started.

## Conflicts

For `Alatyr conflicts {TASK_ID}`:

1. Keep allowed actions `read-only`.
2. Compare active tasks by changed-fact IDs and canonical owners first.
3. Compare shared contracts, dependencies, migrations, generated artifacts,
   approvals, and branch/base revisions.
4. Compare files or expected surfaces as secondary evidence.
5. Classify each overlap as `none`, `compatible`, `sequencing-required`,
   `conflicting`, or `unresolved`.
6. Recommend coordination, sequencing, task merge, scope split, or blocking.

Do not claim absence of conflict when changed facts or active external tasks
are unavailable.

## Checkpoint

For `Alatyr checkpoint {TASK_ID}`:

1. Compare registry state with the current repository revision and task
   backend.
2. Create a record from
   `.ai/assistant/templates/team-checkpoint.md`.
3. Record completed work, changed facts, decisions, diff/revision, review
   state and evidence, validation, approvals, invalidated assumptions,
   blockers, residual risk, minimum resume context, and next action.
4. Update only the checkpoint reference and normalized task state in the work
   registry or configured backend.

## Release

For `Alatyr release {TASK_ID}`:

1. Confirm the actor may release the claim under target policy.
2. Record whether work is paused, handed off, blocked, cancelled, or still
   active without a claim.
3. Preserve checkpoint, diff, validation, approval, and residual-risk evidence.
4. Mark the claim released with time and revision.

Releasing a claim does not mark the task complete or discard unresolved work.

## Final Evidence

Report the operation, task and actor IDs, evidence revision, priority,
changed-fact overlap, claim state, backend synchronization result, approvals,
validation, residual risk, and next responsible actor.
