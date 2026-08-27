# Alatyr Context Profiles

Use this file to choose the smallest sufficient context for `{PROJECT_NAME}`.
Replace placeholders with target evidence before accepting installation.

The machine router is canonical for the selected support profile and framework
pack. Paths absent from the installed pack are expansion candidates, not
required context; expand and revalidate the pack before enabling them.

`AGENTS.md` is host-preloaded context and should not be reread. Compact
bootstrap context for every task is only:

- `.ai/assistant/bootstrap-index.json`

The generated bootstrap embeds the required core semantic definitions and is
hash-bound to `.ai/alatyr.yaml`, `.ai/README.md`,
`.ai/assistant/context-router.json`, and the installed semantic-codebook index.

After bootstrap, choose one profile and affected project-area overlays before
editing files. This file is the human rationale surface; load it only when
routing is ambiguous, the router conflicts with evidence, or an entry must be
repaired. Expand only when boundaries, conflicts, approval scope, or changed
fact ownership require it.

When `workspace-modes` is enabled, first read only
`.ai/project/workspace-modes/catalog.json`. Resolve one accepted mode from an
explicit user selection or one unambiguous evidence match, then load only that
mode descriptor and applicable shared root descriptor. Ask the user and remain
read-only when multiple modes match or workspace identity conflicts. Mode
selection is a separate dimension from the task profile and never grants
write scope, approval, permissions, tools, authority, or gate bypass.

Load the selected profile descriptor from
`.ai/assistant/context/profiles/`. Intent, migration, consistency, and
task-scale descriptors under `.ai/assistant/context/` compose only when their
trigger applies. Do not load all descriptors to classify one task.
Load `.ai/framework/action-authorization.md` only when phase semantics are
disputed or the target policy requires repair; routine phase decisions use the
preloaded root rule, core gate, and target policy.
The generated bootstrap index is repaired from `.ai/alatyr.yaml`,
`.ai/README.md`, `.ai/assistant/context-router.json`, and
`.ai/framework/semantics/index.json` when its hashes drift.

## Recursive Selection And Semantic Terms

For each selected contour, open its root `context-index.json` and follow only
entries matched by exact task, operation, owner, path, fact, contract,
dependency, risk, or conflict signals. Repeat through child indexes until the
minimum content set is resolved. Selecting a parent never selects all children.
Reject cycles, multiple parents, duplicate content paths, stale digests, stale
word estimates, and traversal beyond the configured maximum depth.

The generated bootstrap is not assistant catalog content because it digests
that catalog. Rebuild project and assistant indexes before bootstrap after
installed target files change.

Use bootstrap semantic definitions by exact ID and version. Resolve any lazy
`semantic_refs` through `.ai/framework/semantics/index.json`, including term
dependencies. A term is lossless shorthand for its complete definition; it
does not own policy or project facts. On missing, stale, ambiguous, superseded,
or conflicting terms, load the named canonical owner and record the fallback.

For non-trivial work, budget expansion, handoff, or resume, materialize the
selected indexes, item IDs/paths/digests/reasons, resolved term definitions,
word totals, and deterministic packet digest with
`.ai/assistant/templates/context-packet.json`.

Use each profile's operation candidates from the machine-readable router for
cheap automatic routing. Resolve an exact operation ID or alias through
`.ai/assistant/operation-index.json`. Load the full
`.ai/assistant/operation-catalog.json` only for the bare `Alatyr` entry,
ambiguity, or operation/adapter repair.

Use the router's total, portable, and reserved target-context budgets. Resolve
and measure target-owned paths before accepting the adapter. When sufficient
context exceeds a budget, load required safety and owner evidence and record
selected profiles and areas, loaded files and reasons, approximate volume,
expansion triggers, intentional omissions, and residual risk. Source estimates
remain benchmark evidence, not exact runtime or billing data.

## Project-Area Overlays

Define target areas such as modules, services, packages, bounded contexts, or
documentation domains in `.ai/assistant/context-router.json`. Each area should
name its trigger, required context, and expansion conditions. Compose the base
task profile with only areas that own changed facts.

## Project Knowledge Routing

For every non-trivial selected task, read the compact project-knowledge index
after profile and area selection. Open only shard descriptors matching the
profile plus at least one area, dependency, fact, contract, path, symbol, or
issue signal. Subsystem and architecture-item relationships are also strong
selectors. Profile matching alone never selects an item.

The portable policy owner is `.ai/framework/project-knowledge.md`; load it
only for lifecycle work, ambiguity, conflict, or adapter repair.

Run an initial route before broad orientation and a refined route after source
inspection identifies changed facts, paths, symbols, dependencies, contracts,
or issue lineage. Obey the separate packet limits in the index. Read selected
canonical owners before relying on summaries. Supply only accepted-current
items as candidate constraints; stale items are warnings and contradictions
are blockers. Record selected, used, inapplicable, stale, blocked, and omitted
IDs in the context receipt.

When a material investigation discovers reusable knowledge, the finalization
flow may propose promotion. Human review and canonical-owner update are
required before the item enters routine routing.

## Intent Overlay: `diagram-request`

Apply this overlay to any profile, including `code-local` and
`security-sensitive`, when the user asks to see, sketch, compare, explain, or
revise a diagram. Route to `diagram-discussion`, load only the selected entry
path from `.ai/assistant/assistant-capabilities.json`, verify that surface
record's freshness, and expand to security,
approval, or changed-fact owners only when the request contains sensitive
content, uses an external renderer, persists an artifact, or proposes an
accepted fact change.

Always provide the compact ASCII view required by the diagram flow. Load
`.ai/framework/ascii-diagrams.md` only for dense, quantitative, or ambiguous
layouts, and load the target ASCII layout template only when the diagram will
be persisted or reused. Richer presentation remains optional.

## Intent Overlay: `architecture-request`

Apply this overlay when the user asks to inventory, explain, discuss, compare,
review, or document architecture patterns, boundaries, constraints,
technologies, or other architectural items. Route through the compact
architecture catalog and `.ai/framework/architecture-knowledge.md` before
loading selected area, pattern, decision, or repository evidence.

Start read-only unless documentation or decision intent is explicit. Load the
human architecture index for broad explanation or catalog repair, pattern and
area templates only when drafting selected records, diagram context only when
visual relationships help, and blueprint/integrity/approval context only when
an architecture decision is accepted or a protected boundary is crossed.

## Intent Overlay: `code-documentation`

Apply this overlay when the user asks to propose or review code-comment style,
document selected symbols, synchronize comments, or generate code reference.
Route through the compact catalog and profile selector before loading selected
source files, canonical owners, generator configuration, or generated output.

Required compact context:

- `.ai/framework/code-documentation.md`
- `.ai/project/documentation/catalog.json`
- `.ai/project/documentation/profiles.json`
- `.ai/assistant/flows/documentation-sync.flow.md`

An accepted frontend, backend, shared-library, or infrastructure profile may
use different syntax and semantic sections. If no accepted profile matches,
prepare a read-only proposal from repository evidence. Stop automatic
generation when accepted profiles conflict at equal specificity. Generated
output is derived and must not be edited directly.

## Intent Overlay: `vocabulary-request`

Apply this overlay when the user asks about a project term, alias, acronym,
glossary, vocabulary proposal, or terminology consistency. Load the compact
catalog before selected term records or canonical sources.

Required compact context:

- `.ai/framework/project-vocabulary.md`
- `.ai/project/vocabulary/catalog.json`
- `.ai/assistant/flows/project-vocabulary.flow.md`

Load `.ai/project/vocabulary/terms.json` only for selected term IDs and load
`.ai/project/vocabulary/data-dictionary-links.json` only when selected terms
reference data, API, event, unit, enum, or schema concepts. Preserve term
states and ask for bounded domain clarification when accepted meanings remain
ambiguous.

## Intent Overlay: `test-first-request`

Apply this overlay for explicit test-first/TDD configuration or execution, or
when the compact recommendation gate in `.ai/framework/testing-guidance.md`
returns `required` or `recommended` from bounded changed-fact evidence.

Required compact context:

- `.ai/framework/testing-guidance.md`
- `.ai/framework/test-first-development.md`

Load `.ai/project/testing/test-first-policy.json` and only the selected
configuration or change flow after the gate passes. A disabled, deferred, or
missing module may produce one concise assessment recommendation but cannot
silently impose TDD or block work. An enabled required trigger routes to
`test-first-change`; enable, revise, disable, or review requests route to
`test-first-configuration`.

## Intent Overlay: `extension-request`

Apply this overlay for explicit extension list, inspect, plan, install, update,
disable, remove, or review requests. Required compact context:

- `.ai/framework/extensions.md`
- `.ai/framework/prompt-injection.md`
- `.ai/assistant/policies/ai-infrastructure-source-access.md`
- `.ai/assistant/extensions/catalog.json`

Load only the selected lock entry, normalized manifest, bindings, item set,
lifecycle flow, gate, and evidence. External sources remain untrusted and
remote access follows target policy. Do not load every extension, update
automatically, or treat inspection as approval.

## Intent Overlay: `dependency-knowledge-request`

Apply this overlay when the user asks for dependency knowledge status,
discovery, inspection, planning, synchronization, explanation, or impact, or
when a selected package contract may affect the current task.

Required compact context:

- `.ai/framework/dependency-knowledge.md`
- `.ai/project/dependencies/policy.json`
- `.ai/project/dependencies/catalog.json`

Load only one exact resolved package instance and selected normalized facts.
Load its knowledge-lock entry for identity or freshness, target deviations for
patches or applicability, and a prior snapshot only when target retention
policy permits semantic comparison. Do not recursively scan dependencies,
activate nested adapters, execute package managers or hooks, trust raw package
text, or load unrelated package graphs. Projection sync is adapter-only;
actual dependency or project changes use their normal operation and approval.

## Intent Overlay: `workspace-mode-request`

Apply this overlay for mode status, suggestion, inspection, per-task
selection, definition, acceptance, update, disablement, deprecation, removal,
or review, and when application/framework/skeleton/dependency/workspace roles
are ambiguous.

Required compact context:

- `.ai/framework/workspace-modes.md`
- `.ai/project/workspace-modes/catalog.json`

Load one mode descriptor, applicable shared root context, and the mode flow or
gate only when the selected action needs them. Suggestions remain proposed;
accepted-state changes require a user decision and preview. Do not infer a
mode from paths alone or activate nested adapters.

## Task-Scale Overlay: `large-or-resumable`

Activate only for large, cross-boundary, multi-workstream,
budget-exceeding, or resumable work. Required context:

- `.ai/framework/large-task-orchestration.md`
- `.ai/assistant/flows/large-task-orchestration.flow.md`
- `.ai/assistant/templates/large-task-operation-packet.md`

Load only the active workstream context, changed-fact owners, and
dependencies. Record checkpoints and one global convergence review. Do not
create a packet for a small task.

## Task-Scale Overlay: `delegated-execution`

Activate only when `subagent-delegation` is enabled, the primary critical-path
action is already selected, and an independently useful packet has local
acceptance criteria plus disjoint writes or read-only scope. Required context:

- `.ai/framework/subagent-delegation.md`
- `.ai/assistant/delegation-policy.json`
- `.ai/assistant/flows/subagent-delegation.flow.md`
- `.ai/assistant/templates/subagent-task-packet.md`
- `.ai/assistant/assistant-capabilities.json`

Load only the selected assistant capability record and packet context. Keep
project decisions, approval, integration, and final convergence with the
primary assistant. Fall back when capability evidence is unsupported, stale,
or unverifiable, or when coordination overhead exceeds expected benefit.

## Task-Scale Overlay: `change-package`

Activate only for a coherent material outcome, semantic multi-surface
approval, architecture segment or capability, audit, pilot, or publishable
before-to-after evidence. Required context:

- `.ai/framework/change-packages.md`
- `.ai/assistant/change-packages/index.json`
- `.ai/assistant/flows/change-package.flow.md`

Load the package record template, human report, plan, discussion, companion,
correction, or validation detail only when the current phase needs it. Compose
with `large-or-resumable` only when both gates pass. Do not create a package
for an ordinary local task.

## Task-Scale Overlay: `engineering-evidence`

Apply lazily at finalization for material semantic, architectural, or
non-obvious repair work when reusable knowledge may be lost, or for an
explicit evidence lookup/capture request. Required context:

- `.ai/framework/engineering-evidence.md`
- `.ai/assistant/gates/engineering-evidence.md`
- `.ai/project/engineering-evidence/index.json`

Load the capture flow and machine template only for an authorized write or
repair. Load only the selected historical record for lookup. A small
self-explanatory task may skip with a specific reason; capture does not
activate a change package and raw session reasoning is never evidence input.

## Task-Scale Overlay: `debug-mode`

Activate only after an explicit current-task or current-session user request
when the optional `debug-mode` module is enabled. Required compact context:

- `.ai/framework/debug-mode.md`
- `.ai/assistant/flows/debug-mode.flow.md`
- `.ai/assistant/gates/debug-mode.md`
- `.ai/project/debug/index.json`

Load the active record, record template, or summary template only for the
current checkpoint, finalization, selected lookup, or comparison. Capture
material normalized events rather than transcript detail. Debug activation
does not authorize engineering changes, commits, publication, live actions,
or protected work, and it expires when the logical scope completes or changes.
At finalization, load `.ai/project/source-of-truth-registry.md` only when a
skip claims canonical preservation, and load only the exact validation owner
needed to classify reproducer fidelity.

## Task-Scale Overlay: `team-active`

Activate only for team status, task start/claim/release, concurrent-work
conflict review, checkpoint, handoff, team decision, review, or merge
readiness. Load `.ai/assistant/team/context-overlay.json`, then its required
context:

- `.ai/framework/team-collaboration.md`
- `.ai/project/team-operating-model.md`
- `.ai/assistant/team/work-registry.json`
- `.ai/assistant/gates/team-collaboration.md`
- only the selected team flow

Load only the selected task projection, possibly overlapping active tasks,
changed-fact owners, dependencies, current checkpoint, and handoff. Do not load
all team history. Compose with `large-or-resumable` only when both activation
gates apply.

## Optional Consistency Relationship Routing

When the `consistency-map` module is enabled and a semantic fact changes or
drift is suspected, load:

- `.ai/project/source-of-truth-registry.md`
- `.ai/project/consistency-map.json`

Resolve changed fact IDs, follow applicable direct edges, and expand to
dependent contracts only for propagation, conflicts, failed validation, or
approval boundaries. Load `.ai/framework/consistency-model.md` only when
relationship semantics are disputed, adapter repair is required, or registry
and map evidence conflict. Record selected and skipped edges with reasons.

## Profile: `docs-local`

Use when: local wording, README, or non-semantic documentation changes do not
alter accepted project behavior.

Operation candidates: `documentation-sync`, `drift-review`,
`logical-integrity-review`, `support-generation` when enabled.

Load `.ai/framework/support-information.md` only when support diff, generation
ownership, or relationship-candidate semantics are disputed.

Required context:

- `.ai/framework/context-discovery.md`
- `.ai/assistant/gates/core.md`
- `.ai/assistant/gates/documentation.md`
- `.ai/assistant/gates/final-evidence.md`
- `{TARGET_DOC_SOURCE_OF_TRUTH}`

For a diagram request or diagram-relevant change, load
`.ai/framework/diagram-guidance.md` through the selected diagram flow rather
than for every documentation task.

Approval gates: only if docs change accepted behavior, security posture,
public contract, or approval rules.

Validation/evidence: report changed docs, owner file, skipped checks, and why
no logical integrity expansion was needed.

## Profile: `code-local`

Use when: implementation, tests, review comments, or defect fixes change
without changing accepted behavior, architecture, data model, external
contract, security posture, or AI infrastructure.

Operation candidates: `logical-integrity-review`, `drift-review`,
`product-change`, `test-first-change`, `support-generation` when enabled.

Load `.ai/framework/support-information.md` only for support-state, bounded
impact, candidate, or generation-contract ambiguity.

Required context:

- `.ai/framework/change-risk-model.md`
- `.ai/framework/logical-integrity.md`
- `.ai/assistant/gates/core.md`
- `.ai/assistant/gates/code-and-tests.md`
- `.ai/assistant/gates/final-evidence.md`
- `{TARGET_CODE_SOURCE_OF_TRUTH}`

Load general testing guidance only when test selection, isolation, or boundary
validation is unfamiliar or disputed. Add semantic-integrity or security-
approval gate fragments only when the repair reaches those boundaries.

Approval gates: only if the task crosses a protected category.

Validation/evidence: run or report `{TARGET_CODE_VALIDATION}`, re-derive
invariants, reconcile related review items, and explain doc sync or why none
was needed.

## Profile: `business-change`

Use when: accepted behavior, domain rules, product policy, workflows, or public
contract change.

Operation candidates: `architecture-assistance`, `product-change`,
`create-project-blueprint`, `logical-integrity-review`, `test-first-change`
when enabled.

Required context:

- `.ai/framework/context-discovery.md`
- `.ai/framework/change-risk-model.md`
- `.ai/framework/source-of-truth-registry.md`
- `.ai/framework/logical-integrity.md`
- `.ai/assistant/gates/core.md`
- `.ai/assistant/gates/semantic-integrity.md`
- `.ai/assistant/gates/final-evidence.md`
- `{TARGET_BLUEPRINT_OR_PRODUCT_SOURCE_OF_TRUTH}`

Load blueprint, approval, testing, product-flow, security gate, or complete
checklist context only when the accepted decision enters that stage or crosses
that boundary.

Approval gates: explicit programmer approval before changing accepted business
behavior.

Validation/evidence: changed fact, owning blueprint or source of truth,
re-derived invariants, review-item reconciliation, implementation/test/doc
sync, diagram sync if applicable, machine-readable approval-scope result, and
final logical integrity result.

## Profile: `architecture-change`

Use when: modules, dependencies, boundaries, runtime topology, public APIs, or
cross-component contracts change.

Operation candidates: `product-change`, `create-project-blueprint`,
`logical-integrity-review`, `test-first-change` when enabled.

Required context:

- `.ai/framework/context-discovery.md`
- `.ai/framework/change-risk-model.md`
- `.ai/framework/source-of-truth-registry.md`
- `.ai/framework/logical-integrity.md`
- `.ai/assistant/gates/core.md`
- `.ai/assistant/gates/semantic-integrity.md`
- `.ai/assistant/gates/final-evidence.md`
- `{TARGET_ARCHITECTURE_SOURCE_OF_TRUTH}`

Load blueprint, approval, security, testing, product-flow, security gate, or
complete checklist context only when the accepted decision enters that stage
or crosses that boundary.

Load `.ai/framework/diagram-guidance.md` when diagram discussion or a
diagram-relevant architecture change is selected.

Approval gates: explicit programmer approval for architecture changes and new
production dependencies or services.

Validation/evidence: architecture owner update, affected areas, re-derived
invariants, review-item reconciliation, validation, diagrams or why none
changed, machine-readable approval-scope result, and residual risk.

## Profile: `data-change`

Use when: schema, persistence, migrations, data contracts, retention,
backfills, imports, exports, or data ownership change.

Operation candidates: `product-change`, `logical-integrity-review`,
`drift-review`, `test-first-change` when enabled.

Required context:

- `.ai/framework/context-discovery.md`
- `.ai/framework/change-risk-model.md`
- `.ai/framework/source-of-truth-registry.md`
- `.ai/framework/logical-integrity.md`
- `.ai/assistant/gates/core.md`
- `.ai/assistant/gates/semantic-integrity.md`
- `.ai/assistant/gates/code-and-tests.md`
- `.ai/assistant/gates/final-evidence.md`
- `{TARGET_DATA_SOURCE_OF_TRUTH}`

Load context-discovery, security, testing, security-approval, or complete-
checklist context only when source selection, migration, privacy, destructive,
live, or audit boundaries require it.

Approval gates: explicit approval for destructive, data-loss, live-service,
privacy, or migration-risk changes.

Validation/evidence: canonical data owner, derived surfaces, migration or
rollback notes where applicable, scope/identity/persistence invariants,
observable external failure distinctions, validation, and unresolved risk.

## Profile: `security-sensitive`

Use when: secrets, credentials, permissions, authentication, authorization,
network access, external services, destructive actions, spend, production, or
third-party trust boundaries are involved.

Operation candidates: `product-change`, `logical-integrity-review`,
`skill-adaptation`, `test-first-change` when enabled.

Required context:

- `.ai/framework/security-safety-guidance.md`
- `.ai/framework/logical-integrity.md`
- `.ai/framework/approval-records.md`
- `.ai/assistant/policies/prompt-injection.md`
- `.ai/assistant/gates/core.md`
- `.ai/assistant/gates/semantic-integrity.md`
- `.ai/assistant/gates/security-approval.md`
- `.ai/assistant/gates/final-evidence.md`
- `{TARGET_SECURITY_SOURCE_OF_TRUTH}`

Load the full change-risk owner only when classification or escalation
semantics are disputed; the routed security gate carries the routine compact
obligation.

Approval gates: explicit approval before protected changes; use approval
records when scope or plan evidence matters.

Validation/evidence: security owner evidence, actions avoided, approvals,
validation, skipped checks, and residual risk.

## Profile: `ai-infrastructure`

Use when: inventorying or recommending additions and existing-item
improvements, or adding, importing, adapting, replacing, or reviewing prompts,
skills, assistant rules, wrappers, bridge files, MCP/tool configs, checkers,
gates, flows, templates, or other AI infrastructure.

Operation candidates: `ai-infrastructure-inventory`,
`ai-infrastructure-recommendation`, `skill-adaptation`,
`extension-management`.

Required context:

- `.ai/framework/ai-infrastructure-routing.md`
- `.ai/assistant/ai-infrastructure-router.json`
- `.ai/assistant/gates/core.md`
- `.ai/assistant/gates/final-evidence.md`

Select one AI infrastructure route and item ID before loading additional
skill, prompt, gate, checker, tool/MCP, bridge, source-access,
prompt-injection, approval, permission, validation, or output-contract context.
Load `.ai/assistant/gates/security-approval.md` for source import, permission
change, live/destructive capability, credential access, protected integration,
or weakened governance; read-only inventory and recommendation do not load it.
For `recommend`, load only the bounded project area, its owner, relevant
inventory/items, `.ai/project/development-evidence.json`, and
`.ai/framework/ai-infrastructure-recommendations.md`. Inspect only evidence
referenced by selected patterns. Project facts justify the need;
recommendation and item mechanics remain assistant-contour owned.
For `extension-management`, start from the compact extension catalog and load
only one selected lock/manifest/binding set. Package review, compatibility,
ownership, update, and removal follow `.ai/framework/extensions.md`.

Approval gates: explicit approval before importing third-party infrastructure
into canonical target files or changing tool permissions.

Validation/evidence: selected route; inventory; project-contour basis,
existing-item comparison, quality/context/maintenance cost and acceptance
criteria for recommendation; or provenance, normalized target surfaces,
compatibility review, and approval evidence for adaptation.

## Profile: `framework-upgrade`

Use when: installing Alatyr, updating Alatyr Core, rechecking the adapter,
reviewing maturity, or repairing drift after framework changes.

Operation candidates: `adapter-health`, `recheck-after-framework-update`,
`recheck-after-installation`, `adapter-maturity-review`,
`support-generation`, and `extension-management` when the corresponding
optional module or installed extension compatibility is in scope.

Load `.ai/framework/support-information.md` when the migration impact selects
support policy, state, relationship, or generation contracts.

Required context:

- `.ai/assistant/context/migration-routing.json`
- `{TARGET_UPGRADE_IMPACT_REPORT}`
- `.ai/assistant/gates/core.md`
- `.ai/assistant/gates/final-evidence.md`

Generate or review the migration assessment before loading lifecycle, rule,
flow, or note files. Then load only canonical framework sources and target
adapter surfaces named by `upgrade-impact.json`, changed rule IDs, affected
categories/profiles, template changes, bridge capability changes, enabled
modules, or local-deviation conflicts. Record intentionally omitted candidate
context in the context receipt.

Candidate framework context, loaded only when selected by migration impact:

- `.ai/framework/README.md`
- `.ai/framework/adapter-maturity.md`
- `.ai/framework/bridge-capability-matrix.md`
- `.ai/framework/blueprint-driven-change.md`
- `.ai/framework/context-profiles.md`
- `.ai/framework/context-router.md`
- `.ai/framework/contour.md`
- `.ai/framework/effectiveness-metrics.md`
- `.ai/framework/guarantees.md`
- `.ai/framework/installed-operations.md`
- `.ai/framework/lifecycle.md`
- `.ai/framework/migration-diff.md`
- `.ai/framework/module-profile.md`
- `.ai/framework/operation-help.md`
- `.ai/framework/portability.md`
- `.ai/framework/project-adapter-contract.md`
- `.ai/framework/prompt-injection.md`
- `.ai/framework/rule-ownership.md`
- `.ai/framework/rule-registry.json`
- `.ai/framework/rule-registry.md`
- `.ai/framework/scaffolding.md`
- `.ai/framework/skill-adaptation.md`

Approval gates: approval before overwriting existing instructions, changing
protected adapter behavior, or adopting third-party assistant infrastructure.

Validation/evidence: adapter version/schema state, changed framework baseline,
affected target files, gaps, local deviations, validation, and migration
actions.
