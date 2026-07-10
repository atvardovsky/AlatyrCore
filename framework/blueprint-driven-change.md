---
alatyr_doc:
  id: framework.blueprint-driven-change
  type: framework-rule-owner
  owns_rules:
    - ALATYR-CHANGE-001
  depends_on:
    - ALATYR-SOURCE-001
    - ALATYR-RISK-001
    - ALATYR-INTEGRITY-001
  applies_to:
    - business-change
    - architecture-change
    - data-change
---
# AI Framework Blueprint-Driven Change

This file defines a portable product-change workflow for projects that use
Alatyr Core.

"Blueprint" means the target project's canonical source-of-truth docs or an
equivalent project-owned record of accepted behavior. The framework does not
require a universal filename or document format.

Concrete product facts, blueprint files, flows, diagrams, commands, and final
evidence formats belong to the project adapter.

## Purpose

Blueprint-driven change keeps product intent, accepted project facts,
implementation, tests, diagrams, and assistant rules synchronized.

Use this workflow when a requested change may affect:

- business or domain behavior
- use cases, workflows, runtime flows, or state transitions
- architecture, module boundaries, data ownership, or external contracts
- security, privacy, live-service, destructive-operation, dependency, or
  permission behavior
- diagrams, prompts, skills, gates, bridge files, or checker rules

## Pipeline

Apply this sequence before claiming the change is complete:

1. Record change intent and non-goals.
2. Load target context from the adapter and project source-of-truth docs.
3. Run logical integrity review for the proposed or discovered change.
4. Identify affected project areas, contracts, tests, diagrams, and assistant
   governance surfaces.
5. Update the owning blueprint or source-of-truth docs when accepted facts
   change.
6. Update project flow, use-case, data, runtime, or architecture docs when
   those facts change.
7. Prepare an implementation plan that names affected boundaries and validation.
8. Change code, tests, diagrams, prompts, skills, bridge files, gates, or
   checker rules as required by the accepted fact change.
9. Run target validation that exists, or record manual/unresolved checks.
10. Perform a final consistency check across changed surfaces.
11. Report final evidence, skipped checks, approvals, and residual risk.

For small documentation-only changes, some steps may be a short explicit
decision rather than a separate artifact.

## Approval And Sequencing

Approval is required before protected changes, including:

- architecture changes
- accepted business-policy changes
- weakened tests, gates, approval rules, or documentation-sync rules
- new production dependencies, services, credentials, or permissions
- live, destructive, spend-affecting, data-loss, security, or privacy changes
- overwriting existing target assistant instructions
- integrating third-party assistant infrastructure into canonical target files

If approval is missing, stop before applying the protected change. Planning and
analysis may continue when they do not modify protected behavior.

## Adapter Responsibilities

The project adapter must define:

- canonical blueprint or source-of-truth docs
- project flow, architecture, data, diagram, and public-doc owners when those
  concerns exist
- local approval triggers and escalation rules
- test levels, validation commands, manual reviews, and unresolved-check format
- generated artifact ownership and diagram source/visual policy
- prompt, skill, bridge, gate, and checker synchronization rules
- final evidence format

If those facts are missing, report the missing adapter fact instead of
inventing project policy.

## Evidence Format

A blueprint-driven change should leave evidence for:

- change intent and non-goals
- changed facts and risk classification
- source-of-truth or blueprint updates
- flow, implementation, test, diagram, prompt, skill, gate, bridge, or checker
  updates
- validations or manual checks run
- approvals used
- skipped checks and residual risk

## Rejection Criteria

Reject or revise work that:

- implements a behavior change without updating the owning source of truth
- updates a blueprint-equivalent doc without carrying the accepted fact into
  code, tests, diagrams, or assistant rules when applicable
- treats installer flow as the product-change workflow
- invents blueprint files, commands, diagrams, or tests for a target project
- hides missing approval or unresolved validation
