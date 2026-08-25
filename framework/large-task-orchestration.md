# Large-Task Orchestration

This file defines how an installed Alatyr adapter can keep large,
cross-boundary, or resumable work coherent without loading the whole project
into one assistant context.

It composes `ALATYR-CONTEXT-001`, `ALATYR-SOURCE-001`,
`ALATYR-APPROVAL-001`, `ALATYR-INTEGRITY-001`, `ALATYR-CHANGE-001`, and
`ALATYR-EVIDENCE-001`. It does not replace their canonical owner documents.

Concrete project areas, owners, commands, packet storage policy, and
validation belong to the target adapter.

When `team-collaboration` is also enabled, compose the
`large-or-resumable` and `team-active` overlays. The operation packet owns
workstream decomposition; the team registry owns current actor assignment,
claim, overlap, handoff, and review evidence. Cross-reference stable IDs
instead of copying either record.

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

Large-task activation does not automatically require a change package. Compose
the operation packet with `ALATYR-PACKAGE-001` only when coherent outcome,
semantic approval, audit, or publishable provenance needs also pass the package
activation gate. Cross-reference IDs instead of duplicating plan, approval,
discussion, or validation detail.

## Operation Packet

The target adapter should provide a Markdown operation-packet template. One
packet coordinates one operation and records:

- operation identity, goal, non-goals, allowed actions, and current phase
- selected task profiles, task-scale overlay, and project-area overlays
- changed facts, canonical owners, risk, approval state, and affected surfaces
- selected and skipped consistency relationships when the optional target map
  is enabled
- workstreams, dependencies, required context, outputs, and validation
- context receipts, ordered semantic-guidance bundle identities and digests,
  and reasons for budget expansion
- resumable checkpoints, unresolved decisions, and the next ready action
- final convergence across workstreams, owners, approvals, and validation
- active change-package ID when package evidence is also required

The packet is coordination evidence, not a canonical owner of project facts.
Link to source-of-truth entries instead of copying full business, architecture,
data, security, or assistant policy into the packet.

## Workstream Contract

Split work only where each workstream has a coherent boundary and a local
completion test. Every workstream should define:

- stable workstream ID and goal
- owner actor or team-task reference when team collaboration is enabled
- project area and changed-fact IDs
- dependencies and blocking decisions
- minimum required context and explicitly deferred context
- allowed files or surfaces
- expected outputs and validation
- status, evidence, unresolved risk, and handoff state
- worker execution-plan task, delegation packet, normalized result, selected
  role/model/native evidence, write isolation, and retry/fallback when
  `subagent-delegation` is enabled for that workstream

Do not split one semantic fact across independent workstreams unless one
workstream owns final reconciliation. Parallel-looking edits are not
independent when they share a source-of-truth decision, approval, generated
artifact, migration order, or external contract.

When `subagent-delegation` is enabled, dispatch only independently useful,
locally verifiable ready tasks through the target orchestration and role
contracts. Delegates do not own project decisions, approval, or final
convergence. Keep the primary assistant on the immediate critical path and
require disjoint writes or read-only packets.

## Resume Protocol

To resume an operation:

1. Load the compact adapter bootstrap.
2. Load the operation packet and only the active workstream's required
   context, changed-fact owners, and dependencies.
   When team collaboration is enabled, also load only the selected team task,
   current claim, relevant overlap, and latest checkpoint or handoff.
3. Compare the packet checkpoint with current repository evidence. Treat stale
   paths, changed owners, invalidated approvals, or modified dependencies as
   drift.
4. Resolve the current ordered semantic-guidance bundle and compare its digest
   with the last accepted resolved digest in the packet. Apply the semantic
   guidance revalidation protocol when it differs or is unavailable.
5. Record new context, identity changes, or changed assumptions as a receipt
   delta.
6. Continue from the next ready action; do not replay completed discovery
   unless evidence changed.

Packet summaries do not override current repository evidence. When they
disagree, repair the packet and re-run affected decisions.

## Semantic Guidance Revalidation

Record planned, resolved, and observed semantic-guidance identities in the
normalized context receipt. Bind every accepted checkpoint to the resolved
ordered bundle digest, including digest schema version and algorithm. The
resolved bundle is the deterministic comparison surface; observed delivery
may remain partial or unavailable. Keep the bundle within the selected route's
packet limits; a digest does not justify unbounded identity or owner loading.

Re-resolve and compare the current bundle before:

- protected implementation begins or resumes
- a material decision changes accepted behavior, architecture, data,
  security, public contracts, approval scope, or workstream dependencies
- final target validation begins
- final evidence is accepted

If the current resolved digest differs from the last accepted digest, or a
required digest cannot be resolved:

1. Stop the affected implementation, decision, validation, or evidence phase.
2. Record ordered identities that were added, removed, reordered, or changed
   in owner digest, authority, freshness, or applicability.
3. Load only new or changed canonical owners and dependencies. Do not reload
   unchanged guidance or the full project knowledge set.
4. Re-evaluate changed facts, risk, approval coverage, workstream dependencies,
   validation, and any decisions made from invalidated guidance.
5. Record the refreshed planned, resolved, and observed receipt layers and a
   checkpoint. Continue only when the new resolved bundle is accepted for the
   current phase and any newly required approval exists.

An unchanged resolved digest avoids repeated owner loading but does not waive
repository-drift, approval, or validation checks. A bundle digest identifies
the recorded semantic metadata; it is not proof that an assistant read,
understood, remembered, or complied with the guidance.

## Checkpoints

Create a checkpoint before context is likely to be lost, before a handoff,
after an approval boundary, or after a workstream reaches local validation.
A checkpoint should record completed work, decisions, evidence, unresolved
items, invalidated assumptions, the accepted resolved semantic-guidance bundle
digest, and the next ready action.

Do not claim a workstream complete when required approval or validation is
missing. Use `blocked` or `unresolved` and name the missing evidence.

## Final Convergence

Local workstream success is not final operation success. Before completion:

1. Re-resolve semantic guidance and complete the final-validation and
   final-evidence revalidation gates against the last accepted bundle digest.
2. Reconcile all changed facts with canonical owners.
3. Reconcile selected relationship closures and check cross-workstream
   contracts, ordering, and generated artifacts.
4. Confirm approvals still cover the applied scope.
5. Run target validation or record unresolved checks.
6. Perform one global logical integrity review over the combined repair set,
   re-derived invariants, and related review-item clusters.
7. When scoped approval applies, enforce the combined changed path set against
   explicitly selected machine-readable approval records and their diff base.
8. Report residual risk and close or preserve the packet according to target
   policy.
9. Reconcile team task, claim, checkpoint, handoff, review, and next-actor
   evidence when the team module is enabled.
10. When a change package is active, finalize companion decisions,
   implementation corrections, semantic-scope reconciliation, and repository
   provenance after the combined workstream result is known.
11. When subagents were used, reconcile every packet's actual scope, model or
    unverified status, validation, rejected output, fallback, and primary
    review before accepting the workstream result.

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
- treats a semantic bundle digest as proof of model comprehension or compliance
- crosses a protected, material-decision, final-validation, or final-evidence
  gate after its resolved semantic-guidance bundle changed without revalidation
- marks dependent workstreams independent to bypass sequencing or approval
- declares the operation complete from local workstream checks alone
- resumes by loading the full project instead of the active workstream context
