# Large-Task Orchestration Flow

Use this flow in `{PROJECT_NAME}` for large, cross-boundary, multi-workstream,
or resumable work. Do not use it for a small task that fits one context profile
and one coherent change.

Replace placeholders with target facts before accepting installation.

## Target Sources

- Context router: `.ai/assistant/context-router.json`
- Task decomposition policy: `.ai/assistant/task-decomposition.json`
- Task decomposition template:
  `.ai/assistant/templates/task-decomposition.md`
- Operation packet template:
  `.ai/assistant/templates/large-task-operation-packet.md`
- Project source-of-truth registry:
  `.ai/project/source-of-truth-registry.md`
- Approval policy and records: `{TARGET_APPROVAL_POLICY_AND_RECORDS}`
- Target validation: `{TARGET_VALIDATION_OR_MANUAL_REVIEW}`
- Packet storage and retention policy: `{TARGET_OPERATION_PACKET_POLICY}`

## Activation Gate

Activate the `large-or-resumable` task-scale overlay when the request is
explicitly large or resumable, contains multiple independently verifiable
workstreams, crosses multiple project areas or profiles, exceeds the profile
context budget, or needs separate approval or validation checkpoints.

If none applies, continue with the smallest normal operation flow and do not
create a packet.

When the optional `subagent-delegation` module is enabled, apply
`.ai/assistant/flows/subagent-delegation.flow.md` only to independently useful,
locally verifiable workstreams whose implementation levels permit worker
execution, with disjoint writes or read-only scope. Keep the primary assistant
on the immediate critical path and in control of final convergence.

## Steps

Invoke the phase or milestone selected by the outer coordinator. Planning
does not persist packets. Only the outer coordinator owns finalization.

### Analyze

1. Load the compact bootstrap and select the smallest base task profile and
   project-area overlays.
2. Apply the activation gate. Record why orchestration is needed.

### Plan

3. Propose one packet from
   `.ai/assistant/templates/large-task-operation-packet.md` at the
   target-approved path.
   Use only [package planning](change-package.flow.md#plan) separately when
   coherent outcome, semantic approval, audit, or provenance needs pass its
   gate; large-task activation alone does not require a package.

### Apply

#### Initialize

4. Verify current modification authorization and applicable protected approval,
   then create the proposed packet. For an active package, use only
   [Initialize](change-package.flow.md#initialize). Record operation scope,
   allowed actions, changed facts, canonical owners,
   relationship impact closure when enabled, approvals, and the initial
   context receipt. Include planned, resolved, and observed ordered semantic
   guidance identities and each bundle digest's algorithm and schema version.
   Reuse the outer coordinator's operation and package IDs; an already
   initialized package is referenced, not initialized again.

#### Workstreams

5. Split work into coherent workstreams from the task-decomposition plan with
   explicit implementation levels, dependencies, allowed surfaces, executor
   decisions, outputs, validation, and completion evidence.
6. Load only the active workstream's context and its owner/dependency context.
   Execute its authorized implementation once through
   [integrity Apply](logical-integrity-review.flow.md#apply). For eligible
   independent workers, plan bounded waves; cumulative budgets do not reset
   between waves. Recheck capability, remaining budgets, scope and completed
   packet IDs before each wave. Do not redispatch completed work.
7. Update status and create checkpoints after local validation, approval
   boundaries, handoffs, or before a context reset.
   Use [Material Updates](change-package.flow.md#material-updates) only for an
   active package and within current authorization and approval scope.
8. On resume, compare checkpoint claims with current repository evidence and
   invalidate stale assumptions before continuing. Re-resolve the current
   semantic guidance bundle and compare it with the checkpoint's last accepted
   resolved digest.
9. Repeat that resolved-bundle comparison before protected implementation,
   every material decision, final validation, and final evidence. When it
   differs or is unavailable, stop the affected phase, record added, removed,
   reordered, or changed identities, load only changed canonical owners, and
   refresh risk, approval, dependencies, validation, and invalidated decisions
   before accepting a new checkpoint.

#### Converge

10. After local workstreams finish, reconcile cross-workstream contracts and
   run one global logical integrity review over the combined repair set,
   re-derived invariants, and related review-item clusters. When scoped
   approval applies, enforce the complete combined Git change set against the
   explicitly selected machine-readable approval records.
11. Confirm approval coverage, run target validation, and report final
    convergence, skipped checks, and residual risk.
    Complete the combined Project Contour Sync Decision and required companion
    decisions before entering package finalization. This is pre-finalization
    convergence, not final-result binding validation.
12. When a change package is active, finalize its semantic scope, companion
    decisions, material corrections, and repository provenance after global
    convergence through [Finalize](change-package.flow.md#finalize) only if
    this flow is the outer coordinator. Otherwise return evidence to that owner.

### Verify

Do not authorize repairs or finalization here; return to authorized Apply and
refresh affected evidence when a required check fails.

13. Verify the existing Project Contour Sync Decision for the combined code/test
    result. Worker-local documentation conclusions are evidence only; the
    primary reconciles owners, affected surfaces, support state, and residual
    risk.
14. When subagents were used, reconcile packet scope, requested and actual
    model or unverified status, validation, fallback, rejected output, and
    primary review before accepting any workstream result.
    For an active package, use only [Verify](change-package.flow.md#verify).
    Run post-finalization binding validation against the final result. Reuse
    semantic conclusions only where canonical policy and unchanged input,
    scope, approval and guidance bindings permit it; invalidated evidence must
    be refreshed. Do not rerun implementation from a verification phase.

The bundle comparison proves the identity of recorded semantic metadata at the
stated planned, resolved, or observed evidence level. It does not prove that a
model read, understood, remembered, or followed that guidance.

## Final Evidence

Report:

- packet path or target-approved non-persistent disposition
- activation reason, selected profile, scale overlay, and project areas
- task decomposition plan, implementation levels, executor decisions, and
  blocked tasks
- changed facts and canonical owners
- relationship closure, selected/skipped edges, and missing coverage
- Project Contour Sync Decision with checked owners and evidence
- workstream status and dependency result
- planned, resolved, and observed semantic guidance identities and ordered
  bundle digests
- revalidation results before protected implementation, material decisions,
  final validation, and final evidence
- context receipts and bounded budget expansions
- checkpoints and resumed assumptions
- approval coverage and target validation
- global logical integrity result
- active change-package result and evidence quality when applicable
- delegated packet, model/capability, validation, fallback, and primary-review
  evidence when applicable
- unresolved work and residual risk

## Rejection Criteria

Reject or revise work that:

- creates a packet without an activation reason
- copies full source-of-truth content into the packet
- starts a blocked workstream before its dependency or approval is satisfied
- resumes from packet prose without checking current repository evidence
- treats a bundle digest as proof of model comprehension or compliance
- crosses a required semantic revalidation gate after the resolved bundle
  changed without refreshing affected owners, decisions, and controls
- claims global completion from workstream-local validation only
