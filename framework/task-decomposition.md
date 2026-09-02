---
alatyr_doc:
  id: framework.task-decomposition
  type: framework-rule-owner
  owns_rules:
    - ALATYR-DECOMPOSITION-001
  depends_on:
    - ALATYR-CONTEXT-001
    - ALATYR-SOURCE-001
    - ALATYR-RISK-001
    - ALATYR-APPROVAL-001
    - ALATYR-AUTHORIZATION-001
    - ALATYR-INTEGRITY-001
  applies_to:
    - docs-local
    - code-local
    - business-change
    - architecture-change
    - data-change
    - security-sensitive
    - ai-infrastructure
    - framework-upgrade
---
# Task Decomposition

This file defines how an installed Alatyr adapter should turn a user request
into bounded subtasks before analysis, modification, validation, delegation, or
final evidence.

Task decomposition is required for non-trivial work and may collapse to one
local task for small work. It is not the same as subagent delegation. The
primary assistant can decompose and execute work itself when no worker support
is available, useful, safe, or cost-effective.

The target adapter owns project-specific task areas, source owners,
validation, worker availability, implementation-level thresholds, and local
evidence storage. Portable framework core owns the shape and safety boundaries
of the decomposition contract.

## Objective

Use decomposition to choose the smallest quality-preserving execution path:

- split by semantic responsibility before splitting by files
- assign an implementation level to each subtask
- attach only the context needed by that subtask
- identify dependencies, owners, validation, and allowed actions
- choose primary execution or an eligible worker role per subtask
- keep final convergence with the primary assistant

Decomposition should reduce repeated context loading and improve consistency.
It must not hide risk, skip source-of-truth review, weaken approval, or turn a
discussion into implementation.

## Decomposition Sequence

For every non-trivial request:

1. Classify current user authorization, allowed actions, task profile, task
   scale, changed facts, project areas, and risk.
2. Split the work by changed fact, canonical owner, contract, area,
   dependency, validation need, and support-surface synchronization.
3. Assign one implementation level to each subtask.
4. Record dependencies and reject cycles.
5. Select the executor: primary assistant, eligible worker role, suggestion-
   only handoff, or blocked.
6. Attach bounded context, explicit non-goals, allowed files or surfaces,
   validation, and acceptance criteria.
7. Execute or dispatch only ready tasks.
8. Reconcile results, changed facts, approvals, validation, documentation,
   diagrams, support information, and residual risk in the primary operation.

For a small request, the decomposition result can be one task with one profile,
one local surface or direct neighbor set, and compact final evidence. Do not
create heavy operation packets when the one-task plan is enough.

## Implementation Levels

Implementation levels describe how deep a subtask may go. They are action
ceilings, not permission grants.

Level `L0`: discussion only.
Use for questions, tradeoff discussion, brainstorming, or clarification.
Allowed actions: read-only.
Executor: primary assistant unless the target explicitly permits read-only
review workers.
Quality gate: no repository edits.

Level `L1`: read-only analysis.
Use for inspection, evidence collection, issue review, inventory, status, or
recommendations.
Allowed actions: read-only.
Executor: primary assistant or read-only worker.
Quality gate: report evidence and uncertainty; do not modify files.

Level `L2`: documentation or support update.
Use for bounded docs, adapter support information, prompts, gates, diagrams,
or generated-reference updates when the underlying project fact is already
owned elsewhere.
Allowed actions: docs-only or adapter-only as selected by current scope.
Executor: primary assistant, documentation worker, or fast focused worker when
the target policy permits it.
Quality gate: no invented facts; reconcile with canonical owners.

Level `L3`: tests or validation.
Use for adding or running tests, checkers, fixtures, or validation evidence
when product behavior is already understood or being characterized.
Allowed actions: read-only or code-and-tests according to current scope.
Executor: primary assistant, test worker, reviewer, or fast focused worker
when local acceptance is objective.
Quality gate: do not change expectations to hide a defect or bypass the
selected contract.

Level `L4`: bounded implementation.
Use for a local code change with settled design, known owners, bounded write
scope, and objective validation.
Allowed actions: code-and-tests.
Executor: primary assistant or implementer; fast focused worker only for small,
reversible, mechanically verifiable tasks.
Quality gate: validate locally and update required companion surfaces.

Level `L5`: coherent change package.
Use when code, tests, docs, diagrams, support information, approvals, or
multiple project surfaces must move together as one semantic result.
Allowed actions: docs-only, adapter-only, code-and-tests, or full-with-
approval according to current scope.
Executor: primary assistant owns convergence; workers may handle bounded
sidecars only.
Quality gate: one global logical integrity review over the combined repair set.

Level `L6`: architecture or business decision.
Use for accepted behavior changes, architectural intent, source-of-truth
conflict resolution, data ownership, public contracts, security posture, or
other semantic authority decisions.
Allowed actions: read-only until the target decision owner and required
approval are explicit.
Executor: primary assistant only. Related evidence collection can be split
into separate `L1` read-only subtasks, but workers must not own the `L6`
decision task.
Quality gate: route accepted facts to canonical owners before implementation.

Level `L7`: protected external or publication action.
Use for commit, push, deploy, destructive action, live external effect,
credential, permission, spend, production dependency, migration, or release.
Allowed actions: only the explicitly authorized current phase and approval
scope.
Executor: primary assistant only.
Quality gate: recheck newest user authorization immediately before action.

## Executor Selection

Choose the least costly executor that can satisfy the subtask's implementation
level and validation without increasing total coordination cost.

Primary execution is preferred when:

- the plan has one ready task
- the task owns a semantic, approval, architecture, or conflict decision
- worker setup, packet creation, review, or merge cost exceeds expected gain
- current capability evidence is missing, stale, expired, or unavailable
- write scopes overlap or dependencies are unresolved

Worker execution may be proposed or used only when the target delegation
module, policy, role catalog, and selected assistant capability record permit
it. A worker receives a task packet after the primary assistant assigns the
implementation level, context, scope, dependencies, and validation.

## Quality Guard

Escalate the level or return work to the primary assistant when:

- a changed semantic fact appears
- source-of-truth ownership is missing, disputed, or contradicted
- approval, authorization, safety, security, data, architecture, public
  contract, or live-external scope appears
- validation fails or does not prove the changed contract
- a worker reports a scope violation, stale baseline, unexpected repository
  state, or architecture deviation
- a new dependency or relationship appears during the task

Escalation should load only the new owner, relationship, policy, or validation
surface that triggered it. Do not respond to escalation by loading the whole
adapter or project.

## Evidence

For material work, final evidence should include:

- decomposition policy and template revision
- task IDs, implementation levels, and executor decisions
- dependencies and readiness/blocker state
- context selected and intentionally omitted for each task
- worker packet and result IDs when delegation was used
- validation and acceptance evidence per task
- primary convergence result and residual risk

Do not claim cost, latency, or quality improvement without comparable
measurement. A decomposition plan is evidence of process structure; it is not
proof that an assistant understood or followed every rule.

## Rejection Criteria

Reject or revise decomposition that:

- splits by files before identifying changed facts and owners
- marks dependent or overlapping semantic work as independent
- assigns architecture, business, approval, commit, publish, or live-external
  authority to a worker
- chooses a faster worker for a task whose risk requires stronger reasoning
- hides missing context behind a low implementation level
- runs full orchestration for a small one-task request without a concrete
  benefit
- accepts local worker success as final operation completion
