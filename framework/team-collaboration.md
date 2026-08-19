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
contributor. It needs a target owner, a machine-readable team policy, a
coordination backend contract, storage and privacy rules, and a maintained
work registry or equivalent integration.

## Ownership Split

The project contour owns:

- actor IDs, roles, teams, and decision authority
- display names, aliases, identity mappings, and identity-verification needs
- priority classes and target-specific prioritization criteria
- required reviewers and escalation paths
- the accepted issue, decision, and source-of-truth systems
- project retention, privacy, and coordination-backend policy

The repository adapter contour owns:

- operation routing and team workflow mechanics
- ignored local actor selection and its explicit attribution boundary
- active-task index, per-task, claim, checkpoint, conflict, and handoff records
- optimistic-concurrency and backend-capability evidence
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

The target should keep those machine-relevant fields in one structured team
policy. A human operating-model document may explain the policy but must not
become a second actor or authority registry.

An enabled adapter may let a user select the current actor through an explicit
assistant request such as `Alatyr set actor <actor-id-or-name>`. Resolve the
input to exactly one active target actor and store only the selected actor ID,
selection time, policy revision, and verification state in ignored local
state. Unknown or ambiguous names produce an enrollment proposal or a bounded
clarifying question; they do not create an actor automatically.

Local actor selection supports attribution. It is not authentication and does
not modify Git configuration. Git author, operating-system username, assistant
account, task ownership, or an unverified display name must not be treated as
identity proof. When the target requires verified identity for an action, use
its configured identity provider and record the external reference without
storing credentials.

Approvals remain governed by `ALATYR-APPROVAL-001`. Assignment, review, task
claim, or decision participation does not grant protected-change approval.

## Shared Work Registry

The target adapter should provide one machine-readable registry or a
deterministic projection of the selected coordination backend. For repository
storage, prefer one record per task plus a generated compact active-work index;
do not make every actor edit one monolithic task array. The registry records
locations, projection metadata, backend state, and its own revision.

Each task should record:

- stable task ID, goal, non-goals, priority, and priority rationale
- requesting, owning, reviewing, updating, and assistant actor IDs
- status, task record revision, expected revision, backend revision, and
  evidence revision
- parent request, branch or worktree, and coordination-backend reference
- selected context profiles, project areas, and allowed actions
- changed-fact IDs, canonical owner references, and expected surfaces
- dependencies, blockers, related tasks, and overlap state
- approval records, validation state, latest checkpoint, and handoff state
- review state and revision-bound review evidence references
- claim lease, actor, mode, base/backend revisions, heartbeat, timestamps, and
  staleness evidence

Keep the registry compact. Store references and normalized evidence instead of
raw chats, copied source-of-truth prose, secrets, or large diffs.

The active-work index is a deterministic projection for routing and conflict
preflight, not a write authority. It should contain only stable task ID,
status, actors, branch/worktree, priority, changed-fact and owner references,
contract/dependency/surface selectors, task record path, and record/backend
revisions needed to select relevant work.

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

1. Read the compact active-work index and current repository revision.
2. Match the explicit task/backend reference, branch or worktree, project
   areas, changed-fact IDs, canonical owners, contracts, dependencies, and
   expected surfaces against active work.
3. When a match or unresolved overlap exists, load the selected task, relevant
   overlaps, team policy, backend contract, flow, and gate.
4. Resolve the current actor before a task or claim write.
5. Compare changed-fact IDs and canonical owner references with active tasks.
6. Compare shared contracts, dependencies, generated artifacts, migrations,
   and approval scope.
7. Use expected or changed file overlap only as secondary evidence.
8. Classify overlap as none, compatible, sequencing-required, conflicting, or
   unresolved.
9. Coordinate, sequence, merge tasks, or stop when unresolved overlap can
   invalidate assumptions.

Claims should include a base revision and target-defined staleness evidence.
An expired, abandoned, or revision-invalid claim must not block work forever.
Releasing a claim does not mark a task complete.

Every task mutation uses optimistic concurrency or an equivalent target-native
atomic update. The writer supplies the task revision it observed. If the
current task or backend revision differs, stop, refresh the selected record,
re-evaluate overlap and authority, and produce a new proposed delta. Never
silently overwrite another actor's update. Active claims should use a stable
lease ID and target-defined heartbeat or expiry evidence when supported.

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
- `Alatyr set actor <actor-id-or-name>`
- `Alatyr who am I`
- `Alatyr clear actor`
- `Alatyr start <task>`
- `Alatyr claim <task-id>`
- `Alatyr conflicts <task-id>`
- `Alatyr checkpoint <task-id>`
- `Alatyr handoff <task-id>`
- `Alatyr review <task-id>`
- `Alatyr merge check <task-id>`
- `Alatyr release <task-id>`

They are chat shortcuts, not portable shell commands. `who am I` is read-only;
set and clear actor may change only ignored local identity state. Read-only
operations must not mutate the registry. Record-changing operations require
the target's permitted adapter action mode and must not broaden project-change
scope.

## Context And Cost

Keep full team coordination out of routine bootstrap. In an enabled team
project, a state-changing operation may run a compact preflight against the
active-work index. Expand through the optional `team-active` task-scale overlay
only when an explicit team request, task/branch match, or possible fact,
contract, dependency, migration, generated-artifact, or surface overlap exists.

The expanded overlay loads:

- the structured target team policy and only needed operating guidance
- the registry metadata, backend contract, and selected task record
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

The target backend contract should declare its stable ID, provider, canonical
task source, projection direction, consistency model, write strategy,
capabilities, idempotency, conflict behavior, permissions, authentication,
availability behavior, validation, and optional Alatyr extension ID. Portable
capabilities are read tasks, create task, claim, release, checkpoint, handoff,
review, and synchronization status. Unsupported capabilities remain explicit.

Provider-specific integrations belong in target-owned tools or reviewed Alatyr
extensions. The portable framework does not execute a provider, store access
tokens, or assume that a backend write succeeded. Write-capable integrations
must support target-native atomic updates or compare-and-swap semantics and
return current backend revision evidence.

## Installation And Update

During installation:

1. Inventory existing team roles, ownership, trackers, task states, branch or
   worktree conventions, review rules, decision records, and privacy policy.
2. Select the coordination backend and source or synchronization direction.
3. Record one machine-readable team policy and its human explanation from
   target evidence.
4. Create the backend contract and local-identity ignore rule.
5. Initialize empty registry metadata, task-record storage, and active-work
   index unless active tasks are explicitly
   reviewed and imported.
6. Enable the module only when its owner, storage, validation, and conflict
   policy are known.

During framework or adapter update:

1. Compare the team contract and target schema before changing active records.
2. Preserve task IDs, actor references, claims, decisions, external links, and
   local identity without committing local state.
3. Migrate monolithic schema-1 task entries to separate schema-2 task records
   and generate the active-work index before replacing registry metadata.
4. Use a copy or prepare a plan when the schema changed; never partially split
   active tasks.
5. Recheck stale claims, revisions, module paths, operation routes, and active
   overlaps.
6. Do not overwrite current team state with a source template.

## Continuous Improvement

At a target-owned review cadence, aggregate bounded coordination evidence such
as stale claims, rejected revision conflicts, overlaps found before versus
after edits, handoff states, invalidated review evidence, repeated ownership or
authority gaps, and team-context volume. Do not rank individuals, infer
productivity, or retain raw conversations.

Repeated or one high-impact collaboration failure may become a normalized
project development-evidence pattern. A later read-only AI infrastructure
recommendation may propose improving or adding a target gate, checker, skill,
flow, tool, backend extension, or template. Apply existing-item-first, cost,
privacy, ownership, approval, validation, and rollback rules. Target evidence
does not directly change AlatyrCore framework policy.

## Final Evidence

Report:

- module state, owner, and coordination backend
- selected current user, requesting, owning, reviewing, updating, and assistant
  actor references plus verification state
- priority and decision authority evidence
- overlap result across facts, contracts, dependencies, and files
- task/backend revisions, compare-and-swap result, claim, checkpoint, handoff,
  review, and merge-readiness state
- approvals, validation, logical integrity, and current revision
- external evidence that was unavailable
- residual risks and next responsible actor

## Rejection Criteria

Reject or revise team coordination that:

- makes the optional module mandatory for every target
- treats a registry, tracker, task, or handoff as project source of truth
- infers authority or approval from assignment, identity, or priority
- treats local actor selection as authentication or silently enrolls an actor
- modifies global Git identity as part of actor selection
- detects conflicts only from file paths
- lets an ordinary state-changing operation bypass active-work preflight
- stores active tasks only in one conflict-prone repository array when
  concurrent repository writes are expected
- overwrites a task after its observed record or backend revision changed
- marks work merge-ready without binding evidence to a current revision
- overwrites active target records during installation or update
- loads all team history or active tasks for unrelated work
- stores secrets, raw chats, or unnecessary personal data
- requires one tracker, hosting service, or assistant vendor
