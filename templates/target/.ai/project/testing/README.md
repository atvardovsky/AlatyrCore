# Project Testing And Test-First Policy

Use this project-contour index to record how `{PROJECT_NAME}` selects tests and
when test-first development is enabled, recommended, exempted, or blocked.

Replace placeholders from target evidence before enabling the
`test-first-development` module.

Test-first policy: `.ai/project/testing/test-first-policy.json`
General portable testing guidance: `.ai/framework/testing-guidance.md`
Portable test-first rule: `.ai/framework/test-first-development.md`
Source-of-truth registry: `.ai/project/source-of-truth-registry.md`

## Ownership

Testing strategy owner: `{TARGET_TEST_STRATEGY_OWNER}`
Test-first decision authority: `{TARGET_TEST_FIRST_DECISION_AUTHORITY}`
Last reviewed: `{ISO_DATE_OR_UNKNOWN_WITH_REASON}`
Evidence revision: `{TARGET_REVISION_OR_UNKNOWN_WITH_REASON}`

## Enablement

The module is enabled only when the policy records accepted target commands,
test levels, trigger severity, isolation, exceptions, evidence requirements,
and owners. Enabling an advisory adapter workflow does not silently add test
dependencies, CI jobs, required merge gates, or production behavior.

Use `Alatyr enable test-first` to assess and propose or apply this policy. This
is an assistant request shortcut, not a shell command. Approval is required
when target policy, dependencies, CI, merge requirements, permissions, or
protected behavior require it.

## Recommendation Behavior

The assistant may suggest a test-first assessment once per task when bounded
changed-fact and risk evidence matches the portable recommendation gate. A
suggestion states the trigger, proposed mode, likely test level, expected cost,
and next action. It is not mandatory unless an enabled accepted target policy
marks the matching trigger as required.

## Boundaries

Project files own test strategy and policy. The assistant flow and skill apply
that policy. AlatyrCore does not own target commands, tools, fixtures, coverage,
isolation, merge rules, or assertions, and structural validation cannot prove
that a test is semantically correct.
