# Multi-Level Consistency Model

This file defines a portable relationship model for finding the smallest
complete repair set after a project fact changes.

It composes `ALATYR-CONTEXT-001`, `ALATYR-SOURCE-001`,
`ALATYR-INTEGRITY-001`, and `ALATYR-EVIDENCE-001`. Canonical ownership remains
in the source-of-truth registry. The consistency map is an adapter-owned,
machine-readable routing companion, not another source of truth.

Concrete fact IDs, project areas, paths, commands, relationships, and
validation belong to the target adapter.

## Purpose

Large repositories often describe one fact through contracts,
implementations, tests, docs, diagrams, generated artifacts, and assistant
governance. Scanning every surface for every task is expensive and still does
not prove the right relationships were checked.

A consistency map makes those relationships explicit. An assistant starts
from changed fact IDs and follows only applicable edges until it has a bounded
impact closure.

## Consistency Levels

Use levels to describe scope, not to impose a universal architecture:

- `fact`: one accepted business, data, architecture, security, operation, or
  assistant-governance statement
- `contract`: an API, schema, event, workflow, state transition, permission,
  or other agreement between surfaces
- `area`: a target-owned module, package, service, domain, documentation area,
  or assistant-infrastructure area
- `system`: a relationship crossing target project areas or external
  boundaries
- `adapter`: a prompt, skill, gate, flow, bridge, checker, operation, or other
  repository-assistant rule

Generated artifacts and evidence are related surfaces, not canonical levels
that can silently override their owners.

## Relationship Types

A target may narrow or extend these portable relationship meanings:

- `implements`: code or runtime behavior realizes a fact or contract
- `verifies`: a test, checker, review, or validation examines it
- `documents`: project or public documentation explains it
- `visualizes`: a diagram source or visual artifact represents it
- `generates`: one source produces a derived artifact
- `constrains`: a rule limits another fact, contract, or surface
- `depends-on`: a fact or contract cannot remain valid independently
- `routes`: assistant context, operation, prompt, skill, gate, or bridge
  behavior selects or carries it

The canonical owner belongs on the fact node. Do not encode ownership as an
ambiguous relationship edge.

## Relationship Entry

Each relationship should record:

- stable edge ID
- relationship type
- target node or surface
- target level and project area
- direction from the fact node
- conditions that make the edge relevant
- validation or manual review
- approval trigger when following the edge can enter protected scope

Unknown relationships must remain missing facts. Do not infer a complete
dependency graph from filenames or imports alone.

## Impact Closure

Build a bounded impact closure:

1. Name the changed or disputed fact IDs.
2. Resolve each canonical owner in the human source-of-truth registry.
3. Read the corresponding machine-map nodes and direct relationships.
4. Follow edges whose trigger matches the changed fact.
5. Traverse to another fact node only when a contract, `constrains`, or
   `depends-on` relationship can propagate the semantic change.
6. Load the target surface and its validation only after selecting its edge.
7. Record visited nodes, selected edges, skipped edges with reasons, missing
   relationships, and project areas crossed.
8. Use the closure as the candidate repair set, then apply logical integrity
   review before finalizing it.

Expand beyond direct edges when evidence conflicts, an owner is missing, a
cross-area contract changes, validation disproves the assumed boundary, or an
approval trigger is reached. Do not expand merely because another area exists.

## Manual Invariant Closure

The consistency map is optional; invariant review is not. When the map is
disabled, deferred, or missing an applicable edge, derive a compact manual
closure from the canonical owner and target evidence. Check identity and data
scope, ownership boundaries, persistence and lifecycle behavior, callers and
external contracts, tests, and observable failure distinctions that can
propagate the fact.

Record the invariant statements, surfaces inspected, relationships inferred
from evidence, and relationships still unknown. This fallback is more
expensive and less deterministic than an adapted map, so unresolved coverage
must remain residual risk.

## Multi-Level Review

For each applicable level, answer:

- owner: does the canonical source state the accepted fact?
- contract: do dependent interfaces, schemas, workflows, and policies agree?
- area: do implementation, tests, docs, and generated artifacts agree locally?
- system: do crossed areas and external contracts agree on shared facts?
- adapter: do prompts, skills, flows, gates, bridges, and checkers route the
  same behavior?

Not every fact reaches every level. Evidence should name non-applicable levels
instead of forcing empty updates.

## Drift And Staleness

The map is stale when an owner, path, project area, edge target, validation, or
approval trigger no longer matches repository evidence. Report stale entries
as adapter drift. Repair the map from target evidence; do not change product
facts merely to make the map pass.

## Evidence

Report:

- changed fact IDs and canonical owners
- selected and skipped relationship edges with reasons
- consistency levels and project areas reached
- missing or stale relationships
- candidate and applied repair sets
- validation, approvals, and global logical integrity result
- residual risk from omitted or unresolved relationships

## Rejection Criteria

Reject or revise work that:

- treats the machine map as canonical project truth
- scans all project surfaces without first attempting bounded traversal
- assumes a relationship from filename proximity alone
- stops at direct edges when a dependent contract propagates the fact
- hides missing or stale edges behind a successful local test
- claims every consistency level applies to every fact
