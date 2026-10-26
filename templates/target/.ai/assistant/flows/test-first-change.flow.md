---
alatyr_test_execution:
  policy: .ai/project/testing/test-first-policy.json
  timing: target-policy
  red_evidence: target-policy
  coverage_writes: canonical-owner
---
# Test-First Change Flow

## Purpose

Apply the accepted `{PROJECT_NAME}` test-first policy to one bounded changed
fact, defect, invariant, contract, or refactor.

## Steps

1. Confirm `test-first-development` is enabled and load
   `.ai/project/testing/test-first-policy.json`.
   Use `.ai/project/testing/execution.md` when the target has split guidance;
   older adapters retain their current inline owner until a reviewed migration.
2. Name the changed fact, invariant, defect, or contract and canonical owner.
3. Evaluate the target activation triggers and report `required`,
   `recommended`, `not-indicated`, or `blocked`.
4. For `recommended`, state trigger, proposed mode, level, expected cost, and
   next action once. Continue only when the user accepts or the request already
   asks for test-first work. For `required`, apply the target gate.
5. Select the permitted mode and smallest proving target test level. Resolve
   the exact target command, paths, fixtures, helpers, and isolation rules.
   Read its execution contract: canonical owners, configuration, prerequisites,
   effects, environment, suite selection/exclusions, filter support and proof
   boundary. Inventory membership and module enablement never authorize a run.
   If the selected command requires schema-3 selection/timing controls, load
   `.ai/framework/test-execution-selection.md`. Reconcile the complete exact
   request against captured discovery before execution; a missing filename or
   unmatched case must not silently become a smaller successful request.
6. Record observable acceptance examples, negative paths, and boundaries.
   For uncertain/recurring defects, apply the incident review in the canonical
   test policy: qualify the original reproducer, competing causes, falsifier,
   actual fixture boundaries and expected whole-incident effect before repair.
   Load selected `.ai/project/testing/incident-repair.md` guidance when installed,
   not unrelated historical experiments. Preserve concurrent incident heads and
   unresolved predecessor obligations. Record experimental retention/reversion
   rationale in the existing expected/observed-effect review.
   When `repair_review` is enabled, retain the required `repair-evidence-review`
   obligation and author task-bound evidence using the adopted schema's
   `repair-review.json` or `repair-qualification.json` template. Do not
   remove that requirement to obtain acceptance. Missing or unknown boundaries
   remain explicit; component GREEN is not incident acceptance.
   For repeated/escaped incidents, inspect the registered current-task view
   before historical narrative. Keep the original initial state and terminal
   effect visible; if optional qualification is absent, request one explicit
   adoption decision rather than assuming template presence enabled it.
   For schema 2, load `.ai/framework/repair-qualification.md` and bind
   policy-selected actual scenario/control observations from
   JSON run artifacts. Requested flags, a renamed output or a copied verified
   label cannot qualify a repair. A faithful known-failing diagnostic may
   qualify repair; do not require full acceptance GREEN before fixing it.
7. Resolve current-scope execution authorization and target timing before any
   baseline, RED, GREEN, coverage or broader run. If review is pending, author
   tests and exact commands and defer execution. Continue implementation only
   when the accepted mode permits it; otherwise report `authored`/`blocked`
   and wait. Shared manual-review resources require their own explicit target
   permission; disposable-runner access does not authorize their use.
   Serialize selected qualification using target-owned resource admission.
   Strict cooperation preflight may refuse conflict/uncertainty, but never
   establishes a reservation, permission or absence of unreported work.
8. When authorized and required by the selected policy, run baseline/RED.
   Accept RED only when failure is
   caused by the expected missing or incorrect behavior, not syntax, setup,
   imports, unavailable infrastructure, or unrelated failures.
9. Follow the accepted timing: review-first projects may implement and present
   the change before execution. Do not manufacture historical RED or silently
   relax a strict mode. After authorization, prove GREEN with the same focused
   contract and command.
10. Refactor while keeping the focused contract green, or record why refactor
    was skipped.
11. Run broader target validation selected by changed-fact risk and boundary
    crossings. Do not invent commands or call live services without policy and
    approval.
    After a failed incident acceptance, stop dependent patch stacking and obtain
    discriminating evidence before another related attempt. Preserve the failed
    run and classify its cause without waiving it. Check the smallest faithful
    real flow first; known-red full runs need a named diagnostic purpose but
    retain acceptance significance. Final acceptance
    still requires the complete unchanged target matrix on frozen inputs.
    Keep policy-selected comparable performance measurements separate from
    functional acceptance. A component speedup does not clear the original
    incident. Continue independent authorized work around a named blocker.
12. Apply `.ai/assistant/gates/contract-artifacts.md` when the selected
    contract is represented by API, schema, event, generated-reference,
    fixture, persistence, public-interface, or external-boundary artifacts.
13. Apply `.ai/assistant/gates/visual-validation.md` when the behavior has UI,
    layout, accessibility-relevant, rendered diagram, or visual artifact
    effects.
14. Apply logical integrity review and synchronize required docs, diagrams,
    contracts, prompts, skills, gates, and project vocabulary.
    Change the canonical policy/coverage matrix before their Alatyr mirrors.
    Reconcile newly added tests with actual runner configuration and exclusions.
    Use canonical command/configuration evidence, not invented CLI options or
    suite names. Discovery never executes imported project code implicitly.
15. Complete `.ai/assistant/templates/test-first-evidence.md` and report
    approvals, skipped checks, exceptions, and residual risk.
    Keep authored, discovered, executed, passed, skipped and blocked separate.
    Metadata/case-ID checks and mocked browser tests prove only their boundary;
    an exit code alone or an all-skipped run cannot establish behavioral proof.

## Exception Path

Use `test-after-with-reason` only when an accepted target exception matches.
Record the exception ID, authority or approval, reason test-first was not
feasible, alternative validation, and residual risk. Do not create a new
exception during implementation merely to bypass RED evidence.

## Rejection Criteria

Reject or revise work that reports unexecuted RED/GREEN, accepts unrelated
failure as RED, weakens tests to obtain GREEN, uses a level that cannot prove
the contract, or applies a disabled, stale, placeholder, or blocked policy.
