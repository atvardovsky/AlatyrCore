# Alatyr Help

Use this file in `{PROJECT_NAME}` when a programmer asks for Alatyr help,
available actions, commands, or gives an unclear request.

Replace placeholders with target facts before accepting installation.

Alatyr is used here through assistant requests over the installed Markdown
adapter. It is not a universal CLI command unless `{PROJECT_NAME}` defines a
local command in `{TARGET_VALIDATION_OR_LOCAL_COMMANDS}`.

These aliases are chat/request shortcuts, not shell commands.

Full operation reference: `.ai/assistant/help-reference.md`.

Default routing:

- If the operation is clear and low risk, choose the matching operation and
  report the chosen route.
- If the request is unclear, show only the two or three closest operations and
  ask for the smallest missing decision.
- Use `.ai/assistant/context-router.json` to choose task context before
  expanding the reading set, and use `.ai/assistant/context-profiles.md` when
  human rationale or conflict resolution is needed.
- Use `.ai/assistant/module-profile.md` to avoid routing to blocked or
  disabled optional modules.
- Add the `large-or-resumable` task-scale overlay only for multi-workstream,
  cross-boundary, budget-exceeding, or resumable work. Small tasks should not
  create operation packets.

## Quick Operations

Operation: `help`
Use when: the user asks what Alatyr can do or the request is unclear.
Flow: `.ai/assistant/flows/operation-routing.flow.md`
Minimum input: goal or suspected task area.

Operation: `product-change`
Use when: accepted behavior, architecture, data, runtime, or public contract
may change.
Flow: `.ai/assistant/flows/blueprint-driven-change.flow.md`
Minimum input: change intent, non-goals, related review items, and approval
constraints including diff base and explicit JSON records when scoped.

Operation: `logical-integrity-review`
Use when: code, docs, tests, diagrams, prompts, skills, gates, or bridges may
disagree.
Flow: `.ai/assistant/flows/logical-integrity-review.flow.md`
Minimum input: changed fact, suspected drift, or files to inspect.

Operation: `create-project-blueprint`
Use when: creating, repairing, or rechecking blueprint-equivalent
source-of-truth docs from target evidence.
Flow: `.ai/assistant/flows/project-blueprint-creation.flow.md`
Minimum input: blueprint scope and non-goals.

Operation: `recheck-after-framework-update`
Use when: checking whether an Alatyr Core update requires target adapter
migration.
Flow: `.ai/assistant/flows/adapter-recheck.flow.md`
Minimum input: update source, changed framework baseline, or migration
assessment path.

Operation: `large-task`
Use when: work needs multiple workstreams, crosses project areas or profiles,
exceeds the context budget, or must resume after a context reset.
Flow: `.ai/assistant/flows/large-task-orchestration.flow.md`
Minimum input: goal, non-goals, affected areas, and allowed actions.

AI infrastructure shortcuts:

- `alatyr-ai-inventory`: route to `ai-infrastructure-inventory`.
- `alatyr-suggest-ai {RECOMMENDATION_SCOPE}`: route to read-only
  `ai-infrastructure-recommendation` for new-item or existing-item suggestions.
- `alatyr-improve-ai {AI_INFRASTRUCTURE_ITEM_ID}`: route to focused read-only
  `ai-infrastructure-recommendation` for an existing item.
- `alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}`: route to
  `skill-adaptation` in review or adaptation mode.
- `alatyr-add-ai {AI_INFRASTRUCTURE_SOURCE}`: route to `skill-adaptation` with
  canonical integration intent after inventory, provenance, prompt-injection,
  safety, and approval checks.

AI infrastructure requests select `inventory`, `recommend`, or another route
and the smallest item-ID set from
`.ai/assistant/ai-infrastructure-router.json` before loading item-specific
skills, prompts, gates, tools, bridges, permissions, or import policy.

Common aliases:

- `Alatyr help`: `help`
- `update Alatyr` or `обнови Alatyr`: `recheck-after-framework-update`
- `check Alatyr` or `проверь Alatyr`: `recheck-after-installation` or
  `adapter-maturity-review`
- `create blueprint` or `создай blueprint`: `create-project-blueprint`
- `check integrity` or `проверь целостность`: `logical-integrity-review`
- `change business rule` or `измени бизнес-правило`: `product-change`
- `plan large task`, `continue large task`, or `resume Alatyr task`:
  `large-task`

## Minimal Request Shape

```text
Use the installed Alatyr adapter in this repository.

Operation type: `{OPERATION_TYPE}`
Goal: `{GOAL}`
Non-goals: `{NON_GOALS}`
Known context: `{KNOWN_CONTEXT}`
Allowed actions: `{READ_ONLY_DOCS_ONLY_ADAPTER_ONLY_CODE_AND_TESTS_OR_FULL_WITH_APPROVAL}`
Expected final evidence: `{EXPECTED_FINAL_EVIDENCE}`
```

## When Unsure

1. Say which parts of the request are ambiguous.
2. Show the two or three closest options.
3. Ask for the smallest missing decision.
4. Avoid repository edits until the operation is selected.
