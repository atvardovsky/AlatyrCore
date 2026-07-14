# Post-Install Assistant Chat Message

Use this template for the assistant's chat response after Alatyr Core is
installed in `{PROJECT_NAME}`.

Replace placeholders with target facts before sending the message.

```text
Alatyr Core is installed for `{PROJECT_NAME}`.

Entry points:
- `AGENTS.md`
- `AI_ASSISTANTS.md`
- `.ai/alatyr.yaml`
- `.ai/README.md`
- `.ai/assistant/templates/installation-note.md`
- `.ai/assistant/help.md`
- `.ai/assistant/help-reference.md`
- `.ai/assistant/context-router.json`
- `.ai/assistant/context-profiles.md`
- `.ai/assistant/module-profile.md`
- `.ai/project/source-of-truth-registry.md`
- `.ai/assistant/maturity-profile.md`
- `.ai/assistant/bridge-capability-matrix.md`

Future assistant bootstrap:
- Do not rely on this chat message alone.
- Treat `AGENTS.md` as preloaded; start from `.ai/alatyr.yaml`, `.ai/README.md`, and `.ai/assistant/context-router.json`.
- Load profiles, module state, registries, blueprint, gates, and the installation note only when routing or unclear adapter state requires them.
- If the adapter state is unclear, ask for "Alatyr help" or run `recheck-after-installation` before editing files.

Installed operation help:
- Ask for "Alatyr help" to see available operations.
- Use `.ai/assistant/templates/operation-request.md` for structured requests.

Available next actions:
- `create-project-blueprint`: create or repair project source-of-truth docs from target evidence.
- `recheck-after-installation`: verify the installed adapter and report gaps.
- `product-change`: run blueprint-driven change from intent through validation and evidence.
- `logical-integrity-review`: check consistency across code, docs, tests, diagrams, prompts, skills, gates, and bridges.
- `large-task`: coordinate cross-boundary or resumable work with bounded workstreams, checkpoints, and final convergence.
- `ai-infrastructure-inventory`: check existing AI instructions, prompts, skills, wrappers, bridges, rules, MCP/tool configs, gates, and checkers. Alias: `alatyr-ai-inventory`.
- `skill-adaptation`: adapt or add skills, prompts, wrappers, bridges, rules, MCP/tool configs, gates, checkers, or third-party assistant infrastructure. Aliases: `alatyr-adaptation <source>`, `alatyr-add-ai <source>`.
- Use `continue large task <packet-path-or-operation-id>` to resume a target-approved operation packet without reloading completed workstream context.

Validation run:
`{VALIDATION_RUN_OR_UNRESOLVED}`

Known adapter gaps:
`{KNOWN_GAPS_OR_NONE}`

Suggested first request:
Use the installed Alatyr adapter in this repository.
Operation type: recheck-after-installation
Goal: verify the installation and list remaining adapter gaps.
Non-goals: do not change project behavior.
Allowed actions: read-only
```
