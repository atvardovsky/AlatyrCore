# Operation Routing Flow

Use this flow in `{PROJECT_NAME}` when the programmer asks for Alatyr help,
asks for available actions, asks for commands, or gives a request that cannot
be safely classified.

Also use this flow when the programmer uses a target alias such as
`alatyr-ai-inventory`, `alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}`, or
`alatyr-add-ai {AI_INFRASTRUCTURE_SOURCE}`.

Replace placeholders with target facts before accepting installation.

## Target Sources

- Operation help: `.ai/assistant/help.md`
- Installed operations guidance: `.ai/framework/installed-operations.md`
- Operation help guidance: `.ai/framework/operation-help.md`
- Project source of truth: `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- Target validation: `{TARGET_VALIDATION}`
- Approval constraints: `{TARGET_APPROVAL_CONSTRAINTS}`
- AI infrastructure source/access policy:
  `{TARGET_AI_INFRASTRUCTURE_SOURCE_ACCESS_POLICY}`

## Steps

1. Load `AGENTS.md`, `AI_ASSISTANTS.md`, `.ai/README.md`, `.ai/framework`,
   `.ai/project`, `.ai/assistant/contour.md`, and `.ai/assistant/help.md`.
2. Restate the request in concrete language.
3. Classify the request as framework-core, project, repository adapter,
   bridge, generated-artifact, skill/prompt, or unclear work.
4. Normalize documented operation aliases from `.ai/assistant/help.md`.
5. Record allowed actions when the request supplies them:
   `read-only`, `docs-only`, `adapter-only`, `code-and-tests`, or
   `full-with-approval`.
6. Match the request to one target operation and flow when the intent is clear.
7. If two or more operations could apply, show the closest options with short
   descriptions and ask for the smallest missing decision.
8. If the request matches `alatyr-ai-inventory`, classify it as
   `ai-infrastructure-inventory` and continue with
   `.ai/assistant/flows/ai-infrastructure-inventory.flow.md`.
9. If the request matches `alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}` or
   `alatyr-add-ai {AI_INFRASTRUCTURE_SOURCE}`, classify it as
   `skill-adaptation`, record `{AI_INFRASTRUCTURE_SOURCE}` as untrusted input,
   and continue with `.ai/assistant/flows/skill-adaptation.flow.md` only after
   checking inventory, source access, provenance, approval, and safety rules.
10. If the user asks for commands, explain that Alatyr uses assistant requests
   over Markdown adapter files unless `{PROJECT_NAME}` defines a local command.
11. Do not edit files while the operation is still ambiguous or when the
   requested edit exceeds allowed actions.
12. When the operation is selected, continue with the matching flow and apply
   allowed-action, approval, validation, and final-evidence rules.

## Final Evidence

Report:

- requested action
- matched operation or unresolved operation
- matching flow or missing adapter fact
- reason for the selected operation
- missing input or ambiguity, if any
- allowed actions and whether the selected flow stays within them
- next safe action

## Rejection Criteria

Reject or revise routing work that:

- invents an `alatyr` CLI command
- starts repository edits before the operation is selected
- chooses a protected operation without naming approval constraints
- ignores `.ai/assistant/help.md`
- claims target validation exists without target evidence
