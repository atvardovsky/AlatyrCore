---
alatyr_doc:
  id: framework.code-documentation
  type: framework-rule-owner
  owns_rules:
    - ALATYR-CODEDOC-001
  depends_on:
    - ALATYR-CONTEXT-001
    - ALATYR-SOURCE-001
    - ALATYR-RISK-001
    - ALATYR-APPROVAL-001
    - ALATYR-INTEGRITY-001
    - ALATYR-ADAPTER-001
  applies_to:
    - docs-local
    - code-local
    - business-change
    - architecture-change
    - data-change
---
# Code Documentation Generation

This document defines the portable process for selecting project-specific code
comment styles and generating reference documentation from structured comments.

Concrete languages, frameworks, path scopes, comment formats, generators,
commands, output paths, publication systems, and quality conventions belong to
the target project contour. Alatyr Core owns only the selection, safety,
source-of-truth, synchronization, and evidence contract.

## Purpose

An enabled code-documentation module should help a target project:

- propose documentation conventions from repository evidence instead of
  imposing one framework-wide style
- support different profiles for frontend, backend, shared libraries,
  infrastructure, or other bounded source sets
- keep structured comments close to the symbols they explain
- generate reference documentation deterministically with target-selected
  language or ecosystem tooling
- update comments and generated reference surfaces with relevant behavior
  changes
- avoid boilerplate comments that merely restate names, types, or syntax
- expose missing, stale, contradictory, or unverified documentation without
  claiming semantic correctness from generator success

Automatic generation means a deterministic tool renders accepted structured
comments and declarations. It does not mean that an assistant may invent
business intent, accepted architecture, security policy, or runtime guarantees
from code alone.

## Source-Of-Truth Boundary

Documentation profiles must classify each documented fact before selecting a
comment or generated output as its owner.

- Code declarations own symbol names, signatures, types, and visibility when
  the target registry says so.
- Structured comments may own bounded symbol-level explanation such as purpose,
  usage, parameter meaning, return meaning, local failure behavior, important
  side effects, examples, and deprecation guidance.
- A registered API specification, schema, decision record, business blueprint,
  security policy, or operational source remains canonical for the facts it
  owns. Comments summarize or link to it; they do not supersede it.
- Generated documentation is always a derived surface. Do not edit it directly.
- Architecture frequency in code does not make a comment an accepted
  architecture decision.

When ownership is missing or contradictory, record the gap and limit comments
to observed behavior. Do not convert observation into accepted intent.

## Multiple Documentation Profiles

A target may define any number of non-overlapping or explicitly ordered
profiles. A profile binds a bounded source set to its documentation contract.
Each profile should record:

- stable ID, state, owner, priority, and path or source-set match
- language, framework, audience, visibility, and documentation purpose
- evidence for existing conventions and the selected style
- structured comment syntax and required semantic sections
- content that should be omitted because it is obvious, duplicated, generated,
  sensitive, or owned elsewhere
- canonical fact owners and links used by comments
- generator, configuration, generation entry point, output location, and output
  retention or publication policy
- lint, generation, link, example, or manual validation
- supported assistant skill or wrapper when one is accepted
- last verified repository revision, gaps, and migration needs

Valid profile states are:

- `proposed`: evidence-backed recommendation awaiting target acceptance
- `accepted`: approved target convention that may guide comment and generation
  changes
- `deprecated`: retained only for existing scope while migration is planned
- `contradicted`: repository behavior and the recorded profile disagree
- `unknown`: evidence or ownership is insufficient

Only an `accepted` profile may direct routine comment generation or broad
documentation synchronization. A proposed profile may be used to prepare a
preview, sample, or review report, but not to mass-edit source files.

## Profile Selection

For a documentation-relevant request or changed source path:

1. Load the compact profile catalog, not all documentation records.
2. Select accepted candidates by path/source-set match, then language and
   framework compatibility.
3. Prefer the most specific match; use explicit priority only to resolve an
   intentionally overlapping scope.
4. If equally specific accepted profiles conflict, stop automatic generation
   and report the ambiguity.
5. If no accepted profile applies, inspect existing repository conventions and
   prepare a read-only proposal.
6. Load only the selected profile, canonical owners, generator configuration,
   and affected source files.

Frontend and backend areas may use different styles even when they share a
language. Syntax choice and semantic content are separate decisions. For
example, a frontend profile may emphasize component behavior, state ownership,
accessibility, and usage, while a backend profile may emphasize invariants,
authorization, transactions, external effects, retries, and failure semantics.

## Style Proposal Process

Before proposing or revising a profile, the assistant must inspect:

- target languages, frameworks, source roots, generated code, and public
  boundaries
- existing comments, docstrings, compiler settings, linter rules, generators,
  documentation sites, package scripts, CI jobs, and editor support
- canonical API specifications, schemas, architecture sources, and business
  owners that comments must not replace
- recurring review findings, missing explanations, stale docs, onboarding
  friction, and development evidence when available
- target ownership, maintenance capacity, compatibility, dependency, security,
  publication, and cost constraints

Prefer an established target convention and existing generator when they meet
the required contract. Otherwise compare a small set of language-appropriate
options using the same criteria: semantic fit, native type or compiler
integration, IDE support, generated output quality, CI support, maintenance,
dependency cost, migration effort, and cross-platform behavior.

The proposal must include sampled evidence, alternatives considered, the
recommended profile, rejected options, migration scope, acceptance criteria,
approval needs, and residual risk. Do not invent measured coverage or cost.

## Comment Content Contract

Document only information that improves safe use or maintenance. Depending on
the selected profile and symbol kind, useful sections can include:

- responsibility, intended usage, and relevant non-goals
- parameter or property semantics not evident from types
- return, yield, event, state-transition, and failure semantics
- business or technical invariants linked to their canonical owner
- authorization, privacy, transaction, concurrency, retry, idempotency, and
  external-side-effect constraints
- lifecycle, cleanup, caching, accessibility, compatibility, and deprecation
  behavior
- concise examples whose assumptions can be validated

Reject comments that merely narrate implementation steps, repeat identifiers or
types, speculate about intent, expose secrets, copy large policy blocks, or
become a second owner for facts held elsewhere.

## Generation And Output Policy

The target chooses one output policy per profile:

- `ci-artifact`: generate during validation or publication without committing
  generated output
- `committed-generated`: commit generated output and require regeneration to
  leave no unexplained diff
- `local-only`: generate for local reference without publication
- `external-publish`: publish through a target-approved external system
- `unresolved`: no output policy has been accepted

Generation must use a target-recorded entry point. Framework examples must not
be copied as target commands. Dependency installation, CI changes, external
publication, broad source rewrites, or permission expansion follow target risk
and approval policy.

Generator success proves only that selected inputs were processed. It does not
prove comment truth, public completeness, architectural consistency, or
business correctness.

## Synchronization Triggers

Review the selected profile and affected comments when a change affects:

- public or supported interfaces
- symbol responsibility, inputs, outputs, failure behavior, or side effects
- business or technical invariants referenced by code
- authorization, privacy, transactions, concurrency, retries, or idempotency
- module ownership, dependency direction, data lifecycle, or external services
- component usage, accessibility behavior, lifecycle, or state ownership
- deprecation, migration, compatibility, or operational behavior
- generator configuration, output policy, public examples, or documentation
  ownership

Local refactoring that changes none of these facts may skip comment and
generation changes, but final evidence should record the decision.

## Assistant Skill Boundary

An accepted target may adapt a project-owned code-documentation skill. The
skill should select the matching accepted profile, load only its required
owners, propose comments, run target-recorded validation when allowed, and
report output evidence.

The skill is an execution aid. It must not own profile policy, source-of-truth
precedence, generator commands, or project facts. Do not activate a placeholder
or proposed skill as if it were an accepted target capability.

## Context Economy

Keep the module outside routine bootstrap. Route through a compact intent
descriptor and profile catalog, then load only the selected source-set profile,
affected symbols, canonical owners, and generator configuration.

Do not load generated output when the source comments and generation result are
sufficient. Load architecture, business, data, security, or AI-infrastructure
context only when the selected profile or changed fact crosses that boundary.

## Evidence

Code-documentation work should report:

- mode, scope, selected profile, state, owner, and match reason
- languages, frameworks, audience, visibility, and repository evidence
- canonical fact owners and source-of-truth boundary
- proposed or accepted comment style and semantic content contract
- generator, configuration, output policy, and publication boundary
- changed comments, skipped symbols, generated outputs, and direct-edit checks
- validation run, skipped checks, acceptance or approval state, and residual
  risk

## Rejection Criteria

Reject or revise code-documentation work that:

- imposes one style across unrelated project areas without evidence
- selects a generator before inspecting existing target tooling
- uses a proposed, contradictory, unknown, or ambiguous profile for mass edits
- treats generated documentation as canonical or edits it directly
- infers accepted business, architecture, security, or operational intent from
  code comments
- requires comments for every symbol regardless of audience or value
- produces comments that only repeat code syntax or type information
- adds dependencies, CI jobs, publication, broad rewrites, or permissions
  without required approval
- loads every profile or generated document for a bounded source change
- claims semantic correctness because generation completed
