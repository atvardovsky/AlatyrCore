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

1. Inspect the current target adapter.
2. Identify framework-core changes versus target-adapter changes.
3. Preserve target project facts.
4. Compare supported assistant bridge needs.
5. Compare framework version, adapter schema version, and template version.
6. Compare bridge capability matrix and supported assistant limitations.
7. Identify new approval, testing, security, diagram, or validation guidance.
8. Compare required core profile and optional module states.
9. Prepare a migration diff, migration note, or installation plan.
10. Require approval before overwriting existing target AI instructions.
11. Recheck the installed adapter for framework references, bridge files, gates,
   prompts, skills, lifecycle notes, and maturity gaps.
12. Recheck adapter owners, review cadence, CODEOWNERS or equivalent owner
   map, operation help, operation-routing flows, and post-update chat message
   templates.
13. Recheck root assistant entry points and supported bridge files so future
    sessions can find the installation note, operation help, and routing flow.
14. Run or report target validation.
15. Send a post-update assistant chat message that names updated surfaces,
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
- adapter recheck results for installed framework updates
- help/routing and post-update chat-message migration needs

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
- claim upgrade success without validation or residual-risk evidence
