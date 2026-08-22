# Alatyr Core Assistant Installation Flow

## Purpose

Guide an assistant through installing Alatyr Core into a target repository
without relying on an installer script.

The flow is portable and assistant-neutral. The target project adapter must be
rewritten from target repository facts.

## Use When

Use this flow when:

- a programmer asks to install Alatyr Core into a project
- a project needs framework/project/repository-adapter contour separation
- an existing AI instruction setup needs to be upgraded to Alatyr Core
- a target repository needs assistant-neutral flows, gates, prompts, skills,
  bridge files, or documentation-sync rules

## Source Bootstrap

Treat root `AGENTS.md` as preloaded. Read `installer/context-router.json` and
the source version files, then choose the current installation stage. Inspect
the target before loading stage-specific sources. The router names required
rule owners, installer documents, templates, checks, and expansion triggers.

For a new installation or upgrade, compare
`framework/file-inventory.json`, file hashes, and rule registries first. Read
changed or selected canonical sources and affected target surfaces only.
Unchanged framework files do not need to be loaded merely to preserve or copy
them.

When target evidence selects an optional module, route to its owner rather than
preloading it. Examples include `framework/project-vocabulary.md`,
`framework/test-first-development.md`, and `framework/extensions.md` before
creating their vocabulary, test-first, or `alatyr-extension.json` surfaces.

Load target templates from `templates/target` only for surfaces the plan will
create or compare, and keep them as placeholders until rewritten from target
evidence.

## Rule References

This flow is derived from canonical framework rules. Keep long policy wording
in the owning framework documents and use these IDs for installation routing:

- `ALATYR-CONTEXT-001`
- `ALATYR-SOURCE-001`
- `ALATYR-RISK-001`
- `ALATYR-APPROVAL-001`
- `ALATYR-SAFETY-001`
- `ALATYR-SAFETY-002`
- `ALATYR-ADAPTER-001`
- `ALATYR-MODULE-001`
- `ALATYR-OPERATION-001`
- `ALATYR-ARCHITECTURE-001`
- `ALATYR-CODEDOC-001`
- `ALATYR-VOCABULARY-001`
- `ALATYR-TDD-001`
- `ALATYR-EXTENSION-001`
- `ALATYR-DIAGRAM-001`
- `ALATYR-TEAM-001`
- `ALATYR-ENGINEERING-EVIDENCE-001`
- `ALATYR-LIFECYCLE-001`
- `ALATYR-EVIDENCE-001`

## Required Target Context

Read in the target repository:

- existing AI instructions and bridge files
- existing CODEOWNERS or equivalent file-owner metadata
- README and public docs
- architecture/design docs, decision records, documented patterns,
  boundaries, constraints, quality attributes, and architecture validation
- source roots, languages, frameworks, existing structured comments,
  docstring conventions, public symbol boundaries, generators, documentation
  sites, generated-reference outputs, and documentation lint/publication rules
- existing glossaries, terminology docs, acronym lists, domain language,
  naming rules, data dictionaries, schemas, APIs, ambiguous terms, deprecated
  wording, and terminology validation
- package/build/dependency files
- tests, fixtures, test helpers, test-first/TDD policy, regression history,
  levels, commands, isolation, exceptions, feedback time, CI, and merge gates
- local validation commands or manual validation policy
- security, live-service, credential, and destructive-operation policies
- diagram sources, generated files, and visual artifacts
- existing prompts, skills, third-party assistant infrastructure, provenance
  notes, source-access policies, gates, checker rules, operation help, routing
  flows, and assistant chat-message templates
- existing AI infrastructure router entries, item IDs, permissions, gates,
  output contracts, conflicts, wrappers, recommendation records, and adaptation
  records
- existing `alatyr-extension.json` packages, extension catalog and lock,
  immutable source revisions, digests, bindings, installed-file ownership,
  conflicts, local modifications, dependents, and lifecycle evidence
- existing target development-pattern index, evidence owner, retention/privacy
  policy, and references to recurring requests, corrections, reviews, rework,
  validation failures, or context expansion
- existing manifests, version notes, context profiles, approval records, and
  prompt-injection or imported-source policies
- existing source-of-truth registry, maturity profile, bridge capability
  matrix, and migration notes
- existing fact IDs, consistency maps, relationship coverage, and staleness
  evidence
- existing team roles, stable actor IDs, display-name mappings, local identity,
  decision authority, priority and transition policy, issue/task tracker,
  active work, claims, branch/worktree conventions, backend atomic-write
  capability, review and merge rules, checkpoints, handoffs, decisions,
  coordination storage, retention, and privacy policy

## Ownership Classification

Classify every proposed target file:

- framework core: portable Alatyr Core rules copied or adapted into
  `.ai/framework`
- project fact: target product/code/business/data/runtime fact
- repository adapter fact: local assistant workflow, prompt, gate, skill,
  bridge, validation, or final-evidence rule
- bridge/wrapper: assistant-specific pointer to canonical target files
- skill or prompt artifact: adapter-owned assistant infrastructure that must be
  normalized to target facts before becoming canonical
- generated/visual artifact: output whose source must be named
- existing target-owned file: preserve unless approval permits overwrite

## Steps

1. Inspect the target repository before creating files.
2. Optionally use source-repository scaffolding only to preview or create
   placeholder structure. Select the smallest `core`, `standard`, or `full`
   support profile justified by the installation plan, and record the
   selection in the target manifest. Select the matching `core`, `standard`,
   or `complete` framework pack, expanding it when enabled modules require
   additional rule owners. Verify that projected manifest, router, operation,
   capability, rule-registry, ownership, and inventory claims reference only
   installed files. Do not treat scaffolding, profile selection, or pack
   selection as installation or module enablement.
3. Fill `installer/readiness-checklist.md` for the target.
4. Prepare an installation plan from
   `installer/installation-plan-template.md`.
5. Record the current logical installation scope and the action phases
   authorized by the newest user request. Installation intent does not imply
   commit, push, release, deployment, or another live action. Apply
   `ALATYR-AUTHORIZATION-001` before each state-changing phase.
6. Identify protected changes and required approvals.
7. If approval is required, stop until the programmer confirms it.
8. Create or adapt target `AGENTS.md` and `AI_ASSISTANTS.md`.
9. Create or preserve `CODEOWNERS` or equivalent owner metadata when the
   target supports file ownership.
10. Create or adapt target `.ai/alatyr.yaml` or equivalent manifest with
   framework version, adapter schema version, template version, owner,
   backup owner, review cadence, CODEOWNERS or equivalent owner map,
   source-of-truth, validation, known gaps, and local deviations.
11. Create or adapt target `.ai/README.md`.
12. Copy or adapt the selected portable framework pack into target
    `.ai/framework`. Record the pack in the manifest and preserve its projected
    rule registry, ownership map, and file inventory. Use `complete` when all
    portable Markdown and JSON files are installed.
13. Create target `.ai/project/contour.md` and target project
   source-of-truth docs from target facts.
    Create `.ai/project/engineering-evidence/README.md` and `index.json` as
    required core surfaces. Resolve the target owner, retained storage mode,
    external-contribution policy, redaction policy, and record access. Start
    with an empty index unless bounded historical records are explicitly
    reviewed; never infer past engineering decisions from the current tree.
    Add `.ai/project/development-evidence.json` only when the target enables
    pattern-based AI infrastructure recommendations. Start with an empty index
    unless bounded historical evidence is explicitly reviewed; never copy raw
    conversations, secrets, credentials, or personal data.
    Add `.ai/project/debug/README.md`, `index.json`, and an empty `records/`
    directory only when the target enables `debug-mode`. Resolve the owner,
    non-canonical authority, storage, visibility, retention, redaction, and
    external-patch policy. Start empty unless bounded historical records were
    explicitly validated; never reconstruct attribution from a final diff or
    raw conversation history.
    Add `.ai/project/consistency-map.json` only when the target enables bounded
    relationship routing. Give every live source-of-truth registry Fact Type
    one resolved, unique map node whose `fact_type` matches exactly; populate
    edges from target evidence or record the module as blocked or deferred.
    Route the human registry and machine map together for semantic work, keep
    redundant portable explanation conditional, and measure the composed
    semantic route before accepting its context budget.
    Add `.ai/project/architecture/README.md` and
    `.ai/project/architecture/catalog.json` only when architecture knowledge is
    enabled. Derive owner, decision authority, item states, selected evidence,
    validation, and evidence revision from the target; never promote observed
    implementation to accepted architecture by inference.
    Add `.ai/project/documentation/README.md`, `catalog.json`, and
    `profiles.json` only when code documentation is enabled. Derive separate
    source-set profiles from target language, framework, existing comment,
    generator, ownership, output, and validation evidence. Record profiles as
    proposed until target decision authority accepts them; never seed one
    repository-wide style by assumption.
    Add `.ai/project/vocabulary/README.md`, `catalog.json`, `terms.json`, and
    `data-dictionary-links.json` only when project vocabulary is enabled.
    Derive scoped terms, aliases, acronyms, owners, states, canonical sources,
    and links from target evidence; never infer acceptance from frequency.
    When workspace roles require distinct perspectives, add
    `.ai/project/workspace-modes/catalog.json`, optional shared root support,
    and one directory per actual mode. Inspect workspace, package, framework,
    skeleton, and ownership evidence and propose zero or more modes. Keep every
    suggestion proposed until a separate user decision accepts it;
    installation approval alone is not acceptance.
    Add `.ai/project/testing/README.md` and `test-first-policy.json` only when
    test-first development is assessed or enabled. Derive owners, trigger
    severity, modes, levels, commands, isolation, exceptions, and evidence from
    the target; never infer strict TDD from the presence of tests.
    Add `.ai/project/team-policy.json` and its human explanation only when the
    target enables team collaboration. Derive actor IDs, display names and
    aliases, authority, priorities, transitions, review, identity verification,
    backend, synchronization, storage, retention, and privacy from evidence.
14. Create target `.ai/assistant/contour.md`, generated hash-bound bootstrap
    index, compact context router, routed gate index/fragments, and selected
    lazy descriptors, operation catalog and checked compact operation
    index, context profiles, module profile, task-specific maturity profile,
    bridge capability matrix, generated assistant-capability index, installed-
    surface capability records, and minimal workflows/gates from target facts.
    Route enabled team operations and matched state-changing work through the
    lazy `.ai/assistant/team/context-overlay.json`. Read the compact active-work
    index first; do not put full team state in bootstrap.
    The router must distinguish host-preloaded instructions from the generated
    compact bootstrap, define context budgets and receipts, and route project-area
    overlays without putting full project sources or the operation catalog in
    mandatory bootstrap. Keep the manifest, project map, and router as hashed
    recovery sources rather than routine startup context. Add compact per-profile candidates and intent
    overlays, resolve exact IDs/aliases through the index, and load the full
    catalog only for the bare Alatyr entry, ambiguity, or repair. Add
    the `large-or-resumable` task-scale overlay only when the target enables
    large-task orchestration.
    Add the `change-package` overlay only when the target enables coherent
    material-change evidence. Keep package records outside routine bootstrap.
    Add the `debug-mode` task-scale overlay only when the optional module and
    its `effectiveness-metrics` and `installed-operations` dependencies are
    enabled. Keep unrelated records outside context and require explicit
    current-task/session activation before record writes.
    Add the `team-active` overlay only when team collaboration is enabled. Run
    its compact index preflight before state-changing operations, then keep the
    full registry, policy, and unrelated tasks outside routine bootstrap.
    Add the `code-documentation` intent overlay only when the optional module
    is enabled. Keep its full profiles, selected source, generator
    configuration, and generated output outside routine bootstrap.
    Add the `vocabulary-request` intent overlay only when project vocabulary is
    enabled. Keep full term records and data links outside routine bootstrap.
    Add the `test-first-request` intent overlay when configuration is supported
    or the module is enabled. Keep policy, flows, skill, and evidence outside
    routine bootstrap; use existing testing guidance for the compact suggestion
    gate.
    Add the `extension-request` intent overlay when extension inspection or
    lifecycle management is supported. Keep package items, unrelated lock
    entries, and installed extension records outside routine bootstrap.
    Add the `dependency-knowledge-request` intent overlay only when passive
    package knowledge is enabled. Keep package-manager graphs, raw dependency
    docs, nested adapters, unrelated packages, and historical snapshots
    outside routine bootstrap.
    Add the `workspace-mode-request` intent overlay only when workspace modes
    are enabled. Read the compact catalog after bootstrap and before the task
    profile; load one selected descriptor plus applicable root context and ask
    on ambiguity. Do not load all mode directories or activate nested adapters.
15. Add bridge files only for assistants the target uses.
16. Add installed-operation, operation-help, automatic operation-routing,
    current-scope action-authorization policy,
    read-only adapter-health, risk-gated pre-change preview,
    diagram-discussion flow, ASCII layout template, and presentation template
    when the diagrams module is enabled,
    architecture-assistance flow, architecture pattern/area/result templates,
    and lazy intent routing when architecture knowledge is enabled,
    code-documentation catalog/profiles, profile-review template, adapted
    skill, documentation flow, and lazy intent routing when code documentation
    is enabled,
    vocabulary catalog/records/data links, term-review template, adapted
    skill, vocabulary flow, and lazy intent routing when project vocabulary is
    enabled,
    test-first configuration/change flows, target policy, recommendation gate,
    RED/GREEN evidence template, adapted skill, and lazy intent routing when
    test-first development is assessed or enabled,
    extension catalog and lock, lifecycle flow, gate, package-review template,
    lifecycle-record template, and lazy intent routing when extensions are
    supported,
    dependency knowledge policy, catalog, exact package-instance knowledge
    lock, deviations, retention-aware snapshot directory, synchronization
    flow, gate, report template, operation, and lazy intent routing when
    passive dependency knowledge is enabled,
    workspace-mode catalog, optional root support, per-mode authoring
    template, intent, flow, gate, suggestion, preflight, and operation when
    workspace modes are enabled,
    AI-infrastructure-inventory, AI-infrastructure-recommendation, adapter output contract
    `.ai/assistant/templates/adapter-output-contracts.md`, source-access
    policy, prompt-injection policy, human and machine-readable approval-record
    templates, migration-note
    template, blueprint-creation, adapter-recheck, and post-install/update
    chat-message templates when the target wants
    post-install operation requests or AI infrastructure adaptation.
    Add the large-task flow and operation-packet template when the target needs
    cross-boundary, multi-workstream, budget-exceeding, or resumable work, and
    record the target packet storage policy.
    Add the target delegation policy, delegated-execution overlay, delegation
    flow, and packet template only when subagent delegation is enabled. Record
    each surface's native, external, suggestion-only, or unsupported dispatch
    backend; any external dispatcher AI-infrastructure item; model override,
    parallelism, actual-model evidence, verified role bindings, write/tool
    boundaries, fallback, privacy, validation, and primary convergence.
    Add the change-package index, flow, machine record, and redacted report
    template when the target needs semantic multi-surface approval, architecture
    segment/capability evidence, audit, pilot, or publishable provenance. Record
    retention and redaction policy; do not seed historical records.
    Add the durable engineering-evidence task-scale overlay, capture flow,
    gate, and machine record template in every accepted core profile. Keep
    them lazy and separate from change-package activation.
    Add the Debug Mode overlay, operation, flow, gate, machine record, and
    compact summary only when the optional module is enabled. Record explicit
    activation/expiry, privacy, capture-quality, timing, event attribution,
    structured architectural impacts, direction-change hypothesis/replacement
    causality, metric derivation, exact durable engineering-evidence reference
    resolution, external projection, active-versus-finalized comparison, and
    validator policy. Enabling the module does not activate observation for a
    task.
    When the target uses multiple AI infrastructure items, add
    `.ai/assistant/ai-infrastructure-router.json`, the recommendation flow and
    report template, lazy development-evidence capture flow, and the
    adaptation-record template. Populate item contracts from target evidence
    and keep unresolved items blocked. Target evidence may improve target-owned
    AI infrastructure but must not directly change `.ai/framework`, AlatyrCore
    source, or portable rules.
    When the target enables team collaboration, add `.ai/.gitignore`, structured
    policy, registry metadata, active-work index, backend contract, per-task
    record template, identity/task/handoff/decision/review flows, team gate,
    adapted skill, and identity/checkpoint/handoff/decision templates. Start
    task storage empty unless target records are explicitly reviewed. On
    upgrade, preserve task IDs, actor references, claims, decisions, handoffs,
    external links, and ignored local identity. Migrate schema-1 task arrays to
    schema-2 task files and regenerate the index as one planned operation;
    never replace active state with placeholders.
17. Ensure root assistant entry points and supported bridge files point future
    sessions to the installation note, compact help, operation catalog, and
    routing flow. Expose `Alatyr` as the single conversational entry and
    `Alatyr status` or `Alatyr doctor` as read-only health aliases on every
    supported surface.
    Team and current-actor aliases route through the same canonical catalog
    when the optional module is enabled; bridge files do not duplicate team or
    identity policy.
    When diagrams are enabled, route `Alatyr diagram` through the canonical
    flow and record native inline, rendered-artifact, ASCII-baseline,
    client-version, freshness, and evidence fields separately for every
    supported surface. Record diagram classification/redaction, external
    renderer approval, artifact retention/sharing, and stable revision lineage.
    When architecture knowledge is enabled, route `Alatyr architecture` and
    inventory/explain/discuss/compare/review/document aliases through the
    canonical catalog and compact architecture index.
    Route extension aliases through the same canonical operation catalog on
    every supported surface. Package inspection remains read-only; install,
    update, disable, and remove require target-owned lifecycle evidence.
    When Debug Mode is enabled, route enable/status/checkpoint/summary/disable/
    compare aliases through the same catalog on every supported assistant
    surface. Bridges do not store activation state or duplicate privacy and
    attribution policy.
18. Add prompts, skills, diagrams, or consistency checks only when they solve
    target friction, can be maintained, and have been adapted to target facts.
19. Run target validation that exists. Do not invent commands.
20. Apply logical integrity review: changed facts, re-derived invariants,
    reconciled review-item clusters, affected contracts, source of truth,
   repair direction, and residual risk.
21. Apply the durable engineering-evidence capture decision. For installation
    itself, capture only when reusable non-obvious target-adaptation knowledge
    would otherwise be lost; otherwise record the specific skip reason.
22. Classify final evidence as `current-state`, `historical-record`, or `mixed`.
    Do not infer past installation, approval, or validation actions only from
    files that exist in the current tree.
23. Report final evidence.
24. Send the appropriate post-install or post-update assistant chat message
    using the target template when installed. Name the single `Alatyr` entry,
    read-only health aliases, automatic routing, and risk-gated preview.
    Name team/current-actor aliases, attribution limits, and module state when
    team collaboration is enabled.
    When workspace modes are enabled, report proposed and accepted modes
    separately, state that installation/update did not accept proposals, and
    name the mode status, suggestion, selection, and acceptance aliases.
    When Debug Mode is enabled, state that it remains inactive until explicitly
    enabled for one task/session and name its status, summary, and disable
    aliases plus the target storage and external-patch boundary.

## Human Approval Gate

Advice and planning do not require approval.

Use `ALATYR-APPROVAL-001` for protected-change approval. Classify protected
scope with `ALATYR-RISK-001`, `ALATYR-SAFETY-001`, and
`ALATYR-SAFETY-002`, then apply the target adapter's stricter local policy
when it exists.

Preferred approval:

```text
APPROVE ALATYR INSTALLATION: <installation-id>
```

When protected-change scope spans multiple files or plan versions, record the
approval using the target human and machine-readable approval-record
templates. Bind the machine record to the approved diff base, explicitly
select it for enforcement, and require every changed path to be allowed and no
changed path to be excluded.
For an activated change package, also bind allowed changed-fact IDs,
architecture areas, behavior categories, excluded semantic effects, and
permitted external effects. A path match does not authorize semantic drift.

## Validation Rule

Alatyr Core has no universal validation command.

Use target repository commands only when they are discovered in the target.
If target validation is missing, manual, or unavailable, report the unresolved
check and residual risk.

For adapter structure, use `migration-staging` only as an intermediate rewrite
check. It may retain target placeholders and exit zero, but it is never
accepted or ready. Before reporting installation or update completion:

1. Resolve placeholders on required core surfaces and every live surface owned
   by an enabled capability. Preserve placeholders only in explicit reusable
   authoring templates.
2. Synchronize manifest `modules.enabled` with exactly one matching human
   module-profile block in `enabled` or `required` state.
3. Synchronize machine policy indexes and their human README projections.
4. Run strict `acceptance` validation on the checked-out target branch and
   record that branch and exact revision. Repeat this final step separately on
   any other branch whose adapter state is to be accepted.

## Final Evidence

Report:

- evidence basis, observation time, checked-out branch, and repository revision
  when available
- adapter validation phase, active unresolved-placeholder count,
  manifest/module-profile agreement, acceptance eligibility, and required
  strict rerun when staging was used
- dated historical records used and historical claims that remain unverifiable
- installation id and approval used, if any
- `current_user_authorization`: logical installation scope, source request,
  authorized and unauthorized phases, invalidated prior authorization, and
  repository, history, publication, or live actions actually performed
- framework version, adapter schema version, template version, and manifest
  path
- adapter owner, backup owner, review cadence, and CODEOWNERS or equivalent
  owner map status
- scaffolding helper used or skipped
- target repository inspected
- framework core files installed or adapted
- project adapter files rewritten from target facts
- consistency map enabled, skipped, or blocked with relationship gaps recorded
- existing files preserved, skipped, or overwritten with approval
- supported assistant bridges added or skipped
- operation catalog and checked compact index, installed-operation,
  operation-help, automatic routing, current-scope action authorization,
  read-only health, risk-gated preview,
  diagram-discussion flow, ASCII template, and presentation template when enabled,
  architecture index/catalog, discussion flow, pattern/area/result templates,
  and intent routing when enabled,
  AI-infrastructure-inventory, AI-infrastructure-recommendation, adapter output
  contract, context router,
  context profiles, module profile, source-of-truth registry, task-specific
  maturity profile, bridge capability matrix, compact assistant-capability
  projection, source-access policy,
  prompt-injection policy, human and machine-readable approval-record
  templates, migration-note template,
  blueprint-creation, adapter-recheck, and post-install/update chat-message
  templates added or skipped
- large-task orchestration flow, operation packet, and target storage policy
  added or skipped
- subagent delegation policy, overlay, flow, packet, per-surface capability
  evidence, role/model bindings, fallback, and validation added or skipped
- change-package index, lazy overlay, flow, schema, redacted report, retention
  policy, and validator support added, migrated, skipped, or blocked
- durable engineering-evidence owner, policy, compact index, lazy overlay,
  capture flow, gate, record schema, validator, existing-record preservation,
  and current installation capture decision
- Debug Mode module state, dependency closure, owner, non-canonical storage,
  explicit activation/expiry, compact index, lazy overlay, operation, flow,
  gate, record/summary templates, privacy/timing/attribution/metrics policy,
  structured architectural impacts, direction-change hypothesis/replacement
  causality, exact durable engineering-evidence reference resolution, active-
  versus-finalized comparison, clean-upstream boundary, validator, and
  existing-record preservation
- team collaboration policy and operating model, ignored local identity,
  backend capabilities and synchronization, active-work index, registry/task
  schemas, optimistic concurrency, team-active overlay, identity/task/handoff/
  decision/review flows, team gate, skill, templates, active-record
  preservation, and privacy policy added, migrated, skipped, or blocked
- AI infrastructure router, recommendation flow/report, and adaptation-record
  template added or skipped
- development-evidence index, owner, retention/privacy policy, and lazy capture
  flow added or skipped without claiming unavailable history
- root entry-point and bridge compact-bootstrap references checked
- context budgets, task-scale/project-area overlays, and receipt fields adapted or
  explicitly deferred
- static context-cost baseline reviewed and runtime context evidence requested
  or explicitly unavailable
- prompts, skills, or third-party assistant infrastructure adapted or skipped
- AI infrastructure item IDs, canonical sources, permissions, gates,
  validation, outputs, conflicts, and adaptation records resolved or reported
  as gaps
- recommendation policy separates project-contour need/outcome evidence from
  assistant-contour item mechanics and evaluates existing items before new ones
- pattern-based recommendation evidence names selected target pattern IDs and
  does not turn target observations into portable framework changes
- target validation run and skipped
- unresolved adapter facts
- logical integrity review result
- changed facts, selected/skipped relationships, companion surfaces checked,
  and unresolved consistency gaps
- residual risk
- post-install or post-update assistant chat message sent or skipped with
  reason
- diagram discussion module state, portable ASCII layout/width, per-assistant
  rich-presentation capability, freshness or expiry, captured-result evidence, and
  source-revision policy when enabled
- architecture knowledge module state, owner, decision authority, catalog
  revision, item-state coverage, validation, and known gaps when enabled
