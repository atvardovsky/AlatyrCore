# Large-Task Orchestration

This file defines how an installed Alatyr adapter can keep large,
cross-boundary, or resumable work coherent without loading the whole project
into one assistant context.

It composes `ALATYR-CONTEXT-001`, `ALATYR-SOURCE-001`,
`ALATYR-APPROVAL-001`, `ALATYR-INTEGRITY-001`, `ALATYR-CHANGE-001`, and
`ALATYR-EVIDENCE-001`. It does not replace their canonical owner documents.

Concrete project areas, owners, commands, packet storage policy, and
validation belong to the target adapter.

## Activation

Use large-task orchestration when at least one condition is true:

- the user explicitly asks for a large, phased, resumable, or handed-off task
- the work has multiple independently verifiable workstreams
- the work crosses multiple project areas or task profiles
- required context exceeds the selected profile budget
- approvals or validation must happen at different checkpoints
- the work must survive an assistant context reset or a later session

Do not create an operation packet for a small task that fits one profile and
can be completed as one coherent change. A packet adds coordination cost and
must earn that cost by reducing repeated discovery or missed companion work.

## Operation Packet

The target adapter should provide a Markdown operation-packet template. One
packet coordinates one operation and records:

- operation identity, goal, non-goals, allowed actions, and current phase
- selected task profiles, task-scale overlay, and project-area overlays
- changed facts, canonical owners, risk, approval state, and affected surfaces
- selected and skipped consistency relationships when the optional target map
  is enabled
- workstreams, dependencies, required context, outputs, and validation
- context receipts and reasons for budget expansion
- resumable checkpoints, unresolved decisions, and the next ready action
- final convergence across workstreams, owners, approvals, and validation

The packet is coordination evidence, not a canonical owner of project facts.
Link to source-of-truth entries instead of copying full business, architecture,
data, security, or assistant policy into the packet.

## Workstream Contract

Split work only where each workstream has a coherent boundary and a local
completion test. Every workstream should define:

- stable workstream ID and goal
- project area and changed-fact IDs
- dependencies and blocking decisions
- minimum required context and explicitly deferred context
- allowed files or surfaces
- expected outputs and validation
- status, evidence, unresolved risk, and handoff state

Do not split one semantic fact across independent workstreams unless one
workstream owns final reconciliation. Parallel-looking edits are not
independent when they share a source-of-truth decision, approval, generated
artifact, migration order, or external contract.

## Resume Protocol

To resume an operation:

1. Load the compact adapter bootstrap.
2. Load the operation packet and only the active workstream's required
   context, changed-fact owners, and dependencies.
3. Compare the packet checkpoint with current repository evidence. Treat stale
   paths, changed owners, invalidated approvals, or modified dependencies as
   drift.
4. Record new context or changed assumptions as a receipt delta.
5. Continue from the next ready action; do not replay completed discovery
   unless evidence changed.

Packet summaries do not override current repository evidence. When they
disagree, repair the packet and re-run affected decisions.

## Checkpoints

Create a checkpoint before context is likely to be lost, before a handoff,
after an approval boundary, or after a workstream reaches local validation.
A checkpoint should record completed work, decisions, evidence, unresolved
items, invalidated assumptions, and the next ready action.

Do not claim a workstream complete when required approval or validation is
missing. Use `blocked` or `unresolved` and name the missing evidence.

## Final Convergence

Local workstream success is not final operation success. Before completion:

1. Reconcile all changed facts with canonical owners.
2. Reconcile selected relationship closures and check cross-workstream
   contracts, ordering, and generated artifacts.
3. Confirm approvals still cover the applied scope.
4. Run target validation or record unresolved checks.
5. Perform one global logical integrity review over the combined repair set.
6. Report residual risk and close or preserve the packet according to target
   policy.

## Storage And Privacy

The target adapter decides whether packets are tracked, ignored, redacted, or
stored outside the repository. Never put secrets, private prompts, credentials,
or unnecessary imported source content in a packet. Record references, hashes,
or redacted evidence where full content is unsafe or too costly.

## Rejection Criteria

Reject or revise orchestration that:

- creates packets for every small task
- copies canonical project facts into packet prose without owner references
- treats a checkpoint as proof that current repository evidence is unchanged
- marks dependent workstreams independent to bypass sequencing or approval
- declares the operation complete from local workstream checks alone
- resumes by loading the full project instead of the active workstream context
