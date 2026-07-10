# Alatyr Context Profiles

Use this file to choose the smallest sufficient context for `{PROJECT_NAME}`.
Replace placeholders with target evidence before accepting installation.

Bootstrap context for every task:

- `AGENTS.md`
- `.ai/alatyr.yaml`
- `.ai/README.md`
- `.ai/assistant/context-profiles.md`
- `.ai/assistant/module-profile.md`
- `.ai/project/contour.md`
- `.ai/project/source-of-truth-registry.md`
- `.ai/assistant/contour.md`
- `{TARGET_PROJECT_SOURCE_OF_TRUTH}`

After bootstrap, choose one profile and read its required context before
editing files. Expand only when boundaries, conflicts, or approval scope
require it.

## Profile: `docs-local`

Use when: local wording, README, diagram text, or non-semantic documentation
changes do not alter accepted project behavior.

Required context:

- `.ai/framework/context-discovery.md`
- `.ai/framework/testing-guidance.md`
- `.ai/framework/diagram-guidance.md`
- `.ai/assistant/gates/checklist.md`
- `{TARGET_DOC_SOURCE_OF_TRUTH}`

Approval gates: only if docs change accepted behavior, security posture,
public contract, or approval rules.

Validation/evidence: report changed docs, owner file, skipped checks, and why
no logical integrity expansion was needed.

## Profile: `code-local`

Use when: implementation or tests change without changing accepted behavior,
architecture, data model, external contract, security posture, or AI
infrastructure.

Required context:

- `.ai/framework/context-discovery.md`
- `.ai/framework/change-risk-model.md`
- `.ai/framework/testing-guidance.md`
- `.ai/framework/logical-integrity.md`
- `.ai/assistant/gates/checklist.md`
- `{TARGET_CODE_SOURCE_OF_TRUTH}`

Approval gates: only if the task crosses a protected category.

Validation/evidence: run or report `{TARGET_CODE_VALIDATION}` and explain doc
sync or why none was needed.

## Profile: `business-change`

Use when: accepted behavior, domain rules, product policy, workflows, or public
contract change.

Required context:

- `.ai/framework/context-discovery.md`
- `.ai/framework/change-risk-model.md`
- `.ai/framework/source-of-truth-registry.md`
- `.ai/framework/logical-integrity.md`
- `.ai/framework/blueprint-driven-change.md`
- `.ai/framework/testing-guidance.md`
- `.ai/assistant/flows/blueprint-driven-change.flow.md`
- `.ai/assistant/gates/checklist.md`
- `{TARGET_BLUEPRINT_OR_PRODUCT_SOURCE_OF_TRUTH}`

Approval gates: explicit programmer approval before changing accepted business
behavior.

Validation/evidence: changed fact, owning blueprint or source of truth,
implementation/test/doc sync, diagram sync if applicable, approvals, and final
logical integrity result.

## Profile: `architecture-change`

Use when: modules, dependencies, boundaries, runtime topology, public APIs, or
cross-component contracts change.

Required context:

- `.ai/framework/context-discovery.md`
- `.ai/framework/change-risk-model.md`
- `.ai/framework/source-of-truth-registry.md`
- `.ai/framework/logical-integrity.md`
- `.ai/framework/blueprint-driven-change.md`
- `.ai/framework/security-safety-guidance.md`
- `.ai/framework/testing-guidance.md`
- `.ai/framework/diagram-guidance.md`
- `.ai/assistant/flows/blueprint-driven-change.flow.md`
- `.ai/assistant/gates/checklist.md`
- `{TARGET_ARCHITECTURE_SOURCE_OF_TRUTH}`

Approval gates: explicit programmer approval for architecture changes and new
production dependencies or services.

Validation/evidence: architecture owner update, affected areas, validation,
diagrams or why none changed, and residual risk.

## Profile: `data-change`

Use when: schema, persistence, migrations, data contracts, retention,
backfills, imports, exports, or data ownership change.

Required context:

- `.ai/framework/context-discovery.md`
- `.ai/framework/change-risk-model.md`
- `.ai/framework/source-of-truth-registry.md`
- `.ai/framework/logical-integrity.md`
- `.ai/framework/security-safety-guidance.md`
- `.ai/framework/testing-guidance.md`
- `.ai/assistant/gates/checklist.md`
- `{TARGET_DATA_SOURCE_OF_TRUTH}`

Approval gates: explicit approval for destructive, data-loss, live-service,
privacy, or migration-risk changes.

Validation/evidence: canonical data owner, derived surfaces, migration or
rollback notes where applicable, validation, and unresolved risk.

## Profile: `security-sensitive`

Use when: secrets, credentials, permissions, authentication, authorization,
network access, external services, destructive actions, spend, production, or
third-party trust boundaries are involved.

Required context:

- `.ai/framework/change-risk-model.md`
- `.ai/framework/security-safety-guidance.md`
- `.ai/framework/logical-integrity.md`
- `.ai/framework/approval-records.md`
- `.ai/assistant/policies/prompt-injection.md`
- `.ai/assistant/gates/checklist.md`
- `{TARGET_SECURITY_SOURCE_OF_TRUTH}`

Approval gates: explicit approval before protected changes; use approval
records when scope or plan evidence matters.

Validation/evidence: security owner evidence, actions avoided, approvals,
validation, skipped checks, and residual risk.

## Profile: `ai-infrastructure`

Use when: adding, importing, adapting, replacing, or reviewing prompts, skills,
assistant rules, wrappers, bridge files, MCP/tool configs, checkers, gates,
flows, templates, or other AI infrastructure.

Required context:

- `.ai/framework/project-adapter-contract.md`
- `.ai/framework/portability.md`
- `.ai/framework/skill-adaptation.md`
- `.ai/framework/security-safety-guidance.md`
- `.ai/framework/prompt-injection.md`
- `.ai/framework/approval-records.md`
- `.ai/assistant/flows/ai-infrastructure-inventory.flow.md`
- `.ai/assistant/flows/skill-adaptation.flow.md`
- `.ai/assistant/policies/ai-infrastructure-source-access.md`
- `.ai/assistant/policies/prompt-injection.md`
- `.ai/assistant/gates/checklist.md`

Approval gates: explicit approval before importing third-party infrastructure
into canonical target files or changing tool permissions.

Validation/evidence: inventory, provenance, source hash or commit, license or
unknown-license note, normalized target surfaces, compatibility review, and
approval evidence.

## Profile: `framework-upgrade`

Use when: installing Alatyr, updating Alatyr Core, rechecking the adapter,
reviewing maturity, or repairing drift after framework changes.

Required context:

- `.ai/framework/README.md`
- `.ai/framework/contour.md`
- `.ai/framework/guarantees.md`
- `.ai/framework/rule-ownership.md`
- `.ai/framework/rule-registry.md`
- `.ai/framework/rule-registry.json`
- `.ai/framework/project-adapter-contract.md`
- `.ai/framework/portability.md`
- `.ai/framework/module-profile.md`
- `.ai/framework/scaffolding.md`
- `.ai/framework/context-profiles.md`
- `.ai/framework/source-of-truth-registry.md`
- `.ai/framework/bridge-capability-matrix.md`
- `.ai/framework/migration-diff.md`
- `.ai/framework/effectiveness-metrics.md`
- `.ai/framework/adapter-maturity.md`
- `.ai/framework/lifecycle.md`
- `.ai/framework/installed-operations.md`
- `.ai/framework/operation-help.md`
- `.ai/framework/approval-records.md`
- `.ai/assistant/flows/adapter-recheck.flow.md`
- `.ai/assistant/flows/operation-routing.flow.md`
- `.ai/assistant/templates/installation-note.md`
- `.ai/assistant/templates/post-install-message.md`
- `.ai/assistant/templates/post-update-message.md`
- `.ai/assistant/gates/checklist.md`

Approval gates: approval before overwriting existing instructions, changing
protected adapter behavior, or adopting third-party assistant infrastructure.

Validation/evidence: adapter version/schema state, changed framework baseline,
affected target files, gaps, local deviations, validation, and migration
actions.
