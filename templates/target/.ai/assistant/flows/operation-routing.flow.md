# Operation Routing Flow

Use this flow in `{PROJECT_NAME}` when the programmer asks for Alatyr help,
asks for available actions, asks for commands, or gives a request that cannot
be safely classified.

Replace placeholders with target facts before accepting installation.

## Target Sources

- Operation help: `.ai/assistant/help.md`
- Installed operations guidance: `.ai/framework/installed-operations.md`
- Operation help guidance: `.ai/framework/operation-help.md`
- Project source of truth: `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- Target validation: `{TARGET_VALIDATION}`
- Approval constraints: `{TARGET_APPROVAL_CONSTRAINTS}`

## Steps

1. Load `AGENTS.md`, `AI_ASSISTANTS.md`, `.ai/README.md`, `.ai/framework`,
   `.ai/project`, `.ai/assistant/contour.md`, and `.ai/assistant/help.md`.
2. Restate the request in concrete language.
3. Classify the request as framework-core, project, repository adapter,
   bridge, generated-artifact, skill/prompt, or unclear work.
4. Match the request to one target operation and flow when the intent is clear.
5. If two or more operations could apply, show the closest options with short
   descriptions and ask for the smallest missing decision.
6. If the user asks for commands, explain that Alatyr uses assistant requests
   over Markdown adapter files unless `{PROJECT_NAME}` defines a local command.
7. Do not edit files while the operation is still ambiguous.
8. When the operation is selected, continue with the matching flow and apply
   approval, validation, and final-evidence rules.

## Final Evidence

Report:

- requested action
- matched operation or unresolved operation
- matching flow or missing adapter fact
- reason for the selected operation
- missing input or ambiguity, if any
- next safe action

## Rejection Criteria

Reject or revise routing work that:

- invents an `alatyr` CLI command
- starts repository edits before the operation is selected
- chooses a protected operation without naming approval constraints
- ignores `.ai/assistant/help.md`
- claims target validation exists without target evidence
