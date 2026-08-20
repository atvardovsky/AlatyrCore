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
    - ALATYR-INTEGRITY-001
    - ALATYR-BRIDGE-001
  applies_to:
    - code-local
    - ai-infrastructure
---
# Subagent Delegation

This file defines how an installed Alatyr adapter may let a primary assistant
decompose work and delegate bounded packets to subagents or faster models
without transferring project authority or final responsibility.

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
4. Confirm worker launch, model-override behavior, parallelism, actual-model
   evidence, client version, verification time, and freshness evidence. For an
   external dispatcher, also resolve its target AI-infrastructure item,
   provenance, permissions, approval, privacy, and failure behavior.
5. Resolve a target-owned role binding. Treat unavailable, unsupported,
   unknown, expired, or rate-limited bindings as a fallback condition.
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

- packet, operation, workstream, and parent-assistant identifiers
- goal, non-goals, expected output, and local acceptance criteria
- changed facts or explicit confirmation that no semantic fact is owned
- required and excluded context
- allowed actions, tools, files, surfaces, and prohibited actions
- selected assistant surface, role, model binding, and capability evidence
- dependency state, concurrency/write-isolation decision, and fallback
- validation to run and the result/evidence shape to return

Do not send the full project context by default. Do not split one semantic fact
across independent delegates unless one primary-owned workstream performs
reconciliation.

## Dispatch And Convergence

Dispatch independent packets in parallel only when their write sets and
semantic owners do not overlap. Keep urgent blocking work on the primary
critical path unless delegation materially shortens that path and introduces
no coordination uncertainty.

After a delegate returns, the primary assistant must:

1. Verify packet identity, actual model/capability evidence when available,
   touched surfaces, commands run, and unresolved findings.
2. Reject out-of-scope, unsupported, unvalidated, or conflicting output.
3. Review the patch or evidence against current repository state.
4. Run or repeat target validation required by combined risk.
5. Reconcile changed facts, approvals, companion surfaces, and workstreams.
6. Report delegated and locally completed work without overstating model,
   quality, latency, or cost evidence.

A delegate result is evidence for primary review, not operation completion.

## Cost And Performance Evidence

The target policy may optimize for latency, context volume, or measured cost,
but should keep those goals separate. Record:

- why delegation was expected to help
- packet preparation and review overhead when measured
- model or role actually used, or that it could not be verified
- validation/rework outcome
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
