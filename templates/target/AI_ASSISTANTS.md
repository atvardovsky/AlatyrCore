# AI Assistant Entry Point

This repository uses Alatyr Core. All assistants should treat `AGENTS.md` as the canonical instruction file.

Before making changes:

1. Ensure `AGENTS.md` is loaded once; if it was not preloaded by the host,
   read it now. Then read `.ai/assistant/bootstrap-index.json`.
   If stale, repair it from `.ai/alatyr.yaml`, `.ai/README.md`, and `.ai/assistant/context-router.json`.
2. Select the smallest task profile and project-area overlays, then read only
   their required framework, project, assistant, flow, gate, policy, and
   validation files.
3. Read `.ai/assistant/context-profiles.md`, module state, fact owners, and
   full gates only when selected context or conflicting evidence requires them.
4. After installation/update or unclear state, read post-install/update message templates.
5. For an exact operation ID or alias, read `.ai/assistant/operation-index.json`;
   for bare `Alatyr`, ambiguity, or repair, read
   `.ai/assistant/operation-catalog.json`, `.ai/assistant/help.md`, and `.ai/assistant/flows/operation-routing.flow.md`.
6. For AI infrastructure work, use `.ai/assistant/ai-infrastructure-router.json`
   to select a route and item ID before loading item-specific context.
7. Before state changes, use `.ai/assistant/policies/action-authorization.json`; a topic switch or backlog/issue return is read-only.
   Status, discussion, report, analysis, plan, or ambiguous continuation is read-only. Implementation does not imply
   commit; commit does not imply push; prior completed-task authorization expires.

Assistant-specific bridge files must stay short and point back to canonical target files.
