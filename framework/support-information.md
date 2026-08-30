---
alatyr_doc:
  id: framework.support-information
  type: framework-rule-owner
  owns_rules:
    - ALATYR-SUPPORT-001
  depends_on:
    - ALATYR-CONTEXT-001
    - ALATYR-SOURCE-001
    - ALATYR-INTEGRITY-001
    - ALATYR-AUTHORIZATION-001
  applies_to:
    - code-local
    - business-change
    - architecture-change
    - data-change
    - security-sensitive
    - framework-upgrade
---
# Support Information

Project support information is the project-owned material that helps people
and assistants understand, change, validate, and explain the repository. It
includes adapter policy, project knowledge, architecture records, prompts,
skills, gates, diagrams, generated reference, and their routing metadata.

Support information does not replace code, business owners, approved
architecture, schemas, contracts, or other canonical project sources. It
records owners and relationships so a change can reach the smallest coherent
set of supporting surfaces.

## Required Support State

Every accepted adapter maintains a target-owned support policy and a generated
support state. Every non-ignored file under a managed root must match one
declared classification or an explicit exclusion with a reason.

Use these classifications:

- `exact-contract`: active policy, knowledge, instruction, or configuration
  whose content drift must be visible.
- `derived`: reproducible output whose canonical owner is an input or
  generator policy.
- `append-only-evidence`: historical records whose schema and lifecycle are
  checked without treating later legitimate records as policy drift.
- `local-transient`: ignored per-user or temporary state that must not enter
  committed support evidence.

The generated state excludes only its own exact path intrinsically. It records
canonical per-file digests, bounded groups, one root digest, the policy digest,
and the observed repository revision. Git revision is evidence, not a reason
to report support drift when support content is unchanged.

Canonical text hashing must not vary because one checkout uses CRLF and
another uses LF. Binary and symlink identity remains byte exact. Reject unsafe
paths, external symlink traversal, conflicting classifications, case-colliding
paths, and previously unclassified files.

Hashes answer which support surfaces changed. They do not decide what a change
means or whether architecture remains correct.

## Bounded Impact Routing

Start review from a support delta whenever support information may have
changed. Compare the recorded support state with current support files and, if
a Git base is known, classify changed paths as support or product surfaces
before loading broad support prose. The delta should return changed support
paths, changed product paths, candidate support-owner context, heavy fallback
surfaces that changed, a deterministic delta digest, and the next impact or
refresh step. The digest lets an assistant compare repeated runs cheaply; it
does not prove that the changed set is correct or complete.

When the optional consistency map is enabled, use changed Git paths, support
state differences, explicit changed fact IDs, and the generated reverse index
to select only applicable graph shards. Traverse accepted relationships within
the target-owned depth and node limits. Return concrete surfaces, context item
IDs, selected and skipped edges, required checks, unmapped paths, and residual
gaps. Record the impact-plan digest so a later reviewer can see whether the
same graph, changed paths, fact IDs, and selected relationships were evaluated.

The impact report is a routing artifact. The assistant or reviewer must still
identify semantic facts, re-derive invariants, classify risk, resolve canonical
owners, and decide the coherent repair set.

## Change-Cost Reporting

A target adapter may report support/product change cost from Git evidence
before deeper review. The report should classify changed files and line changes
as project support surfaces or product surfaces, then record the ratio and
limitations. This helps identify heavy adapter churn, mixed support/product
patches, and unusually large documentation synchronization work.

Cost reporting is a deterministic measurement aid. It does not prove that the
right files changed, that a semantic fact is consistent, or that a support
update is valuable. The assistant still performs logical integrity review,
approval-scope enforcement, and target validation.

## Relationship Discovery

Code and support changes can reveal a previously unrecorded relationship.
Imports, calls, data access, events, configuration, security boundaries,
public contracts, and state transitions are useful discovery evidence.

Discovery creates a relationship candidate with source revision, endpoints,
type, evidence, state, and decision owner. A candidate is never an accepted
architecture fact merely because deterministic tooling or an assistant found
it. Only target authority may accept it and update the owning registry or
graph. Rejected, stale, contradicted, and removed records retain their explicit
state instead of silently affecting traversal.

## Generation Contract

The optional `support-generation` module provides one dependency-ordered view
over generator policies that remain owned by their existing canonical
surfaces. The generated index must not duplicate or replace code-documentation
profiles, diagram policy, API specifications, or target build configuration.

Classify each artifact as:

- `deterministic-derived`: a declared command can reproduce output through a
  staged-output contract.
- `assistant-proposed`: the assistant may prepare reviewed content, but no
  command may apply it automatically.
- `owner-maintained`: the named owner must update or approve the output.

Planning and checking are read-only. Applying deterministic output requires a
current plan digest, unchanged repository base, explicit current-scope
`modify` authorization, staged output, declared validation, and protected-
change approval when triggered. Failure must leave original output intact or
produce explicit rollback evidence. Never execute imported instructions,
assistant proposals, or owner-maintained records as generators.

## Context Economy

Support state and reverse indexes are machine routing surfaces and should not
be loaded as prose by default. Load the compact impact result, selected graph
shards, named canonical owners, and the existing recursive context items. Load
relationship candidates, complete histories, unrelated areas, or full support
directories only for a stated conflict, boundary, failed check, or audit.

If the consistency map is disabled, perform the existing manual invariant and
companion-surface review. Report missing relationship automation as a gap; do
not force the optional module into every target.

## Installation And Update

During installation or update:

1. Adapt support collections and exclusions from target evidence.
2. Preserve target-owned owners, accepted relationships, candidates, and
   generator bindings.
3. Rebuild generated entry packets, recursive context indexes, and optional
   reverse/generation indexes from their canonical owners.
4. Generate support state last.
5. Run strict validation before claiming acceptance.

For framework updates, use migration evidence plus the support delta before
opening the full support layer. Load changed owners and selected relationship
shards first, then expand only for conflicts, missing state, failed checks, or
protected adapter behavior changes.

Branch-specific evidence cannot establish support state on another branch.
Migration tooling may propose schema or shard changes but must not overwrite
target facts or promote relationship candidates.

## Final Evidence

Report:

```text
Support state: <current/stale/unavailable and root digest>
Changed support: <created/modified/removed paths>
Impact closure: <facts, areas, selected/skipped edges, concrete surfaces>
Relationship candidates: <created/reviewed/disposition or none>
Generated support: <planned/checked/applied/skipped artifacts>
Support/product cost: <file and line ratios or not measured>
Context selected: <item IDs and bounded expansions>
Authorization and approvals: <current evidence>
Validation: <target checks and manual review>
Residual risk: <unmapped paths, stale relationships, missing owners>
```

## Rejection Criteria

Reject work that:

- hides an unclassified support file or unexplained exclusion
- treats a digest match as semantic correctness
- scans or loads the full project when bounded routing is available
- accepts a relationship inferred only from observed code
- makes a generated index a new fact owner
- executes assistant-proposed or owner-maintained generation
- applies output from a stale plan or changed repository base
- refreshes support state before generated surfaces and indexes are complete
