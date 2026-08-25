# Large-Task Orchestration Flow

Use this flow in `{PROJECT_NAME}` for large, cross-boundary, multi-workstream,
or resumable work. Do not use it for a small task that fits one context profile
and one coherent change.

Replace placeholders with target facts before accepting installation.

## Target Sources

- Context router: `.ai/assistant/context-router.json`
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
locally verifiable workstreams with disjoint writes or read-only scope. Keep
the primary assistant on the immediate critical path and in control of final
convergence.

## Steps

1. Load the compact bootstrap and select the smallest base task profile and
   project-area overlays.
2. Apply the activation gate. Record why orchestration is needed.
3. Create one packet from
   `.ai/assistant/templates/large-task-operation-packet.md` at the
   target-approved path.
   Activate `.ai/assistant/flows/change-package.flow.md` separately only when
   coherent outcome, semantic approval, audit, or provenance needs pass its
   gate; large-task activation alone does not require a package.
4. Record operation scope, allowed actions, changed facts, canonical owners,
   relationship impact closure when enabled, approvals, and the initial
   context receipt. Include planned, resolved, and observed ordered semantic
   guidance identities and each bundle digest's algorithm and schema version.
5. Split work into coherent workstreams with explicit dependencies, allowed
   surfaces, outputs, validation, and completion evidence.
6. Load only the active workstream's context and its owner/dependency context.
7. Update status and create checkpoints after local validation, approval
   boundaries, handoffs, or before a context reset.
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
10. After local workstreams finish, reconcile cross-workstream contracts and
   run one global logical integrity review over the combined repair set,
   re-derived invariants, and related review-item clusters. When scoped
   approval applies, enforce the complete combined Git change set against the
   explicitly selected machine-readable approval records.
11. Confirm approval coverage, run target validation, and report final
    convergence, skipped checks, and residual risk.
12. When a change package is active, finalize its semantic scope, companion
    decisions, material corrections, and repository provenance after global
    convergence.
13. When subagents were used, reconcile packet scope, requested and actual
    model or unverified status, validation, fallback, rejected output, and
    primary review before accepting any workstream result.

The bundle comparison proves the identity of recorded semantic metadata at the
stated planned, resolved, or observed evidence level. It does not prove that a
model read, understood, remembered, or followed that guidance.

## Final Evidence

Report:

- packet path or target-approved non-persistent disposition
- activation reason, selected profile, scale overlay, and project areas
- changed facts and canonical owners
- relationship closure, selected/skipped edges, and missing coverage
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
