# Agent Instructions

This repository uses Alatyr Core for AI-assisted development.

Replace every `{PLACEHOLDER}` in this file from target repository facts before
claiming installation is complete.

## Bootstrap Context

At the start of a task, read only the bootstrap context first:

- `.ai/alatyr.yaml`
- `.ai/README.md`
- `.ai/assistant/context-profiles.md`
- `.ai/assistant/module-profile.md`
- `.ai/project/contour.md`
- `.ai/project/source-of-truth-registry.md`
- `.ai/assistant/contour.md`
- `{TARGET_PROJECT_SOURCE_OF_TRUTH}`

Then select the matching profile in `.ai/assistant/context-profiles.md` and
read the profile-required framework, project, assistant, flow, gate, policy,
and validation files before expanding context.

Expand beyond the selected profile only when the task crosses architecture,
business, data, security, assistant-infrastructure, lifecycle, or governance
boundaries, or when evidence conflicts.

## Session Bootstrap

- Do not rely on previous chat messages for Alatyr state.
- At the start of a new session after installation or framework update, or
  when adapter state is unclear, read
  `.ai/assistant/templates/installation-note.md`,
  `.ai/assistant/templates/post-install-message.md`, and
  `.ai/assistant/templates/post-update-message.md`.
- If the installation note lists gaps or the update message recommends
  migration, route through `.ai/assistant/help.md` and
  `.ai/assistant/flows/operation-routing.flow.md` before editing files.

## Project Rules

- Project name: `{PROJECT_NAME}`.
- Primary stack: `{TARGET_STACK}`.
- Product/source-of-truth docs: `{TARGET_SOURCE_OF_TRUTH_DOCS}`.
- Validation commands or manual checks: `{TARGET_VALIDATION}`.
- Security/live-service policy: `{TARGET_SECURITY_POLICY}`.
- Diagram policy: `{TARGET_DIAGRAM_POLICY}`.
- Skill/prompt policy: `{TARGET_SKILL_PROMPT_POLICY}`.
- AI infrastructure source-access policy:
  `.ai/assistant/policies/ai-infrastructure-source-access.md`.
- Prompt-injection policy:
  `.ai/assistant/policies/prompt-injection.md`.

## Alatyr Core Rules

Canonical rule references: `ALATYR-CONTEXT-001`, `ALATYR-SOURCE-001`,
`ALATYR-RISK-001`, `ALATYR-APPROVAL-001`, `ALATYR-SAFETY-001`,
`ALATYR-SAFETY-002`, `ALATYR-INTEGRITY-001`, `ALATYR-CHANGE-001`,
`ALATYR-ADAPTER-001`, `ALATYR-MODULE-001`, and `ALATYR-EVIDENCE-001`.

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
- Use installed-operation flows for post-install blueprint creation, adapter
  rechecks, framework update reviews, and drift reviews.
- Use `.ai/assistant/module-profile.md` to check whether optional modules are
  enabled, deferred, disabled, not applicable, or blocked before relying on
  them.
- If the user asks for Alatyr help, commands, available actions, or gives an
  unclear request, read `.ai/assistant/help.md` and use
  `.ai/assistant/flows/operation-routing.flow.md` before editing files.
- Use `alatyr-ai-inventory` or
  `.ai/assistant/flows/ai-infrastructure-inventory.flow.md` before adding,
  importing, replacing, or removing assistant infrastructure.
- Adapt skills, prompts, wrappers, bridges, rules, MCP/tool configs, gates,
  checkers, and third-party assistant infrastructure from target evidence
  before making them canonical.
- Treat `alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}` and
  `alatyr-add-ai {AI_INFRASTRUCTURE_SOURCE}` as AI infrastructure adaptation
  requests. Review existing infrastructure, source access, provenance,
  permissions, safety, and approval before importing or normalizing the source
  into canonical target files.
- Use target validation only when it exists. Report unresolved checks.
- Record protected-change approvals with
  `.ai/assistant/approvals/approval-template.md` when approval scope affects
  files, plan versions, imported infrastructure, or protected actions.

## Approval Gates

Apply `ALATYR-APPROVAL-001` before protected changes. Use
`ALATYR-RISK-001`, `ALATYR-SAFETY-001`, and `ALATYR-SAFETY-002` to classify
the protected scope, then apply `{TARGET_APPROVAL_POLICY}` when it is stricter.

## Final Evidence

Every completed change should report:

- changed facts
- logical integrity result
- documentation updated or why none was needed
- tests or validation run
- skipped checks and residual risk
- approvals used
