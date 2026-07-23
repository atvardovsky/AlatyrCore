# Alatyr Context Profiles

Use this file to choose the smallest sufficient context for `{PROJECT_NAME}`.
Replace placeholders with target evidence before accepting installation.

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

Use each profile's operation candidates from the machine-readable router for
cheap automatic routing. Load `.ai/assistant/operation-catalog.json` only for
the explicit `Alatyr` entry, status, ambiguity, operation handoff, or adapter
repair.

Use the router's context budgets. When sufficient context exceeds a budget,
record selected profiles and areas, loaded files and reasons, approximate
volume, expansion triggers, intentional omissions, and residual risk in the
context receipt.

## Project-Area Overlays

Define target areas such as modules, services, packages, bounded contexts, or
documentation domains in `.ai/assistant/context-router.json`. Each area should
name its trigger, required context, and expansion conditions. Compose the base
task profile with only areas that own changed facts.

## Task-Scale Overlay: `large-or-resumable`

Activate only for large, cross-boundary, multi-workstream,
budget-exceeding, or resumable work. Required context:

- `.ai/framework/large-task-orchestration.md`
- `.ai/assistant/flows/large-task-orchestration.flow.md`
- `.ai/assistant/templates/large-task-operation-packet.md`

Load only the active workstream context, changed-fact owners, and
dependencies. Record checkpoints and one global convergence review. Do not
create a packet for a small task.

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

Use when: local wording, README, diagram text, or non-semantic documentation
changes do not alter accepted project behavior.

Operation candidates: `documentation-sync`, `drift-review`,
`logical-integrity-review`.

Required context:

- `.ai/framework/context-discovery.md`
- `.ai/framework/testing-guidance.md`
- `.ai/framework/diagram-guidance.md`
- `.ai/assistant/gates/checklist.md`
- `{TARGET_DOC_SOURCE_OF_TRUTH}`

Approval gates: only if docs change accepted behavior, security posture,
public contract, or approval rules.

Validation/evidence: report changed docs, owner file, skipped checks, and why
no logical integrity expansion was needed.

## Profile: `code-local`

Use when: implementation, tests, review comments, or defect fixes change
without changing accepted behavior, architecture, data model, external
contract, security posture, or AI infrastructure.

Operation candidates: `logical-integrity-review`, `drift-review`,
`product-change`.

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

Operation candidates: `product-change`, `create-project-blueprint`,
`logical-integrity-review`.

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
`logical-integrity-review`.

Required context:

- `.ai/framework/context-discovery.md`
- `.ai/framework/change-risk-model.md`
- `.ai/framework/source-of-truth-registry.md`
- `.ai/framework/logical-integrity.md`
- `.ai/framework/blueprint-driven-change.md`
- `.ai/framework/approval-records.md`
- `.ai/framework/security-safety-guidance.md`
- `.ai/framework/testing-guidance.md`
- `.ai/framework/diagram-guidance.md`
- `.ai/assistant/flows/blueprint-driven-change.flow.md`
- `.ai/assistant/gates/checklist.md`
- `{TARGET_ARCHITECTURE_SOURCE_OF_TRUTH}`

Approval gates: explicit programmer approval for architecture changes and new
production dependencies or services.

Validation/evidence: architecture owner update, affected areas, re-derived
invariants, review-item reconciliation, validation, diagrams or why none
changed, machine-readable approval-scope result, and residual risk.

## Profile: `data-change`

Use when: schema, persistence, migrations, data contracts, retention,
backfills, imports, exports, or data ownership change.

Operation candidates: `product-change`, `logical-integrity-review`,
`drift-review`.

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
`skill-adaptation`.

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
`ai-infrastructure-recommendation`, `skill-adaptation`.

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
`recheck-after-installation`, `adapter-maturity-review`.

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
