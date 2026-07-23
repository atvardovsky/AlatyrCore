# Team Collaboration Gate

Use this gate only when the target enables the `team-collaboration` module.

## Activation

- Module profile says `team-collaboration` is enabled.
- Team operating model has an owner, coordination backend, synchronization
  direction, storage, retention, privacy, actor, authority, priority, review,
  and conflict policy.
- Work registry or deterministic backend projection is available.
- Team-active context remains outside routine bootstrap.

## Before Start Or Resume

- Stable task and actor IDs resolved.
- Goal, non-goals, priority rationale, owner, reviewers, allowed actions,
  profiles, areas, base revision, and backend reference recorded.
- Changed-fact IDs and canonical owner references resolved or gaps recorded.
- Active-task overlap checked by facts and owners first; contracts,
  dependencies, migrations, generated artifacts, approvals, and file/surface
  overlap checked as applicable.
- Claim state and staleness checked.
- Conflicting or unresolved overlap coordinated, sequenced, merged, split, or
  blocked before implementation.

## Before Handoff

- Current checkpoint records revision, diff, completed work, changed facts,
  decisions, validation, approvals, invalidated assumptions, blockers,
  residual risk, minimum resume context, and next action.
- Destination actor or role exists in the operating model.
- Handoff acceptance remains explicit.
- Project facts are referenced from canonical owners, not copied as handoff
  authority.

## Before Review Or Merge Readiness

- Current diff remains inside task scope and allowed actions.
- Concurrent overlap and invalidated assumptions were rechecked.
- Required roles, specialists, and CODEOWNERS-equivalent reviewers are
  evidenced.
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
- Read-only status, conflict, review, and merge-check operations do not mutate
  the registry.
- Team records contain no secrets, raw chats, private prompts, credentials, or
  unnecessary personal data.
- Unavailable external tracker evidence is reported as partial or unverified.
