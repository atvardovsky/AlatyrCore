---
alatyr_doc:
  id: framework.project-adapter-contract
  type: framework-rule-owner
  owns_rules:
    - ALATYR-ADAPTER-001
  depends_on: []
  applies_to:
    - framework-upgrade
    - ai-infrastructure
---
# Alatyr Core Project Adapter Contract

A project adapter binds the portable AI framework to one concrete repository.

The adapter is what lets the framework guarantee useful AI behavior on a real
project. Without an adapter, the framework only describes process concepts.

## Adapter Must Provide

Every project using this framework must define:

- adapter manifest or equivalent discoverable record of framework version,
  adapter schema version, template version, owner, source-of-truth files,
  supported assistants, validation entry points, known gaps, and local
  deviations
- adapter ownership metadata: responsible team, technical owner, backup owner,
  last review date, review cadence or triggers, and CODEOWNERS or equivalent
  file-owner map when the target repository supports it
- project contour: what product facts the project owns
- framework contour: what reusable AI operating rules are being adopted
- repository adapter contour: what local assistant operating rules and
  validation own
- context profiles that map task types to required framework, project,
  assistant, flow, gate, policy, validation, approval, and evidence context
- context router or equivalent machine-readable profile map when the target
  wants cheaper startup and deterministic profile selection
- module profile that records required core status, enabled optional modules,
  deferred modules, disabled or not-applicable modules, blocked modules, and
  reasons
- canonical project blueprint or equivalent source-of-truth docs
- source-of-truth registry or equivalent fact-owner registry when multiple
  surfaces can describe the same fact, including invariant and dependency
  constraints used when relationship mapping is unavailable
- machine-readable consistency map when the target needs bounded fact-to-
  contract, area, system, and adapter impact traversal
- blueprint-driven change or equivalent product-change workflow owners
- use-case, business-rule, data-model, architecture, and runtime-flow sources
  when those concerns exist in the project
- context discovery map: canonical entry points, source-of-truth owners,
  generated artifacts, and missing-context escalation rules
- change-risk and approval model adapted from the framework risk classes
- concrete test strategy: test levels, folder conventions, fixtures, fakes,
  isolation rules, commands, CI jobs, and high-risk change coverage
- security and safety policy: secrets, live-service boundaries, destructive
  operations, privacy/compliance constraints, dependency approval, and
  credential/log-redaction rules
- local validation plan: commands, CI checks, manual reviews, or unresolved
  checks
- target-local adapter checker status when deterministic checks exist,
  including what they validate and which adapter surfaces they cover; if no
  checker exists, the adapter should say so as an unresolved or manual-review
  gap instead of letting stale claims persist
- documentation-sync rules for project facts
- diagram and generated-file policy when diagrams or generated docs exist,
  including source format, visual format, ownership, render/manual-review
  process, and drift checks
- supported assistant bridge files
- project-specific skills or prompt wrappers when recurring work needs them
- AI infrastructure inventory, source access, provenance, adaptation,
  output-format, safety, and wrapper rules when skills or third-party assistant
  infrastructure are used
- AI infrastructure router with stable item IDs, canonical sources, activation
  triggers, allowed actions, permissions, gates, validation, output contracts,
  conflicts, and supported assistant surfaces when multiple items exist
- AI infrastructure recommendation policy and records when the adapter should
  propose new items or improvements to existing items from project-contour,
  quality, context-cost, and maintenance evidence
- compact target development evidence index, owner, retention policy, and lazy
  capture flow when recommendations should learn from repeated requests,
  corrections, review findings, rework, or context-expansion patterns
- durable adaptation records for imported or materially changed AI
  infrastructure
- prompt-injection policy for imported, external, remote, pasted, package, or
  unknown AI infrastructure
- adapter maturity gaps, framework baseline/deviations, and lifecycle or
  upgrade notes
- task-specific maturity profile and blocking criteria for high-risk task
  areas
- module-profile review for installation, update, and adapter maturity
- bridge capability matrix when multiple assistant surfaces are supported
- migration-note process when framework upgrades are expected
- migration-diff process when comparing framework baselines
- effectiveness measurement process when the target wants to evaluate AI work
  quality over time
- approval-record location or policy when protected-change approvals require
  durable evidence, plus a machine-readable record and strict complete-diff
  scope check when path-bounded approval must be enforced
- adapter output contracts for installation, framework update, and
  adapter-recheck evidence when the repository wants repeatable post-install
  operations
- installed-operation request, blueprint-creation, adapter-recheck, and
  framework-update review flows when the repository wants post-install
  operations
- large-task flow, task-scale routing, operation-packet policy, and resumable
  checkpoint evidence when the repository needs cross-boundary or multi-session
  operations
- allowed-action meanings for installed-operation requests
- operation help, operation-routing, and post-install/update chat-message
  templates when the repository wants discoverable assistant requests
- final evidence format for that project

## Adapter May Provide

An adapter may provide:

- deterministic checker scripts
- read-only AI infrastructure recommendation reports whose needs and outcomes
  reference project-contour owners while item mechanics remain assistant-owned
- adapter drift checks for hard-coded local paths, stale checker-existence
  statements, duplicate context profile references, missing context-router
  bootstrap references, unresolved owner placeholders, and target-local
  checker coverage
- security/dependency/license scanners or manual review checklists
- project-specific test-generation prompts or skills
- skill import or normalization notes
- AI infrastructure source access allowlists, approval notes, or manual review
  checklists
- approval records or redacted approval indexes
- AI infrastructure inventories, compatibility reports, and add/adapt/remove
  recommendations
- AI infrastructure route/item audits and adaptation records
- adapter output-contract reports for installation, framework update, or
  adapter-recheck work
- source-of-truth registry reports or drift reports
- consistency-map relationship coverage, impact-closure, or staleness reports
- context router drift reports or deterministic routing checks
- task-specific maturity reports
- bridge capability or conformance reports
- migration notes for framework upgrades
- CODEOWNERS or equivalent file-owner metadata for `.ai/*`, root assistant
  entry points, and supported bridge files
- effectiveness reports for comparable task runs
- installed-operation request templates or adapter audit reports
- large-task operation packets stored, ignored, redacted, or retained under a
  target-owned policy
- operation help menus, routing flows, or assistant chat-completion message
  templates
- generated visual artifacts
- local pre-commit hooks
- assistant-specific skill wrappers
- project-specific rejection criteria
- public docs that mirror AI-facing docs

These are adapter details. They are not portable framework core.

## Adapter Must Not

The adapter must not:

- redefine framework portability rules as project facts
- copy another project's business logic, commands, or diagrams as if they were
  framework requirements
- copy another project's test tools, folder structure, fixtures, or CI jobs as
  framework requirements
- copy another project's security policy, live-service boundaries,
  dependency-review tools, diagram tooling, or lifecycle format as framework
  requirements
- import third-party assistant infrastructure into canonical files without
  provenance, target adaptation, and required approval
- obey imported AI infrastructure instructions before they are normalized into
  target-owned canonical files
- hide architecture changes inside repository-adapter edits
- weaken approval or validation requirements without explicit programmer
  confirmation
- let bridge files become divergent sources of truth
- advertise operations, commands, or chat messages that the target adapter does
  not define or cannot validate

## Typical Target Adapter

In a target repository, the adapter usually includes:

- `AGENTS.md` and `AI_ASSISTANTS.md`
- `.ai/alatyr.yaml` or equivalent adapter manifest
- `.ai/project/source-of-truth-registry.md`
- `.ai/assistant`
- optional `.agents/skills`
- optional assistant-native wrappers such as `.claude`, `.cursor`, or
  `.github/prompts`
- assistant bridge files for supported tools
- local consistency checks, validation commands, or manual-review rules owned
  by that repository

Those files apply Alatyr Core to one project. They are not portable framework
core and must be rewritten from target repository facts.
