# AlatyrCore Source Architecture

This document describes the maintenance architecture for the AlatyrCore source
repository. It is a source-maintainer guide, not a portable framework rule.
Canonical portable behavior remains owned by the framework documents and the
rule registry.

## Chosen Model

AlatyrCore should be maintained as a contracted modular monolith with
capability modules and a validation pipeline.

The repository remains one versioned source package because the framework,
templates, schemas, tools, and conformance evidence must move together. Inside
that package, every capability should have a clear contract owner, a bounded
support surface, and focused validation. Shared code should expose pure,
reusable primitives first; command-line wrappers should stay thin and handle
I/O, reporting, and process exit behavior.

This model fits AlatyrCore better than splitting into services or independent
packages. The product value depends on repository-owned knowledge and checked
consistency between many text, schema, template, and tool surfaces. A single
repository keeps that consistency visible while modular boundaries keep routine
changes cheap.

## Source Boundaries

- Framework contracts live under `framework/` and own portable rule semantics.
- Installer behavior lives under `installer/` and owns assistant-led adaptation
  flow.
- Target projections live under `templates/target/` and must remain
  placeholder-based until installed into a real project.
- Schemas under `schemas/` own machine-readable target adapter contracts.
- Source tools under `tools/` validate this repository and optional installed
  target adapters; they do not create portable runtime requirements.
- `tools/source_context_router.json` owns source task routing, while
  `tools/source_worker_policy.json` owns provider-neutral source workstream
  decomposition and `tools/source_worker_contract.py` owns its executable
  validation contract. The active assistant owns current-session capability
  evidence and the primary assistant owns integration and action authorization.
- Target adapter validation modules under `tools/target_adapter_validation/`
  should own capability-specific checks when the legacy validator is split.
- Conformance files under `conformance/` own captured or prepared evidence, not
  unverified product claims.
- Maintainer documentation under `docs/` explains source-repository operation
  and must link back to canonical owners instead of duplicating full policy.

## Engineering Principles

Use bounded contexts for source changes. A change to context routing should not
require loading every source tool, and a change to one checker should not imply
rewriting the framework corpus unless a rule owner is affected.

Use contract-first design for every generated or machine-checked surface. The
contract can be Markdown, JSON, YAML, or a schema, but it must identify the
owner, consumers, validation command, and synchronization direction.

Prefer a functional-core and imperative-shell shape for Python tools. Parsing,
classification, matching, and validation helpers should be pure functions or
small data classes. CLI entry points should collect input, call those helpers,
print diagnostics, and return an exit code.

Use pipeline validation instead of one broad checker whenever a capability can
be checked in stages. A cheap structural check should run before expensive
fixtures or broad source scans.

Use a minimum-work planning step before routine source changes. The planner
should resolve changed paths, explicit micro eligibility, selected checks,
context hints, heavy checks, and optional hash-bound reuse candidates before
implementation starts. It is a routing surface only; it does not approve edits,
commit, publish, or replace semantic review.

Keep user intent, source task profile, task scale, validation profile, and
executor selection as separate decisions. Changed-path automation can reduce
validation cost after scope is known, but it cannot infer that an explicit
repository audit is a small task merely because no files have changed.

Use source worker decomposition as a strategy boundary. Reusable workstreams
remain provider-neutral and read-only; the active assistant verifies runtime
capability. Explicit repository audits should dispatch at least two independent
eligible workstreams when capability is verified, unless the primary assistant
records a concrete skip reason. Architecture decisions, conflict resolution,
logical integrity, integration, final validation, and state-changing phases
remain primary-owned.

Use a strategy boundary for provider-specific or capability-specific behavior.
Assistant surfaces, operating systems, optional modules, and target profiles
should be data-driven or isolated behind small modules instead of hard-coded
inside one large function.

Keep documentation in a CQRS-like split: canonical owner documents define
rules and contracts; generated indexes and human guides explain or summarize
them. Derived surfaces must be reproducible or explicitly checked for drift.

Apply least sufficient context to the source repository itself. Add indexes,
manifests, and narrow trigger paths so agents and checks load only what the
task actually needs.

## Extraction Rules

- Extract pure helpers before moving CLI behavior.
- Preserve command names, output shape, and exit codes unless the change is
  explicitly classified as a behavior change.
- Add or update tests for the extracted behavior before relying on the new
  module as a contract surface.
- Update `tools/check_manifest.json` whenever a checker imports a new local
  helper or a new source file needs focused routing.
- Keep large-function allowlist entries as no-growth caps. Lower or remove a
  cap only after an extraction makes the legacy function smaller.
- Do not move portable framework semantics into source tooling helpers.
- Do not copy target-project facts into reusable validators or templates.

## Validation Pipeline Shape

The expected source-tooling flow is:

1. Classify the source change and choose the smallest context route.
2. For a named operation, select its explicit source profile before consulting
   changed-path automation.
3. Generate a read-only minimum-work plan when the scope is not already
   obvious from the selected profile.
4. Evaluate bounded worker decomposition and verify runtime capability when the
   selected profile requires it.
5. Dispatch eligible independent read-only packets or record concrete skip
   reasons while the primary assistant runs the authoritative critical path.
6. Run cheap structural checks first.
7. Run changed-path focused checks when the route is unambiguous.
8. Reuse a previous passed check only when its manifest, command, runtime, and
   declared input fingerprint match the current run.
9. Expand to full validation when a broad route, failed check, contract change,
   release change, or ownership conflict appears.
10. Record final evidence with worker decisions, checks that actually ran,
    reused or explicitly skipped, and any residual risk.

This preserves quality while reducing routine task cost. The optimization is
valid only when the focused route proves that the changed files are covered by
the owning checks.

## Current Refactoring Priorities

- Keep extracting reusable source-check manifest primitives from CLI wrappers.
- Use `tools/plan_minimum_work.py` and the `micro` profile to identify cheap
  source routes before adding broader default checks.
- Split `tools/validate_target_adapter.py` by optional capability modules after
  behavior is covered by focused regression tests.
- Split large target validation methods into schema parsing, relationship
  traversal, fixture checks, and diagnostic rendering.
- Convert repeated source-tool read, parse, path, and subprocess patterns into
  shared helpers only when at least one caller and test prove the abstraction.
- Review broad trigger routes after each new helper so small documentation or
  tooling changes do not accidentally select heavy checks.

## Non-Goals

- Do not convert AlatyrCore into a hosted service.
- Do not add a universal installer as the primary installation mechanism.
- Do not split source packages before release and migration contracts require
  it.
- Do not weaken validation to improve speed. Speed improvements must come from
  better routing, smaller pure helpers, caching, or staged checks.
