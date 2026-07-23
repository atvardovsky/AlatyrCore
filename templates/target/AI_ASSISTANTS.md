# AI Assistant Entry Point

This repository uses Alatyr Core. All assistants should treat `AGENTS.md` as
the canonical instruction file.

Before making changes:

1. Ensure `AGENTS.md` is loaded once; if it was not preloaded by the host,
   read it now. Then read `.ai/alatyr.yaml`, `.ai/README.md`, and `.ai/assistant/context-router.json`.
2. Select the smallest task profile and project-area overlays, then read only
   their required framework, project, assistant, flow, gate, policy, and
   validation files.
3. Read `.ai/assistant/context-profiles.md`, the module profile, source-of-truth
   registry, blueprint, and gates only when selected context or conflicting
   evidence requires them.
4. After installation/update or unclear state, read post-install/update message templates.
5. For `Alatyr`, status/doctor, enabled team aliases, or AI aliases (`alatyr-ai-inventory`, `alatyr-suggest-ai`,
   `alatyr-improve-ai`, `alatyr-adaptation`, `alatyr-add-ai`), read
   `.ai/assistant/operation-catalog.json`, `.ai/assistant/help.md`, and `.ai/assistant/flows/operation-routing.flow.md`.
6. For AI infrastructure work, use `.ai/assistant/ai-infrastructure-router.json`
   to select a route and item ID before loading item-specific context.

Assistant-specific bridge files must stay short and point back to canonical
target files.
