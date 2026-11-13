# Alatyr Context Profiles

Use this file to choose the smallest sufficient context for `{PROJECT_NAME}`.
Replace placeholders with target evidence before accepting installation.

The machine router is canonical for the selected support profile and framework
pack. Paths absent from the installed pack are expansion candidates, not
required context; expand and revalidate the pack before enabling them.

`AGENTS.md` is host-preloaded context and should not be reread. Compact
bootstrap context for every task is only:

- `.ai/assistant/bootstrap-index.json`

The generated bootstrap embeds the required core semantic definitions. Its
lazy integrity record binds it to `.ai/alatyr.yaml`, `.ai/README.md`,
`.ai/assistant/context-router.json`, the installed semantic-codebook index, and
the rule registry without adding those hashes to routine model context.

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
Load `.ai/framework/task-decomposition.md` only when non-trivial task splitting,
implementation levels, dependency ordering, or executor selection is ambiguous
or the target task-decomposition policy needs repair. Routine routing uses
`.ai/assistant/task-decomposition.json`.

## Recursive Selection And Semantic Terms

Local observations: direct source reads; see
`.ai/framework/context-profiles.md#read-only-project-questions`.

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

For non-trivial work that crosses a machine-router receipt trigger,
materialize the selected indexes, item IDs/paths/digests/reasons, resolved term definitions,
word totals, and deterministic packet digest with
`.ai/assistant/templates/context-packet.json`.

For compaction, resume, fork, handoff, client/model change, or suspected
context loss, compose the lightweight `session-continuity` overlay. Load its
canonical owner `.ai/framework/session-continuity.md` only when the compact
contract is missing, stale, or conflicting. Small tasks may use an in-memory
or host-native checkpoint; they do not require a large-task packet. Before
state-changing continuation, verify current state and reapply authorization
from the newest user instruction.

Use each profile's operation candidates from the machine-readable router for
cheap automatic routing. Resolve an exact operation ID or alias through
`.ai/assistant/operation-index.json`. Load the full
`.ai/assistant/operation-catalog.json` only for the bare `Alatyr` entry,
ambiguity, or operation/adapter repair.

Use file, word, character, portable and reserved-target budgets. Character limits
protect dense data, not provider billing. Resolve/measure target-owned paths
before acceptance. Required safety/owner expansion records profiles, areas,
paths/reasons, volume, triggers, omissions and risk; estimates are not telemetry.

The profile-default budget is the compact route. An expansion receipt may
cross that budget, but the composed end-to-end route, including bootstrap,
must remain inside `context_budgets.expanded`. If it cannot, split the task or
stop for an explicit context decision instead of silently loading more files.

### Optional Working Sets

When the selected planner supports working-set requests, classify information
need and delivery phase. Preserve mandatory owners/gates; only optional
candidates compete for remaining budget. Exhaustive review retains every indexed
item in named contours or blocks for decomposition, never top-k truncation.
Use compact plan output for navigation, full reports for detail, and verified
identity deltas at phase boundaries. Keep current obligations in existing task
projections. Missing delivery/token evidence remains unknown; summaries and
phase labels grant no approval or host context eviction.

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

Load `.ai/framework/repair-qualification.md` and its schema-2 authoring template
only for explicit adoption or selected qualified incident evidence. Schema-1
and ordinary test-first work keep those details conditional.
Load `.ai/framework/test-execution-selection.md` only for adopted execution-
contract-3 selection/timing controls or a named conflict; ordinary and legacy
execution keep this detail conditional.

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

## Task Classification

Classify task scale after compact bootstrap and before loading broad profile
prose, full help, full gate checklist, large-task packets, change packages,
Debug Mode records, or team history.

Canonical class IDs and exact criteria are owned by
`.ai/framework/task-classes.json`. The router contains a checked execution
projection of that registry; do not maintain another prose definition here.

Ambiguity stays read-only. Select the smallest plausible class for inspection,
ask for the missing fact, and do not edit until the current action phase is
authorized.

The `small-task` class uses the `small-task` overlay only for compact evidence
and explicit skip reasons. Stop using it and reclassify if semantic facts,
source-of-truth ownership, approval, safety, data, architecture, public
contract, live-external, multi-area, failed-validation, or broad-audit
triggers appear.

## Task-Scale Overlay: `small-task`

Activate only when task classification selects `small-task`. Required compact
context:

- `.ai/assistant/gates/core.md`
- `.ai/assistant/gates/final-evidence.md`

Reuse the selected base profile and directly linked owner evidence. Do not
load package, large-task, debug, team, full-help, or full-checklist surfaces.
Record compact small-task evidence or a short final skip reason. If an
expansion trigger fires, stop and route through the broader selected profile
or overlay.

## Task-Scale Overlay: `large-or-resumable`

Activate only for large, cross-boundary, multi-workstream,
budget-exceeding, or resumable work. Required context:

- `.ai/framework/large-task-orchestration.md`
- `.ai/assistant/flows/large-task-orchestration.flow.md`
- `.ai/assistant/templates/large-task-operation-packet.md`

Load `.ai/framework/task-state-delivery.md` only for adopted execution dependencies
or reconciliation of named-task current disposition with historical reports.

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

## Profile Explanations

Canonical rules: `.ai/framework/rule-registry.json`; navigation:
`.ai/framework/context-index.json`.

The selected profile descriptor owns operations, required and conditional context,
expansion, approvals, validation and evidence. These explanations add no bootstrap
requirements. Use installed, enabled capabilities only. Resolve missing or
conflicting evidence instead of loading every profile. Preserve the target
bindings below and reconcile them with the descriptor.

For changed facts, re-derive invariants, reconcile related review items and
synchronize code, tests, documentation and diagrams. Record the Project Contour
Sync Decision, applicable approval-scope and logical integrity results through
the selected task-scale gate. Report validation, skipped checks and residual risk.
Load support-information policy for selected support-impact contracts or disputed
state, ownership, relationship-candidate or generation semantics.

## Profile: `docs-local`

[Descriptor](context/profiles/docs-local.json). Non-behavioral documentation.
Owner: `{TARGET_DOC_SOURCE_OF_TRUTH}`. Report changed docs, ownership and why
semantic expansion was unnecessary. Escalate for accepted behavior, security,
public contracts or approvals. Diagram guidance comes through the selected flow.
For runtime acceptance, recurrence contradictions or a selected observation gate,
inspect compact evidence first. Full runtime guidance and raw logs remain
conditional on a boundary, failure, contradiction, unknown event, dispute or
explicit review.

## Profile: `code-local`

[Descriptor](context/profiles/code-local.json). Implementation, tests or repairs
without changed accepted behavior, architecture, data models, external contracts,
security posture or AI infrastructure. Owner: `{TARGET_CODE_SOURCE_OF_TRUTH}`.
Validation: `{TARGET_CODE_VALIDATION}`. Reconcile validation with the descriptor.
Load general testing guidance for unfamiliar or disputed selection, isolation or
boundary validation. Integrity and security context remain boundary-specific;
protected changes retain approval.

## Profile: `business-change`

[Descriptor](context/profiles/business-change.json). Accepted behavior, business
rules, product policy, workflows or public contracts.
Owner: `{TARGET_BLUEPRINT_OR_PRODUCT_SOURCE_OF_TRUTH}`. Explicit programmer
approval precedes business-behavior changes. Identify the changed fact and owner;
expand blueprint, testing, approval, product-flow, security or checklist guidance
at the applicable stage.

## Profile: `architecture-change`

[Descriptor](context/profiles/architecture-change.json). Modules, dependencies,
boundaries, topology, APIs or cross-component contracts.
Owner: `{TARGET_ARCHITECTURE_SOURCE_OF_TRUTH}`. Architecture changes and new
production dependencies/services require explicit programmer approval. Update
the owner and affected areas. Load stage-specific guidance, including diagrams
when relevant; report diagram updates or why none were needed.

## Profile: `data-change`

[Descriptor](context/profiles/data-change.json). Schema, persistence, migration,
data contracts, retention, backfills, imports/exports or ownership.
Owner: `{TARGET_DATA_SOURCE_OF_TRUTH}`. Destructive, data-loss, live-service,
privacy and migration-risk changes require approval. Review ownership, derived
surfaces, scope/identity/persistence invariants, observable external failures and
migration/rollback notes. Expand other guidance only for the boundary reached.

## Profile: `security-sensitive`

[Descriptor](context/profiles/security-sensitive.json). Credentials, permissions,
authentication/authorization, networks, external services, destructive actions,
spend, production or third-party trust.
Owner: `{TARGET_SECURITY_SOURCE_OF_TRUTH}`. Approve protected changes and bind
scope/plan evidence when applicable. Report ownership, approvals and actions
avoided. Use the compact gate; load full risk guidance for classification disputes
or escalation.

## Profile: `ai-infrastructure`

[Descriptor](context/profiles/ai-infrastructure.json). Inventory, recommendation,
improvement, adaptation or review of skills, prompts, rules, wrappers, bridges,
MCP/tools, checkers, gates, flows, templates or extensions. Select one route/item
through `.ai/assistant/ai-infrastructure-router.json`.

Use bounded project evidence, owners, relevant inventory and selected patterns.
Recommendations record need, existing-item comparison, quality/context/maintenance
cost and acceptance criteria. Adaptation records provenance, normalized surfaces,
compatibility and approval. Extensions select one catalog/lock/manifest/binding
set. Security context applies to imports, permission changes, live/destructive
capability, credentials, protected integration or weakened governance, not routine
read-only inventory. Third-party canonical imports and tool-permission changes
require explicit approval.

## Profile: `framework-upgrade`

[Descriptor](context/profiles/framework-upgrade.json). Installation, update,
recheck, maturity or drift repair. Evidence: `{TARGET_UPGRADE_IMPACT_REPORT}`.
Start with `.ai/assistant/context/migration-routing.json` and the assessment.
Select owners and surfaces through `upgrade-impact.json`, changed rules,
affected categories/profiles, templates, bridges, enabled modules or deviation
conflicts. Record omitted candidates with reasons; never preload the candidate
corpus. Approve instruction overwrites, protected changes and imported assistant
infrastructure. Report versions, baseline, affected files, gaps, deviations,
validation and migration actions.
