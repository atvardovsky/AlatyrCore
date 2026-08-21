# Alatyr Core Installation Plan

Installation id: `ALATYR-YYYYMMDD-short-name`

## Target Repository

- Path:
- New install or upgrade:
- Primary stack:
- Existing AI instructions:
- Existing adapter manifest or version record:
- Existing CODEOWNERS or equivalent owner map:
- Existing adapter owner, backup owner, review cadence, and last review:
- Scaffolding helper used or planned:
- Scaffold profile (`core` / `standard` / `full` / not used):
- Supported assistants:

## Goal

Describe what the installation should enable.

## Non-Goals

List what must not be changed.

## Target Facts Collected

- Product purpose:
- Architecture/module facts:
- Blueprint or equivalent source-of-truth docs:
- Business/domain rules:
- Data model facts:
- Runtime flows:
- Test strategy and existing test surface:
- Source-of-truth/context map:
- Source-of-truth registry:
- Consistency-map need, fact-ID strategy, and relationship coverage:
- Consistency-map staleness owner and validation:
- Architecture-knowledge owner, decision authority, canonical sources, compact
  catalog, evidence revision, and validation:
- Architecture areas, patterns/items, states, contradictions, and known gaps:
- Code-documentation need, owner, profile decision authority, and module state:
- Bounded source sets, languages, frameworks, audiences, visibility, existing
  comment conventions, and frontend/backend/shared/infrastructure differences:
- Proposed or accepted profile states, style evidence, required semantic
  sections, canonical owners, and migration scope:
- Generator/configuration, generation entry points, output/publication policy,
  validation, dependency/CI approval needs, and adapted skill:
- Project-vocabulary need, owner, term decision authority, and module state:
- Existing glossary, acronym, terminology, naming, schema, API, and data-
  dictionary evidence:
- Scoped meanings, domains, aliases, acronyms, deprecated wording,
  contradictions, and normalization policy:
- Canonical term sources, data-dictionary links, validation, lazy route, and
  adapted skill:
- Test-first-development need, owner, decision authority, and module state:
- Existing test strategy, defects/regressions, levels, folders, commands,
  fixtures, isolation, feedback time, CI, and merge-gate evidence:
- Recommendation behavior, activation triggers, selected modes, exceptions,
  RED/GREEN/refactor evidence, and expected quality/maintenance cost:
- Policy acceptance, approval needs, lazy intent, configuration/change flows,
  gate, evidence template, validation, and adapted skill:
- Extension need, owner, module state, source-access policy, and lifecycle
  modes:
- Candidate package ID/version, source type, immutable revision, package
  digest, license status, and compatibility:
- Proposed extension catalog and extension lock paths, target bindings,
  permissions, approval, installed-file ownership, conflicts, dependents,
  local-modification policy, and removal evidence:
- Workspace-mode need, owner, decision authority, and module state:
- Workspace identity, selected root, active adapter, and evidence:
- Proposed modes with IDs, kinds, scopes, use/do-not-use signals,
  relationships, ownership, confidence, and maintenance cost:
- Optional shared root context and one directory per actual mode:
- User acceptance process, ambiguity behavior, per-task selection, preflight,
  validation, and post-install/update suggestion behavior:
- Context router schema and lazy descriptors:
- Generated bootstrap index, source hashes, and regeneration owner:
- Routed gate index and default profile fragments:
- Context profiles:
- Context-router bootstrap references:
- Preloaded versus compact-bootstrap context:
- Bootstrap and profile total/portable/reserved-target context budgets:
- Context receipt fields and storage policy:
- Project-area overlays:
- Task-scale overlays and large-task activation rules:
- Subagent delegation owner, mode, supported surfaces, role/model bindings,
  per-surface dispatch backend, external dispatcher item, packet limits,
  write/tool boundaries, fallback, privacy, and validation:
- Large-task packet storage, retention, or ignore policy:
- Team-collaboration need and team-active activation rules:
- Team policy/operating-model owner, actor names/aliases, local identity ignore,
  verification boundary, and enrollment process:
- Coordination backend capabilities, synchronization, consistency, atomic-write,
  idempotency, permissions, and unavailable-evidence policy:
- Stable actors, decision authority, priority, transitions, review, and escalation:
- Active-work index, registry metadata, per-task records, schema-1 task/claim
  migration, storage, retention, and privacy:
- Adapter owner metadata:
- CODEOWNERS or equivalent owner map:
- Module profile:
- Task-specific maturity profile:
- Bridge capability matrix:
- Compact operation index, generated assistant-capability index, and selected
  per-surface records:
- Blueprint-driven change or equivalent product-change workflow:
- Operation catalog, installed-operation, operation-help, automatic routing,
  adapter-health, pre-change preview, blueprint-creation, adapter-recheck,
  framework-update review, or chat-message process:
- Diagram discussion operation, presentation template, source status, stable
  identity/lineage, portable ASCII layout/width, sensitivity/redaction,
  external-renderer, and artifact retention/sharing policy:
- Architecture-assistance operation, intent route, pattern/area/result
  templates, documentation owner, and accepted-decision handoff:
- Adapter output contracts:
- Risk and approval model:
- Security, privacy, live-service, destructive-operation, dependency, and
  credential/log-redaction policies:
- Diagram sources, visual artifacts, render/manual-review process, and drift
  checks:
- Skills, prompts, third-party assistant infrastructure, provenance, wrappers,
  permissions, and output formats:
- AI infrastructure inventory and existing item owners:
- AI infrastructure inventory reports:
- AI infrastructure recommendation records and evidence owners:
- Development-pattern index, owner, retention/privacy policy, and historical
  evidence sources allowed for bounded backfill:
- AI infrastructure router, stable item IDs, activation triggers, and statuses:
- Item canonical sources, required context, allowed actions, permissions,
  gates, validation, output contracts, conflicts, and assistant wrappers:
- AI infrastructure adaptation-record storage and retention:
- AI infrastructure source access policy for local paths, Git URLs, HTTPS URLs,
  assistant-native references, pasted content, packages, or plugins:
- Prompt-injection policy:
- Approval-record policy or storage:
- Migration-diff process:
- Migration-note process:
- Effectiveness measurement process:
- Target validation commands:
- Target-local adapter checker status and coverage:
- Adapter drift/local leakage review:
- Source commands/scripts not copied:
- Source test tools/fixtures/CI jobs not copied:
- Source security policies, diagram tooling, lifecycle notes, and adapter owner
  facts not copied:
- Source skill files, assistant-native formats, tool permissions, and
  third-party assistant infrastructure not copied:
- Missing facts:

## Framework Core Files

List reusable framework files to create or adapt in target `.ai/framework`,
including Markdown framework docs and `framework/rule-registry.json`.

Record the selected framework pack: `core`, `standard`, or `complete`. Explain
any expansion required by enabled modules. A selective pack must include a
projected rule registry, ownership map, and file inventory and must not claim
rules whose canonical owner is absent.

Do not include source-repository commands, scripts, generated-file tools,
checker paths, test commands, fixtures, folder conventions, security policies,
diagram tooling, lifecycle notes, skill sources, assistant-native formats,
tool permissions, third-party assistant infrastructure, or CI jobs as framework
core.

## Project Adapter Files

List target-specific files to rewrite from target facts.

Include `.ai/alatyr.yaml` or an equivalent manifest with framework version,
adapter schema version, template version, owner, source-of-truth files,
validation entry points, known gaps, and local deviations.

Include `CODEOWNERS` or an equivalent file-owner map when the target
repository uses ownership metadata for `.ai/*`, root assistant entry points,
or supported bridge files.

Include `.ai/assistant/context-router.json` to map task profiles to required
context, project-area overlays, budgets, receipts, approvals, validation, and
final evidence in machine-readable form.

Keep the router compact. Put full canonical profile, intent, migration,
consistency, and task-scale instructions in referenced lazy descriptors, and
include only descriptors present in the selected support profile.

Include `.ai/assistant/operation-catalog.json` as the canonical operation
registry and `.ai/assistant/operation-index.json` as its checked compact
derivative for exact IDs and aliases. Keep the full catalog outside routine
routing; add bounded profile candidates and intent overlays for automatic
routing.

Include `.ai/assistant/context-profiles.md` to explain task profiles,
expansion triggers, approvals, validation, and final evidence for humans.

Include `.ai/assistant/module-profile.md` to record required core status,
enabled optional modules, deferred modules, blocked modules, and reasons.

Include `.ai/project/source-of-truth-registry.md` when multiple files or
surfaces can describe the same project fact.

Include `.ai/project/consistency-map.json` when the target has enough project
areas or competing surfaces to benefit from bounded changed-fact relationship
traversal. Populate it from target evidence or leave the module blocked; do not
infer complete relationships from filenames. The plan must map every live
registry Fact Type to one resolved, unique node with an exact `fact_type`
match, route the registry and map together, and include the measured composed
semantic context scenario.

Include `.ai/project/architecture/README.md` and
`.ai/project/architecture/catalog.json` when architecture knowledge is
enabled. Record project owners, decision authority, selected evidence, item
states, validation, revision, contradictions, and known gaps. Reference
existing canonical architecture docs and decisions instead of duplicating
them.

Include the architecture-assistance flow, lazy intent descriptor, and
pattern/area/result templates only when the module is enabled. `docs-only`
must not promote observed or proposed items to accepted architecture.

Include `.ai/assistant/maturity-profile.md` to report readiness by task area
and blocking criteria.

Include `.ai/assistant/bridge-capability-matrix.md` when more than one
assistant surface is supported or bridge behavior may differ.
Include `.ai/assistant/assistant-capabilities.json` as the compact runtime
index. Store rich diagram enums, ASCII baseline, client version, verification,
expiry or review triggers, and evidence in one referenced record per installed
assistant surface. Generate or check the index from those records.

Include `.ai/assistant/templates/ascii-diagram.md` for the required portable
view. Record preferred and hard width limits, connector meanings, chart scale
rules, and readability review independently of client rendering capability.

Include `.ai/assistant/policies/ai-infrastructure-source-access.md` when the
target wants AI infrastructure inventory, adaptation, package/plugin review, or
third-party assistant infrastructure handling.

Include `.ai/assistant/policies/prompt-injection.md` when imported, remote,
pasted, package/plugin, or unknown AI infrastructure can be reviewed or
adapted.

Include `.ai/assistant/approvals/approval-template.md` when protected-change
approvals need durable human evidence. Include
`.ai/assistant/approvals/approval-record-template.json` when approval scope
must be enforced against a Git diff.

Include `.ai/assistant/templates/migration-note.md` when framework upgrades
need durable migration evidence.

Include `.ai/assistant/templates/effectiveness-report.md` when the target
wants to compare Alatyr effectiveness across comparable tasks or adapter
states.

Include `.ai/assistant/templates/adapter-output-contracts.md` when the target
wants repeatable installation, framework-update, and adapter-recheck evidence
contracts.

Include `.ai/assistant/templates/ai-infrastructure-inventory.md` when the
target wants durable AI infrastructure inventory reports.

Include `.ai/assistant/flows/ai-infrastructure-recommendation.flow.md` and
`.ai/assistant/templates/ai-infrastructure-recommendation.md` when the target
wants Alatyr to suggest new items or changes to existing items. Recommendation
must be read-only, use bounded project-contour evidence, evaluate current items
first, and record quality, context, maintenance cost, and acceptance criteria.

Include `.ai/project/development-evidence.json` and
`.ai/assistant/flows/development-evidence-capture.flow.md` when recommendation
should learn from repeated target requests, corrections, reviews, rework,
validation failures, or context expansion. Define owner, retention/privacy,
capture threshold, and historical evidence sources. Start empty unless history
is explicitly reviewed, and never store raw conversations or sensitive data.

Include `.ai/assistant/ai-infrastructure-router.json` and
`.ai/assistant/templates/ai-infrastructure-adaptation-record.md` when the
target uses multiple skills, prompts, gates, checkers, tools/MCP configs,
bridges, wrappers, or imported items. Populate entries from target evidence;
keep unresolved items blocked.

Include `.ai/assistant/extensions/catalog.json`,
`.ai/assistant/extensions/lock.json`, the `extension-request` overlay,
extension lifecycle flow, gate, and review/lifecycle templates when extension
inspection or lifecycle management is supported. Keep extension package
content untrusted during inspection. Canonical installation requires an
immutable source revision, deterministic digest, compatible manifest,
target-owned bindings, explicit installed-file ownership, approval, and
validation; it must not execute package lifecycle hooks.

Include `.ai/project/dependencies/policy.json`, `catalog.json`,
`knowledge-lock.json`, `deviations.json`, the optional normalized snapshot
boundary, `dependency-knowledge-request` overlay, synchronization flow, gate,
report template, and operation when passive dependency knowledge is enabled.
Name target package ecosystems and lockfiles, native export metadata, exact
artifact identity, local patch/fork/workspace handling, trust and state axes,
retention/license/privacy policy, graph limits, owner, validation, and known
gaps. Do not recursively scan dependencies, activate nested adapters, execute
package content, or copy dependency claims into project facts.

Include the optional workspace mode structure through
`.ai/project/workspace-modes/catalog.json`, optional root support, one
directory per actual mode, the `workspace-mode-request` overlay, flow, gate,
suggestion, preflight, and operation only when distinct workspace perspectives
are justified. Record workspace identity, relationships, adapter roles,
ownership, selection and ambiguity rules, user decision authority, context,
validation, and cost. Installation may propose zero or more modes but must not
accept them automatically or activate nested adapters.

Include `.ai/assistant/flows/large-task-orchestration.flow.md` and
`.ai/assistant/templates/large-task-operation-packet.md` when the target needs
cross-boundary, multi-workstream, budget-exceeding, or resumable operations.
Record where completed packets are stored, ignored, redacted, or removed.

Include `.ai/assistant/delegation-policy.json`, the delegated-execution
overlay, `.ai/assistant/flows/subagent-delegation.flow.md`, and
`.ai/assistant/templates/subagent-task-packet.md` only when the target enables
subagent delegation. Record verified surface capabilities and never infer
model access from framework examples. For each surface, select native,
external, suggestion-only, or unsupported dispatch and bind an external route
to an approved target AI-infrastructure item.

Include `.ai/assistant/change-packages/index.json`, the lazy change-package
overlay, `.ai/assistant/flows/change-package.flow.md`, and machine/human report
templates only when the target needs coherent material-change evidence,
semantic multi-surface approval, architecture segment/capability evidence,
audit, pilot, or publishable provenance. Define record ownership, retention,
redaction, Git/PR evidence policy, and target validator use. Start with an
empty index and do not infer historical packages.

Include `.ai/.gitignore`, `.ai/project/team-policy.json`, its human operating
model, active-work index, registry metadata, per-task and backend contracts,
team overlay, identity/task/handoff/decision/review flows, team gate, adapted
skill, and identity/checkpoint/handoff/decision templates only when enabled.
Derive actors, aliases, authority, priority, transitions, backend, identity
verification, review, retention, and privacy from target evidence. Start with
empty task storage and index unless active tasks are explicitly reviewed. For
upgrades, preserve task IDs, actor references, claims, handoffs, decisions,
external references, and ignored local identity. Migrate schema-1 arrays to
schema-2 per-task records and regenerate the index before replacing registry
metadata.

## Context, Risk, Safety, Testing, And Diagram Adaptation

- Target context entry points:
- Host-preloaded context:
- Compact bootstrap context:
- Generated bootstrap source-hash verification:
- Context router:
- Task context profiles:
- Context-router bootstrap references:
- Context budgets and exception behavior:
- Context receipt fields:
- Project-area overlays:
- Task-scale overlays:
- Large-task activation, packet storage, and resume rules:
- Change-package activation, owner, record storage, semantic approval scope,
  companion decisions, correction handling, provenance, retention/redaction,
  and validator rules:
- Team-active routing, backend synchronization, active-task projection,
  changed-fact conflict, claim/staleness, checkpoint, handoff, decision,
  review, merge-readiness, storage, retention, and privacy rules:
- Required core profile:
- Adapter owner, backup owner, review cadence, and last review:
- CODEOWNERS or equivalent owner map:
- Optional modules:
- Deferred, disabled, not-applicable, or blocked modules:
- Source-of-truth owners:
- Source-of-truth registry entries:
- Consistency-map fact IDs, levels, areas, relationship edges, and missing
  coverage:
- Impact-closure and map-staleness evidence:
- Blueprint or equivalent owner:
- Generated artifacts and owning sources:
- Missing-context escalation:
- Risk classes and approval triggers:
- Security and live-service boundaries:
- Destructive-operation and dependency approval rules:
- Credential, privacy, and log-redaction rules:
- Recommended test levels:
- Target validation commands or manual checks:
- AI infrastructure adaptation, provenance, wrapper, and output-format rules:
- AI infrastructure inventory rules:
- AI infrastructure recommendation, existing-item review, project-contour
  evidence, quality/context/maintenance cost, and acceptance-criteria rules:
- Development-pattern capture, deduplication, retention/privacy, bounded
  evidence-reference, and target-only optimization rules:
- AI infrastructure route/item selection and lazy context-loading rules:
- AI infrastructure item permissions, gates, validation, output contracts,
  conflicts, and adaptation-record rules:
- AI infrastructure source access and approval rules:
- Prompt-injection rules:
- Approval-record rules:
- Migration-diff rules:
- Effectiveness measurement rules:
- Installed-operation request and adapter-recheck rules:
- Operation catalog, single entry, automatic routing, health, and preview
  rules:
- Large-task workstream, checkpoint, and final-convergence rules:
- Subagent delegation activation, role/model, packet, isolation, fallback,
  primary-review, and evidence rules:
- Adapter output contract rules:
- Adapter drift/local leakage rules:
- Target-local adapter checker rules:
- AI infrastructure inventory report rules:
- AI infrastructure recommendation report rules:
- Post-install/update assistant chat-message rules:
- Architecture knowledge catalog, item-state, evidence-revision, and
  documentation-maintenance rules:
- Code-documentation profile selection, style proposal, structured-comment,
  generator, derived-output, direct-edit, and source-of-truth boundary rules:
- Project-vocabulary lookup, term-state, domain-scope, alias/acronym,
  normalization, data-link, acceptance, and source-of-truth boundary rules:
- Test-first policy state, recommendation, trigger, mode, command, isolation,
  exception, RED/GREEN/refactor, broader-validation, and evidence rules:
- Extension package inspection, catalog, lock, immutable source, digest,
  binding, permission, approval, installed-file ownership, conflict,
  update/disable/remove, and lifecycle-evidence rules:
- Diagram source format:
- Human visual format:
- Render or manual-review policy:
- Drift checks:
- Discussion presentation modes:
- Per-assistant native inline syntaxes:
- Rendered artifact link or attachment capability:
- Required ASCII baseline and width policy:
- Source revision, content hash, or stale-view evidence:
- Adapter maturity level:
- Task-specific maturity:
- Blocking criteria:
- Maturity gaps:
- Bridge capability matrix:
- Framework baseline or source:
- Framework version:
- Adapter schema version:
- Template version:
- Local deviations:
- Upgrade or migration notes:
- Migration assessment path or manual baseline comparison:
- Canonical sources selected from migration impact:
- Candidate upgrade context intentionally omitted:
- Effectiveness metrics:

## Contour Plan

- Framework contour:
- Project contour:
- Repository adapter contour:
- Mixed artifacts to split:

## Bridge File Plan

List assistant-specific bridge files to create, update, skip, or preserve.

Also state how root `AGENTS.md`, `AI_ASSISTANTS.md`, and supported bridge
files will point future sessions to the installation note, compact help,
operation index, operation catalog, and routing flow, including `Alatyr`, read-only
status/doctor aliases, risk-gated preview behavior, and optional team aliases
through the canonical catalog. When diagrams are enabled, include
`diagram-discussion` routing and record presentation limitations in the
selected assistant-capability record rather than bridge policy text. Capture
actual result evidence separately from the prepared conformance prompt.

State whether CODEOWNERS or an equivalent owner map exists for root assistant
entry points and supported bridge files.

## Existing File Preservation

| File | Action | Approval needed |
| --- | --- | --- |

## Rejected Source Facts

List source or example facts that must not be copied into the target project.

## Validation Plan

| Check | Command or review | Required | Notes |
| --- | --- | --- | --- |

Validation commands must come from the target repository. If no command exists,
write a manual review item or mark the check unresolved.

## Approval Required

State whether approval is required and why.

If approval scope spans protected categories, multiple files, or a plan that
may be reused, state the approval record path and approved plan hash or why a
hash is unavailable.

Also state the approved Git diff base, explicit machine-readable approval
record paths, and the command or target-local equivalent that will fail when
the complete changed path set exceeds allowed scope or enters excluded scope.

When change packages are enabled, state how approvals bind changed-fact IDs,
architecture areas, behavior categories, excluded semantic effects, permitted
external effects, and reapproval triggers in addition to paths.

Preferred approval:

```text
APPROVE ALATYR INSTALLATION: ALATYR-YYYYMMDD-short-name
```

## Risks

List drift, overwrite, unsupported-assistant, gate, security, diagram,
maturity, lifecycle, installed-operation, operation-help, context-profile,
context-router, local-path leakage, target-local checker, approval-record,
prompt-injection, skill-adaptation, source-access, migration-diff,
effectiveness-metrics, team identity/authority, active-record overwrite,
concurrent overlap, stale claim/handoff/review evidence, privacy, scaffolding,
and validation risks.
