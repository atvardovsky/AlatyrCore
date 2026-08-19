# Team Collaboration Gate

Use this gate only when the target enables the `team-collaboration` module.

## Activation

- Module profile says `team-collaboration` is enabled.
- Structured team policy has an owner, active actors, authority, priority,
  review, transition, synchronization, storage, retention, privacy, and
  conflict policy; the operating model points to it.
- Backend contract defines capabilities, consistency, write conflict,
  permissions, authentication, and unavailable-evidence behavior.
- Registry metadata, per-task records or deterministic backend projections,
  and compact active-work index are available.
- `.ai/local/` is ignored before local actor selection is written.
- Team-active context remains outside routine bootstrap.

## Before Any State-Changing Operation

- Active-work index checked before loading full team state.
- Task, backend reference, branch/worktree, project area, changed facts,
  canonical owners, contracts, dependencies, migrations, generated artifacts,
  and expected surfaces matched against active work as available.
- Team overlay expanded when a match or unresolved overlap exists.
- Current actor resolved for attribution; unknown or ambiguous identity is not
  silently enrolled.
- Local actor selection is not treated as authentication, authority, review,
  or protected-change approval.

## Before Start Or Resume

- Stable task and actor IDs resolved.
- Requesting, owning, reviewing, updating, and assistant actor IDs remain
  distinct where applicable.
- Goal, non-goals, priority rationale, owner, reviewers, allowed actions,
  profiles, areas, base revision, and backend reference recorded.
- Changed-fact IDs and canonical owner references resolved or gaps recorded.
- Active-task overlap checked by facts and owners first; contracts,
  dependencies, migrations, generated artifacts, approvals, and file/surface
  overlap checked as applicable.
- Claim state and staleness checked.
- Observed task record revision and backend revision match the current values;
  otherwise the write stops and refreshes.
- Conflicting or unresolved overlap coordinated, sequenced, merged, split, or
  blocked before implementation.

## Before Handoff

- Current checkpoint records revision, diff, completed work, changed facts,
  decisions, validation, approvals, invalidated assumptions, blockers,
  residual risk, minimum resume context, and next action.
- Destination actor or role exists in the operating model.
- Source task/backend revision still matches before writing the handoff.
- Handoff acceptance remains explicit.
- Project facts are referenced from canonical owners, not copied as handoff
  authority.

## Before Review Or Merge Readiness

- Current diff remains inside task scope and allowed actions.
- Concurrent overlap and invalidated assumptions were rechecked.
- Required roles, specialists, and CODEOWNERS-equivalent reviewers are
  evidenced.
- Implementer/reviewer separation matches the structured target policy.
- Approved review state and revision-bound review evidence are recorded;
  reviewer assignment alone is insufficient.
- Protected changes have current approval records covering the complete diff.
- Implementation, tests, docs, diagrams, generated artifacts, blueprints, and
  AI infrastructure companion surfaces were checked as applicable.
- Target validation and global logical integrity review are recorded.
- Checkpoint and handoff state are current.
- Merge readiness is bound to current head/base revisions and invalidated by
  material evidence changes.
- Residual risks and next responsible actors are named.

## Safety Boundaries

- Task assignment, claim, review, priority, or handoff never grants approval.
- Current-actor selection never authenticates a user or grants authority.
- Unknown actors require enrollment by the target policy owner.
- Global Git identity is never changed by the team identity flow.
- Task writes never overwrite a newer task or backend revision.
- Read-only status, conflict, review, and merge-check operations do not mutate
  the registry.
- Team records contain no secrets, raw chats, private prompts, credentials, or
  unnecessary personal data.
- Unavailable external tracker evidence is reported as partial or unverified.
