---
alatyr_doc:
  id: framework.lifecycle
  type: framework-rule-owner
  owns_rules:
    - ALATYR-LIFECYCLE-001
  depends_on:
    - ALATYR-ADAPTER-001
  applies_to:
    - framework-upgrade
---
# AI Framework Lifecycle

This file defines portable lifecycle rules for maintaining and upgrading the AI
framework itself.

The framework lifecycle is separate from product architecture decisions. A
project may mirror selected lifecycle notes into its adapter docs, but product
ADRs remain project-owned.

## Versioning

Each installed framework should identify:

- framework version
- adapter schema version
- template version when templates were used
- installed framework pack and its projected file inventory
- framework source or baseline
- installation or upgrade date
- local adapter owner
- adapter review cadence and last review date
- CODEOWNERS or equivalent owner map for `.ai/*`, root assistant entry
  points, and supported bridge files when the target repository supports file
  ownership metadata
- supported assistants
- required core profile and optional module states
- known deviations from the source framework
- unresolved adapter gaps

The source repository may store these facts in simple files such as `VERSION`,
`ADAPTER_SCHEMA_VERSION`, and `TEMPLATE_VERSION`. Installed adapters should
record them in a discoverable manifest such as `.ai/alatyr.yaml` or a
target-owned equivalent.

## Upgrade Process

Before upgrading framework files in a target project:

1. Load the compact bootstrap and the generated upgrade impact only.
2. Inspect the current target manifest, installed framework pack and baseline,
   projected inventory, local deviations, and adapter owner evidence.
3. Prepare or review a migration assessment before changing target files. It
   should compare rule registries, framework files, versions, and structural
   adapter state and emit a hash-bound machine-readable impact projection.
4. Use the impact projection's changed rule IDs, categories, task profiles,
   canonical sources, template surfaces, enabled modules, and bridge
   capabilities to select additional context. Load the full framework corpus
   only when impact is ambiguous, validation disproves the boundary, or a full
   compatibility audit is explicitly requested.
5. Identify framework-core changes versus target-adapter changes.
6. Preserve target project facts.
7. Compare supported assistant bridge needs and limitations.
8. Identify new approval, testing, security, diagram, or validation guidance.
9. Compare required core profile, installed framework pack, and optional module
   states. Expand the pack before enabling a module whose portable owner is not
   installed; do not replace target facts while changing the pack.
   When `team-collaboration` is enabled, compare its rule, structured policy,
   local-identity boundary, registry and task schemas, active-work index,
   backend contract, lazy overlay, operation routes, and operating model.
   When `change-packages` is enabled, compare its record schema, semantic
   approval fields, provenance policy, lazy route, and validator support.
   When `code-documentation` is enabled, compare its catalog/profile schemas,
   source-set selectors, accepted states, canonical-owner boundaries,
   generators, output/publication policies, adapted skill, lazy route, and
   validator support.
   When `project-vocabulary` is enabled, compare its catalog, term, and data-
   link schemas, state and acceptance model, normalization policy, canonical-
   owner boundaries, adapted skill, lazy route, and validator support.
   When `test-first-development` is enabled, compare policy schema and revision,
   owners, recommendation behavior, triggers, modes, levels, commands,
   isolation, exceptions, adapted skill/gate, lazy route, evidence contract,
   and validator support.
   When `extensions` is enabled, compare extension API, catalog/lock schemas,
   package compatibility, installed ownership and hashes, target bindings,
   permissions, lifecycle flow, gates, operation/bridge routing, historical
   records, and validator support.
   When `dependency-knowledge` is enabled, compare its export API, target
   policy/catalog/knowledge-lock/deviation schemas, passive activation
   boundary, independent semantic state axes, artifact identity, retention,
   intent route, flow, gate, operation, and validator support.
   When `subagent-delegation` is enabled, compare its policy schema, selected
   assistant capability records, role/model bindings, client freshness,
   packet and overlay contracts, write isolation, fallbacks, privacy,
   validation, and primary convergence.
10. Prepare a target migration note or installation plan from reviewed
    assessment evidence.
11. Require approval before overwriting existing target AI instructions.
12. Recheck the installed adapter for framework references, bridge files, gates,
   prompts, skills, lifecycle notes, and maturity gaps.
13. Recheck adapter owners, review cadence, CODEOWNERS or equivalent owner
   map, operation catalog, help, routing/health/preview flows, and post-update
   chat message
   templates.
    Preserve active team task IDs, actor references, claims, checkpoints,
    handoffs, decisions, and external references. Never replace current team
    state with the source placeholder registry.
    Preserve target change-package records. Never replace historical package
    evidence with the source placeholder templates.
    Preserve target code-documentation profiles and decisions. Never replace
    accepted frontend, backend, shared, or infrastructure conventions with
    source placeholders or a universal style.
    Preserve target test-first policies and historical cycle evidence. Never
    replace target commands, trigger severity, isolation, exceptions, CI, or
    merge requirements with source placeholders or silently enable stricter
    behavior.
    Preserve installed extension catalog and lock entries, immutable source
    provenance, target bindings, local deviations, installed-file ownership,
    permissions, approvals, and lifecycle history. Never auto-update an
    extension or replace target bindings with source defaults.
    Preserve dependency knowledge policy, reviewed package-instance state,
    target deviations, retention decisions, and permitted historical
    snapshots. Never activate nested adapters, replace target facts with
    dependency claims, or mark stale exports current during a framework update.
    Preserve accepted workspace identity, modes, per-mode support directories,
    root context, relationships, defaults, and user decision evidence. New
    source templates may produce suggestions but must not replace or silently
    activate target modes.
    Preserve target vocabulary term IDs, definitions, states, owners, aliases,
    acronyms, links, and decisions. Never replace accepted project language
    with source placeholders or inferred definitions.
    Preserve target delegation role/model bindings, capability evidence,
    limits, privacy policy, fallbacks, and historical packet evidence. Never
    replace them with source placeholders or assume a newly documented model
    is available on the installed client.
14. Recheck root assistant entry points and supported bridge files so future
    sessions can find the installation note, operation catalog, health, help,
    and routing flow.
15. Run or report target validation.
16. Send a post-update assistant chat message that names updated surfaces,
    recommended recheck operation, validation, and unresolved gaps.

Do not use an installer script as the framework mechanism. Do not overwrite
target-specific rules just because the source framework changed.

For an AlatyrCore source release, the release tag must equal `v<VERSION>`.
Reviewed migration evidence must name the exact baseline and all three version
values, compare every shipped schema contract, and bind the baseline and
destination framework, schema, target-template, and version-file trees with
deterministic SHA-256 values. A generated temporary report does not validate a
different committed migration report.

## Change Log Expectations

Framework lifecycle notes should record:

- new framework files or removed files
- framework version, adapter schema version, or template version changes
- added, changed, removed, or deprecated rule IDs
- changed guarantees
- changed adapter contract requirements
- changed portability boundaries
- changed logical integrity, blueprint-driven change, or skill-adaptation
  guidance
- changed approval, safety, testing, diagram, or validation expectations
- bridge or supported-assistant compatibility changes
- migration actions required by project adapters
- migration-note requirements for installed adapters
- migration-diff requirements for framework baseline comparisons
- migration-assessment evidence and intentionally omitted context
- adapter recheck results for installed framework updates
- help/routing and post-update chat-message migration needs
- team-collaboration rule, policy, identity boundary, registry/task schemas,
  active-work route, backend contract, optimistic-concurrency behavior,
  schema-1 record migration, active-record preservation, and post-update stale-
  state review when that module is enabled
- change-package rule, record schema, lazy route, target retention policy,
  provenance grades, and validator migration when that module is enabled
- code-documentation rule, catalog/profile schemas, source-set selection,
  accepted style decisions, generator/output policy, adapted skill, lazy
  route, and validator migration when that module is enabled
- project-vocabulary rule, catalog/term/data-link schemas, scoped meanings,
  acceptance decisions, normalization policy, adapted skill, lazy route, and
  validator migration when that module is enabled
- test-first rule, policy schema, recommendation/enablement boundaries,
  triggers, modes, commands, isolation, exceptions, evidence, adapted skill,
  lazy route, and validator migration when that module is enabled
- extension rule, extension API and package template, catalog/lock schemas,
  lifecycle operation, ownership/removal behavior, bindings, permissions,
  bridges, lazy route, inspection tooling, and validator migration when that
  module is enabled
- dependency knowledge rule, export API and package template, target policy,
  catalog, knowledge lock, deviations, snapshot policy, routing, gate,
  operation, and validator migration when that module is enabled
- workspace-mode rule, catalog, root context, per-mode descriptor contract,
  suggestion/selection flow, preflight, routing, gate, operation, and validator
  migration when that module is enabled
- subagent delegation rule, target policy, capability records, role/model
  bindings, packet and overlay contracts, fallbacks, and validator migration
  when that module is enabled

## Deprecation

When a framework rule is replaced:

- mark the old rule as deprecated or remove it in the same coherent update
- update adapters, prompts, skills, bridge files, and consistency checks that
  refer to it
- explain the migration path
- avoid leaving two canonical owners for the same rule

## Rejection Criteria

Reject lifecycle changes that:

- silently change framework guarantees
- weaken adapter requirements without explicit rationale
- overwrite target adapter facts during upgrade
- copy source project commands or business facts into framework core
- omit migration notes for supported assistants or bridge files
- omit bridge capability changes from upgrade evidence
- overwrite active team records from a source template or omit enabled-team
  migration evidence
- claim upgrade success without validation or residual-risk evidence
