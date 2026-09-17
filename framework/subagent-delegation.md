---
alatyr_doc:
  id: framework.subagent-delegation
  type: framework-rule-owner
  owns_rules:
    - ALATYR-DELEGATION-001
  depends_on:
    - ALATYR-CONTEXT-001
    - ALATYR-ADAPTER-001
    - ALATYR-APPROVAL-001
    - ALATYR-AUTHORIZATION-001
    - ALATYR-INTEGRITY-001
    - ALATYR-BRIDGE-001
    - ALATYR-DECOMPOSITION-001
  applies_to:
    - code-local
    - ai-infrastructure
---
# Subagent Delegation

This file defines how an installed Alatyr adapter may let a primary assistant
delegate tasks from the primary-owned decomposition plan to subagents or faster
models without transferring project authority or final responsibility.

Subagent delegation is optional and capability-gated. The target adapter owns
the delegation policy, supported assistant surfaces, verified model bindings,
parallelism limits, tool and write permissions, validation, and evidence.
Portable framework core does not require a vendor, model, client feature, or
paid service.

The word `subagent` names a portable worker role, not a product-specific API.
A supported assistant surface may execute the same packet through a native
worker, an approved external dispatcher such as a target tool, MCP server, or
wrapper, or a suggestion-only handoff. When none is supported, the primary
assistant continues locally.

An enabled target owns a portable worker layer made of a delegation policy,
role catalog, orchestration prompt, task graph, execution-tree ledger, bounded
packet, primary-approved branch envelope, normalized result, branch checkpoint,
and primary convergence record. Provider-native agents, managed workers,
external dispatchers, and suggestion-only handoffs are thin execution
bindings to that layer. They do not become policy or project-knowledge owners.

## Responsibility Boundary

The primary assistant remains the operation orchestrator. It owns:

- request interpretation, task profile, changed-fact and risk classification
- source-of-truth, business-rule, architecture, and approval decisions
- the critical-path next action and workstream dependencies
- subagent packet review, result integration, cross-workstream reconciliation
- final logical integrity review, target validation, and completion evidence

A delegate is an execution surface, not a project owner, approver, decision
authority, or automatically enrolled team actor. Delegation does not broaden
allowed actions, tool permissions, network access, approval scope, or changed
files.

Separate dispatch authority from dispatch transport. The primary owns every
branch envelope and all project decisions. A verified branch coordinator may
use provider-native nested transport only for read-only children inside that
immutable, hash-bound envelope. It cannot expand depth, actions, tools, paths,
semantic scope, coverage, context, result, retry, validation, or expiry limits.
Any requested expansion returns to the primary as a proposal.

Delegation also does not broaden current user authorization. A worker inherits
only the parent scope and authorized action phases. It must not commit, push,
publish, deploy, or perform live external effects unless the newest parent
request explicitly authorizes that phase and the primary assistant rechecks it
before integration or execution.

## Activation Gate

Evaluate delegation only after selecting the main operation and task profile.
Use it when all applicable conditions are satisfied:

- the primary assistant has identified its immediate critical-path action
- a sidecar or workstream is independently useful and does not block that next
  action
- the packet has one coherent goal, bounded context, and explicit non-goals
- read/write surfaces are disjoint from concurrent packets, or the packet is
  read-only
- acceptance criteria and validation are local and objective
- required capability, model-access, permission, and freshness evidence exists
- the primary assistant can review and converge the result before completion

Do not delegate merely because a client supports subagents. Skip delegation
when packet preparation, result review, or synchronization is likely to cost
more than doing the work locally.

## Task Planning Contract

Before dispatch, the primary assistant creates or reuses the target
task-decomposition plan. Each worker-eligible task records one implementation
level, one bounded goal, dependencies, changed facts, expected write scope,
required context, objective acceptance, validation, selected role, and current
status.

Use the following portable statuses: `PLANNED`, `BLOCKED`, `READY`, `RUNNING`,
`REVIEW_REQUIRED`, `DONE`, `FAILED`, and `CANCELLED`. Only the primary
assistant may mark a task ready. A task is ready only when:

- every dependency is complete or explicitly not applicable
- its semantic owner and parent authorization are already known
- required context fits the packet budget
- its write scope is disjoint from concurrent work, or it is read-only
- acceptance and validation can be evaluated without a new project decision

Reject dependency cycles. Keep tasks with shared semantic ownership in one
primary-owned convergence stream even when their mechanical work is separate.
Do not turn the task graph into an autonomous scheduler: dispatch still passes
through capability, authorization, approval, and cost gates.

## Delegation Tree And Stop Contract

The primary assistant owns the complete delegation tree and every branch
authorization. In `propose-only` mode, a worker returns child proposals for
primary dispatch. In `primary-preauthorized-read-only` mode, a verified branch
coordinator may instantiate depth-two read-only children within a primary-
issued envelope. It never gains authorization or decision authority. New
scope, overlap, failed validation, stale context, malformed evidence, or budget
pressure ends the branch and returns control to the primary.

The execution-tree ledger is the required synchronization surface for enabled
recursive delegation. It binds current-scope authorization, base revision,
recorded execution time, canonical JSON policy digest, hash-bound capability evidence,
aggregate worker budget, parent-child edges, packet and result IDs, semantic
scope, changed fact IDs, canonical owners, surface references, relationship
references, overlap decisions, child proposals, branch envelopes and
checkpoints, measured result and accepted-summary artifacts, stop reasons,
cancellation, and primary convergence evidence. A
valid packet or result is not sufficient when the tree violates budget,
coverage, semantic-overlap, authorization, or convergence rules.

Use depth `0` for the primary plan and depth `1` for ordinary workers. The
portable default maximum worker depth is `1`; a target may permit depth `2`
only through an explicit policy value not above the portable hard maximum of
`2`. Deeper delegation is invalid. The target policy also sets hard limits for
total delegates, children per parent, aggregate delegated context, total
retries, and parallel delegates. The minimum independent-packet threshold is
an activation condition, not a default fan-out target.

Give every packet a unique coverage key. Reject concurrent or descendant
packets whose coverage duplicates or overlaps work already assigned unless the
primary records a specific reconciliation reason. Stop expansion as soon as
acceptance criteria and required evidence are covered; do not seek additional
workers merely because budget remains.

Every completed, blocked, rejected, or undispatched branch records one
normalized stop reason: scope covered, evidence sufficient, coordination cost
exceeds benefit, maximum depth reached, worker/context/result/retry or primary-
context budget reached, checkpoint required or invalid, context or evidence
digest mismatch, branch-envelope violation, validation regression, semantic
decision required, overlapping scope, primary critical path, capability
unavailable, user restricted, or cancelled by the primary assistant.
Evidence saturation requires assigned local proof obligations as well as
acceptance and required evidence. Missing stop evidence or uncovered assigned
obligations is a failed delegation record, not permission to continue.

## Worker Role Catalog

The target role catalog owns reusable semantic roles such as explorer,
implementer, test runner, documentation worker, reviewer, and fast focused
worker. A role defines its purpose, action ceiling, write mode, packet limits,
required output, and prohibited responsibilities. It does not name a portable
vendor model.

Per-surface capability records bind enabled role IDs to a native profile,
approved external route, inherited model, explicit verified model, or client
default. Installation and update may create provider-native worker definitions
only after verifying that the selected target client supports project-owned
definitions. Those definitions must remain thin: point to the target policy,
role prompt, packet, result, and validation instead of duplicating them.

Do not install speculative native worker files for unsupported or unknown
surfaces. Record suggestion-only or sequential-primary fallback instead.

## Fast Focused Worker

A target may define a `fast-focused-worker` role for latency-sensitive work.
Use that role only for tasks that are small, focused, reversible, context-
bounded, and mechanically verifiable. Typical candidates include:

- one narrow interface or presentation adjustment
- a bounded test, fixture, link, inventory, or documentation update
- a mechanical edit whose design and semantic decision are already settled
- an independent read-only search or evidence collection task

The target must verify the actual model binding on the selected assistant
surface. A model name in source documentation is not capability evidence.
Record why the fast role fits, what it may touch, and which validation it must
run. Fast execution is not proof of lower billing cost or sufficient quality.

## Non-Delegable Work

Keep the following with the primary assistant or a stronger explicitly
verified decision role:

- unresolved requirements, business rules, semantic invariants, or ownership
- architecture selection, source-of-truth conflict resolution, or approval
- security, credentials, permissions, destructive actions, production access,
  spend, migrations, backfills, or external side effects
- broad refactors, shared generated artifacts, or overlapping write scopes
- final integration, global logical integrity review, and completion claims
- work whose validation depends on unstated project knowledge

If risk, scope, ambiguity, permissions, or dependencies expand after dispatch,
stop or discard the delegated result and return the work to the primary
assistant. Do not ask a delegate to resolve the boundary that made delegation
unsafe.

## Capability Negotiation

Before dispatch:

1. Confirm the module is enabled and the operation does not forbid delegation.
2. Load the target delegation policy and only the selected assistant-
   capability record.
3. Select one verified dispatch backend: native worker, approved external
   dispatcher, suggestion-only handoff, or unsupported/local fallback.
4. Confirm exact client product/runtime, explicit or automatic delegation,
   project worker-definition support and paths, tool restrictions, write
   isolation, background and nested behavior, model override, parallelism,
   actual-model evidence, client version, verification time, and freshness.
   For an external dispatcher, also resolve its target AI-infrastructure item,
   provenance, permissions, approval, privacy, and failure behavior.
5. Resolve an enabled target-owned role and its per-surface binding. Treat
   unavailable, unsupported, unknown, expired, or rate-limited bindings as a
   fallback condition.
6. Confirm allowed actions, tools, context, write scope, approval, privacy,
   validation, and maximum concurrency.

If model selection is unavailable, the target may inherit the primary model,
use a verified client default, suggest delegation without executing it, or
continue locally. Never silently claim that a requested model was used.

Do not infer capability parity between assistant products. The same strategy
applies through the shared packet and convergence contract, while execution
mechanics remain target-verified for each surface.

## Delegation Packet

Every dispatched task uses a bounded target packet that records:

- packet, parent-packet, operation, workstream, and parent-assistant identifiers
- depth, remaining worker and context budget, and a unique coverage key
- goal, non-goals, expected output, and local acceptance criteria
- semantic scope, changed facts, canonical owner references, surface
  references, relationship references, and overlap decision
- parent context-packet digest, context delta, and required or excluded context
- allowed actions, tools, files, surfaces, and prohibited actions
- selected assistant surface, role, model binding, and capability evidence
- dependency state, concurrency/write-isolation decision, and fallback
- validation to run and the result/evidence shape to return
- result and accepted-summary budgets
- child proposals or one primary-approved read-only branch envelope

Do not send the full project context by default. Do not split one semantic fact
across independent delegates unless one primary-owned workstream performs
reconciliation.

## Normalized Result Contract

Every backend returns or is normalized into the target worker-result contract.
It records task and packet identity, observed base revision, status, actual
surface/role/model or unverified status, touched surfaces, commands/tools,
validation, acceptance criteria, scope violations, semantic or architecture
deviations, unexpected repository state, authorization concerns, unresolved
findings, follow-up, residual risk, depth, coverage key, semantic scope,
changed fact IDs, canonical owner references, surface references, relationship
references, overlap decision, execution-tree node status, child proposals, and
a normalized stop reason.

The execution node binds the delivered context to a measured UTF-8 artifact;
its recorded context words must match that artifact. The machine result records
observed raw-result and accepted-summary words and characters, content SHA-256
values, input-context identity, tools used, child-result digests, evidence
references, and a deterministic subtree digest. Tool IDs must remain inside a
recursive branch envelope's allowed-tool selectors. Raw payloads remain lazy
references. Routine parent context receives only the accepted summary. A digest
proves identity and integrity, not correctness or comprehension.

A recursive branch also emits a hash-bound checkpoint covering its envelope,
accepted and rejected child results, completed coverage, compact conclusion,
context identity, canonical JSON digests of accepted child evidence manifests
and validation, unresolved escalation, next action, and stop reason. The
newest accepted checkpoint plus delta replaces older branch prose when work
resumes. Load raw child evidence only for a named conflict, scope concern,
failed validation, semantic decision, or final-review requirement.

Provider-native prose is not accepted directly as completion evidence. The
primary assistant must normalize it first. A missing identity, stale baseline,
out-of-scope write, unsupported model claim, or omitted required validation is
a rejection or rework condition.

## Retry And Conflict Handling

Retry only when the target policy allows it, the parent scope and authorization
are unchanged, and the failure is transient or has one bounded local repair.
Do not retry authorization, capability, approval, scope, dependency, semantic,
or architecture failures. Do not repeat an identical failing attempt without
new evidence.

Reject concurrent overlapping writes. Return contradictory results to the
primary assistant rather than asking workers to vote. Revalidate a result
against current repository state before integration when its baseline is
stale. Reject scope violations even when their output appears useful; create a
new primary-owned plan and authorization gate if that work is still desired.

## Dispatch And Convergence

Dispatch independent packets in parallel only when their write sets and
semantic owners do not overlap. Keep urgent blocking work on the primary
critical path unless delegation materially shortens that path and introduces
no coordination uncertainty.

After a delegate returns, the primary assistant must:

1. Verify packet identity, hash the recorded capability-evidence artifact,
   verify actual model/capability evidence when available,
   execution-tree node status, touched surfaces, commands run, and unresolved
   findings.
2. Reject out-of-scope, unsupported, unvalidated, or conflicting output.
3. Review the patch or evidence against current repository state.
4. Verify measured context, result, and summary artifacts, recursive envelope
   and checkpoint digests, and direct versus indirect result coverage.
5. Update the execution-tree ledger with accepted, rejected, cancelled, or
   undispatched branches and their stop reasons.
6. Run or repeat target validation required by combined risk.
7. Reconcile changed facts, approvals, companion surfaces, and workstreams.
8. Record primary convergence over delegated outputs, semantic-overlap
   decisions, aggregate budget use, validation, residual risk, and rejected
   child proposals.
9. Report delegated and locally completed work without overstating model,
   quality, latency, or cost evidence.

A delegate result is evidence for primary review, not operation completion.

Provider-native nested delegation never grants autonomous recursion. A target
may use verified nested transport only when policy permits depth `2` and the
primary has issued the exact branch envelope. Every child packet narrows its
parent's context and remains inspect-only with no write scope.

## Cost And Performance Evidence

The target policy may optimize for latency, context volume, or measured cost,
but should keep those goals separate. Record:

- why delegation was expected to help
- packet preparation and review overhead when measured
- model or role actually used, or that it could not be verified
- validation/rework outcome
- aggregate worker context and raw-result words
- accepted-summary words actually ingested by the primary
- whether hierarchical compaction avoided loading descendant raw outputs
- observed latency or cost only when comparable evidence exists

Do not claim percentage savings from model labels or parallelism alone.

## Rejection Criteria

Reject or revise delegation that:

- delegates the primary assistant's immediate blocking action without a clear
  wall-clock benefit
- assigns overlapping writes or one unresolved invariant to parallel agents
- lets a delegate choose its own permissions, approval scope, or project facts
- hard-codes an unverified vendor model as a portable requirement
- treats a fast model as appropriate for architecture, security, or semantic
  decisions because it is available
- omits a fallback for unavailable or failed subagents
- accepts delegated output without primary review and final convergence
- claims cost or quality improvement without measured evidence
