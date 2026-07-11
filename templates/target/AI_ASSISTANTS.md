# AI Assistant Entry Point

This repository uses Alatyr Core. All assistants should treat `AGENTS.md` as
the canonical instruction file.

Before making changes:

1. Read `AGENTS.md`, `.ai/alatyr.yaml`, `.ai/README.md`,
   `.ai/assistant/context-router.json`,
   `.ai/assistant/context-profiles.md`, and
   `.ai/assistant/module-profile.md`.
2. Select the task profile, then read only profile-required framework,
   project, assistant, flow, gate, policy, and validation files.
3. Read `.ai/assistant/templates/installation-note.md`,
   `.ai/project/source-of-truth-registry.md`, `{TARGET_PROJECT_SOURCE_OF_TRUTH}`,
   and `.ai/assistant/gates/checklist.md` when required by the selected
   profile.
4. After installation/update, or when adapter state is unclear, read the
   post-install/update message templates before editing.
5. For Alatyr help or aliases (`alatyr-ai-inventory`, `alatyr-adaptation`,
   `alatyr-add-ai`), read `.ai/assistant/help.md` and
   `.ai/assistant/flows/operation-routing.flow.md`.

Assistant-specific bridge files must stay short and point back to canonical
target files.
