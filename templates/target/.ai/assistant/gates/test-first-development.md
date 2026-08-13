# Test-First Development Gate

Apply this gate only after the compact recommendation check or an explicit
test-first/configuration request.

## Recommendation

- Policy state and evidence revision are known.
- Changed fact, defect, invariant, contract, or refactor risk is named.
- Result is `required`, `recommended`, `not-indicated`, or `blocked`.
- A recommendation names trigger, proposed mode, likely test level, expected
  cost, and next action and is shown no more than once per task.
- Disabled, deferred, or missing module state does not become a blocker unless
  another target-owned gate requires test-first work.

## Enablement

- Target owner and decision authority are recorded.
- Commands, levels, paths, fixtures, isolation, exceptions, and evidence rules
  come from target evidence.
- Placeholder or blocked policy is not reported as enabled.
- Dependency, CI, merge-gate, permission, or protected changes have approval.

## Execution

- Selected mode and test level match the accepted policy trigger.
- Acceptance examples prove observable behavior or contract.
- RED was executed and failed for the expected behavior reason.
- GREEN used the same focused contract and passed.
- Existing useful assertions were not weakened or removed to obtain GREEN.
- Refactor result or skip reason is recorded.
- Broader risk-selected validation and logical integrity were completed or
  reported unresolved.
- Structural validation is not claimed as proof of test semantic quality.
