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

Operation: `help`
Use when: the user asks what Alatyr can do or the request is unclear.
Flow: `.ai/assistant/flows/operation-routing.flow.md`
Minimum input: goal or suspected task area.

Operation: `create-project-blueprint`
Use when: creating, repairing, or rechecking blueprint-equivalent
source-of-truth docs from target evidence.
Flow: `.ai/assistant/flows/project-blueprint-creation.flow.md`
Minimum input: blueprint scope and non-goals.

Operation: `recheck-after-installation`
Use when: verifying the installed adapter after initial installation.
Flow: `.ai/assistant/flows/adapter-recheck.flow.md`
Minimum input: installation note or known gaps.

Operation: `recheck-after-framework-update`
Use when: checking whether an Alatyr Core update requires target adapter
migration.
Flow: `.ai/assistant/flows/adapter-recheck.flow.md`
Minimum input: update source or changed framework baseline.

Operation: `product-change`
Use when: changing accepted project behavior, architecture, data, runtime, or
public contract.
Flow: `.ai/assistant/flows/blueprint-driven-change.flow.md`
Minimum input: change intent, non-goals, and approval constraints.

Operation: `logical-integrity-review`
Use when: reviewing whether code, docs, tests, diagrams, prompts, skills,
gates, and bridges agree.
Flow: `.ai/assistant/flows/logical-integrity-review.flow.md`
Minimum input: changed fact, suspected drift, or files to inspect.

Operation: `ai-infrastructure-inventory`
Use when: checking what AI infrastructure already exists and what can be kept,
adapted, added, removed, or left unresolved.
Flow: `.ai/assistant/flows/ai-infrastructure-inventory.flow.md`
Minimum input: inventory scope and target assistant surfaces.
Alias: `alatyr-ai-inventory`.

Operation: `skill-adaptation`
Use when: importing, adapting, adding, or reviewing skills, prompts, wrappers,
bridges, rules, MCP/tool configs, gates, checkers, or third-party assistant
infrastructure.
Flow: `.ai/assistant/flows/skill-adaptation.flow.md`
Minimum input: source, item type, source type, intended use, target assistant
surfaces, and permissions.
Aliases: `alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}`,
`alatyr-add-ai {AI_INFRASTRUCTURE_SOURCE}`.

Operation: `drift-review`
Use when: finding stale source-of-truth, docs, diagrams, gates, prompts,
skills, or bridge files.
Flow: `.ai/assistant/flows/logical-integrity-review.flow.md`
Minimum input: drift area or recently changed facts.

Operation: `documentation-sync`
Use when: syncing docs, diagrams, prompts, gates, skills, or bridge files
after a fact changed.
Flow: `.ai/assistant/flows/documentation-sync.flow.md`
Minimum input: changed fact and owning source.

Operation: `adapter-maturity-review`
Use when: reporting whether the adapter is incomplete, minimal, usable, or
mature for a requested task.
Flow: `.ai/assistant/flows/adapter-recheck.flow.md`
Minimum input: task scope and maturity concern.

## Operation Type Aliases

Treat these as target request aliases, not executable commands. Replace,
remove, or extend them with `{PROJECT_NAME}` terminology before accepting the
adapter.

Alias: `Alatyr help`
Route to: `help`.

Alias: `update Alatyr` or `обнови Alatyr`
Route to: `recheck-after-framework-update` when a framework update source is
known. If no update context is known, show `help` and ask for the update
source or intended recheck scope.

Alias: `check Alatyr` or `проверь Alatyr`
Route to: `recheck-after-installation` after initial installation, or
`adapter-maturity-review` when the request is a broader adapter readiness
review.

Alias: `create blueprint` or `создай blueprint`
Route to: `create-project-blueprint`.

Alias: `check integrity` or `проверь целостность`
Route to: `logical-integrity-review`.

Alias: `change business rule` or `измени бизнес-правило`
Route to: `product-change`.

## Request Shape

Use this shape when asking for an operation:

```text
Use the installed Alatyr adapter in this repository.

Operation type: `{OPERATION_TYPE}`
Goal: `{GOAL}`
Non-goals: `{NON_GOALS}`
Known context: `{KNOWN_CONTEXT}`
Allowed actions: `{READ_ONLY_DOCS_ONLY_ADAPTER_ONLY_CODE_AND_TESTS_OR_FULL_WITH_APPROVAL}`
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
