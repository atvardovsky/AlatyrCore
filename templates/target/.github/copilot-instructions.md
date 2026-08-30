# GitHub Copilot Instructions

This repository uses Alatyr Core.

Ensure `AGENTS.md` is loaded once; if it was not preloaded by the host, read it now.
Then read `AI_ASSISTANTS.md` and `.ai/assistant/bootstrap-index.json`, then `.ai/assistant/entry-packet.json`.
If the derived index is missing or stale, repair it from its named canonical sources.
Select the smallest profile before reading task-owned context or flows.

For an exact operation ID or alias, including diagram, team, or AI aliases, read
`.ai/assistant/operation-index.json`; for bare `Alatyr`, ambiguity, or repair, read
`.ai/assistant/operation-catalog.json`, `.ai/assistant/help.md`, and `.ai/assistant/flows/operation-routing.flow.md`.
When delegation is selected, use `.ai/assistant/prompts/worker-orchestration.md` and the selected capability record; do not infer native worker support.

Keep this file as a bridge. Do not duplicate full project or framework policy
here.
