---
alatyr_doc:
  id: framework.test-first-development
  type: framework-rule-owner
  owns_rules:
    - ALATYR-TDD-001
  depends_on:
    - ALATYR-CONTEXT-001
    - ALATYR-RISK-001
    - ALATYR-INTEGRITY-001
    - ALATYR-MODULE-001
    - ALATYR-OPERATION-001
  applies_to:
    - code-local
    - business-change
    - architecture-change
    - data-change
    - security-sensitive
---
# Test-First Development

This document defines the optional portable contract for target-adapted
test-first development. It covers explicit enablement, bounded recommendation,
RED/GREEN/refactor evidence, and exceptions without forcing one test method or
tool onto every repository.

Concrete test commands, frameworks, folders, fixtures, isolation rules,
feedback-time limits, trigger severity, exceptions, and merge policy belong to
the target project contour.

## Purpose

An enabled `test-first-development` module should help a target project:

- express a changed behavior or defect as an observable example before code
- choose the smallest test level that proves the relevant contract
- distinguish intended RED failure from setup, syntax, or infrastructure failure
- keep implementation focused until the selected examples pass
- refactor only while behavior remains green
- preserve characterization evidence before risky behavior-preserving changes
- recommend test-first work when bounded risk evidence makes it valuable
- record justified exceptions instead of creating low-value tests

Test-first development is a workflow, not an architectural layer and not a
requirement to write unit tests for every change.

## Modes

A target policy may enable these modes:

- `strict-tdd`: specify an observable example, prove expected RED, implement
  the minimum behavior, prove GREEN, then refactor
- `regression-first`: reproduce a reported defect with a failing test before
  applying the fix
- `characterization-first`: capture current behavior before risky refactoring
  or work in poorly understood legacy code
- `contract-first`: define an API, event, schema, module, or component contract
  before implementation
- `test-after-with-reason`: permit implementation before the test only when a
  target-recorded exception applies, then record the reason and validation

The target decides which modes are available and which trigger selects each
mode. Do not silently convert a test-after project into strict TDD.

## Enablement Contract

The module is enabled only when the target records:

- module state, owner, decision authority, review cadence, and evidence revision
- accepted test-first policy and recommendation behavior
- applicable project areas, changed-fact classes, and activation triggers
- permitted modes and test levels
- target commands, folders, naming, fixtures, fakes, and helpers
- database, queue, clock, filesystem, network, secrets, and external-service
  isolation rules
- RED, GREEN, refactor, broader-validation, and final-evidence requirements
- exception categories, approval needs, and residual risks

`Alatyr enable test-first` is a chat request, not a shell command or blind
toggle. The assistant first assesses target evidence, proposes a policy, and
changes adapter/project policy surfaces only within allowed actions. New test
dependencies, CI requirements, merge gates, protected behavior, or weakened
validation require the target's normal approval process.

## Recommendation Gate

Evaluate the recommendation gate from already selected task and risk context;
do not load the full test-first module for every task.

Test-first work is usually a strong candidate when one or more of these are
supported by target evidence:

- a defect can be reproduced deterministically
- a business invariant, calculation, state transition, permission, or failure
  classification changes
- an API, event, schema, persistence, module, or UI interaction contract changes
- a refactor touches behavior that lacks reliable characterization
- retry, idempotency, concurrency, ordering, time, or rollback behavior changes
- the same area has recurring regressions, review corrections, or escaped defects
- the target policy marks a matching trigger as required

Do not recommend test-first work merely because code is being edited. It is
normally not indicated for wording-only documentation, generated output,
mechanical formatting, disposable exploration, or a change whose useful proof
is necessarily a target-approved manual or external validation. Record the
reason when risk evidence is material but test-first work is not feasible.

The recommendation result is one of:

- `required`: an enabled accepted target policy has a matching required trigger
- `recommended`: bounded evidence shows likely quality value, but the policy
  does not make it mandatory
- `not-indicated`: no supported trigger justifies the workflow
- `blocked`: the workflow is needed but target commands, isolation, ownership,
  fixtures, permissions, or validation are missing

When the module is disabled, deferred, or absent, the assistant may recommend a
read-only assessment or `test-first-configuration`. It must not claim TDD is
enabled or block ordinary work unless another target-owned gate independently
requires it. Show at most one concise recommendation per task and include the
trigger, proposed mode, likely test level, expected cost, and next safe action.

## Execution Flow

For an activated test-first change:

1. Name the changed fact, invariant, defect, or contract and its owner.
2. Select the target policy trigger, mode, smallest proving test level, and
   allowed command.
3. Record observable acceptance examples and important negative or boundary
   cases.
4. Run the relevant baseline when the target policy requires it.
5. Add or select the focused test and prove RED for the expected behavior
   reason. A syntax, import, setup, unavailable-service, or unrelated failure is
   not valid RED evidence.
6. Make the minimum implementation change needed to satisfy the selected
   contract and prove GREEN with the same focused command.
7. Refactor only while the focused test remains green.
8. Run broader target validation selected by risk and boundary crossings.
9. Apply logical integrity and companion-surface synchronization.
10. Report evidence, exceptions, skipped checks, and residual risk.

Existing useful tests must not be weakened or deleted merely to obtain GREEN.
Passing generated, mocked, or lower-level tests does not prove a boundary that
requires integration, contract, accessibility, visual, security, or end-to-end
evidence.

## Evidence Contract

Evidence should record:

- policy revision, trigger result, selected mode, changed fact, and owner
- acceptance examples and selected test level
- RED command, result, expected failure reason, and relevant test reference
- GREEN command and result for the same focused contract
- refactor performed or explicitly skipped
- broader validation run, skipped, or unresolved
- exception reason and authority when `test-after-with-reason` applies
- companion updates, approvals, residual risk, and final revision when known

Command output may be summarized and linked according to target retention and
sensitivity policy. Structural records do not prove that assertions are
semantically correct.

## Context Economy

Keep the full test-first policy, skill, flow, and evidence template outside
routine bootstrap. Existing test selection guidance may evaluate the compact
recommendation gate from changed-fact and risk context. Load the target policy
only after an explicit test-first request, a supported recommendation trigger,
or policy configuration work.

## Rejection Criteria

Reject or revise test-first work that:

- treats the module as enabled without an accepted target policy
- invents project commands, test levels, fixtures, isolation, or merge rules
- reports RED without running the selected test or without the expected failure
- uses syntax, setup, infrastructure, or unrelated failure as RED evidence
- weakens assertions or deletes useful tests to obtain GREEN
- tests private implementation detail while leaving the changed contract unproven
- requires strict TDD for every code edit regardless of target policy and value
- repeatedly suggests the module without new evidence
- claims deterministic checks prove test semantic quality
