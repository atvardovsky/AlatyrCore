---
alatyr_doc:
  id: framework.module-profile
  type: framework-rule-owner
  owns_rules:
    - ALATYR-MODULE-001
  depends_on:
    - ALATYR-ADAPTER-001
  applies_to:
    - framework-upgrade
---
# Module Profile

Module profiles keep Alatyr Core from treating every capability as mandatory
for every target repository.

The framework has a required core profile and optional modules. A target
adapter records which modules are enabled, deferred, disabled, or not
applicable from target evidence.

The installed `capabilities.json` catalog is the machine-readable owner for
optional-module dependencies, minimum framework packs, required target files,
rule IDs, and deterministic check IDs. Human module profiles explain target
state and evidence; they must not redefine that closure independently.

Scaffolding may begin with no optional modules and add an explicit dependency
closure through selected capability IDs. The target validator should dispatch
deep optional checks only for enabled modules or explicit module evidence.
Universal manifest, contour, routing, safety, framework-drift, and final-
evidence checks remain independent of optional module selection.

## Required Core Profile

Every accepted installation should provide:

- contour separation for framework, project, and repository adapter facts
- adapter manifest with framework version, adapter schema version, template
  version, owner, supported assistants, known gaps, and local deviations
- adapter ownership metadata with responsible owner, backup owner, review
  cadence, last review date, and CODEOWNERS or equivalent file-owner map when
  supported
- context profiles with a generated hash-bound bootstrap index, task-specific
  expansion rules, routed gate fragments, a compact router, and selected lazy
  profile descriptors
- source-of-truth registry or explicit missing owner records for important
  fact types
- change-risk classification and approval triggers
- current-scope action authorization that separates inspection, working-tree
  modification, local Git mutation, publication, and live external effects;
  expires prior-scope authorization; and does not infer one phase from another
- logical integrity review for changed semantic or logical facts
- validation or manual-review evidence, including unresolved checks
- final evidence format
- durable engineering-evidence capture decision, compact index, target storage
  policy, and record validation for material tasks
- project-knowledge promotion review, canonical-owner update, compact sharded
  routing index, two-stage bounded delivery, freshness, conflict, supersession,
  and paired reuse evidence

If any required core item is missing, the adapter can still exist, but it must
report the missing item as a gap before claiming maturity.

## Optional Modules

Optional modules are enabled only when the target repository needs and can
maintain them:

- `blueprint-change`: blueprint-driven product-change workflow and project
  blueprint creation or repair.
- `consistency-map`: machine-readable changed-fact relationships and bounded
  impact closure for targets with many project areas or competing surfaces.
- `architecture-knowledge`: project-owned architecture index and compact
  catalog, pattern and area records, evidence-based architecture discussion,
  alternative comparison, review, documentation maintenance, and accepted
  decision handoff.
- `code-documentation`: project-owned documentation catalog and multiple
  source-set profiles for evidence-backed comment-style proposals, structured
  comment maintenance, target-specific deterministic generation, and derived
  output validation without loading all code documentation by default.
- `project-vocabulary`: project-owned compact terminology catalog, scoped term
  records, aliases, acronyms, ambiguity states, and links to canonical data or
  project facts without loading the complete vocabulary by default.
- `test-first-development`: target-owned test-first policy, bounded
  recommendation triggers, explicit enablement, RED/GREEN/refactor evidence,
  justified exceptions, and a project-adapted execution skill.
- `extensions`: declarative external assistant-infrastructure packages with
  read-only inspection, target normalization, compact catalog, immutable
  source and installed-file lock, permissions, lifecycle evidence, safe update,
  and ownership-aware removal.
- `dependency-knowledge`: passive package-owned public knowledge exports,
  exact artifact binding, target-owned trust/freshness/authority/applicability
  projection, bounded graph synchronization, deviations, retention, lazy
  explanation, and impact routing without activating nested adapters.
- `workspace-modes`: user-owned workspace identity, accepted development modes,
  explicit framework/application/library/skeleton/dependency relationships,
  optional shared root context, one directory per mode, evidence-based
  installation suggestions, bounded selection, and pre-change mode evidence.
- `diagrams`: diagram source, visual artifact, render or manual-review, drift,
  discussion presentation, generated capability index, per-assistant
  capability/freshness records, captured result conformance, security/privacy,
  stable revision lineage, portable ASCII layout/width, and optional rich
  presentation policy.
- `ai-infrastructure`: inventory, source access, prompt-injection handling,
  evidence-based recommendations, routed skill/prompt/gate/checker/tool/MCP/
  bridge selection, target development-pattern evidence and lazy capture,
  adaptation records, wrappers, permissions, output contracts, and provenance.
- `multi-assistant-bridges`: bridge capability matrix and assistant-specific
  wrappers for multiple supported assistants.
- `installed-operations`: post-install operation requests, machine-readable
  catalog, single entry, automatic routing, read-only health, risk-gated
  preview, adapter recheck, help, and chat-message templates.
- `large-task-orchestration`: task-scale routing, operation packets,
  workstreams, resumable checkpoints, and final convergence evidence for
  repositories that need large or multi-session changes.
- `subagent-delegation`: capability-gated decomposition into bounded,
  independently verifiable tasks, target-owned worker roles/prompts and
  assistant role/model/native bindings, deterministic readiness, normalized
  results, disjoint writes, retry/conflict fallbacks, and primary convergence.
- `change-packages`: coherent material-change evidence with semantic approval
  scope, companion-surface decisions, implementation corrections, compact
  architecture discussion, and before-to-after repository provenance.
- `team-collaboration`: target-owned actor and priority model, shared work
  registry, advisory claims, changed-fact overlap review, checkpoints,
  handoffs, decisions, team review, and revision-bound merge readiness for
  concurrent human and assistant work.
- `durable-approvals`: human and machine-readable approval-record storage plus
  strict diff-base/path-scope enforcement for protected changes that need plan,
  scope, or file evidence.
- `migration-diff`: human migration notes, framework baseline comparisons, and
  a machine-readable delta-first upgrade impact router.
- `effectiveness-metrics`: comparable task reporting for measuring framework
  usefulness.
- `debug-mode`: explicitly activated task/session observability with compact
  origin-attributed events, timing and capture-quality evidence, event-derived
  human-supervision metrics, structured architectural impacts, causal
  hypothesis replacement for direction changes, exact durable engineering-
  evidence references, completed-record comparison, clean-upstream projection,
  and non-canonical storage. It depends on `effectiveness-metrics` and
  `installed-operations`.
- `scaffolding`: optional source-repository scaffolding helpers used only to
  create placeholder structure.

Targets may add local modules when they record the owner, enabled state,
required files, validation, and residual risk.

The manifest and human module profile are one projected contract. Every module
listed in `modules.enabled` must have exactly one matching profile block in
`enabled` or `required` state. A profile block in either state must be listed
in the manifest. Migration staging may expose disagreement as repair work, but
strict adapter acceptance must reject it.

## Module States

Use these states in target adapters:

- `required`: part of the required core profile.
- `enabled`: installed and maintained for the target.
- `deferred`: useful, but intentionally postponed with a recorded reason.
- `disabled`: not used by the target.
- `not-applicable`: irrelevant to the target's current shape.
- `blocked`: needed, but missing owner, policy, approval, or validation.

Do not hide missing adapter facts by marking a needed module as disabled.

## Installation Use

During installation or update:

1. Establish the required core profile first.
2. Select optional modules from target needs, not from source-repository
   availability.
3. Record module states in the target adapter manifest and module profile.
4. Select and record the `core`, `standard`, or `full` support profile, then
   create only the target templates needed for enabled or required modules.
5. Select a compatible `core`, `standard`, or `complete` framework pack. The
   pack controls installed portable files, while context routing controls what
   is loaded for a task. A smaller pack must never be used to claim support for
   a broader profile or enabled module.
6. Leave deferred, disabled, not-applicable, or blocked modules in evidence
   with the reason and next safe action.

Optional modules must not add target project facts from guesses or from another
repository.

## Evidence

A module profile review should report:

```text
Core profile state: <complete/missing gaps>
Adapter ownership: <owner/cadence/CODEOWNERS or equivalent/gaps>
Framework pack: <core/standard/complete and expansion needs>
Enabled modules: <modules>
Deferred modules: <modules and reasons>
Blocked modules: <modules and missing owners/policies/validation>
Files created or skipped: <target adapter surfaces>
Validation: <target checks or manual review>
Residual risk: <unresolved module gaps>
```

## Rejection Criteria

Reject module-profile work that:

- treats optional modules as mandatory for every target
- claims a module is enabled without owner, context, validation, and evidence
- enables test-first development without an accepted target policy, concrete
  commands, isolation rules, trigger modes, exception handling, and RED/GREEN
  evidence requirements
- enables extensions without immutable provenance, license and compatibility
  review, resolved target bindings, permission and approval evidence, exact
  installed-file ownership, lock validation, and safe removal behavior
- enables dependency knowledge without native-metadata-only discovery, exact
  artifact identity, untrusted-source handling, independent semantic state
  axes, target ownership, bounded graph traversal, retention policy, lazy
  routing, and structural validation
- enables workspace modes without user-owned acceptance, explicit workspace
  identity, one active root adapter, relationship/ownership evidence, one
  directory per actual mode, ambiguity handling, lazy context, preflight, and
  structural validation
- enables team collaboration without a coordination backend, actor and
  decision-owner evidence, storage/privacy policy, or conflict review
- enables subagent delegation without a target policy, current per-surface
  capability evidence, bounded role catalog/model/native bindings, task and
  result contracts, write isolation, validation, retry/conflict fallback, and
  primary-agent convergence
- enables Debug Mode without explicit per-scope activation, target-owned
  privacy/retention/publication policy, non-canonical authority, causal event
  attribution, event-derived metric validation, bounded context, and expiry
- enables a consistency map without target-owned fact IDs, relationship
  coverage, or staleness handling
- enables architecture knowledge without a project owner, compact catalog,
  evidence revision, status separation, selected-source routing, and
  validation or manual review
- enables diagrams without portable ASCII presentation, source/visual
  ownership, compact assistant capability evidence, security/privacy policy,
  revision lineage, and render or manual-review evidence
- copies source-repository helper behavior into target requirements
- installs bridge, diagram, skill, or operation-help surfaces the target does
  not use
- hides blocked core gaps behind a broad maturity claim
