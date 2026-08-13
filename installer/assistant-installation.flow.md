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

Read in this repository first:

- `README.md`
- `AGENTS.md`
- `INSTALL.md`
- `framework/README.md`
- `framework/context-profiles.md`
- `framework/context-router.md`
- `framework/project-adapter-contract.md`
- `framework/portability.md`
- `framework/module-profile.md`
- `framework/architecture-knowledge.md`
- `framework/code-documentation.md`
- `framework/project-vocabulary.md`
- `framework/test-first-development.md`
- `framework/extensions.md`
- `framework/rule-ownership.md`
- `framework/rule-registry.md`
- `framework/rule-registry.json`
- `installer/readiness-checklist.md`
- `installer/installation-plan-template.md`

Then inspect the target repository and load additional source files from the
smallest matching installation scope. For a new full-core installation, use a
deterministic framework file list and inspect rule owners as needed without
loading all prose into one context. For an upgrade, compare file hashes and
rule registries first, then read changed or added canonical sources and their
affected target surfaces. Unchanged framework files do not need to be loaded
again merely to preserve or copy them, and the full framework remains outside
the compact startup set, not as a default bootstrap.

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
- existing team roles and stable actor IDs, decision authority, priority
  policy, issue/task tracker, active work, claims, branch/worktree
  conventions, review and merge rules, checkpoints, handoffs, decision
  records, coordination storage, retention, and privacy policy

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
   selection in the target manifest. Verify that projected manifest, router,
   operation, and capability claims reference only files present in that
   profile. Do not treat scaffolding or profile selection as installation or
   module enablement.
3. Fill `installer/readiness-checklist.md` for the target.
4. Prepare an installation plan from
   `installer/installation-plan-template.md`.
5. Identify protected changes and required approvals.
6. If approval is required, stop until the programmer confirms it.
7. Create or adapt target `AGENTS.md` and `AI_ASSISTANTS.md`.
8. Create or preserve `CODEOWNERS` or equivalent owner metadata when the
   target supports file ownership.
9. Create or adapt target `.ai/alatyr.yaml` or equivalent manifest with
   framework version, adapter schema version, template version, owner,
   backup owner, review cadence, CODEOWNERS or equivalent owner map,
   source-of-truth, validation, known gaps, and local deviations.
10. Create or adapt target `.ai/README.md`.
11. Copy or adapt portable framework files into target `.ai/framework`,
    including `framework/*.md` and `framework/rule-registry.json`.
12. Create target `.ai/project/contour.md` and target project
   source-of-truth docs from target facts.
    Add `.ai/project/development-evidence.json` only when the target enables
    pattern-based AI infrastructure recommendations. Start with an empty index
    unless bounded historical evidence is explicitly reviewed; never copy raw
    conversations, secrets, credentials, or personal data.
    Add `.ai/project/consistency-map.json` only when the target enables bounded
    relationship routing; populate fact IDs and edges from target evidence or
    record the module as blocked or deferred.
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
    Add `.ai/project/testing/README.md` and `test-first-policy.json` only when
    test-first development is assessed or enabled. Derive owners, trigger
    severity, modes, levels, commands, isolation, exceptions, and evidence from
    the target; never infer strict TDD from the presence of tests.
    Add `.ai/project/team-operating-model.md` only when the target enables team
    collaboration. Derive actor IDs, authority, priorities, review,
    coordination backend, synchronization, storage, retention, and privacy
    from target evidence.
13. Create target `.ai/assistant/contour.md`, compact context router and
    selected lazy descriptors, operation catalog and checked compact operation
    index, context profiles, module profile, task-specific maturity profile,
    bridge capability matrix, generated assistant-capability index, installed-
    surface capability records, and minimal workflows/gates from target facts.
    Route enabled team operations through the lazy
    `.ai/assistant/team/context-overlay.json`, not routine bootstrap.
    The router must distinguish host-preloaded instructions from compact
    bootstrap, define context budgets and receipts, and route project-area
    overlays without putting full project sources or the operation catalog in
    mandatory bootstrap. Add compact per-profile candidates and intent
    overlays, resolve exact IDs/aliases through the index, and load the full
    catalog only for the bare Alatyr entry, ambiguity, or repair. Add
    the `large-or-resumable` task-scale overlay only when the target enables
    large-task orchestration.
    Add the `change-package` overlay only when the target enables coherent
    material-change evidence. Keep package records outside routine bootstrap.
    Add the `team-active` overlay only when team collaboration is enabled. Keep
    the full work registry and unrelated active tasks outside routine
    bootstrap.
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
14. Add bridge files only for assistants the target uses.
15. Add installed-operation, operation-help, automatic operation-routing,
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
    Add the change-package index, flow, machine record, and redacted report
    template when the target needs semantic multi-surface approval, architecture
    segment/capability evidence, audit, pilot, or publishable provenance. Record
    retention and redaction policy; do not seed historical records.
    When the target uses multiple AI infrastructure items, add
    `.ai/assistant/ai-infrastructure-router.json`, the recommendation flow and
    report template, lazy development-evidence capture flow, and the
    adaptation-record template. Populate item contracts from target evidence
    and keep unresolved items blocked. Target evidence may improve target-owned
    AI infrastructure but must not directly change `.ai/framework`, AlatyrCore
    source, or portable rules.
    When the target enables team collaboration, add the work registry,
    task-coordination, handoff, decision, and review flows, team gate, and
    checkpoint/handoff/decision templates. Initialize active tasks as empty
    unless target records are explicitly reviewed. On upgrade, preserve task
    IDs, actor references, claims, decisions, handoffs, and external links;
    never replace active state with source placeholders.
16. Ensure root assistant entry points and supported bridge files point future
    sessions to the installation note, compact help, operation catalog, and
    routing flow. Expose `Alatyr` as the single conversational entry and
    `Alatyr status` or `Alatyr doctor` as read-only health aliases on every
    supported surface.
    Team aliases route through the same canonical catalog when the optional
    module is enabled; bridge files do not duplicate the team policy.
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
17. Add prompts, skills, diagrams, or consistency checks only when they solve
    target friction, can be maintained, and have been adapted to target facts.
18. Run target validation that exists. Do not invent commands.
19. Apply logical integrity review: changed facts, re-derived invariants,
    reconciled review-item clusters, affected contracts, source of truth,
    repair direction, and residual risk.
20. Classify final evidence as `current-state`, `historical-record`, or `mixed`.
    Do not infer past installation, approval, or validation actions only from
    files that exist in the current tree.
21. Report final evidence.
22. Send the appropriate post-install or post-update assistant chat message
    using the target template when installed. Name the single `Alatyr` entry,
    read-only health aliases, automatic routing, and risk-gated preview.
    Name team aliases and module state when team collaboration is enabled.

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

## Final Evidence

Report:

- evidence basis, observation time, and repository revision when available
- dated historical records used and historical claims that remain unverifiable
- installation id and approval used, if any
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
  operation-help, automatic routing,
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
- change-package index, lazy overlay, flow, schema, redacted report, retention
  policy, and validator support added, migrated, skipped, or blocked
- team collaboration operating model, coordination backend and synchronization
  direction, work registry, team-active overlay, task/handoff/decision/review
  flows, team gate, templates, active-record preservation, and privacy policy
  added, migrated, skipped, or blocked
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
