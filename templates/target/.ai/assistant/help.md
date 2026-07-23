# Alatyr Help

Use this file in `{PROJECT_NAME}` when a programmer asks for Alatyr help,
available actions, commands, or gives an unclear request.

Replace placeholders with target facts before accepting installation.

Alatyr is used here through assistant requests over the installed Markdown
adapter. It is not a universal CLI command unless `{PROJECT_NAME}` defines a
local command in `{TARGET_VALIDATION_OR_LOCAL_COMMANDS}`.

These aliases are chat/request shortcuts, not shell commands.

Full operation reference: `.ai/assistant/help-reference.md`.
Canonical operation catalog: `.ai/assistant/operation-catalog.json`.

Send `Alatyr` by itself for a compact adapter state and up to three relevant
actions. Send `Alatyr status` or `Alatyr doctor` for a read-only adapter health
check. A clear ordinary task is routed automatically; an operation ID is not
required.

Default routing:

- If the operation is clear and low risk, choose the matching operation and
  report the chosen route.
- If the request is `Alatyr` alone, do not edit files. Report whether health
  evidence is fresh or unchecked and show at most three available actions.
- If the request asks for status or doctor, route to `adapter-health` and keep
  allowed actions `read-only`.
- If the request is unclear, show only the two or three closest operations and
  ask for the smallest missing decision.
- Use `.ai/assistant/context-router.json` to choose task context before
  expanding the reading set, and use `.ai/assistant/context-profiles.md` when
  human rationale or conflict resolution is needed.
- Use `.ai/assistant/module-profile.md` to avoid routing to blocked or
  disabled optional modules.
- Load `.ai/assistant/operation-catalog.json` for explicit Alatyr routing,
  status, ambiguity resolution, or operation handoff. Do not add it to every
  routine task's context.
- Show `.ai/assistant/templates/pre-change-preview.md` before edits only when
  semantic or protected risk, boundary crossing, external effects, or unclear
  allowed-action scope triggers it.
- Add the `large-or-resumable` task-scale overlay only for multi-workstream,
  cross-boundary, budget-exceeding, or resumable work. Small tasks should not
  create operation packets.
- Add the `team-active` overlay only for team task, claim, conflict,
  checkpoint, handoff, decision, review, merge-check, or release work. Keep
  unrelated active tasks and team history out of context.

## Quick Operations

Operation: `help`
Use when: the user asks what Alatyr can do or the request is unclear.
Flow: `.ai/assistant/flows/operation-routing.flow.md`
Minimum input: goal or suspected task area.

Operation: `adapter-health`
Use when: the user asks for Alatyr status, doctor, or current adapter health.
Flow: `.ai/assistant/flows/adapter-health.flow.md`
Minimum input: optional health scope. Allowed actions are `read-only`.

Operation: `product-change`
Use when: accepted behavior, architecture, data, runtime, or public contract
may change.
Flow: `.ai/assistant/flows/blueprint-driven-change.flow.md`
Minimum input: change intent, non-goals, and approval constraints.

Operation: `large-task`
Use when: work needs multiple workstreams, crosses project areas or profiles,
exceeds the context budget, or must resume after a context reset.
Flow: `.ai/assistant/flows/large-task-orchestration.flow.md`
Minimum input: goal, non-goals, affected areas, and allowed actions.

Operation: `team-status`
Use when: reporting active work, stale claims, conflicts, handoffs, and review
state without editing.
Flow: `.ai/assistant/flows/team-task-coordination.flow.md`
Minimum input: optional team, area, actor, or task scope.

Use `Alatyr team status` for the compact team view. Detailed team, blueprint,
integrity, update, documentation, and AI-infrastructure operations and aliases
are in `.ai/assistant/help-reference.md`.

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
