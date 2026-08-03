# Architecture Assistance Flow

Use this flow when a programmer asks to inventory, explain, discuss, compare,
review, or document `{PROJECT_NAME}` architecture, patterns, boundaries,
constraints, technologies, or other architectural items.

Replace placeholders from target evidence before enabling the
`architecture-knowledge` module.

## Required Context

- Portable rule: `.ai/framework/architecture-knowledge.md`
- Compact catalog: `.ai/project/architecture/catalog.json`
- Result contract:
  `.ai/assistant/templates/architecture-discussion-result.md`
- Selected target area, pattern, decision, and repository evidence named by
  the catalog

Load `.ai/project/architecture/README.md` when human rationale, status meaning,
catalog repair, or broad overview is needed. Load pattern or area templates
only when drafting a new target-owned record. Load diagram guidance only when a
visual relationship materially helps. Load source-of-truth, risk, integrity,
approval, blueprint, security, data, testing, or large-task context only when
the selected question crosses that boundary or an architecture decision is
being accepted.

## Allowed Actions

- `read-only`: inspect and discuss; do not create or change project files.
- `docs-only`: create or synchronize evidence-backed `observed`, `proposed`,
  `contradicted`, or `unknown` architecture documentation. Do not mark an
  architecture item accepted, preferred, restricted, or deprecated.
- `full-with-approval`: update accepted architecture owners only with target
  decision and approval evidence, then hand implementation to
  `product-change`.

## Routing Modes

- `inventory`: discover selected architecture items, evidence, owners, states,
  and documentation gaps.
- `explain`: explain current observed and intended architecture separately.
- `discuss`: evaluate one pattern or architecture question.
- `compare`: evaluate alternatives against shared drivers and constraints.
- `review`: find inconsistency, misuse, drift, debt, or missing evidence.
- `document`: draft or synchronize supporting project architecture docs.

Infer the mode from a clear request. Ask only for a missing decision that
blocks safe routing.

## Flow

1. Record mode, scope, problem or question, non-goals, allowed actions, and
   whether the user is exploring or asking to accept a decision.
2. Check that `architecture-knowledge` is enabled or required. If it is
   unavailable, use target evidence for a bounded read-only discussion and
   report the missing module or catalog instead of inventing it.
3. Load the compact catalog. Select only applicable area IDs, pattern IDs,
   canonical owners, decisions, and evidence. Record the catalog evidence
   revision and stale or missing entries.
4. Separate `observed`, `proposed`, `accepted`, `preferred`, `restricted`,
   `deprecated`, `contradicted`, and `unknown` items. Never infer intended
   architecture from implementation frequency.
5. State the problem, business and quality drivers in priority order, hard
   constraints, assumptions, unknowns, and target decision authority.
6. For discussion or comparison, evaluate the no-change baseline, reuse of an
   accepted project pattern, adaptation of an existing pattern, and a new
   pattern. Record why any option is non-viable or omitted.
7. Compare viable options with the same criteria: consistency, complexity,
   delivery, maintenance, performance, reliability, security, operability,
   migration, and reversibility. Do not recommend a pattern by popularity or
   familiarity.
8. When useful, create a bounded ASCII view of current and proposed
   relationships. Keep proposals visually and textually distinct from current
   or accepted architecture.
9. Report the recommendation as `proposed` unless the target decision owner
   and approval evidence accept it. Explain whether reuse, adaptation, or a new
   pattern is justified and include the maintenance cost of proliferation.
10. Under `docs-only`, write only evidence-backed observed, proposed,
    contradicted, or unknown project-contour records. Under
    `full-with-approval`, update the canonical architecture owner and catalog
    status, then route accepted changed facts to blueprint-driven change,
    logical integrity, diagrams, tests, implementation planning, and target
    validation.
11. Report selected and skipped evidence, documentation updates, handoff,
    validation, approvals, contradictions, skipped checks, and residual risk
    using the result template.

## Documentation Triggers

Recommend a catalog or supporting-document update after:

- accepted architecture decisions or changed quality constraints
- new project areas, dependencies, integrations, data owners, or trust
  boundaries
- repeated undocumented pattern use or inconsistent accepted-pattern use
- recurring review, incident, migration, security, or operability findings
- pattern restriction, deprecation, replacement, or contradiction
- moved owners, stale evidence paths, diagrams, or validation claims

Documentation recommendation is not permission to change accepted
architecture.

## Rejection Criteria

Reject or revise work that:

- invents architecture facts, pattern states, owners, drivers, or constraints
- treats observed implementation as an accepted project rule
- recommends a pattern without a concrete problem and common criteria
- introduces a pattern without checking no-change, reuse, and adaptation
- changes accepted architecture under `read-only` or `docs-only`
- scans all architecture docs before selecting catalog entries
- updates the catalog without updating or referencing the canonical owner
- hides contradictions, missing validation, skipped evidence, or residual risk
