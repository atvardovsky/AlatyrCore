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
Command/evidence execution contract version 2 also binds concrete credential-free
runtime resources and access modes. Resolve concurrent use through
`testing-guidance.md`; an effect or disposable-environment label alone does not
establish resource isolation. Actual write runs retain serialization or verified
namespace-isolation evidence without granting permission to execute.

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

## Execution Authority And Ownership

Before any baseline, RED, GREEN, coverage or broader run, resolve canonical
project testing owners, current-scope execution authorization, and target timing.
Module enablement, command availability and an accepted recommendation grant no
execution permission. Manual-review-first may defer execution while tests are
authored; it does not fabricate RED or automatically approve a strict-mode
exception. Preserve the accepted timing and report unresolved conflicts.

Policy `execution_contract` version 2 records canonical policy/coverage owners,
timing, RED requirements, review authority and explicitly selected current
evidence paths. Keep mirrors subordinate: edit canonical sources first, then
reconcile JSON-equivalent adapter copies. Skills, flows, gates and templates
bind to that policy rather than maintaining independent execution sequences.

Targets may select up to 16 exact Markdown paths in
`execution_contract.additional_evidence_templates` (omitted means empty).
These supplement, never replace, the four built-in test surfaces and use the
same `alatyr_test_execution` frontmatter binding. Validate existence,
containment, uniqueness and a 128 KiB per-file limit; do not discover templates
by scanning prose. Add paths at the canonical policy owner before reconciling
its adapter projection. This selection changes neither timing nor RED policy.

Each command records kind, configuration paths, prerequisites, effects, resources,
environment, suite scope, proof boundary and supported/unsupported/unknown
filtering. Distinguish disposable automated resources from the shared manual
review application and database. Never broaden an unsupported focused command.
Reconcile test additions and exclusions against actual runner configuration;
metadata alone cannot establish command semantics or suite completeness.
Case-ID inventory is metadata, runner discovery is not execution, and database
configuration is not database behavior proof. Label each using its command
kind, measured execution state/counts and proof boundary; do not infer proof
from a checker's success message. Opaque historical logs remain opaque.

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
4. Resolve the execution contract and current authorization; defer commands
   while the target's review gate is pending. Missing legacy contracts are
   unresolved execution readiness, not automatic permission.
5. When execution is authorized, run the selected baseline or focused test.
   Prove RED only when required by the selected mode/policy, before implementation
   for strict modes. A syntax, import, setup, unavailable-service, or unrelated failure is
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

Optional `target-test-execution-evidence` records separate authored, discovered,
passed, failed, skipped and blocked states. Bind current revision, canonical
policy, coverage owner, selected tests/configuration, changed implementation
inputs and raw result artifacts by SHA-256. Deleted implementation inputs may
use `null` in `input_sha256`, verified as contained missing paths. Selected
tests, configuration and coverage owners always require content hashes. Record
authorization/timing, availability, prerequisites, actual filter, proof boundary,
environment, case counts, selected/executed files and explicit exclusions. Counts conserve
discovered = executed + skipped + not_run (default 0) and
executed = passed + failed. Zero-execution
or all-skipped runs prove no behavior. Suite claims reconcile target-owned
`suite_patterns` against current Git-visible files before runner exclusions;
full claims cannot hide filtering, exclusions or skips. Static case-ID checks
and mocked browser tests never establish real persistence or end-to-end proof.
Validate only explicitly selected current records, not the historical corpus.
`full` is limited to the declared command and proof boundary, never all project
behavior; mocked runs retain narrower claims. These run records do not establish
RED/GREEN ordering or satisfy the manual test-first completion gate by themselves.

Command output may be summarized and linked according to target retention and
sensitivity policy. Structural records do not prove that assertions are
semantically correct.

## Incident Repair Review

For uncertain or repeated defects, qualify the original reproducer before a
repair: competing causes, a falsifying observation, expected incident-level
effect, and the smallest faithful check. Review actual entry/producer/consumer
paths, persistence ACK and independent reload, process topology, resource
accounting, and positive-case preconditions. Unknown is not verified;
non-applicability needs a concrete reviewed reason and evidence. Benchmark
rankings from an instrumented test environment are diagnostic until checked
against the intended runtime. Never change deadlines or thresholds to qualify
a proposed optimization.

The target may enable optional `repair_review` schema 1 in its canonical test
policy. It names full end-to-end acceptance command IDs and bounded current
task/path records using `repair-review.json`. Existing policies remain valid;
installation/update proposes enablement rather than inventing target decisions.
Enabled uncertain/systemic incident tasks retain a required `repair-evidence-review` proof
obligation. Removal or deferral cannot turn that captured requirement into
successful acceptance. Record checks reuse canonical execution evidence,
current policy/input hashes and original-case identity, not copied statuses.

Each attempt binds its run bytes, observed timezone-bound `run_window`,
expected/observed effect and distinguishes production,
fixture, test-author, environment and unverified failure. After failed acceptance,
another related acceptance attempt requires a later diagnostic tied to that
failed run and a changed tested input or command selection, not a timestamp or
renamed output. Every selected current acceptance run, including failures, is
retained in observed order. Historical failures bind their captured policy and
raw output; old passes cannot qualify current source. Reclassifying never waives
a failure. Unfiltered end-to-end failures retain acceptance significance even
when run for diagnostic inventory or retained under an older policy. Validate syntax and the
focused counterexample, then the coherent slice and original flow before the
frozen full matrix. A known-red full run needs a named diagnostic purpose;
avoid rerunning it as a substitute for diagnosis. Relevant edits invalidate
affected evidence; retain failures, uncertainty and the incident lineage.

Repair-bound execution records use `run_window.started_at` and
`run_window.finished_at` from observed timezone-aware command receipts.
Unexecuted work keeps an empty attempt list, never invented times or results.
Historical attempts set `historical_policy` to a captured `{path, sha256}`
binding; current attempts use `null`. `failure_ref` identifies the failure a
diagnostic addresses; `reassessment_ref` identifies that completed diagnostic
before a related retry. Never rewrite original failed records to manufacture
current evidence. Registry completeness and causal relevance remain reviewed;
the checker does not scan undeclared session history.

All configured acceptance commands must have full observed end-to-end passes
before `incident-fixed`. This checks declared relationships and existing run
contracts, not causal truth, reviewer authenticity, runtime timing stability or
agent obedience. Primary review still decides fidelity, non-applicability and
whether observations actually discriminate the proposed mechanism. Policy
checkers must state which fields and behavior they validate; test every declared
mandatory member through the actual checker, not merely a separate prose test.

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
