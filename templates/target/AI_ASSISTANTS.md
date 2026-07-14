# AI Assistant Entry Point

This repository uses Alatyr Core. All assistants should treat `AGENTS.md` as
the canonical instruction file.

Before making changes:

1. Treat `AGENTS.md` as preloaded; then read `.ai/alatyr.yaml`,
   `.ai/README.md`, and `.ai/assistant/context-router.json`.
2. Select the smallest task profile and project-area overlays, then read only
   their required framework, project, assistant, flow, gate, policy, and
   validation files.
3. Read `.ai/assistant/context-profiles.md`, the module profile, source-of-truth
   registry, blueprint, and gates only when selected context or conflicting
   evidence requires them.
4. After installation/update, or when adapter state is unclear, read the
   post-install/update message templates before editing.
5. For Alatyr help or aliases (`alatyr-ai-inventory`, `alatyr-adaptation`,
   `alatyr-add-ai`), read `.ai/assistant/help.md` and
   `.ai/assistant/flows/operation-routing.flow.md`.

Assistant-specific bridge files must stay short and point back to canonical
target files.
