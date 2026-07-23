---
alatyr_doc:
  id: framework.team-collaboration
  type: framework-rule-owner
  owns_rules:
    - ALATYR-TEAM-001
  depends_on:
    - ALATYR-CONTEXT-001
    - ALATYR-SOURCE-001
    - ALATYR-RISK-001
    - ALATYR-APPROVAL-001
    - ALATYR-INTEGRITY-001
    - ALATYR-MODULE-001
    - ALATYR-OPERATION-001
    - ALATYR-EVIDENCE-001
  applies_to:
    - all
---
# Team Collaboration

This file defines the portable contract for coordinating multiple humans,
assistants, and automation through an installed Alatyr adapter.

Team collaboration is an optional module. It supplements project trackers,
version control, code ownership, review policy, and large-task orchestration;
it does not replace them or require a particular vendor.

Concrete people, teams, priorities, branch names, issue trackers, storage
locations, review requirements, and decision authority belong to the target
project or repository adapter.

## Activation

Enable `team-collaboration` when a target needs at least one of:

- concurrent human or assistant work on related facts or contracts
- explicit task ownership, reviewer assignment, or handoff evidence
- coordination across branches, worktrees, sessions, or assistants
- changed-fact overlap detection before implementation or merge
- durable team checkpoints, decisions, or merge-readiness evidence

Do not enable the module merely because a repository has more than one
contributor. It needs a target owner, a coordination backend, storage and
privacy rules, and a maintained work registry or equivalent integration.

## Ownership Split

The project contour owns:

- actor IDs, roles, teams, and decision authority
- priority classes and target-specific prioritization criteria
- required reviewers and escalation paths
- the accepted issue, decision, and source-of-truth systems
- project retention, privacy, and coordination-backend policy

The repository adapter contour owns:

- operation routing and team workflow mechanics
- active-task, claim, checkpoint, conflict, and handoff records
- synchronization with a target-selected external tracker when present
- deterministic structural checks and final evidence format

Accepted business, architecture, data, security, or product decisions remain
project facts. A work registry, task packet, checkpoint, or handoff is
coordination evidence and must point to canonical owners instead of replacing
them.

## Actor Contract

Use stable target-owned actor IDs for:

- human implementers
- human reviewers
- AI assistants
- automation or CI
- business, architecture, data, security, or adapter decision owners

The target operating model should record actor type, active status, roles,
decision authority, review scopes, and escalation owner. Do not infer a real
person, authority, or approval from a username, commit author, assistant
session, or task assignment.

Approvals remain governed by `ALATYR-APPROVAL-001`. Assignment, review, task
claim, or decision participation does not grant protected-change approval.

## Shared Work Registry

The target adapter should provide one machine-readable registry or a
deterministic projection of the selected coordination backend. Each active
task should record:

- stable task ID, goal, non-goals, priority, and priority rationale
- owner actor, reviewer actors, status, and evidence revision
- parent request, branch or worktree, and coordination-backend reference
- selected context profiles, project areas, and allowed actions
- changed-fact IDs, canonical owner references, and expected surfaces
- dependencies, blockers, related tasks, and overlap state
- approval records, validation state, latest checkpoint, and handoff state
- review state and revision-bound review evidence references
- claim actor, mode, base revision, timestamps, and staleness evidence

Keep the registry compact. Store references and normalized evidence instead of
raw chats, copied source-of-truth prose, secrets, or large diffs.

## Priority

Priority is a target scheduling and tradeoff fact, not proof of correctness or
authority.

Every non-default priority should name:

- target priority class
- rationale and deciding actor
- dependencies or deadlines that justify it
- preemption or escalation rule when applicable

Priority must not bypass source-of-truth ownership, safety, review, validation,
or approval. When priorities conflict, use the target decision owner and
record the result instead of letting an assistant silently choose.

## Claims And Concurrent Work

A task claim communicates intent to work. It is advisory unless the target
explicitly enables enforcement through its selected backend.

Before starting or resuming implementation:

1. Read the compact team overlay, selected task, and current repository
   revision.
2. Compare changed-fact IDs and canonical owner references with active tasks.
3. Compare shared contracts, dependencies, generated artifacts, migrations,
   and approval scope.
4. Use expected or changed file overlap only as secondary evidence.
5. Classify overlap as none, compatible, sequencing-required, conflicting, or
   unresolved.
6. Coordinate, sequence, merge tasks, or stop when unresolved overlap can
   invalidate assumptions.

Claims should include a base revision and target-defined staleness evidence.
An expired, abandoned, or revision-invalid claim must not block work forever.
Releasing a claim does not mark a task complete.

## Task Lifecycle

The portable states are:

- `proposed`
- `ready`
- `claimed`
- `active`
- `blocked`
- `review`
- `merge-ready`
- `complete`
- `cancelled`
- `stale`

Targets may map local tracker states to these values. Record any lossy mapping.

Starting, claiming, checkpointing, handing off, reviewing, merge-checking, and
releasing a task update coordination evidence only. If the action also changes
project facts or code, route the implementation through the appropriate
product, integrity, documentation, or large-task operation.

## Checkpoints And Handoffs

Create a checkpoint before a handoff, context reset, approval boundary, or
material dependency change. A checkpoint should record:

- completed work and current diff or revision
- changed facts, owner references, and decisions
- validation and approval state
- invalidated assumptions, blockers, and residual risk
- minimum resume context and exact next action

A handoff adds source actor, destination actor or role, reason, accepted scope,
required context, unresolved questions, and acceptance state. The receiving
actor must compare the handoff with current repository and registry evidence
before accepting it.

Handoff records are not evidence that validation ran, approval exists, or
project facts remain current.

## Decisions And Discussions

For business or architecture discussion, record:

- decision question and owner
- changed or disputed fact IDs
- considered options and evaluation criteria
- priority implications and affected dependencies
- selected result, rationale, consequences, and review date
- dissent, unresolved concerns, superseded decisions, and approval references

The accepted decision must be written to the target-selected canonical
decision or source-of-truth surface. The team decision template is only a
capture and routing aid.

## Team Review And Merge Readiness

Team review should verify:

- task scope, allowed actions, changed facts, and owner references
- active-task overlap and assumptions invalidated by concurrent work
- required role, specialist, and CODEOWNERS-equivalent review
- approval records against the complete current operation diff
- implementation, tests, docs, diagrams, generated artifacts, and blueprints
- target validation and one logical integrity review over the combined repair
  set
- checkpoint and handoff completeness
- residual risks, unresolved blockers, and follow-up ownership

`merge-ready` means the target-defined review and validation evidence is
present at the recorded revision. Reviewer assignment alone is not approval.
It is not a universal authorization to merge and becomes stale when the diff,
base revision, approvals, dependencies, or relevant concurrent tasks change.

## Team Operations

An enabled target may expose these assistant request aliases:

- `Alatyr team status`
- `Alatyr start <task>`
- `Alatyr claim <task-id>`
- `Alatyr conflicts <task-id>`
- `Alatyr checkpoint <task-id>`
- `Alatyr handoff <task-id>`
- `Alatyr review <task-id>`
- `Alatyr merge check <task-id>`
- `Alatyr release <task-id>`

They are chat shortcuts, not portable shell commands. Read-only operations must
not mutate the registry. Record-changing operations require the target's
permitted adapter action mode and must not broaden project-change scope.

## Context And Cost

Keep team coordination out of routine bootstrap. Route it through an optional
`team-active` task-scale overlay that loads:

- the target team operating model
- the compact work registry or selected task projection
- the relevant team flow and gate
- only the active task's fact owners, dependencies, checkpoint, and handoff

Compose `team-active` with `large-or-resumable` only when both activation gates
apply. Do not load all active tasks, team history, or tracker data when the
selected task has no possible dependency or changed-fact overlap.

## Storage, Privacy, And Integrations

The target chooses `repository`, `external-tracker`, `both`, or another
coordination backend and defines the synchronization direction. Alatyr Core
must not require GitHub, GitLab, Jira, Slack, or another provider.

Record IDs, hashes, bounded references, and normalized status. Do not store
credentials, private prompts, unnecessary personal data, raw chats, or secrets.
When external evidence is unavailable, report team state as partial or
unverified instead of inventing it.

## Installation And Update

During installation:

1. Inventory existing team roles, ownership, trackers, task states, branch or
   worktree conventions, review rules, decision records, and privacy policy.
2. Select the coordination backend and source or synchronization direction.
3. Record the operating model from target evidence.
4. Initialize an empty work registry unless active tasks are explicitly
   reviewed and imported.
5. Enable the module only when its owner, storage, validation, and conflict
   policy are known.

During framework or adapter update:

1. Compare the team contract and target schema before changing active records.
2. Preserve task IDs, actor references, claims, decisions, and external links.
3. Migrate a copy or prepare a plan when the schema changed.
4. Recheck stale claims, revisions, module paths, operation routes, and active
   overlaps.
5. Do not overwrite current team state with a source template.

## Final Evidence

Report:

- module state, owner, and coordination backend
- selected task and actor references
- priority and decision authority evidence
- overlap result across facts, contracts, dependencies, and files
- claim, checkpoint, handoff, review, and merge-readiness state
- approvals, validation, logical integrity, and current revision
- external evidence that was unavailable
- residual risks and next responsible actor

## Rejection Criteria

Reject or revise team coordination that:

- makes the optional module mandatory for every target
- treats a registry, tracker, task, or handoff as project source of truth
- infers authority or approval from assignment, identity, or priority
- detects conflicts only from file paths
- marks work merge-ready without binding evidence to a current revision
- overwrites active target records during installation or update
- loads all team history or active tasks for unrelated work
- stores secrets, raw chats, or unnecessary personal data
- requires one tracker, hosting service, or assistant vendor
