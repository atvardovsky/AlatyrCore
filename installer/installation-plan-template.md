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
- Context router:
- Context profiles:
- Context-router bootstrap references:
- Preloaded versus compact-bootstrap context:
- Bootstrap and profile context budgets:
- Context receipt fields and storage policy:
- Project-area overlays:
- Task-scale overlays and large-task activation rules:
- Large-task packet storage, retention, or ignore policy:
- Adapter owner metadata:
- CODEOWNERS or equivalent owner map:
- Module profile:
- Task-specific maturity profile:
- Bridge capability matrix:
- Blueprint-driven change or equivalent product-change workflow:
- Installed-operation, operation-help, operation-routing, blueprint-creation,
  adapter-recheck, framework-update review, or chat-message process:
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

Include `.ai/assistant/context-profiles.md` to explain task profiles,
expansion triggers, approvals, validation, and final evidence for humans.

Include `.ai/assistant/module-profile.md` to record required core status,
enabled optional modules, deferred modules, blocked modules, and reasons.

Include `.ai/project/source-of-truth-registry.md` when multiple files or
surfaces can describe the same project fact.

Include `.ai/project/consistency-map.json` when the target has enough project
areas or competing surfaces to benefit from bounded changed-fact relationship
traversal. Populate it from target evidence or leave the module blocked; do not
infer complete relationships from filenames.

Include `.ai/assistant/maturity-profile.md` to report readiness by task area
and blocking criteria.

Include `.ai/assistant/bridge-capability-matrix.md` when more than one
assistant surface is supported or bridge behavior may differ.

Include `.ai/assistant/policies/ai-infrastructure-source-access.md` when the
target wants AI infrastructure inventory, adaptation, package/plugin review, or
third-party assistant infrastructure handling.

Include `.ai/assistant/policies/prompt-injection.md` when imported, remote,
pasted, package/plugin, or unknown AI infrastructure can be reviewed or
adapted.

Include `.ai/assistant/approvals/approval-template.md` when protected-change
approvals need durable evidence.

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

Include `.ai/assistant/ai-infrastructure-router.json` and
`.ai/assistant/templates/ai-infrastructure-adaptation-record.md` when the
target uses multiple skills, prompts, gates, checkers, tools/MCP configs,
bridges, wrappers, or imported items. Populate entries from target evidence;
keep unresolved items blocked.

Include `.ai/assistant/flows/large-task-orchestration.flow.md` and
`.ai/assistant/templates/large-task-operation-packet.md` when the target needs
cross-boundary, multi-workstream, budget-exceeding, or resumable operations.
Record where completed packets are stored, ignored, redacted, or removed.

## Context, Risk, Safety, Testing, And Diagram Adaptation

- Target context entry points:
- Host-preloaded context:
- Compact bootstrap context:
- Context router:
- Task context profiles:
- Context-router bootstrap references:
- Context budgets and exception behavior:
- Context receipt fields:
- Project-area overlays:
- Task-scale overlays:
- Large-task activation, packet storage, and resume rules:
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
- AI infrastructure route/item selection and lazy context-loading rules:
- AI infrastructure item permissions, gates, validation, output contracts,
  conflicts, and adaptation-record rules:
- AI infrastructure source access and approval rules:
- Prompt-injection rules:
- Approval-record rules:
- Migration-diff rules:
- Effectiveness measurement rules:
- Installed-operation request and adapter-recheck rules:
- Operation help and routing rules:
- Large-task workstream, checkpoint, and final-convergence rules:
- Adapter output contract rules:
- Adapter drift/local leakage rules:
- Target-local adapter checker rules:
- AI infrastructure inventory report rules:
- Post-install/update assistant chat-message rules:
- Diagram source format:
- Human visual format:
- Render or manual-review policy:
- Drift checks:
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
- Effectiveness metrics:

## Contour Plan

- Framework contour:
- Project contour:
- Repository adapter contour:
- Mixed artifacts to split:

## Bridge File Plan

List assistant-specific bridge files to create, update, skip, or preserve.

Also state how root `AGENTS.md`, `AI_ASSISTANTS.md`, and supported bridge
files will point future sessions to the installation note, operation help, and
operation-routing flow.

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

Preferred approval:

```text
APPROVE ALATYR INSTALLATION: ALATYR-YYYYMMDD-short-name
```

## Risks

List drift, overwrite, unsupported-assistant, gate, security, diagram,
maturity, lifecycle, installed-operation, operation-help, context-profile,
context-router, local-path leakage, target-local checker, approval-record,
prompt-injection, skill-adaptation, source-access, migration-diff,
effectiveness-metrics, scaffolding, and validation risks.
