---
alatyr_doc:
  id: framework.change-packages
  type: framework-rule-owner
  owns_rules:
    - ALATYR-PACKAGE-001
  depends_on:
    - ALATYR-CHANGE-001
    - ALATYR-APPROVAL-001
    - ALATYR-INTEGRITY-001
    - ALATYR-EVIDENCE-001
  applies_to:
    - business-change
    - architecture-change
    - data-change
    - security-sensitive
---
# Change Packages

A change package binds one coherent, material project outcome to its changed
facts, plan, approval, implementation, companion updates, validation, and
repository provenance.

Changed facts remain the universal unit of Alatyr reasoning. A package is an
optional evidence and coordination layer for changes whose architectural or
cross-surface scope makes a file list or ordinary final response too weak.

A durable engineering-evidence record is a smaller project-memory artifact for
the invariant, root cause, solution rationale, and regression reasoning of one
material task. It may exist without a package. When both apply, the package
links the evidence ID instead of duplicating those conclusions.

## Activation

Use a change package when at least one condition is true:

- one approval is intended to authorize a coherent result across several
  implementation, test, contract, configuration, documentation, architecture,
  diagram, or assistant-governance surfaces
- the change introduces or materially revises an architecture segment,
  business capability, cross-cutting policy, migration, or public contract
- multiple changed facts or project areas require one combined integrity and
  provenance result
- a pilot, audit, review, or publication needs a reproducible before-to-after
  evidence chain

Do not create a package for a small task that fits one profile, changes one
local fact, and can be evidenced by the ordinary operation result. Large-task
orchestration and change packages are independent overlays: use a workstream
packet for execution complexity and a package for coherent outcome evidence;
compose them only when both activation gates pass.

## Package Types

Use a target-owned type such as:

- `architecture-segment`
- `business-capability`
- `cross-cutting-change`
- `migration`
- `public-contract`
- `other`

An architecture segment is one package type, not the only valid unit. The
package type does not replace changed-fact IDs, canonical owners, or target
architecture terminology.

## Package Contract

A package should record:

- stable package, operation, and plan identities
- goal, non-goals, activation reason, package type, owner, and status
- selected task profile, project areas, and active workstream reference when
  large-task orchestration is also active
- changed fact IDs, statements, canonical owners, and re-derived invariants
- approved semantic and path scope
- plan file, version, and hash when available
- approval record references and invalidation state
- implementation discoveries and corrections
- companion-surface decisions
- compact architecture discussion evidence when architecture reasoning applies
- validation results, skipped checks, and residual risks
- before and after revisions and evidence-quality classification
- linked durable engineering-evidence IDs when that capture gate applies
- incident-family identity, trigger, corrective iteration, digest-bound
  predecessors, latest failed gate, and selected problem-model binding while
  the package is active

The package is historical evidence. It links to canonical project owners and
must not become a second source of truth for business, architecture, data,
security, runtime, or assistant policy.

## Incident Continuity

When a defect, failed gate, or escaped behavior leads to another correction,
continue one incident family instead of treating the next edit as an unrelated
task. Use `new` for the first bounded repair, `continuation` for its first
corrective iteration, and `systemic-repair` from the second corrective
iteration onward. A recurring correction uses the `recurring-correction`
trigger and cannot return to an isolated local-repair classification.

Every active package records a digest-bound runtime problem model. Continued
work also records digest-bound predecessor package records from the compact
index. The predecessor must belong to the same family and have a lower
corrective iteration. A failed required gate remains open in the problem model
until evidence resolves it; a prior local green result is not reusable proof
after a later failure invalidates its assumption.

An escaped defect, failed required gate, recurring correction, or systemic
repair requires a whole-lifecycle model. It names states, transitions, owners,
producer, orchestrator, persistence, and consumer boundaries, conservation
rules, and explicit success, rejection, deferral, expiry, recovery, and
failure outcomes. This is a bounded contract model, not a demand to load every
implementation file.

Ordinary non-incident packages use `mode: none`, `family_id: none`, iteration
zero, no predecessors, and a non-required lifecycle model. Completed legacy
packages remain historical and are not rewritten solely to add this contract.

Before declaring a corrective package isolated, perform a bounded recurrence
preflight. An explicit predecessor, failed required gate, repeated changed-fact
identity, or fresh runtime contradiction is a recurrence candidate. Record an
incident-lineage disposition for each candidate. These signals prevent silent
loss of continuity; they do not by themselves prove shared business causality.
When acceptance depends on runtime behavior, the optional runtime-observation
module binds completion claims to counted events and a complete post-result
window.

## Semantic Approval Scope

Path scope is necessary but not sufficient for material changes. Package and
approval records should also name:

- allowed changed-fact IDs
- allowed architecture areas
- allowed behavior categories
- excluded semantic effects
- permitted external effects
- allowed and excluded files or surfaces

Reapproval is required when implementation introduces a protected changed
fact, architecture area, behavior category, external effect, or path outside
the approved scope. A correction that preserves the approved outcome and stays
inside semantic and path scope may continue with a recorded explanation.

Deterministic checks can compare declared values and paths. They cannot prove
that an implementation has no undeclared semantic effect; logical integrity
review remains required.

## Discoveries And Corrections

Record material implementation-time discoveries and corrections with:

- stable ID and `discovery` or `correction` kind
- statement and evidence
- affected changed-fact IDs
- scope impact: `none`, `within-approved-scope`, or `reapproval-required`
- approval action and validation consequence

Do not hide corrections that change the plan, invalidate an invariant, or
alter approval scope. Do not force trivial refactoring notes into the package
when they do not affect facts, scope, evidence, or validation.

## Companion-Surface Decisions

For every applicable companion surface, record one decision:

- `updated`
- `not-required`
- `missing`

The record names the surface type, owner or path, reason, and evidence. Review
at least source-of-truth or blueprint docs, architecture decisions, source-of-
truth registry, contracts, tests, configuration, public docs, diagrams,
changelog or release notes, prompts, skills, gates, bridges, and checkers when
they are relevant to the changed facts.

Every newly created package containing code or test changes includes a
`project-contour-sync` companion decision. It records checked project owners,
affected or intentionally unchanged surfaces, support-state result, and
residual risk. Existing historical records are not rewritten solely to add
this newer evidence convention.

`not-required` needs a fact-specific reason. `missing` must become a residual
risk or blocker under target policy. The framework does not require an ADR or
changelog for every task; it requires an explicit decision when the surface is
applicable.

## Architecture Discussion Evidence

When architecture reasoning affects the package, retain a compact summary:

- problem and decision boundary
- alternatives considered, including no change or reuse when applicable
- selected direction and decision authority
- accepted, proposed, observed, contradicted, or unknown status
- canonical evidence references
- assumptions and unresolved disagreement

Do not store raw chat transcripts by default. The target controls retention,
privacy, redaction, and whether the summary is tracked.

## Repository Provenance

Classify evidence:

- `git-range`: resolvable before/after revisions and reproducible diff
- `pull-request`: stable review reference with base/head revisions
- `selected-file-snapshot`: explicit paths and digest without a clean range
- `unverified`: insufficient revision or snapshot evidence

Only ranges and pull requests support strong complete-change claims. Snapshots
provide bounded internal evidence; omissions and unrelated edits limit claims.
Unverified evidence supports no historical completeness claim.

Snapshot SHA-256 hashes sorted normalized target-relative paths: each UTF-8
path, NUL, raw file bytes, NUL. Missing files, directories, absolute paths and
parent traversal invalidate it.

Optional `provenance.selected_file_snapshot.source_commit` pins historical
bytes to an exact available immutable commit, with exact `before_revision`
ancestry. Verification requires SHA-256 and 1..256 unique safe literal paths,
bounded to 4 MiB/file and 64 MiB total. Only unselected `historical-record`
packages, distinct from the selected task's identity, operation and model,
qualify; unknown or malformed task ownership fails closed. Claims remain
`limited` or `unsupported`, never current freshness, task completion or strong
case acceptance. Omitting this field preserves existing snapshot behavior.

A complete clean commit, range or pull request is valid. Prefer dedicated
branches/worktrees for public/audit cases; record cleanliness at start and
validation and how unrelated work was isolated. Dirty worktrees do not
automatically invalidate ranges, but inseparable unrelated changes weaken them.

## Machine Validation

A target validator may verify:

- record shape, enum values, and target-relative paths
- referenced plan and approval records and their hashes when available
- resolvable Git revisions and declared range paths
- actual changed paths against approved path scope
- declared actual facts, areas, behavior categories, and external effects
  against semantic approval lists
- companion decisions, correction scope impact, and required reasons
- evidence-quality prerequisites and public-claim limits
- active package auto-discovery, incident-family projection, predecessor
  identity and digest, problem-model synchronization, failed-gate state, and
  lifecycle-model activation
- changed package plans are bound to an active compact-index record
- every project path in a final semantic package maps through the enabled
  consistency map, while adapter/support paths remain governed by their own
  support-state contract

It cannot infer missing domain invariants, prove semantic correctness, decide
whether architecture is accepted, or establish that all affected facts were
declared. Those remain project reasoning, ownership, review, and test duties.

## Cost Control

Keep the compact index derived from its named record: package ID/status;
changed-fact IDs/owners from `changed_facts`; project areas from `routing`;
evidence quality from `provenance`; approvals from `approved_scope`; active
workstream from `operation`; incident family, corrective iteration and latest
failed-gate state. Load plans, discussions, companion decisions, corrections
and validation logs only when needed.

Residual risk derives only from `validation.residual_risks`: empty means `none`;
otherwise retain its bounded count, digest and pointer, never a manual sentence.
Regeneration never rewrites source records. Full validation checks every
projection; changed scope checks changed indexes/records without reopening
unrelated historical evidence.

An unchanged index shard proves only that the shard bytes are unchanged. When
a referenced package record changes, changed-scope validation must still open
that record's compact entry and compare the projection without deep-loading
unrelated historical records.

Use the canonical projection renderer when available instead of editing
projection fields by hand. For sharded indexes it must update the shard
contents and the root descriptor SHA-256 and record count as one derived
state.

When completed package records make a directory or recursive context index
exceed its target budget, move completed records into bounded chronological
subdirectories such as `change-packages/archive/2026-09/`. Keep active records
and the compact machine index directly addressable. Regenerate recursive
context indexes after the move; moving evidence does not change package
identity, status, provenance, or canonical-owner references.

When the compact root index itself grows beyond the target budget, retain
active and recent entries in `records` and move closed entries into bounded
index shards. The root `shards` directory contains target-relative shard path,
SHA-256, and record count; each shard uses
`target-change-package-index-shard`. Suggestion and full validation process one
shard at a time. Changed-scope validation opens only a changed shard, a changed
record, or every shard after its root descriptor changes. Do not use sharding
to omit package identity, status, owners, projection checks, or evidence.

Reuse the package across checkpoints and handoffs instead of rediscovering the
same scope. Do not copy large source documents, raw chats, diffs, or test logs
into the package.

Keep the top-level package directory typed and compact. Machine package JSON
uses `record_kind: alatyr-change-package`; large replay, trace, or raw evidence
belongs in a dedicated evidence location and is linked by target-relative
reference. Validators should report untyped or oversized top-level artifacts,
but must not move historical evidence without authorization.

## Rejection Criteria

Reject or revise a package that:

- was created without an activation reason
- replaces changed facts with a list of files
- claims approval from path scope while semantic scope changed
- marks a companion surface `not-required` without a reason
- hides a correction that requires reapproval
- starts a new unrelated package for a correction in an existing incident
  family
- keeps a second corrective iteration in local continuation mode
- closes work while its latest failed gate or required lifecycle obligation is
  unresolved
- claims a complete public case from a selected-file snapshot
- claims deterministic validation proved logical or architectural correctness
- copies canonical project facts or raw private discussion into evidence
