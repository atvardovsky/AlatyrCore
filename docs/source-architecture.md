# AlatyrCore Source Architecture

This document describes the maintenance architecture for the AlatyrCore source
repository. It is a source-maintainer guide, not a portable framework rule.
Canonical portable behavior remains owned by the framework documents and the
rule registry.

## Chosen Model

Maintain a contracted modular monolith: one versioned package, capability
modules and an ordered validation pipeline. Framework, templates, schemas,
tools and conformance evidence move together. Give each capability one contract
owner, bounded surfaces and focused checks. Share pure primitives; keep CLI I/O,
reporting and exit behavior thin.

Keep boundaries inside the repository. Services or independent packages would
complicate cross-surface consistency without a demonstrated deployment need.

## Source Boundaries

Material source tasks reuse the canonical request/model/delivery contracts via
the [source self-application lane](source-self-application.md). Source policy
and reference indexes live under `tools/`; runtime projections remain ignored.
No duplicate task schema, portable framework copy or second planner is introduced.

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

Resolve installation and scaffold choices through one immutable composition
model. Support-profile inheritance, capability closure, framework-pack
selection, and assistant-surface aliases are separate inputs whose resolved
paths retain origin evidence. Existing catalogs remain canonical; the
composition object is a derived read model and must not become a competing
source of truth.

Schema-3 `template_file_capabilities` reuse direct inventories, never activation,
dependency closure, pack escalation or capability origins. Preserve legacy
literal profiles, independent mandatory expectations and complete composition
parity. Offline resources remain unchanged.

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

Keep user intent, source profile, task scale, validation and executor separate.
Changed-path automation selects checks after scope is known; it cannot downgrade
an explicit repository audit because the worktree is clean.

Source workers remain provider-neutral and read-only. Explicit audits dispatch
at least two independent eligible workstreams when runtime capability is
verified, or record a concrete skip reason. The primary owns architecture,
conflicts, logical integrity, integration, final validation and state changes.

Use a strategy boundary for provider-specific or capability-specific behavior.
Assistant surfaces, operating systems, optional modules, and target profiles
should be data-driven or isolated behind small modules instead of hard-coded
inside one large function.

Keep documentation in a CQRS-like split: canonical owner documents define
rules and contracts; generated indexes and human guides explain or summarize
them. Derived surfaces must be reproducible or explicitly checked for drift.

Model generated surfaces as an acyclic projection graph when one output feeds
another. Each node declares its owner, inputs, outputs, generator, and checker.
Generated indexes must not select their own inputs, and validators must never
silently repair outputs while checking them.

Use named path dialects at policy boundaries. Source-host matching, portable
manifest matching, support-tree matching, and approval-scope matching have
different compatibility semantics; sharing a parser must not silently make
those contracts equivalent.

Use content-addressed sparse writes for deterministic projections. An
unchanged desired byte stream is not rewritten. Omission and deletion remain
separate ownership decisions and are never inferred from a sparse overlay.

Treat every optimized or parity path as a refinement of its canonical path.
Use its canonical resolver or parser as the oracle; never copy requirements or
approximate them with substring checks. Differential tests must cover valid
entry points and missing, malformed, near-match, below-, exact-, and over-limit
inputs. Representation may shrink; enforcement may not.

Read-only project questions may use bounded source selection without creating
a change task. `project_lookup` composes `ProjectEvidence`, the shared
`registry_facts` parser, existing architecture source review and passive
`code_navigation` evidence. It is not a second context/impact planner or an
acceptance packet. Keep external report snapshots open through result assembly
and preserve snapshot nesting. Captured tool identity is not authentication;
ordinary source reads remain the fallback, with no mandatory backend.
Treat identifiers as opaque; derive status from its declared field, never a
status-like identifier spelling.

Derive behavioral fixtures from the canonical owner independently of generated
metadata. Include capability-disabled and minimal accepted targets, not only
full profiles that agree with each other. Mutate selected metadata through the
public API and CLI before testing downstream operations; invalid JSON-compatible
types must yield structured diagnostics, not tracebacks or silent defaults.
Preserved dirty history, current approvals and current outcome evidence are
different roles and require separate negative controls.

Apply least sufficient context to the source repository itself. Add indexes,
manifests, and narrow trigger paths so agents and checks load only what the
task actually needs. Context-affecting changes follow the conditional
[development context contract](#development-context-contract).

Source-profile conditionals declare stable IDs, bounded resolvers, paths or
indexed queries, and load conditions. Resolve only evidence-supported selectors;
retain selected/omitted reasons and fail-closed owner fallback. Budgets cover the
full packet in files, words and characters, preserving reserves; bootstrap
limits apply separately.

The machine router generates `tools/source-context/index.json` and per-profile
descriptors. Agents load this compact entry and one descriptor; canonical router
data remains machine-owned, not a second manually maintained policy. Exact JSON
records and Markdown sections carry source/projection digests. Whole-file
requirements, changed paths and canonical owners take precedence over excerpts.
Unknown or ambiguous selectors remain explicit readiness blockers in both full
and compact plan views; a projection is never accepted architecture or approval.

Source refresh uses a conservative complete-snapshot dependency closure and
run-scoped canonical check reuse. A check is reusable only for identical source
bytes/membership, checker invocation and isolated Git index within that call.
Checkers must not mutate the snapshot. Final output ownership, convergence,
normalization and concurrency guards remain active. Narrow per-stage inputs
only after dependency completeness is established; do not infer them from the
ordering DAG or persist this optimization as release evidence.
Checker-first generation is opt-in. Entry/bootstrap provenance normalizers
retain their canonical generators; once outputs change, the full repair path
runs except for the independently audited input contracts described below.

Refresh children use private Git refs, HEAD, configuration and index, with shared
immutable objects only. Each executed checker retains a full post-call byte/mode
observation and Git-control comparison. Narrow check reuse is limited to the
audited rules/findings input contracts in `refresh_source_projections.py`, bound
to exact renderer hashes, output bytes and inventory membership. Changed or
unknown implementations fall back to the full closure; ordering edges alone
never establish input completeness. Entry/bootstrap normalization is unchanged.

Planning shares one snapshot index and builds reuse identity for the emitted
runner command, including resolved refs and default capacity. Invocation-local
task/policy reuse retains final freshness checks, not cached authority. Optional
unit timing hints choose a bounded shard layout by queued-work estimates;
coverage, resource capacity and cold acceptance remain unchanged. Estimates are
not measured latency, and missing hints retain file-size scheduling.

Focused source tooling can persist direct Python import observations through
`--source-cache local`; direct planner/runner calls default to `off`, while
`check-source-focused` enables it. Result reuse remains a separate control.
The disposable Git-local JSON binds source bytes and path, module inventory,
loaded resolver code, implementation files, workspace and Python runtime.
Observed import sources and implementation files are rehashed and the current
resolution inventory checked before returning the plan; changed or unreadable
source inputs require replanning. Corrupt/unavailable cache data falls back to
canonical scanning. Whole graph JSON records are bounded to 10 MiB each and
the newest 16 graph identities
(best-effort retention under concurrent writers). Full/release profiles reject
persistent source reuse. Hashes establish identity, not semantic correctness
or authority; cached observations never replace cold acceptance.

## Development Context Contract

For context-delivery or agent-workflow changes, follow the
[development context contract](source-optimization/development-context-contract.md).
Keep the detailed guide conditional. Select it through existing `contract_paths`
in `source-tooling`, or `audit_context_paths` in `repository-audit`; this pointer
alone is not the complete contract. Neither route changes authorization,
canonical owners, or validation requirements. Routine tasks need not load it.

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
8. Reuse a previous passed check only when its command, runtime, transitive
   local implementation closure, declared contract inputs, and run identity
   match the current run. Reuse is per check, locally bounded, and never release
   evidence.
9. Expand to full validation when a broad route, failed check, contract change,
   release change, or ownership conflict appears.
10. Record final evidence with worker decisions, checks that actually ran,
    reused or explicitly skipped, and any residual risk.

This preserves quality while reducing routine task cost. The optimization is
valid only when the focused route proves that the changed files are covered by
the owning checks.

## Current Refactoring Priorities

- Package-index traversal retains shared snapshots, Git evidence, findings and
  overridable public delegates. Shared delegation/lifecycle/repair primitives
  remain below orchestrators; no cycle exceptions remain.
- Derive opted-in activation from the manifest; preserve target rationale,
  inactive dispositions, legacy profiles and rollback. Resource removal or
  always-loaded context requires separate offline and enforcement parity.

- Keep the extracted team collaboration, architecture knowledge, code
  documentation, project vocabulary, test-first development, extension,
  dependency knowledge, and development-evidence checks behind the
  contract-closed capability registry. Preserve the stable target-validator
  CLI facade and finding contract while reducing the remaining no-growth
  functions internally.
- Keep generated entry, capability, semantic, and report projections compact;
  their canonical source contracts must retain strict closure checks.
- Keep diagrams, delegation, and workspace modes on the narrow capability
  context. Debug Mode remains an explicit compatibility route until its Git
  history and repository-binding dependencies can be extracted with finding
  parity; dispatch must never depend on reflective method lookup.
- Keep target validation as an ordered phase pipeline with unique IDs,
  declared dependencies, and cost classes. Execution remains sequential until
  phase isolation proves that parallel reads preserve finding order and input
  mutation detection.
- Keep the typed installer stage model bound to the canonical context router.
  A stage checkpoint is disposable optimization evidence only; it cannot grant
  approval, authorize an action, or establish semantic correctness.
- Split large target validation methods into schema parsing, relationship
  traversal, fixture checks, and diagnostic rendering.
- Convert repeated source-tool read, parse, path, and subprocess patterns into
  shared helpers only when at least one caller and test prove the abstraction.
- Review broad trigger routes after each new helper so small documentation or
  tooling changes do not accidentally select heavy checks.
- Keep source-check concurrency parent-owned. Heavy checks receive an explicit
  child capacity and may parallelize only independent subprocesses with private
  mutable state. Scheduling history may optimize order but never validation
  coverage.
- Keep changed-surface target validation fail-closed and non-acceptance. The
  universal validator core always runs; optional module routing may reduce
  development-loop work, while installation, update, and release evidence stays
  full-scope.
- Prefer C-backed safe YAML parsing when the installed PyYAML build provides it,
  but retain the safe portable loader fallback and identical node-mark behavior.
  Reuse parsed content and file inventories only within one immutable validator
  run; never cache target-boundary resolution across filesystem accesses.

## Non-Goals

- Do not convert AlatyrCore into a hosted service.
- Do not add a universal installer as the primary installation mechanism.
- Do not split source packages before release and migration contracts require
  it.
- Do not weaken validation to improve speed. Speed improvements must come from
  better routing, smaller pure helpers, caching, or staged checks.
