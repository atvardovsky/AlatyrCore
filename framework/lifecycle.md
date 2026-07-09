# AI Framework Lifecycle

This file defines portable lifecycle rules for maintaining and upgrading the AI
framework itself.

The framework lifecycle is separate from product architecture decisions. A
project may mirror selected lifecycle notes into its adapter docs, but product
ADRs remain project-owned.

## Versioning

Each installed framework should identify:

- framework source or baseline
- installation or upgrade date
- local adapter owner
- supported assistants
- known deviations from the source framework
- unresolved adapter gaps

The exact versioning format is adapter-owned. The framework only requires the
facts to be recorded somewhere discoverable.

## Upgrade Process

Before upgrading framework files in a target project:

1. Inspect the current target adapter.
2. Identify framework-core changes versus target-adapter changes.
3. Preserve target project facts.
4. Compare supported assistant bridge needs.
5. Identify new approval, testing, security, diagram, or validation guidance.
6. Prepare a migration note or installation plan.
7. Require approval before overwriting existing target AI instructions.
8. Run or report target validation.

Do not use an installer script as the framework mechanism. Do not overwrite
target-specific rules just because the source framework changed.

## Change Log Expectations

Framework lifecycle notes should record:

- new framework files or removed files
- changed guarantees
- changed adapter contract requirements
- changed portability boundaries
- changed logical integrity, blueprint-driven change, or skill-adaptation
  guidance
- changed approval, safety, testing, diagram, or validation expectations
- bridge or supported-assistant compatibility changes
- migration actions required by project adapters

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
- claim upgrade success without validation or residual-risk evidence
