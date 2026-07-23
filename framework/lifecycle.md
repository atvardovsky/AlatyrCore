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

1. Load the compact bootstrap and migration-first context only.
2. Inspect the current target manifest, installed framework baseline, local
   deviations, and adapter owner evidence.
3. Prepare or review a migration assessment before changing target files. It
   should compare rule registries, framework files, versions, and structural
   adapter state.
4. Use changed rule IDs, categories, task profiles, canonical sources, template
   surfaces, and bridge capabilities to select additional context. Do not load
   the full framework corpus by default.
5. Identify framework-core changes versus target-adapter changes.
6. Preserve target project facts.
7. Compare supported assistant bridge needs and limitations.
8. Identify new approval, testing, security, diagram, or validation guidance.
9. Compare required core profile and optional module states.
   When `team-collaboration` is enabled, compare its rule, registry schema,
   lazy overlay, operation routes, and target operating model.
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
14. Recheck root assistant entry points and supported bridge files so future
    sessions can find the installation note, operation catalog, health, help,
    and routing flow.
15. Run or report target validation.
16. Send a post-update assistant chat message that names updated surfaces,
    recommended recheck operation, validation, and unresolved gaps.

Do not use an installer script as the framework mechanism. Do not overwrite
target-specific rules just because the source framework changed.

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
- team-collaboration rule, registry schema, lazy route, active-record
  preservation, and post-update stale-state review when that module is enabled

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
