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

The package is historical evidence. It links to canonical project owners and
must not become a second source of truth for business, architecture, data,
security, runtime, or assistant policy.

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

Classify package evidence as one of:

- `git-range`: resolvable before and after revisions with a reproducible diff
- `pull-request`: a named review surface with base/head revisions and a stable
  reference
- `selected-file-snapshot`: an explicit path set and content digest used when
  a clean repository range is unavailable
- `unverified`: insufficient revision or snapshot evidence

Only `git-range` and `pull-request` support a strong public claim about the
complete change set. `selected-file-snapshot` can support bounded internal
evidence, but unrelated working-tree changes and omitted paths limit the
  claim. `unverified` supports no historical completeness claim.

For a deterministic selected-file snapshot, sort normalized target-relative
paths, then hash each UTF-8 path, a NUL byte, the file's raw bytes, and a final
NUL byte with SHA-256. Missing, directory, absolute, or parent-traversal paths
invalidate the snapshot.

A clean single commit is useful but not mandatory. A clean commit range or
pull request is equally valid when the complete package is reviewable.
For public or audit cases, prefer a dedicated branch or worktree, record
whether the tree was clean at start and validation, and explain how unrelated
changes were isolated. Dirty-tree evidence does not automatically invalidate a
Git range, but it weakens confidence when package and unrelated changes cannot
be separated.

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

It cannot infer missing domain invariants, prove semantic correctness, decide
whether architecture is accepted, or establish that all affected facts were
declared. Those remain project reasoning, ownership, review, and test duties.

## Cost Control

Keep the default package index compact: identity, status, changed-fact IDs,
owners, project areas, provenance, approval references, active workstream, and
residual risk. Load plan details, discussion evidence, companion decisions,
corrections, or validation logs only when the active task needs them.

Reuse the package across checkpoints and handoffs instead of rediscovering the
same scope. Do not copy large source documents, raw chats, diffs, or test logs
into the package.

## Rejection Criteria

Reject or revise a package that:

- was created without an activation reason
- replaces changed facts with a list of files
- claims approval from path scope while semantic scope changed
- marks a companion surface `not-required` without a reason
- hides a correction that requires reapproval
- claims a complete public case from a selected-file snapshot
- claims deterministic validation proved logical or architectural correctness
- copies canonical project facts or raw private discussion into evidence
