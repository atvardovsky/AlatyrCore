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

## Steps

1. Load the compact bootstrap and select the smallest base task profile and
   project-area overlays.
2. Apply the activation gate. Record why orchestration is needed.
3. Create one packet from
   `.ai/assistant/templates/large-task-operation-packet.md` at the
   target-approved path.
4. Record operation scope, allowed actions, changed facts, canonical owners,
   approvals, and the initial context receipt.
5. Split work into coherent workstreams with explicit dependencies, allowed
   surfaces, outputs, validation, and completion evidence.
6. Load only the active workstream's context and its owner/dependency context.
7. Update status and create checkpoints after local validation, approval
   boundaries, handoffs, or before a context reset.
8. On resume, compare checkpoint claims with current repository evidence and
   invalidate stale assumptions before continuing.
9. After local workstreams finish, reconcile cross-workstream contracts and
   run one global logical integrity review over the combined repair set.
10. Confirm approval coverage, run target validation, and report final
    convergence, skipped checks, and residual risk.

## Final Evidence

Report:

- packet path or target-approved non-persistent disposition
- activation reason, selected profile, scale overlay, and project areas
- changed facts and canonical owners
- workstream status and dependency result
- context receipts and budget expansions
- checkpoints and resumed assumptions
- approval coverage and target validation
- global logical integrity result
- unresolved work and residual risk

## Rejection Criteria

Reject or revise work that:

- creates a packet without an activation reason
- copies full source-of-truth content into the packet
- starts a blocked workstream before its dependency or approval is satisfied
- resumes from packet prose without checking current repository evidence
- claims global completion from workstream-local validation only
