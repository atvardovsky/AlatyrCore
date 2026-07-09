# Post-Update Assistant Chat Message

Use this template for the assistant's chat response after Alatyr Core is
updated in `{PROJECT_NAME}`.

Replace placeholders with target facts before sending the message.

```text
Alatyr Core has been updated for `{PROJECT_NAME}`.

Framework baseline:
`{ALATYR_CORE_SOURCE_OR_BASELINE}`

Updated adapter surfaces:
`{UPDATED_ADAPTER_SURFACES}`

Future assistant bootstrap:
- Do not rely on this chat message alone.
- Future sessions should start from `AGENTS.md`, `AI_ASSISTANTS.md`, `.ai/README.md`, and `.ai/assistant/templates/installation-note.md`.
- If the updated baseline or adapter state is unclear, ask for "Alatyr help" or run `recheck-after-framework-update` before editing files.

Recommended follow-up:
Use the installed Alatyr adapter in this repository.
Operation type: recheck-after-framework-update
Goal: compare the installed adapter against the updated Alatyr Core baseline and report required migrations.
Non-goals: do not change project behavior without approval.

Operation help:
- Ask for "Alatyr help" to see available operations and matching flows.
- Use `.ai/assistant/help.md` and `.ai/assistant/templates/operation-request.md` for structured requests.

Validation run:
`{VALIDATION_RUN_OR_UNRESOLVED}`

Known adapter gaps or migrations:
`{KNOWN_GAPS_OR_MIGRATIONS}`
```
