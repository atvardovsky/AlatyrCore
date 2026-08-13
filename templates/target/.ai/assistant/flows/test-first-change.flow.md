# Test-First Change Flow

## Purpose

Apply the accepted `{PROJECT_NAME}` test-first policy to one bounded changed
fact, defect, invariant, contract, or refactor.

## Steps

1. Confirm `test-first-development` is enabled and load
   `.ai/project/testing/test-first-policy.json`.
2. Name the changed fact, invariant, defect, or contract and canonical owner.
3. Evaluate the target activation triggers and report `required`,
   `recommended`, `not-indicated`, or `blocked`.
4. For `recommended`, state trigger, proposed mode, level, expected cost, and
   next action once. Continue only when the user accepts or the request already
   asks for test-first work. For `required`, apply the target gate.
5. Select the permitted mode and smallest proving target test level. Resolve
   the exact target command, paths, fixtures, helpers, and isolation rules.
6. Record observable acceptance examples, negative paths, and boundaries.
7. Run the relevant baseline when required by target policy.
8. Add or select the focused test and run it. Accept RED only when failure is
   caused by the expected missing or incorrect behavior, not syntax, setup,
   imports, unavailable infrastructure, or unrelated failures.
9. Make the minimum implementation change and prove GREEN with the same focused
   contract and command.
10. Refactor while keeping the focused contract green, or record why refactor
    was skipped.
11. Run broader target validation selected by changed-fact risk and boundary
    crossings. Do not invent commands or call live services without policy and
    approval.
12. Apply logical integrity review and synchronize required docs, diagrams,
    contracts, prompts, skills, gates, and project vocabulary.
13. Complete `.ai/assistant/templates/test-first-evidence.md` and report
    approvals, skipped checks, exceptions, and residual risk.

## Exception Path

Use `test-after-with-reason` only when an accepted target exception matches.
Record the exception ID, authority or approval, reason test-first was not
feasible, alternative validation, and residual risk. Do not create a new
exception during implementation merely to bypass RED evidence.

## Rejection Criteria

Reject or revise work that reports unexecuted RED/GREEN, accepts unrelated
failure as RED, weakens tests to obtain GREEN, uses a level that cannot prove
the contract, or applies a disabled, stale, placeholder, or blocked policy.
