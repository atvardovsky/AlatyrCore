# Roo Code Legacy Instructions

Ensure `AGENTS.md` is loaded once; if it was not preloaded by the host, read it now.
Then read `AI_ASSISTANTS.md` and `.ai/assistant/bootstrap-index.json`, then `.ai/assistant/entry-packet.json`.
For an exact operation ID or alias, read `.ai/assistant/operation-index.json`.
For bare `Alatyr`, ambiguity, or repair, read `.ai/assistant/operation-catalog.json`,
`.ai/assistant/help.md`, and `.ai/assistant/flows/operation-routing.flow.md`.
When delegation is selected, use `.ai/assistant/task-decomposition.json`,
`.ai/assistant/prompts/worker-orchestration.md`, and the selected capability record; do not infer native worker support.

This legacy bridge does not claim maintained Roo runtime support or override
Alatyr authorization with Roo mode or auto-approve settings.
