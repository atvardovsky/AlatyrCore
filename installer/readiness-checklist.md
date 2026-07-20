# Alatyr Core Installation Readiness Checklist

Use this checklist before installing Alatyr Core into a target repository.

This is an assistant reasoning aid. It is not a script and does not approve
changes.

## 1. Target Repository Profile

- Target repository path:
- New install or upgrade:
- Primary language/framework:
- Package/build files:
- Existing docs:
- Existing tests:
- Existing CI:
- Known validation commands:
- Existing test tools, fixtures, helpers, and isolation rules:
- Existing source-of-truth/context map:
- Existing source-of-truth registry:
- Existing fact IDs, relationship maps, or consistency manifests:
- Existing adapter manifest or version record:
- Existing CODEOWNERS or equivalent owner map:
- Existing adapter owner, backup owner, review cadence, and last review:
- Existing context profiles:
- Existing module profile:
- Existing task-specific maturity profile:
- Existing bridge capability matrix:
- Existing blueprint or equivalent source-of-truth docs:
- Existing operation catalog, installed-operation, operation-help, automatic
  routing, adapter-health, pre-change preview, blueprint-creation,
  adapter-recheck, or chat-message process:
- Existing adapter output contracts:
- Existing risk or approval policy:
- Existing security, privacy, live-service, destructive-operation, dependency,
  and credential/log-redaction policies:
- Existing diagram sources, visual artifacts, render/manual-review process, and
  drift checks:
- Existing assistant instruction files:
- Scaffolding helper used or planned:
- Scaffold profile (`core` / `standard` / `full` / not used):
- Existing skills, prompts, third-party assistant infrastructure, provenance
  notes, and wrappers:
- Existing AI infrastructure inventory reports:
- Existing AI infrastructure router, item IDs, permissions, gates, output
  contracts, recommendation records, and adaptation records:
- Existing approval records, machine-readable scopes, diff-base binding, or
  approval evidence:
- Existing migration notes:
- Existing migration-diff process:
- Existing migration assessment or reviewed baseline comparison:
- Existing effectiveness metrics or reports:
- Existing prompt-injection or imported-source policy:
- Supported assistants needed:

## 2. Existing AI Surface

Check whether the target already has:

- `AGENTS.md` or `agents.md`
- `AI_ASSISTANTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `.github/copilot-instructions.md`
- `.github/instructions`
- `.github/prompts`
- `.cursor/rules` or `.cursorrules`
- `.cursor/skills`
- `.claude/skills`
- `.devin/rules`
- `.windsurf/rules` or `.windsurfrules`
- `.ai`
- `.ai/alatyr.yaml`
- `.ai/assistant/policies`
- `.ai/assistant/context-router.json`
- `.ai/assistant/context-profiles.md`
- `.ai/assistant/maturity-profile.md`
- `.ai/assistant/bridge-capability-matrix.md`
- `.ai/assistant/approvals`
- `.agents/skills`

Do not overwrite existing target instructions without explicit approval.

## 3. Core Versus Adapter

Classify every proposed file:

- Framework core:
- Project adapter:
- Project fact:
- Assistant bridge/wrapper:
- Skill/prompt/third-party assistant infrastructure:
- Generated/visual artifact:
- Existing target-owned file:
- Do not copy:

Framework core may be structurally copied or adapted from `framework/`.
Project adapter files must be rewritten from target facts.

Commands, scripts, generated-file tools, checker paths, hooks, test tools,
fixture helpers, folder names, CI jobs, security policies, live-service
allowlists, dependency scanners, diagram formats/tools, generated visual paths,
framework version strings, lifecycle notes, adapter owner names, skill sources,
assistant-native formats, tool permissions, and third-party assistant
infrastructure are target adapter details, not framework core.

## 4. Required Target Contours

The target installation must define or adapt:

- framework contour: what portable AI operating rules own
- project contour: what target product/code/business facts own
- repository adapter contour: what local assistant operating rules and
  validation own
- adapter manifest: framework version, adapter schema version, template
  version, owner, source-of-truth files, validation, known gaps, and local
  deviations
- adapter owner metadata: responsible team, technical owner, backup owner,
  review cadence, last review date, and CODEOWNERS or equivalent owner map
- module profile: required core status, enabled optional modules, deferred
  modules, blocked modules, and reasons
- source-of-truth registry: fact owners, invariant/dependency constraints,
  derived surfaces, sync direction, validation, and conflict resolvers
- optional consistency map: stable fact IDs, levels, project areas,
  relationships, impact traversal, staleness handling, and missing coverage
- context profiles: task-specific required context, approval, validation, and
  evidence rules
- task-specific maturity profile and blocking criteria
- bridge capability matrix for supported assistants

Reject installation plans that keep framework rules, project facts, and
adapter details mixed without a clear split.

## 5. Target Project Adapter Inputs

Collect target-specific facts before writing project docs:

- product purpose
- architecture/module facts
- use cases or main workflows
- blueprint-driven change or equivalent product-change workflow
- business/domain rules
- data model
- runtime flows
- test strategy
- existing test levels, folders, fixtures, fakes, and isolation rules
- validation commands and manual checks
- context/source-of-truth owners and generated artifacts
- source-of-truth registry entries for important fact types
- consistency-map need, owner, fact-ID strategy, relationship coverage, and
  staleness checks
- adapter owner, backup owner, review cadence, and file-owner map expectations
- risk classes and approval triggers
- security, privacy, live-service, destructive-operation, dependency, and
  credential/log-redaction rules
- deployment/operations facts
- diagram needs, source format, visual format, render/manual-review policy, and
  drift checks
- skills, prompts, wrappers, third-party assistant infrastructure, provenance,
  output formats, permissions, and safety rules
- AI infrastructure inventory expectations and existing item owners
- AI infrastructure recommendation expectations: bounded project-contour need
  and outcome evidence, existing-item-first review, labeled quality/context/
  maintenance estimates, acceptance criteria, and read-only behavior
- Target development-pattern index, owner, retention/privacy policy, capture
  threshold, bounded evidence references, and allowed historical sources
- AI infrastructure router/item expectations for canonical source, triggers,
  status, required context, allowed actions, permissions, gates, validation,
  output, conflicts, wrappers, and adaptation records
- AI infrastructure source access policy for local paths, Git URLs, HTTPS URLs,
  assistant-native references, pasted content, packages, or plugins
- prompt-injection policy for imported, remote, pasted, package/plugin, or
  unknown AI infrastructure
- approval-record policy or storage location for protected changes
- approved diff-base policy, machine-readable record format, and complete
  changed-path scope enforcement
- adapter maturity gaps and lifecycle expectations
- task-specific maturity expectations and blockers
- module profile expectations and blockers
- bridge capability matrix expectations
- framework migration-note expectations
- framework migration-diff expectations
- effectiveness measurement expectations
- installed-operation request, blueprint-creation, adapter-recheck, and
  framework-update review expectations
- large-task activation, task-scale overlay, operation packet, workstream,
  checkpoint, storage, resume, and final-convergence expectations when needed
- operation catalog, single entry, automatic routing, read-only health,
  risk-gated preview, and post-install/update assistant chat-message
  expectations

## 6. Assistant Compatibility

Choose only bridge files that the target needs:

- Generic assistant entry point
- Codex / AGENTS-aware tools
- Claude
- Gemini
- GitHub Copilot
- Cursor
- Devin/Cascade
- Windsurf legacy

Bridge files must stay short and point to canonical target files.
Assistant-specific skill wrappers must also point to canonical target rules
instead of duplicating full policy.

## 7. Approval And Risk

Approval is required before:

- overwriting existing AI instructions
- changing target project architecture
- weakening target gates
- changing accepted business behavior
- adding production dependencies
- importing third-party assistant infrastructure into canonical target files
- broadening assistant tool permissions, live-service access, destructive
  capabilities, or credential handling
- enabling live, destructive, spend-affecting, or data-loss side effects
- reusing an approval after the approved plan or protected scope changed

## 8. Validation Plan

List commands or manual checks:

- target package/build validation:
- target tests:
- target test structure advice:
- target test isolation rules:
- static analysis:
- docs/diagram checks:
- installed-operation or adapter-recheck review:
- adapter output contract review:
- context-profile review:
- context-router bootstrap reference review:
- preloaded versus compact-bootstrap review:
- context budget and receipt review:
- project-area overlay review:
- adapter drift/local leakage review:
- module-profile review:
- source-of-truth registry review:
- task-specific maturity review:
- bridge capability matrix review:
- migration-diff review:
- migration assessment completed before target upgrade changes:
- effectiveness metrics review:
- operation-catalog, automatic-routing, health, or preview review:
- skill/provenance/safety review:
- AI infrastructure inventory review:
- AI infrastructure recommendation and existing-item improvement review:
- Development-pattern evidence ownership, privacy, retention, and framework
  non-mutation review:
- AI infrastructure router/item and adaptation-record review:
- AI infrastructure source access review:
- prompt-injection review:
- approval-record review:
- changed paths subset of approved scope review:
- AI consistency checks, if installed:
- target-local adapter checker status and coverage:
- source commands intentionally not copied:
- source test tools/fixtures/CI jobs intentionally not copied:
- source security policies, diagram tooling, lifecycle notes, and adapter owner
  facts intentionally not copied:
- skipped gates and reason:

## 9. Final Evidence

Final evidence must say:

- framework core installed/adapted
- adapter manifest and version facts recorded
- adapter owner, backup owner, review cadence, and CODEOWNERS or equivalent
  owner map recorded or explicitly unresolved
- target adapter rewritten
- contours created or updated
- source-of-truth registry created or updated
- consistency-map module enabled, deferred, disabled, or blocked with reason
- context profiles created or updated
- context router references checked in compact bootstrap, gates, operation routing,
  root entry points, and bridge files
- operation catalog stays outside routine bootstrap; context profiles expose
  bounded operation candidates
- preloaded context is not duplicated in bootstrap
- blueprint, registries, contours, module profile, and human profile rationale
  are routed after task selection instead of loaded for every task
- context budgets and receipt fields are adapted from target evidence
- large-task orchestration is enabled or skipped from target evidence; enabled
  adapters define activation, packet storage, bounded resume context,
  checkpoints, and global convergence
- adapter drift checks run or recorded as manual/unresolved, including local
  path leakage, stale checker statements, duplicate profile references,
  unresolved owner placeholders, and target-local checker status
- module profile created or updated
- task-specific maturity profile created or updated
- bridge capability matrix created or updated
- bridge files added or checked
- operation catalog, installed-operation, operation-help, automatic routing,
  read-only adapter-health, risk-gated preview, blueprint-creation,
  adapter-recheck, or post-install/update chat-message templates added or
  skipped
- adapter output contracts added or skipped
- large-task flow and operation-packet template added or skipped
- AI infrastructure inventory report template added or skipped
- AI infrastructure recommendation flow and report template added or skipped
- development-evidence index and lazy capture flow added or skipped
- AI infrastructure router and adaptation-record template added or skipped
- root entry-point and bridge compact-bootstrap references checked
- AI infrastructure source-access policy added or skipped
- prompt-injection policy added or skipped
- human and machine-readable approval-record templates added or skipped
- migration-note template added or skipped
- effectiveness-report template added or skipped
- scaffolding helper used or skipped
- skills, prompts, wrappers, or third-party assistant infrastructure adapted or
  skipped
- selected AI infrastructure routes/items, permission/gate/output contracts,
  and adaptation-record results reported or skipped
- recommendation results report project-contour evidence, existing-item
  comparison, cost/quality gate, acceptance criteria, actions avoided, and next
  route, or are explicitly skipped
- pattern-based recommendations name selected pattern IDs and references;
  target evidence did not directly change framework files or portable rules
- existing target instructions preserved or approved for overwrite
- commands or manual checks run
- skipped checks and residual risk
