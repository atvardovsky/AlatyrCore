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
- Existing intent overlays:
- Existing module profile:
- Existing task-specific maturity profile:
- Existing bridge capability matrix:
- Existing generated assistant-capability index, per-surface records, and
  freshness or expiry evidence:
- Existing blueprint or equivalent source-of-truth docs:
- Existing operation catalog, installed-operation, operation-help, automatic
  routing, action-authorization policy, adapter-health, pre-change preview,
  blueprint-creation,
  adapter-recheck, or chat-message process:
- Existing structured team policy and operating model, stable actor IDs and
  display-name mappings, current-user selection, identity verification,
  decision authority, priority/transitions, task backend and atomic-write
  behavior, active tasks, claims, branches/worktrees, reviews, checkpoints,
  handoffs, decisions, merge rules, storage, retention, and privacy:
- Existing adapter output contracts:
- Existing risk or approval policy:
- Existing security, privacy, live-service, destructive-operation, dependency,
  and credential/log-redaction policies:
- Existing diagram sources, visual artifacts, render/manual-review process, and
  drift checks:
- Existing diagram discussion flow, presentation template, stable IDs/revision
  lineage, sensitivity/redaction policy, external-renderer policy, assistant
  inline or artifact capabilities, portable ASCII baseline, and source-revision
  evidence:
- Existing architecture index/catalog, pattern and area docs, owners, decision
  authority, states, evidence revisions, validation, and contradictions:
- Existing assistant instruction files:
- Scaffolding helper used or planned:
- Scaffold profile (`core` / `standard` / `full` / not used):
- Existing skills, prompts, third-party assistant infrastructure, provenance
  notes, and wrappers:
- Existing extension package manifests, extension catalog and lock, immutable
  source revisions and digests, target bindings, installed-file ownership,
  local modifications, dependents, and lifecycle evidence:
- Existing AI infrastructure inventory reports:
- Existing AI infrastructure router, item IDs, permissions, gates, output
  contracts, recommendation records, and adaptation records:
- Existing approval records, machine-readable scopes, diff-base binding, or
  approval evidence:
- Existing migration notes:
- Existing migration-diff process:
- Existing migration assessment or reviewed baseline comparison:
- Existing effectiveness metrics or reports:
- Existing Debug Mode policy, non-canonical index/records, active scope,
  privacy/retention, event attribution, structured architectural impacts,
  direction-change hypothesis/replacement chains, durable evidence links,
  timing/capture quality, supervision metrics, external projection, and
  comparison evidence:
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
- `.ai/assistant/bootstrap-index.json`
- `.ai/assistant/context/profiles`
- `.ai/assistant/context-profiles.md`
- `.ai/assistant/maturity-profile.md`
- `.ai/assistant/bridge-capability-matrix.md`
- `.ai/assistant/assistant-capabilities.json`
- `.ai/assistant/assistant-capabilities`
- `.ai/assistant/operation-index.json`
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
- current-scope action authorization: phase definitions, scope invalidation,
  default read-only intent classes, independent gates, delegation inheritance,
  and final evidence
- task-specific maturity profile and blocking criteria
- bridge capability matrix for supported assistants

Reject installation plans that keep framework rules, project facts, and
adapter details mixed without a clear split.

## 5. Target Project Adapter Inputs

Collect target-specific facts before writing project docs:

- product purpose
- architecture/module facts
- architecture patterns and other items, including observed versus intended
  status, scope, owners, decisions, constraints, and validation
- use cases or main workflows
- blueprint-driven change or equivalent product-change workflow
- business/domain rules
- data model
- runtime flows
- test strategy
- existing test levels, folders, fixtures, fakes, and isolation rules
- existing test-first/TDD policy, regression patterns, activation triggers,
  commands, feedback time, exceptions, CI, merge gates, and decision authority
- validation commands and manual checks
- context/source-of-truth owners and generated artifacts
- source-of-truth registry entries for important fact types
- consistency-map need, owner, fact-ID strategy, relationship coverage, and
  staleness checks, including exact one-to-one coverage from every live
  registry Fact Type to its referenced map node
- adapter owner, backup owner, review cadence, and file-owner map expectations
- risk classes and approval triggers
- current-scope authorization expectations for inspection, working-tree
  changes, local Git state, remote publication, and live external effects
- security, privacy, live-service, destructive-operation, dependency, and
  credential/log-redaction rules
- deployment/operations facts
- diagram needs, source format, visual format, render/manual-review policy, and
  drift checks
- diagram discussion need, draft/source status policy, per-assistant native
  inline syntaxes, rendered-artifact presentation, ASCII layout/width,
  capability expiry or review triggers, captured-result evidence, and
  stale-view evidence
- skills, prompts, wrappers, third-party assistant infrastructure, provenance,
  output formats, permissions, and safety rules
- AI infrastructure inventory expectations and existing item owners
- AI infrastructure recommendation expectations: bounded project-contour need
  and outcome evidence, existing-item-first review, labeled quality/context/
  maintenance estimates, acceptance criteria, and read-only behavior
- Target development-pattern index, owner, retention/privacy policy, capture
  threshold, bounded evidence references, and allowed historical sources
- Durable engineering-evidence owner, retained storage mode, redaction and
  external-contribution policy, capture threshold, task/revision binding, and
  access path for future developers and assistants
- Project-knowledge owner, decision authority, canonical owner registry,
  promotion policy, compact index/shards, two-stage selectors, freshness and
  contradiction policy, retention/redaction, and evidence access
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
- approved changed-fact IDs, architecture areas, behavior categories,
  excluded semantic effects, permitted external effects, and reapproval
  triggers when change packages are enabled
- adapter maturity gaps and lifecycle expectations
- task-specific maturity expectations and blockers
- module profile expectations and blockers
- bridge capability matrix expectations
- framework migration-note expectations
- framework migration-diff expectations
- effectiveness measurement expectations
- optional Debug Mode owner, activation/expiry, storage, visibility,
  retention/redaction, normalized event origins and causal links, timing,
  structured architectural impacts, direction-change hypothesis/replacement
  causality, exact durable evidence reference resolution, capture quality,
  observer effect, metric derivation, clean-upstream boundary, active-versus-
  finalized comparison quality criteria, and overhead limit
- installed-operation request, blueprint-creation, adapter-recheck, and
  framework-update review expectations
- large-task activation, task-scale overlay, operation packet, workstream,
  checkpoint, storage, resume, and final-convergence expectations when needed
- subagent capability, target policy, automatic/suggestion-only mode, worker
  role catalog/prompts, task graph/result contract, native, external,
  suggestion-only, or unsupported per-surface dispatch backend, exact
  client/runtime, external dispatcher item, native definition format/paths,
  role/model binding, disjoint-write/tool/background/nested behavior,
  retry/conflict fallback, privacy, validation, and primary convergence when
  needed
- change-package activation, compact index, semantic and path approval scope,
  companion decisions, implementation corrections, provenance quality,
  retention/redaction, and validator expectations when needed
- team-collaboration owner, structured actor/authority/priority/transition
  policy, ignored local identity boundary, backend capabilities and
  synchronization, active-work index, per-task registry and optimistic
  concurrency, claim/staleness, changed-fact conflict, checkpoint, handoff,
  decision, review, merge-readiness, storage, retention, and privacy when needed
- operation catalog, single entry, automatic routing, read-only health,
  risk-gated preview, and post-install/update assistant chat-message
  expectations
- diagram-discussion operation, ASCII template, presentation template, and
  bridge capability expectations when the diagrams module is enabled
- architecture-assistance operation, compact catalog, lazy intent route,
  pattern/area/result templates, and acceptance boundaries when the
  architecture-knowledge module is enabled
- code-documentation owner, profile decision authority, bounded frontend,
  backend, shared, or infrastructure source sets, existing comment styles,
  canonical fact-owner boundaries, generators, output/publication policy,
  validation, lazy intent route, and adapted skill when the optional module is
  enabled
- project-vocabulary owner, term decision authority, scoped meanings, aliases,
  acronyms, term states, normalization policy, canonical sources, data-
  dictionary links, terminology validation, lazy route, and adapted skill when
  the optional module is enabled
- test-first owner, decision authority, accepted policy state, bounded
  recommendation behavior, triggers, modes, test levels, commands, isolation,
  exceptions, RED/GREEN/refactor evidence, lazy route, gate, and adapted skill
  when the optional module is enabled
- extension owner, source-access and prompt-injection policy, extension package
  manifest, immutable source and digest, compatibility, catalog/lock, bindings,
  permissions, approval, installed-file ownership, update/removal policy, lazy
  route, and cross-assistant exposure when optional extensions are supported
- dependency knowledge owner, package-manager manifests and lockfiles,
  native-metadata-only export discovery, exact artifact identity, untrusted
  source policy, independent trust/freshness/authority/applicability state,
  project deviations, retention, graph bounds, lazy route, synchronization
  flow, gate, operation, and validation when the optional module is enabled
- workspace-mode owner and decision authority, workspace identity and active
  adapter evidence, proposed or accepted mode states, artifact relationships,
  one directory per actual mode, optional shared root support, ambiguity
  behavior, user decisions, routing, preflight, gate, cost, and validation
  when the optional module is enabled

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
- diagram discussion routing, ASCII presentation/readability, rich capability
  freshness, captured-result, read-only behavior, and stale-view review:
- installed-operation or adapter-recheck review:
- adapter output contract review:
- context-profile review:
- context-router bootstrap reference review:
- generated bootstrap source-hash and deterministic projection review:
- routed gate-index/profile-fragment review:
- preloaded versus compact-bootstrap review:
- context total/portable/reserved-target budget and receipt review:
- project-area overlay review:
- adapter drift/local leakage review:
- module-profile review:
- source-of-truth registry review:
- task-specific maturity review:
- bridge capability matrix review:
- migration-diff review:
- migration assessment completed before target upgrade changes:
- machine-readable upgrade-impact projection reviewed before broad upgrade
  context:
- checked-out target branch and revision recorded for migration and final
  validation evidence:
- migration-staging output classified as non-accepting, with active unresolved
  placeholders listed and an acceptance-phase rerun required:
- manifest `modules.enabled` and human module-profile enabled/required blocks
  agree one-to-one:
- effectiveness metrics review:
- Debug Mode dependency, explicit activation/expiry, non-canonical authority,
  privacy, event attribution, structured architectural impacts, direction-
  change hypothesis/replacement causality, timing/capture quality, metric
  derivation, exact durable engineering-evidence reference resolution, active-
  versus-finalized comparison, clean-upstream, observer-effect, and validator
  review:
- operation-catalog, automatic-routing, health, or preview review:
- team policy/operating model, local identity ignore and attribution boundary,
  registry/task schemas, active index, backend capabilities/synchronization,
  optimistic concurrency, schema-1 migration, active-record preservation,
  overlap, claim, handoff, decision, review, merge-readiness, retention, and
  privacy review:
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

- current logical scope and `current_user_authorization`, including source
  request, authorized and unauthorized phases, invalidated prior
  authorization, and state-changing actions actually performed
- framework core installed/adapted
- selected framework pack is compatible with the support profile and enabled
  modules; projected registry and inventory match installed files
- adapter manifest and version facts recorded
- adapter owner, backup owner, review cadence, and CODEOWNERS or equivalent
  owner map recorded or explicitly unresolved
- target adapter rewritten
- contours created or updated
- source-of-truth registry created or updated
- consistency-map module enabled, deferred, disabled, or blocked with reason
- context profiles created or updated
- context router index and lazy descriptor references checked against the
  selected support profile, compact bootstrap, gates, operation routing, root
  entry points, and bridge files
- generated bootstrap index matches the manifest, project map, and router
  source hashes; bridges load the projection and retain canonical repair paths
- profile default gate fragments match the gate index; the complete checklist
  remains lazy outside ambiguity, repair, or full audit
- operation catalog stays outside routine routing; exact aliases use the
  checked compact index and context profiles/intent overlays expose bounded
  candidates
- preloaded context is not duplicated in bootstrap
- blueprint, registries, contours, module profile, and human profile rationale
  are routed after task selection instead of loaded for every task
- context budgets and receipt fields are adapted from target evidence
- large-task orchestration is enabled or skipped from target evidence; enabled
  adapters define activation, packet storage, bounded resume context,
  checkpoints, and global convergence
- subagent delegation is enabled or skipped from target evidence; enabled
  adapters define current per-surface capabilities, native/external/
  suggestion-only/unsupported dispatch, external dispatcher item where used,
  target-owned role catalog/prompts, deterministic task readiness, normalized
  results, bounded role/model bindings, verified native definition paths,
  packet limits, disjoint writes, retry/conflict fallback, privacy, validation,
  and primary convergence
- change packages are enabled or skipped from target evidence; enabled
  adapters define activation, owner, empty initial index, semantic/path scope,
  companion decisions, correction handling, provenance grades, record
  retention/redaction, and validator support
- team collaboration is enabled or skipped from target evidence; enabled
  adapters define a policy owner, backend capability/synchronization contract,
  stable actor/authority/priority/transition evidence, ignored local identity,
  compact preflight, per-task records, atomic writes, conflict policy, storage,
  retention/privacy, and revision-bound review evidence
- adapter drift checks run or recorded as manual/unresolved, including local
  path leakage, stale checker statements, duplicate profile references,
  unresolved owner placeholders, and target-local checker status
- module profile created or updated
- workspace modes are enabled, deferred, disabled, not applicable, or blocked
  with reason; installation suggestions remain proposed until separately
  accepted by the user
- each actual mode has its own directory, optional shared root support is
  bounded, nested adapters remain inactive, and mode constraints grant no
  approval, write scope, permissions, authority, tools, or gate bypass
- architecture knowledge is enabled, skipped, deferred, or blocked from
  target evidence; enabled adapters define owner, decision authority, compact
  catalog, states, selected-source routing, validation, and known gaps
- task-specific maturity profile created or updated
- bridge capability matrix created or updated
- portable ASCII baseline plus per-assistant inline/artifact capabilities,
  client version, verification time, and evidence resolved or explicitly
  unknown with reason
- bridge files added or checked
- operation catalog, installed-operation, operation-help, automatic routing,
  action-authorization policy,
  read-only adapter-health, risk-gated preview, blueprint-creation,
  adapter-recheck, or post-install/update chat-message templates added or
  skipped
- manifest installation state and machine-readable transition history agree;
  the chain starts at `scaffolded` for a new install or at truthful `staged`
  `legacy-migration-baseline` for a pre-record adapter, contains no invalid
  jump, and reaches `accepted` only with current strict validation evidence
- project-knowledge policy/index/promotions/routes, two-stage routing
  descriptor, flow, gate, authoring templates, and validator added or blocked
  with unresolved owner/authority facts
- diagram-discussion flow, ASCII template, presentation template, stable lineage,
  security/privacy/external-renderer policy, and operation conformance fixture
  added, skipped, or blocked from target evidence
- architecture index/catalog, assistance flow, intent route, and
  pattern/area/result templates added, migrated, skipped, or blocked without
  promoting observed implementation to accepted architecture
- adapter output contracts added or skipped
- large-task flow and operation-packet template added or skipped
- subagent delegation policy, role catalog/prompts, orchestration prompt,
  delegated-execution overlay, flow, native-binding authoring, execution plan,
  packet, normalized result, native definition bindings, and per-surface
  capability fields added or skipped
- change-package index, lazy overlay, flow, machine record, redacted report,
  and retention/redaction policy added, migrated, skipped, or blocked
- team policy and operating model, local ignore rule, active-work index,
  registry metadata, per-task template, backend contract, team-active overlay,
  identity/task/handoff/decision/review flows, team gate, adapted skill, and
  identity/checkpoint/handoff/decision templates added, migrated, skipped, or
  blocked without overwriting active target state
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
- Debug Mode index/records, lazy overlay, operation, flow, gate, record/summary
  templates, structured event classification and durable evidence reference
  validation added, preserved, migrated, skipped, or blocked; task activation
  remains inactive unless explicitly requested, and legacy records remain
  migration-limited rather than silently inferred
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
