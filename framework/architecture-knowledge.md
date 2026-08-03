---
alatyr_doc:
  id: framework.architecture-knowledge
  type: framework-rule-owner
  owns_rules:
    - ALATYR-ARCHITECTURE-001
  depends_on:
    - ALATYR-CONTEXT-001
    - ALATYR-SOURCE-001
    - ALATYR-RISK-001
    - ALATYR-INTEGRITY-001
    - ALATYR-CHANGE-001
    - ALATYR-DIAGRAM-001
  applies_to:
    - docs-local
    - architecture-change
    - data-change
    - security-sensitive
---
# Architecture Knowledge And Discussion

This document defines a portable process for discussing project architecture,
evaluating patterns and other architectural items, and maintaining supporting
project documentation.

Concrete architecture facts, patterns, areas, constraints, technologies,
paths, decisions, diagrams, and validation belong to the target project
contour. Framework core owns only the process and record shape.

## Purpose

Architecture assistance should help a project:

- explain the architecture currently evidenced by the repository
- document intended architecture without treating inference as acceptance
- discuss reuse, adaptation, introduction, restriction, or retirement of
  architecture patterns
- compare alternatives against the same drivers and constraints
- detect inconsistent pattern use or architecture documentation drift
- carry accepted architecture decisions into blueprints, implementation,
  tests, diagrams, gates, skills, prompts, and validation

A pattern is never a goal by itself. Start with the project problem, drivers,
constraints, and existing architecture before recommending one.

## Knowledge States

Every architecture item must distinguish its evidence and decision state:

- `observed`: supported by implementation evidence but not confirmed as an
  intended project rule
- `proposed`: an alternative under discussion
- `accepted`: approved by the target decision owner and recorded in the
  canonical architecture source
- `preferred`: accepted for new work within a named scope
- `restricted`: allowed only in named scopes or circumstances
- `deprecated`: retained for compatibility but not for new work
- `contradicted`: intended documentation and repository evidence disagree
- `unknown`: evidence is insufficient or conflicting

Do not promote `observed` to `accepted` because the implementation is common,
old, recent, or convenient. Do not describe a proposal as current project
architecture.

## Project Architecture Knowledge

An enabled target module should maintain a compact machine-readable catalog
and a human architecture index. They route to existing project architecture
docs, decision records, diagrams, and selected detail records; they do not
replace canonical owners.

The catalog should cover architecture items relevant to the target, including:

- architectural styles and decomposition strategies
- domains, services, modules, layers, and dependency directions
- API, event, integration, workflow, and failure-handling patterns
- data ownership, consistency, migration, caching, and lifecycle patterns
- concurrency, retry, idempotency, and state-management patterns
- trust boundaries, authorization, privacy, and security patterns
- runtime topology, deployment, observability, and operational patterns
- quality attributes, constraints, technologies, and known architecture debt

Large projects should keep the catalog compact and load selected pattern, area,
decision, or view records lazily.

## Pattern Record Contract

Each documented pattern should record:

- stable pattern ID, name, kind, state, scope, and project areas
- problem and architecture drivers it addresses
- repository evidence and canonical decision owner
- intended rules, invariants, dependency direction, and allowed exceptions
- when to use it and when not to use it
- benefits, liabilities, operational effects, and migration cost
- related, compatible, conflicting, replacement, or superseded patterns
- validation, fitness check, or manual review
- diagram or architecture-view references when useful
- last verified repository revision and known evidence gaps

Pattern detail may live in existing target documentation. The catalog should
point to that owner rather than duplicate the full explanation.

## Discussion Modes

One architecture-assistance operation may route these modes:

- `inventory`: discover architecture areas, items, patterns, owners, and gaps
- `explain`: explain selected current architecture from target evidence
- `discuss`: evaluate a pattern or architectural question
- `compare`: compare alternatives against common drivers and constraints
- `review`: inspect consistency, fit, drift, debt, or misuse
- `document`: draft or synchronize project-owned architecture documentation

Clear requests should route automatically. The user does not need to know the
mode name.

## Pattern Discussion Sequence

For a selected question or scope:

1. Name the problem, non-goals, decision status, and allowed actions.
2. Load the compact architecture catalog and only the selected project area,
   pattern records, canonical owners, and evidence.
3. Separate observed implementation, intended architecture, proposals, and
   contradictions.
4. Identify business and quality drivers, hard constraints, assumptions,
   unknowns, and decision authority.
5. Consider the no-change baseline, reuse of an accepted project pattern,
   adaptation of an existing pattern, and introduction of a new pattern.
   Omit an option only with an explicit reason.
6. Compare viable options using the same criteria: consistency with existing
   architecture, complexity, delivery cost, maintenance cost, performance,
   reliability, security, operability, migration, and reversibility.
7. Present focused current and proposed ASCII views when a visual relationship
   materially improves the discussion.
8. Report a recommendation as `proposed` until the target decision owner and
   approval policy accept it.
9. When accepted architecture changes, hand off to blueprint-driven change,
   logical integrity review, approval, and target validation.

Prefer reuse when an accepted project pattern solves the problem without
violating stronger drivers. A new pattern requires evidence that reuse or
adaptation is insufficient and must account for the long-term consistency and
maintenance cost of another architectural approach.

## Documentation Maintenance

Architecture knowledge should be reviewed when target evidence shows:

- an accepted architecture decision or changed quality constraint
- a new module, service, dependency, integration, data owner, or trust boundary
- repeated use of an undocumented architecture approach
- inconsistent implementations of an accepted or preferred pattern
- recurring review, incident, migration, or operability problems
- a deprecated pattern still used for new work
- implementation that contradicts intended architecture documentation
- a moved owner, stale path, stale diagram, or unverifiable validation claim

For `read-only`, report findings without editing files. Under `docs-only`, an
assistant may record evidence-backed observed items or draft/proposed docs, but
must not convert them to accepted architecture. Accepted architecture facts
require the target owner and approval policy, then normal companion updates.

## Context Economy

Architecture knowledge must not enter ordinary task context by default. Start
with the compact catalog, then load only selected area, pattern, decision, and
evidence records.

Load security, data, runtime, diagram, consistency-map, or product-change
context only when the selected architecture question crosses that boundary.
Use a large-task packet only for multi-area, multi-workstream, or resumable
architecture work.

## AI Infrastructure Support

Repeated architecture problems may justify project-contour recommendations for
target-owned skills, prompts, gates, checkers, or review flows. Recommendations
must use architecture evidence and the existing-item-first process. Do not add
generic architecture infrastructure merely because the framework provides a
template.

## Evidence

Architecture assistance should report:

- mode, scope, problem, non-goals, and decision state
- loaded architecture items, owners, evidence, and evidence revision
- current patterns and relevant alternatives
- drivers, constraints, assumptions, contradictions, and unknowns
- option comparison and pattern-proliferation result
- recommendation, confidence, and decision authority
- ASCII views or reason no diagram was needed
- documentation, decision, blueprint, consistency, and implementation handoff
- validation, approvals, skipped checks, and residual risk

## Rejection Criteria

Reject or revise architecture work that:

- invents current architecture, pattern use, constraints, or decision status
- treats common implementation as accepted architecture without an owner
- recommends a pattern before naming the problem it solves
- introduces a pattern without evaluating no-change, reuse, or adaptation
- compares alternatives using different or hidden criteria
- hides architecture inconsistency behind local implementation success
- changes accepted architecture under `read-only` or `docs-only`
- duplicates canonical target architecture facts into framework core
- loads the complete architecture corpus when a selected catalog route is
  sufficient
