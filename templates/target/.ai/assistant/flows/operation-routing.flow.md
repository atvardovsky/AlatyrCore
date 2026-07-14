# Operation Routing Flow

Use this flow in `{PROJECT_NAME}` when the programmer asks for Alatyr help,
asks for available actions, asks for commands, or gives a request that cannot
be safely classified.

Also use this flow when the programmer uses a target alias such as
`alatyr-ai-inventory`, `alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}`, or
`alatyr-add-ai {AI_INFRASTRUCTURE_SOURCE}`.

Replace placeholders with target facts before accepting installation.

## Target Sources

- Context router: `.ai/assistant/context-router.json`
- Context profiles: `.ai/assistant/context-profiles.md`
- Operation help: `.ai/assistant/help.md`
- Installed operations guidance: `.ai/framework/installed-operations.md`
- Operation help guidance: `.ai/framework/operation-help.md`
- Project source of truth: `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- Target validation: `{TARGET_VALIDATION}`
- Approval constraints: `{TARGET_APPROVAL_CONSTRAINTS}`
- AI infrastructure source/access policy:
  `{TARGET_AI_INFRASTRUCTURE_SOURCE_ACCESS_POLICY}`

## Steps

1. Treat `AGENTS.md` as preloaded. Load bootstrap context only:
   `.ai/alatyr.yaml`, `.ai/README.md`, and
   `.ai/assistant/context-router.json`. Load `.ai/assistant/help.md` because
   this flow handles help or ambiguity.
2. Select the smallest matching context profile from
   `.ai/assistant/context-router.json`; use
   `.ai/assistant/context-profiles.md` for the human rationale or when router
   and Markdown evidence conflict.
3. Load only the selected profile and project-area overlays' required
   framework, project, assistant, flow, gate, policy, and validation context
   before editing. Do not load all `.ai/framework` or `.ai/project` files just
   to route an operation. Record budget exceptions in the context receipt.
4. Restate the request in concrete language.
5. Classify the request as framework-core, project, repository adapter,
   bridge, generated-artifact, skill/prompt, or unclear work.
6. Normalize documented operation aliases from `.ai/assistant/help.md`.
7. Record allowed actions when the request supplies them:
   `read-only`, `docs-only`, `adapter-only`, `code-and-tests`, or
   `full-with-approval`.
8. Match the request to one target operation and flow when the intent is clear.
9. Decide whether the `large-or-resumable` task-scale overlay applies. Route
   large, cross-boundary, multi-workstream, budget-exceeding, or resumable work
   through `.ai/assistant/flows/large-task-orchestration.flow.md`; keep small
   work on its normal operation flow.
10. If two or more operations could apply, show the closest options with short
   descriptions and ask for the smallest missing decision.
11. If the request matches `alatyr-ai-inventory`, classify it as
   `ai-infrastructure-inventory` and continue with
   `.ai/assistant/flows/ai-infrastructure-inventory.flow.md` using the
   `inventory` route from `.ai/assistant/ai-infrastructure-router.json`.
12. If the request matches `alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}` or
   `alatyr-add-ai {AI_INFRASTRUCTURE_SOURCE}`, classify it as
   `skill-adaptation`, record `{AI_INFRASTRUCTURE_SOURCE}` as untrusted input,
   and continue with `.ai/assistant/flows/skill-adaptation.flow.md` only after
   checking inventory, source access, provenance, approval, and safety rules.
    Select the `adapt-import` route and target item ID before loading source
    policy or item content.
13. If the user asks for commands, explain that Alatyr uses assistant requests
   over Markdown adapter files unless `{PROJECT_NAME}` defines a local command.
14. Do not edit files while the operation is still ambiguous or when the
   requested edit exceeds allowed actions.
15. When the operation is selected, continue with the matching flow and apply
   allowed-action, approval, validation, and final-evidence rules.

## Final Evidence

Report:

- requested action
- matched operation or unresolved operation
- matching flow or missing adapter fact
- reason for the selected operation
- missing input or ambiguity, if any
- allowed actions and whether the selected flow stays within them
- task-scale overlay and packet requirement, if any
- next safe action

## Rejection Criteria

Reject or revise routing work that:

- invents an `alatyr` CLI command
- starts repository edits before the operation is selected
- chooses a protected operation without naming approval constraints
- ignores `.ai/assistant/help.md`
- claims target validation exists without target evidence
