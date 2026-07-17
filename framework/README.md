# Alatyr Core Framework

This directory defines the portable Alatyr Core assistant framework.

It is the reusable source that an assistant can adapt into a target project.
It is separate from any target project's product facts and from any target
repository's local AI adapter.

The framework exists to make assistants work predictably on a project by
forcing context discovery, ownership separation, approval gates, documentation
sync, logical integrity review, and final evidence.

## Owns

- framework contour and portability rules
- guarantees the framework provides to a project
- rule category ownership and duplicate-policy boundaries
- structured metadata on rule-owner documents
- rule identifiers and canonical rule registry
- project-adapter contract
- adapter ownership and review-cadence expectations
- required core profile and optional module profile
- optional scaffolding boundaries
- context-discovery and source-of-truth decision rules
- machine-readable context router guidance for cheaper task startup
- context profiles for task-specific minimum reading sets
- source-of-truth registry guidance for fact ownership and sync direction
- optional multi-level consistency mapping for bounded changed-fact impact
  traversal
- change-risk classification and approval trigger model
- first-class logical integrity review
- blueprint-driven product-change workflow
- optional large-task orchestration with bounded workstreams, context receipts,
  resumable checkpoints, and final convergence
- portable security, safety, and live-service reasoning rules
- prompt-injection handling for imported AI infrastructure
- approval-record guidance for protected changes
- machine-readable changed-path approval scope enforcement
- diagram reasoning and source/visual synchronization guidance
- AI infrastructure inventory plus skill, prompt, wrapper, bridge, and
  third-party assistant infrastructure adaptation guidance
- compact AI infrastructure routing for selecting only relevant skills,
  prompts, gates, checkers, tools, MCP configs, bridges, and wrappers
- evidence-based AI infrastructure recommendations for adding new items or
  improving, consolidating, replacing, retiring, and keeping existing items
- installed-adapter operation and recheck guidance
- operation help and routing guidance for unclear installed-adapter requests
- reusable assistant workflow categories
- reusable approval, documentation-sync, logical integrity, and evidence
  concepts
- stack-aware testing analysis guidance
- supported-assistant bridge pattern
- bridge capability matrix pattern
- migration diff and effectiveness measurement patterns
- task-specific adapter maturity and framework lifecycle guidance

## Does Not Own

- target project business logic, data model, architecture, diagrams, or
  runtime flows
- local commands, CI job names, generated files, hooks, or checker scripts
- project-specific skills, prompts, gates, or bridge wording
- target project facts during installation into another repository

Those belong to a project contour or repository adapter.

## Files

- `.ai/framework/README.md`: index for portable framework core files and
  ownership.
- `.ai/framework/contour.md`: boundary for portable framework core.
- `.ai/framework/guarantees.md`: what the framework guarantees and what it
  cannot guarantee without a project adapter.
- `.ai/framework/rule-ownership.md`: canonical owner map for framework rule
  categories and duplicate-policy boundaries.
- Rule-owner framework documents carry `alatyr_doc` front matter so source
  helpers can validate rule ownership, dependencies, and task-profile scope.
- `.ai/framework/rule-registry.md`: stable rule identifiers and canonical
  source references for migration, adapters, and checkers.
- `.ai/framework/rule-registry.json`: machine-readable rule manifest used by
  source-repository migration and consistency helpers.
- `.ai/framework/project-adapter-contract.md`: what a project must provide so
  the framework can work on that project.
- `.ai/framework/portability.md`: rules for separating framework core from
  repository adapter details.
- `.ai/framework/module-profile.md`: required core and optional module model
  for target installations.
- `.ai/framework/scaffolding.md`: optional scaffolder boundaries and evidence
  rules; scaffolding is not installation.
- `.ai/framework/testing-guidance.md`: portable reasoning guidance for choosing
  test levels and structure from the target stack and risk profile.
- `.ai/framework/context-discovery.md`: portable process for finding required
  context, owners, missing facts, and source-of-truth conflicts.
- `.ai/framework/context-router.md`: portable machine-readable routing
  contract that maps task profiles to bootstrap context, required files,
  approvals, validation, and final evidence.
- `.ai/framework/context-profiles.md`: portable task profiles that limit the
  initial required reading set and define expansion triggers.
- `.ai/framework/source-of-truth-registry.md`: portable registry model for
  fact ownership, derived surfaces, sync direction, validation, and conflict
  resolution.
- `.ai/framework/consistency-model.md`: portable relationship model for
  bounded impact closure across fact, contract, area, system, and adapter
  levels.
- `.ai/framework/change-risk-model.md`: portable risk classes used to decide
  approvals, tests, docs, diagrams, and final evidence.
- `.ai/framework/logical-integrity.md`: portable semantic/logical review for
  changed facts, source-of-truth decisions, repair sets, and evidence.
- `.ai/framework/blueprint-driven-change.md`: portable product-change workflow
  from intent through source-of-truth, implementation, sync, and evidence.
- `.ai/framework/security-safety-guidance.md`: portable security and safety
  expectations for secrets, live services, dependencies, and destructive work.
- `.ai/framework/prompt-injection.md`: policy for treating imported AI
  infrastructure instructions as untrusted data until normalized.
- `.ai/framework/diagram-guidance.md`: portable diagram reasoning and
  source/visual split rules.
- `.ai/framework/skill-adaptation.md`: portable guidance for adapting skills,
  prompts, wrappers, and third-party assistant infrastructure.
- `.ai/framework/ai-infrastructure-routing.md`: portable route and item
  contract for loading one target AI capability and its required gates,
  permissions, validation, and output.
- `.ai/framework/ai-infrastructure-recommendations.md`: portable read-only
  decision contract for recommending new AI items or changes to existing items
  from bounded project-contour, quality, and cost evidence.
- `.ai/framework/approval-records.md`: durable evidence pattern for protected
  changes that require scoped approval.
- `.ai/framework/adapter-maturity.md`: readiness model for judging whether a
  project adapter can support reliable assistant work.
- `.ai/framework/bridge-capability-matrix.md`: portable model for documenting
  assistant bridge loading behavior, limitations, and conformance checks.
- `.ai/framework/migration-diff.md`: portable process for comparing framework
  baselines and deriving target migration actions.
- `.ai/framework/effectiveness-metrics.md`: metrics for evaluating Alatyr's
  impact across comparable tasks and adapter states.
- `.ai/framework/large-task-orchestration.md`: optional coordination contract
  for large, cross-boundary, multi-workstream, or resumable changes.
- `.ai/framework/lifecycle.md`: framework versioning, upgrade, deprecation,
  and migration guidance.
- `.ai/framework/installed-operations.md`: portable guidance for post-install
  requests, blueprint creation, adapter rechecks, and framework update reviews.
- `.ai/framework/operation-help.md`: portable guidance for installed-adapter
  help, operation menus, ambiguous-request routing, and next safe actions.

## Target Repository Adapter

In a target repository, `.ai/assistant` is normally the repository adapter. It
applies Alatyr Core to that project through local flows, gates, prompts,
skills, bridge files, consistency manifests, and local validation commands or
manual checks.

Portable framework files may point to adapter concepts, but must not require
Alatyr Core's source repository commands or any source project facts.
