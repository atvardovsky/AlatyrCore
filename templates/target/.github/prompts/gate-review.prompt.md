---
mode: agent
description: Review a change against the target repository's Alatyr Core gates.
---

This prompt is a bridge, not the source of truth. Ensure `AGENTS.md` is loaded
once; if it was not preloaded by the host, read it now. Then read
`AI_ASSISTANTS.md` and `.ai/assistant/bootstrap-index.json` before selecting
gate-review context. Repair a missing or stale derived index from its named
canonical sources. Then use `.ai/assistant/gates/index.json` to select the
smallest applicable gate fragments. Load `.ai/assistant/gates/checklist.md`
only for ambiguity, full audit, or gate-repair work. Also read
`.ai/assistant/flows/logical-integrity-review.flow.md`,
`.ai/framework/logical-integrity.md`, and the changed files.
For an exact operation ID or alias, including diagram, team, or AI aliases, read
`.ai/assistant/operation-index.json`; for bare `Alatyr`, ambiguity, or repair, read
`.ai/assistant/operation-catalog.json`, `.ai/assistant/help.md`, and `.ai/assistant/flows/operation-routing.flow.md`.
When delegation is selected, use `.ai/assistant/prompts/worker-orchestration.md` and the selected capability record; do not infer native worker support.
Return blockers first, then final evidence.
