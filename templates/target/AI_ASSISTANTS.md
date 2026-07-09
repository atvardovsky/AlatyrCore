# AI Assistant Entry Point

This repository uses Alatyr Core.

All assistants should treat `AGENTS.md` as the canonical instruction file.

Before making changes:

1. Read `AGENTS.md`, `.ai/README.md`, and `.ai/framework/README.md`.
2. Read task-relevant framework docs, especially logical integrity,
   blueprint-driven change, AI infrastructure adaptation, installed operations,
   and operation help guidance.
3. Read `.ai/project/contour.md`, `.ai/assistant/contour.md`,
   `.ai/assistant/templates/installation-note.md`,
   `{TARGET_PROJECT_SOURCE_OF_TRUTH}`, the matching `.ai/assistant/flows/*.flow.md`,
   and `.ai/assistant/gates/checklist.md`.
4. After installation/update, or when adapter state is unclear, read the
   post-install/update message templates before editing.
5. For Alatyr help or aliases (`alatyr-ai-inventory`, `alatyr-adaptation`,
   `alatyr-add-ai`), read `.ai/assistant/help.md` and
   `.ai/assistant/flows/operation-routing.flow.md`.

Assistant-specific bridge files must stay short and point back to canonical
target files.
