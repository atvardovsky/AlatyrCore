# Agent Instructions

This repository uses Alatyr Core for AI-assisted development.

Replace every `{PLACEHOLDER}` in this file from target repository facts before
claiming installation is complete.

## Mandatory Context

Before changing code, tests, docs, diagrams, prompts, gates, or architecture,
read:

- `.ai/README.md`
- `.ai/framework/README.md`
- `.ai/framework/contour.md`
- `.ai/framework/guarantees.md`
- `.ai/framework/project-adapter-contract.md`
- `.ai/framework/portability.md`
- `.ai/framework/context-discovery.md`
- `.ai/framework/change-risk-model.md`
- `.ai/framework/logical-integrity.md`
- `.ai/framework/blueprint-driven-change.md`
- `.ai/framework/security-safety-guidance.md`
- `.ai/framework/diagram-guidance.md`
- `.ai/framework/testing-guidance.md`
- `.ai/framework/skill-adaptation.md`
- `.ai/framework/adapter-maturity.md`
- `.ai/framework/lifecycle.md`
- `.ai/project/contour.md`
- `.ai/assistant/contour.md`
- `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- `.ai/assistant/gates/checklist.md`
- the matching flow under `.ai/assistant/flows`

## Project Rules

- Project name: `{PROJECT_NAME}`.
- Primary stack: `{TARGET_STACK}`.
- Product/source-of-truth docs: `{TARGET_SOURCE_OF_TRUTH_DOCS}`.
- Validation commands or manual checks: `{TARGET_VALIDATION}`.
- Security/live-service policy: `{TARGET_SECURITY_POLICY}`.
- Diagram policy: `{TARGET_DIAGRAM_POLICY}`.
- Skill/prompt policy: `{TARGET_SKILL_PROMPT_POLICY}`.

## Alatyr Core Rules

- Keep framework rules under `.ai/framework`.
- Keep target project facts under `.ai/project` or target public docs.
- Keep repository adapter workflows, prompts, gates, skills, bridge files, and
  validation facts under `.ai/assistant` or assistant-specific bridge files.
- Do not invent project facts, commands, business rules, security policy, or
  diagram tooling.
- Use logical integrity review for semantic fact changes and repair the
  smallest coherent set of owning files.
- Use blueprint-driven change or the target equivalent for accepted product
  behavior changes.
- Adapt skills, prompts, wrappers, and third-party assistant infrastructure
  from target evidence before making them canonical.
- Use target validation only when it exists. Report unresolved checks.

## Approval Gates

Require explicit programmer approval before:

- architecture changes
- accepted business behavior changes
- weakened tests, gates, documentation-sync rules, or approval requirements
- new production dependencies or external services
- live, destructive, spend-affecting, or data-loss side effects
- importing third-party assistant infrastructure into canonical target files
- overwriting existing AI instructions

## Final Evidence

Every completed change should report:

- changed facts
- logical integrity result
- documentation updated or why none was needed
- tests or validation run
- skipped checks and residual risk
- approvals used
