# Post-Update Assistant Chat Message

Use this template for the assistant's chat response after Alatyr Core is
updated in `{PROJECT_NAME}`.

Replace placeholders with target facts before sending the message.

```text
Alatyr Core has been updated for `{PROJECT_NAME}`.

Framework baseline:
`{ALATYR_CORE_SOURCE_OR_BASELINE}`

Framework version/schema:
`{ALATYR_CORE_VERSION}`, adapter schema `{ALATYR_ADAPTER_SCHEMA_VERSION}`, template `{ALATYR_TEMPLATE_VERSION}`

Updated adapter surfaces:
`{UPDATED_ADAPTER_SURFACES}`

Future assistant bootstrap:
- Do not rely on this chat message alone.
- Treat `AGENTS.md` as preloaded; start from `.ai/alatyr.yaml`, `.ai/README.md`, and `.ai/assistant/context-router.json`.
- Load profiles, module state, registries, blueprint, gates, and the installation note only when routing or unclear adapter state requires them.
- Send `Alatyr` for compact actions or `Alatyr status` for a read-only adapter health check.
- If migration impact is unclear, run `recheck-after-framework-update` before editing files.

Recommended follow-up:
Use the installed Alatyr adapter in this repository.
Operation type: recheck-after-framework-update
Goal: compare the installed adapter against the updated Alatyr Core baseline and report required migrations.
Non-goals: do not change project behavior without approval.
Allowed actions: read-only

Migration assessment:
`{MIGRATION_ASSESSMENT_PATH_OR_MANUAL_REVIEW}`

Load only canonical sources and target surfaces selected by the migration
assessment. Record candidate context intentionally omitted.

Operation help:
- Send `Alatyr` for compact relevant operations; use `Alatyr status` or
  `Alatyr doctor` for read-only health evidence.
- Clear requests route automatically through
  `.ai/assistant/operation-catalog.json`; operation IDs are optional.
- Risky or cross-boundary changes show a pre-change preview before edits.
- Use `.ai/assistant/help.md`, `.ai/assistant/help-reference.md`, and `.ai/assistant/templates/operation-request.md` for structured requests.
- Use `large-task` only for cross-boundary or resumable work, and resume an existing packet when one is named.
- Recheck AI infrastructure router entries and adaptation records when skills, prompts, gates, tools, or bridge contracts changed.
- Use `alatyr-suggest-ai <scope>` or `alatyr-improve-ai <item-id>` for a read-only recommendation when project needs or existing item outcomes changed.

Validation run:
`{VALIDATION_RUN_OR_UNRESOLVED}`

Known adapter gaps or migrations:
`{KNOWN_GAPS_OR_MIGRATIONS}`

Migration note:
`.ai/assistant/templates/migration-note.md` or `{MIGRATION_NOTE_RESULT}`
```
