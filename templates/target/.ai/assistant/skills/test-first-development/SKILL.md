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
3. Record observable examples and boundaries.
4. Prove valid RED with the target command and expected behavior failure.
5. Make the minimum implementation change and prove GREEN.
6. Refactor while green, run broader risk-selected validation, and apply
   logical integrity.
7. Record the evidence template, exceptions, skipped checks, and residual risk.

## Prohibited

- Do not activate this placeholder as an accepted target skill.
- Do not invent commands, fixtures, test levels, isolation, or exceptions.
- Do not accept syntax, setup, infrastructure, or unrelated failure as RED.
- Do not weaken useful tests or assertions to obtain GREEN.
- Do not claim structural records prove semantic test quality.
