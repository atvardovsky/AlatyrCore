# Alatyr Help

Use this file in `{PROJECT_NAME}` when a programmer asks for Alatyr help,
available actions, commands, or gives an unclear request.

Replace placeholders with target facts before accepting installation.

Alatyr is used here through assistant requests over the installed Markdown
adapter. It is not a universal CLI command unless `{PROJECT_NAME}` defines a
local command in `{TARGET_VALIDATION_OR_LOCAL_COMMANDS}`.

Supported request aliases:

- `alatyr-ai-inventory`: route to `ai-infrastructure-inventory` and report
  existing AI instructions, prompts, skills, rules, wrappers, bridges, MCP/tool
  configs, gates, checkers, and generated assistant artifacts.
- `alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}`: route to
  `skill-adaptation` using `{AI_INFRASTRUCTURE_SOURCE}` as a local path, Git
  URL, HTTPS URL, assistant-native skill or prompt reference, pasted content,
  package/plugin reference, or other target-approved source form.
- `alatyr-add-ai {AI_INFRASTRUCTURE_SOURCE}`: route to `skill-adaptation` with
  integration intent after inventory, provenance, safety, and approval checks.

## Operation Menu

| Operation | Use When | Flow | Minimum Input |
| --- | --- | --- | --- |
| `help` | The user asks what Alatyr can do or the request is unclear. | `.ai/assistant/flows/operation-routing.flow.md` | Goal or suspected task area. |
| `create-project-blueprint` | Create, repair, or recheck blueprint-equivalent source-of-truth docs from target evidence. | `.ai/assistant/flows/project-blueprint-creation.flow.md` | Blueprint scope and non-goals. |
| `recheck-after-installation` | Verify the installed adapter after initial installation. | `.ai/assistant/flows/adapter-recheck.flow.md` | Installation note or known gaps. |
| `recheck-after-framework-update` | Check whether an Alatyr Core update requires target adapter migration. | `.ai/assistant/flows/adapter-recheck.flow.md` | Update source or changed framework baseline. |
| `product-change` | Change accepted project behavior, architecture, data, runtime, or public contract. | `.ai/assistant/flows/blueprint-driven-change.flow.md` | Change intent, non-goals, and approval constraints. |
| `logical-integrity-review` | Review whether code, docs, tests, diagrams, prompts, skills, gates, and bridges agree. | `.ai/assistant/flows/logical-integrity-review.flow.md` | Changed fact, suspected drift, or files to inspect. |
| `ai-infrastructure-inventory` | Check what AI infrastructure already exists and what can be kept, adapted, added, removed, or left unresolved. Alias: `alatyr-ai-inventory`. | `.ai/assistant/flows/ai-infrastructure-inventory.flow.md` | Inventory scope and target assistant surfaces. |
| `skill-adaptation` | Import, adapt, add, or review skills, prompts, wrappers, bridges, rules, MCP/tool configs, gates, checkers, or third-party assistant infrastructure. Aliases: `alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}`, `alatyr-add-ai {AI_INFRASTRUCTURE_SOURCE}`. | `.ai/assistant/flows/skill-adaptation.flow.md` | Source, item type, source type, intended use, target assistant surfaces, and permissions. |
| `drift-review` | Find stale source-of-truth, docs, diagrams, gates, prompts, skills, or bridge files. | `.ai/assistant/flows/logical-integrity-review.flow.md` | Drift area or recently changed facts. |
| `documentation-sync` | Sync docs, diagrams, prompts, gates, skills, or bridge files after a fact changed. | `.ai/assistant/flows/documentation-sync.flow.md` | Changed fact and owning source. |
| `adapter-maturity-review` | Report whether the adapter is incomplete, minimal, usable, or mature for a requested task. | `.ai/assistant/flows/adapter-recheck.flow.md` | Task scope and maturity concern. |

## Request Shape

Use this shape when asking for an operation:

```text
Use the installed Alatyr adapter in this repository.

Operation type: `{OPERATION_TYPE}`
Goal: `{GOAL}`
Non-goals: `{NON_GOALS}`
Known context: `{KNOWN_CONTEXT}`
Expected final evidence: `{EXPECTED_FINAL_EVIDENCE}`
```

AI infrastructure inventory shorthand:

```text
alatyr-ai-inventory

Goal: `{GOAL}`
Inventory scope: `{AI_INFRASTRUCTURE_INVENTORY_SCOPE}`
Target assistant surfaces: `{TARGET_ASSISTANT_SURFACES}`
```

AI infrastructure adaptation shorthand:

```text
alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}

Goal: `{GOAL}`
Non-goals: `{NON_GOALS}`
Item type: `{SKILL_PROMPT_WRAPPER_BRIDGE_RULE_MCP_TOOL_CHECKER_FLOW_GATE_TEMPLATE_OR_OTHER}`
Source type: `{LOCAL_PATH_OR_GIT_URL_OR_HTTPS_URL_OR_NATIVE_REFERENCE_OR_PASTED}`
Target assistant surfaces: `{TARGET_ASSISTANT_SURFACES}`
Integration mode: `{REVIEW_ONLY_OR_CANONICAL_INTEGRATION}`
```

AI infrastructure add shorthand:

```text
alatyr-add-ai {AI_INFRASTRUCTURE_SOURCE}

Goal: `{GOAL}`
Non-goals: `{NON_GOALS}`
Item type: `{SKILL_PROMPT_WRAPPER_BRIDGE_RULE_MCP_TOOL_CHECKER_FLOW_GATE_TEMPLATE_OR_OTHER}`
Source type: `{LOCAL_PATH_OR_GIT_URL_OR_HTTPS_URL_OR_NATIVE_REFERENCE_OR_PASTED}`
Target assistant surfaces: `{TARGET_ASSISTANT_SURFACES}`
Integration mode: `{CANONICAL_INTEGRATION}`
```

## When Unsure

If the assistant cannot safely choose an operation, it should:

1. Say which parts of the request are ambiguous.
2. Show the operation menu or the two or three closest options.
3. Ask for the smallest missing decision.
4. Avoid repository edits until the operation is selected.

## Target Notes

- Supported assistants: `{SUPPORTED_ASSISTANTS}`
- Target validation or manual checks: `{TARGET_VALIDATION}`
- Approval constraints: `{TARGET_APPROVAL_CONSTRAINTS}`
- Allowed AI infrastructure source access:
  `{TARGET_AI_INFRASTRUCTURE_SOURCE_ACCESS_POLICY}`
- Known adapter gaps: `{KNOWN_GAPS}`
