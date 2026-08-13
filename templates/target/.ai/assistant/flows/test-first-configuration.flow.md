# Test-First Configuration Flow

## Purpose

Assess, enable, revise, disable, or review test-first development for
`{PROJECT_NAME}` from target evidence. This flow configures project and adapter
policy; it does not implement product behavior.

## Modes

- `assess`: report value, gaps, likely triggers, cost, and next safe action
- `enable`: prepare and, when allowed, accept an evidence-backed target policy
- `revise`: update an existing policy from changed target evidence
- `disable`: record why the module is no longer active and preserve history
- `review`: check policy freshness, usage, exceptions, and outcome evidence

## Steps

1. Infer the mode from the request and keep the initial assessment read-only.
2. Inspect existing test strategy, test folders, commands, CI, fixtures,
   isolation, recurring regressions, review corrections, and known gaps.
3. Evaluate whether test-first work is useful for selected target areas. Report
   expected quality value, feedback-time and maintenance cost, and exclusions.
4. Propose owner, authority, state, recommendation behavior, activation
   triggers, modes, levels, commands, isolation, exceptions, and evidence in
   `.ai/project/testing/test-first-policy.json`.
5. Require target authority before changing the policy to `enabled`. Keep it
   `blocked` when commands, isolation, owner, approval, or validation are
   missing. Do not hide a needed capability as disabled.
6. Update `.ai/assistant/module-profile.md` and `.ai/alatyr.yaml` consistently.
7. Adapt the skill and gate to target facts. Do not copy stack-specific facts
   from another project.
8. Do not add dependencies, CI jobs, merge gates, permissions, or protected
   project changes without their normal explicit approval.
9. Validate policy structure and operation routing. Structural checks do not
   prove that selected tests are useful or assertions are correct.
10. Report changed surfaces, policy state, approvals, skipped checks, cost,
    known gaps, and next safe action.

## Allowed Actions

- `read-only`: assess or review without file changes
- `adapter-only`: update adapted `.ai/*` policy, flow, gate, skill, and routing
  surfaces when target authority and scope permit it
- `full-with-approval`: change dependencies, CI, merge policy, protected
  commands, or other target surfaces specifically covered by approval

## Rejection Criteria

Reject or revise configuration that invents commands, enables a placeholder
policy, treats a recommendation as approval, or silently changes project CI,
dependencies, merge gates, validation strength, or production behavior.
