# Project Testing And Test-First Policy

Use this project-contour index to record how `{PROJECT_NAME}` selects tests and
when test-first development is enabled, recommended, exempted, or blocked.

Replace placeholders from target evidence before enabling the
`test-first-development` module.

Test-first policy: `.ai/project/testing/test-first-policy.json`
Canonical project policy/matrix: resolve `execution_contract` from target
evidence. Edit those owners first; this adapter may be a subordinate mirror.
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

Resolve execution timing, review authority and current authorization before
running baseline, RED, GREEN, coverage or other test commands. Availability is
separate from permission. Record configuration, prerequisites, effects,
environment, suite scope, proof boundary and filter support per command.
Reconcile newly added tests and intentional exclusions against real selection.
Do not treat static case-ID discovery, all-skipped runs or mocked UI tests as
stronger behavioral evidence. The optional machine evidence template is
`.ai/assistant/templates/test-execution-evidence.json`; select current records
explicitly in the policy, never scan historical results during routine work.

For uncertain or repeated defects, assess optional `repair_review` with the
target owner. Use `.ai/assistant/templates/repair-review.json` only after that
decision. Keep the required `repair-evidence-review` obligation in incident
models; canonical model hypotheses own their statements. Review fixture fidelity,
falsifiers and expected original-case effects. The selected task validator
checks linked canonical runs, not whether the causal interpretation is true.
Do not replace the original full matrix with focused or favorable reruns.

Schema 1 remains supported. Explicit schema-2 adoption uses
`.ai/assistant/templates/repair-qualification.json` with policy-owned assertions
and digest-bound JSON result artifacts, not copied observed values. See the
portable owner's Incident Repair Review section for fields, limits and stage
semantics. Qualification may be based on a faithful failing diagnostic; it is
not functional acceptance or execution permission. Optional comparable median
measurements never turn historical passes into current acceptance. A framework
update alone enables none of these controls.

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
