---
mode: agent
description: Review a change against the target repository's Alatyr Core gates.
---

This prompt is a bridge, not the source of truth. Ensure `AGENTS.md` is loaded
once; if it was not preloaded by the host, read it now. Then read
`AI_ASSISTANTS.md`, `.ai/alatyr.yaml`, `.ai/README.md`, and
`.ai/assistant/context-router.json` before selecting gate-review context.
Then read `.ai/assistant/gates/checklist.md`,
`.ai/assistant/flows/logical-integrity-review.flow.md`,
`.ai/framework/logical-integrity.md`, and the changed files.
For Alatyr help or aliases (`alatyr-ai-inventory`, `alatyr-suggest-ai`,
`alatyr-improve-ai`, `alatyr-adaptation`, and `alatyr-add-ai`), read `.ai/assistant/help.md` and
`.ai/assistant/flows/operation-routing.flow.md`.
Return blockers first, then final evidence.
