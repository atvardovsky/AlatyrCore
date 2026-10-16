---
alatyr_test_execution:
  policy: .ai/project/testing/test-first-policy.json
  timing: target-policy
  red_evidence: target-policy
  coverage_writes: canonical-owner
---
# Test-First Development Skill

Status: `{PROPOSED_ACCEPTED_DEPRECATED_CONTRADICTED_OR_UNKNOWN}`
Target policy: `.ai/project/testing/test-first-policy.json`
Portable rule: `.ai/framework/test-first-development.md`

Use this skill only after the target has adapted it and enabled the
`test-first-development` module.

## Activation

- The user explicitly requests test-first, TDD, regression-first,
  characterization-first, or contract-first work.
- An enabled target trigger returns `required`.
- A `recommended` result has been accepted for this task.

## Process

1. Load the accepted target policy and selected trigger only.
2. Name the changed fact and choose the smallest proving target test level.
3. Follow `.ai/assistant/flows/test-first-change.flow.md`; do not maintain a
   separate RED/GREEN sequence here. Target execution timing and current-scope
   authorization apply before every command, including baseline and coverage.
4. Write canonical project testing sources first; refresh Alatyr mirrors from
   those owners, never in the reverse direction.
5. Report actual evidence state and proof boundary. A manual-review deferral is
   not RED, a passed test, or an automatically accepted test-after exception.

## Prohibited

- Do not activate an unadapted or unresolved target policy.
- Do not invent commands, fixtures, test levels, isolation, or exceptions.
- Do not accept syntax, setup, infrastructure, or unrelated failure as RED.
- Do not weaken useful tests or assertions to obtain GREEN.
- Do not claim structural records prove semantic test quality.
