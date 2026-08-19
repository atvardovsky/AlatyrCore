# Alatyr Context Profiles

Use this file to choose the smallest sufficient context for `{PROJECT_NAME}`.
Replace placeholders with target evidence before accepting installation.

The machine router is canonical for the selected support profile and framework
pack. Paths absent from the installed pack are expansion candidates, not
required context; expand and revalidate the pack before enabling them.

`AGENTS.md` is host-preloaded context and should not be reread. Compact
bootstrap context for every task is:

- `.ai/alatyr.yaml`
- `.ai/README.md`
- `.ai/assistant/context-router.json`

After bootstrap, choose one profile and affected project-area overlays before
editing files. This file is the human rationale surface; load it only when
routing is ambiguous, the router conflicts with evidence, or an entry must be
repaired. Expand only when boundaries, conflicts, approval scope, or changed
fact ownership require it.

Load the selected profile descriptor from
`.ai/assistant/context/profiles/`. Intent, migration, consistency, and
task-scale descriptors under `.ai/assistant/context/` compose only when their
trigger applies. Do not load all descriptors to classify one task.

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

## Task-Scale Overlay: `large-or-resumable`

Activate only for large, cross-boundary, multi-workstream,
budget-exceeding, or resumable work. Required context:

- `.ai/framework/large-task-orchestration.md`
- `.ai/assistant/flows/large-task-orchestration.flow.md`
- `.ai/assistant/templates/large-task-operation-packet.md`

Load only the active workstream context, changed-fact owners, and
dependencies. Record checkpoints and one global convergence review. Do not
create a packet for a small task.

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

- `.ai/framework/consistency-model.md`
- `.ai/project/consistency-map.json`

Resolve changed fact IDs, follow applicable direct edges, and expand to
dependent contracts only for propagation, conflicts, failed validation, or
approval boundaries. Record selected and skipped edges with reasons.

## Profile: `docs-local`

Use when: local wording, README, or non-semantic documentation changes do not
alter accepted project behavior.

Operation candidates: `documentation-sync`, `drift-review`,
`logical-integrity-review`.

Required context:

- `.ai/framework/context-discovery.md`
- `.ai/framework/testing-guidance.md`
- `.ai/assistant/gates/checklist.md`
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
`product-change`, `test-first-change` when enabled.

Required context:

- `.ai/framework/context-discovery.md`
- `.ai/framework/change-risk-model.md`
- `.ai/framework/testing-guidance.md`
- `.ai/framework/logical-integrity.md`
- `.ai/assistant/gates/checklist.md`
- `{TARGET_CODE_SOURCE_OF_TRUTH}`

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
- `.ai/framework/blueprint-driven-change.md`
- `.ai/framework/approval-records.md`
- `.ai/framework/testing-guidance.md`
- `.ai/assistant/flows/blueprint-driven-change.flow.md`
- `.ai/assistant/gates/checklist.md`
- `{TARGET_BLUEPRINT_OR_PRODUCT_SOURCE_OF_TRUTH}`

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
- `.ai/framework/blueprint-driven-change.md`
- `.ai/framework/approval-records.md`
- `.ai/framework/security-safety-guidance.md`
- `.ai/framework/testing-guidance.md`
- `.ai/assistant/flows/blueprint-driven-change.flow.md`
- `.ai/assistant/gates/checklist.md`
- `{TARGET_ARCHITECTURE_SOURCE_OF_TRUTH}`

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
- `.ai/framework/security-safety-guidance.md`
- `.ai/framework/testing-guidance.md`
- `.ai/assistant/gates/checklist.md`
- `{TARGET_DATA_SOURCE_OF_TRUTH}`

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

- `.ai/framework/change-risk-model.md`
- `.ai/framework/security-safety-guidance.md`
- `.ai/framework/logical-integrity.md`
- `.ai/framework/approval-records.md`
- `.ai/assistant/policies/prompt-injection.md`
- `.ai/assistant/gates/checklist.md`
- `{TARGET_SECURITY_SOURCE_OF_TRUTH}`

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
- `.ai/assistant/gates/checklist.md`

Select one AI infrastructure route and item ID before loading additional
skill, prompt, gate, checker, tool/MCP, bridge, source-access,
prompt-injection, approval, permission, validation, or output-contract context.
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
`extension-management` when installed extension compatibility or drift is in
scope.

Required context:

- `.ai/framework/lifecycle.md`
- `.ai/framework/migration-diff.md`
- `.ai/framework/rule-registry.json`
- `.ai/assistant/flows/adapter-recheck.flow.md`
- `.ai/assistant/templates/installation-note.md`
- `.ai/assistant/templates/migration-note.md`

Run or review the migration assessment before loading more framework files.
Then load only canonical framework sources and target adapter surfaces named by
changed rule IDs, affected categories/profiles, template changes, bridge
capability changes, or local-deviation conflicts. Record intentionally omitted
candidate context in the context receipt.

Candidate framework context, loaded only when selected by migration impact:

- `.ai/framework/README.md`
- `.ai/framework/adapter-maturity.md`
- `.ai/framework/bridge-capability-matrix.md`
- `.ai/framework/context-profiles.md`
- `.ai/framework/context-router.md`
- `.ai/framework/contour.md`
- `.ai/framework/effectiveness-metrics.md`
- `.ai/framework/guarantees.md`
- `.ai/framework/installed-operations.md`
- `.ai/framework/module-profile.md`
- `.ai/framework/operation-help.md`
- `.ai/framework/portability.md`
- `.ai/framework/project-adapter-contract.md`
- `.ai/framework/prompt-injection.md`
- `.ai/framework/rule-ownership.md`
- `.ai/framework/rule-registry.md`
- `.ai/framework/scaffolding.md`
- `.ai/framework/skill-adaptation.md`

Approval gates: approval before overwriting existing instructions, changing
protected adapter behavior, or adopting third-party assistant infrastructure.

Validation/evidence: adapter version/schema state, changed framework baseline,
affected target files, gaps, local deviations, validation, and migration
actions.
