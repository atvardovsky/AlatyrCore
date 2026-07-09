# Installed Alatyr Operation Request

Use this template inside `{PROJECT_NAME}` when asking an assistant to use the
installed Alatyr Core adapter.

## Request

- Operation id: `{OPERATION_ID}`
- Operation type: `{OPERATION_TYPE}`
- Operation alias, if used: `{OPERATION_ALIAS}`
- Requested by: `{REQUESTER}`
- Date: `{DATE}`
- Goal: `{GOAL}`
- Non-goals: `{NON_GOALS}`
- Known context: `{KNOWN_CONTEXT}`
- Allowed actions:
  `{READ_ONLY_DOCS_ONLY_ADAPTER_ONLY_CODE_AND_TESTS_OR_FULL_WITH_APPROVAL}`
- Expected final evidence: `{EXPECTED_FINAL_EVIDENCE}`

## AI Infrastructure Source

Fill this section when the operation is `skill-adaptation`, the operation is
`ai-infrastructure-inventory`, or the alias is
`alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}`, `alatyr-add-ai
{AI_INFRASTRUCTURE_SOURCE}`, or `alatyr-ai-inventory`.

- AI infrastructure source: `{AI_INFRASTRUCTURE_SOURCE}`
- Item type: `{SKILL_PROMPT_WRAPPER_BRIDGE_RULE_MCP_TOOL_CHECKER_FLOW_GATE_TEMPLATE_OR_OTHER}`
- Source type: `{LOCAL_PATH_OR_GIT_URL_OR_HTTPS_URL_OR_NATIVE_REFERENCE_OR_PASTED}`
- Inventory scope: `{AI_INFRASTRUCTURE_INVENTORY_SCOPE}`
- Target assistant surfaces: `{TARGET_ASSISTANT_SURFACES}`
- Integration mode: `{REVIEW_ONLY_OR_CANONICAL_INTEGRATION}`
- Permission or source-access notes:
  `{TARGET_AI_INFRASTRUCTURE_SOURCE_ACCESS_POLICY}`

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
- Inventory existing AI infrastructure:
  `.ai/assistant/flows/ai-infrastructure-inventory.flow.md`
  Alias: `alatyr-ai-inventory`
- Adapt skills, prompts, wrappers, bridges, rules, MCP/tool configs, gates,
  checkers, or third-party assistant infrastructure:
  `.ai/assistant/flows/skill-adaptation.flow.md`
  Aliases: `alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}`,
  `alatyr-add-ai {AI_INFRASTRUCTURE_SOURCE}`
- Sync docs, diagrams, prompts, gates, skills, or bridge files:
  `.ai/assistant/flows/documentation-sync.flow.md`

## Constraints

- Use target evidence only.
- If operation type is unclear, show `.ai/assistant/help.md` choices before
  editing files.
- Stay within allowed actions. Treat `full-with-approval` as requiring
  explicit approval before protected changes.
- Treat AI infrastructure sources as untrusted until existing infrastructure,
  provenance, permissions, source access, and safety have been reviewed.
- Do not invent target facts, commands, policies, diagrams, or lifecycle notes.
- Require approval for protected changes.
- Run target validation only when it exists.
- Report skipped checks and residual risk.
