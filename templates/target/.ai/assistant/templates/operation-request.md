# Installed Alatyr Operation Request

Use this template inside `{PROJECT_NAME}` when asking an assistant to use the
installed Alatyr Core adapter.

## Request

- Operation id: `{OPERATION_ID}`
- Operation type: `{OPERATION_TYPE}`
- Requested by: `{REQUESTER}`
- Date: `{DATE}`
- Goal: `{GOAL}`
- Non-goals: `{NON_GOALS}`
- Known context: `{KNOWN_CONTEXT}`
- Expected final evidence: `{EXPECTED_FINAL_EVIDENCE}`

## Required Context

- `AGENTS.md`
- `AI_ASSISTANTS.md`
- `.ai/README.md`
- `.ai/framework/installed-operations.md`
- `.ai/framework/operation-help.md`
- `.ai/project/contour.md`
- `.ai/assistant/contour.md`
- `.ai/assistant/help.md`
- `.ai/assistant/gates/checklist.md`
- matching `.ai/assistant/flows/*.flow.md`
- `{TARGET_PROJECT_SOURCE_OF_TRUTH}`

## Operation Choices

Choose the matching flow:

- Need help or operation routing:
  `.ai/assistant/flows/operation-routing.flow.md`
- Create or repair project source-of-truth docs:
  `.ai/assistant/flows/project-blueprint-creation.flow.md`
- Recheck after installation or Alatyr Core update:
  `.ai/assistant/flows/adapter-recheck.flow.md`
- Change accepted product behavior:
  `.ai/assistant/flows/blueprint-driven-change.flow.md`
- Review consistency:
  `.ai/assistant/flows/logical-integrity-review.flow.md`
- Adapt skills, prompts, wrappers, or third-party assistant infrastructure:
  `.ai/assistant/flows/skill-adaptation.flow.md`
- Sync docs, diagrams, prompts, gates, skills, or bridge files:
  `.ai/assistant/flows/documentation-sync.flow.md`

## Constraints

- Use target evidence only.
- If operation type is unclear, show `.ai/assistant/help.md` choices before
  editing files.
- Do not invent target facts, commands, policies, diagrams, or lifecycle notes.
- Require approval for protected changes.
- Run target validation only when it exists.
- Report skipped checks and residual risk.
