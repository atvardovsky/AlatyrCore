# AI Assistant Entry Point

This repository uses Alatyr Core.

All assistants should treat `AGENTS.md` as the canonical instruction file.

Before making changes:

1. Read `AGENTS.md`.
2. Read `.ai/README.md`.
3. Read `.ai/framework/README.md` and the task-relevant framework docs,
   especially logical integrity, blueprint-driven change, skill adaptation,
   installed operations, and operation help guidance.
4. Read `.ai/project/contour.md` and `.ai/assistant/contour.md`.
5. Read `.ai/assistant/help.md` when the request asks for help, commands, or
   an unclear Alatyr action.
6. Read `{TARGET_PROJECT_SOURCE_OF_TRUTH}`.
7. Read the matching `.ai/assistant/flows/*.flow.md`.
8. Apply `.ai/assistant/gates/checklist.md`.

Assistant-specific bridge files must stay short and point back to canonical
target files.
