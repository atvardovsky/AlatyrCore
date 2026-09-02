# AI Assistant Entry Point

This repository uses Alatyr Core. All assistants should treat `AGENTS.md` as the canonical instruction file.
Before making changes:

1. Ensure `AGENTS.md` is loaded once; if it was not preloaded by the host, read it.
   Then read `.ai/assistant/bootstrap-index.json`, then `.ai/assistant/entry-packet.json`.
   Repair a stale index from `.ai/alatyr.yaml`, `.ai/README.md`, and `.ai/assistant/context-router.json`.
2. Load its semantic preload once; resolve lazy IDs through the semantic index, falling back to canonical owner prose on missing, stale, or conflicting terms.
3. Select the smallest task profile and follow only matching `context-index.json`
   entries; never load a directory solely because its parent index was selected.
4. Expand through `.ai/assistant/context-profiles.md`, module state, fact owners,
   or full gates only when selected context or conflicting evidence requires them.
   For code or support changes, start from changed paths, the support-state
   difference, and the consistency reverse index when enabled. Load selected
   graph shards only; hashes and relationship candidates are not authority.
5. After installation/update or unclear state, read post-install/update message templates.
6. For an exact operation ID or alias, read `.ai/assistant/operation-index.json`;
   for bare `Alatyr`, ambiguity, or repair, read `.ai/assistant/operation-catalog.json`, `.ai/assistant/help.md`, and `.ai/assistant/flows/operation-routing.flow.md`.
7. Route AI infrastructure through `.ai/assistant/ai-infrastructure-router.json`.
8. For non-trivial work, use `.ai/assistant/task-decomposition.json` and `.ai/assistant/templates/task-decomposition.md` before implementation or delegation.
9. Before state changes, use `.ai/assistant/policies/action-authorization.json`; a topic switch or backlog/issue return is read-only.
   Implementation does not imply commit; commit does not imply push; prior authorization expires.
10. Delegate only through the primary-owned decomposition plan, `.ai/assistant/prompts/worker-orchestration.md`, and the selected capability record.
Assistant-specific bridge files must stay short and point back to canonical target files.
