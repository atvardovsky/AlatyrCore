# Alatyr Help

Alatyr is used here through assistant requests over the installed Markdown
adapter. It is not a universal CLI command unless `{PROJECT_NAME}` defines a
local command in `{TARGET_VALIDATION_OR_LOCAL_COMMANDS}`.

These aliases are chat/request shortcuts, not shell commands.

First-use packet: `.ai/assistant/entry-packet.json`.
Full operation reference: `.ai/assistant/help-reference.md`.
Compact operation index: `.ai/assistant/operation-index.json`.
Canonical operation catalog: `.ai/assistant/operation-catalog.json`.

Send `Alatyr` by itself for compact adapter state and up to three relevant
actions. Send `Alatyr status` for compact read-only adapter health. Send
`Alatyr doctor` for read-only adapter health with prioritized repair routes.
A clear ordinary task is routed automatically; an operation ID is not required.

Default routing:

- Treat `AGENTS.md` as preloaded, then load
  `.ai/assistant/bootstrap-index.json` and `.ai/assistant/entry-packet.json`.
- If the operation is clear and low risk, choose the matching route and report
  the selected profile, gates, and allowed-action ceiling.
- If the request is `Alatyr` alone, do not edit files. Report fresh or
  unchecked health evidence and show at most three available actions.
- If the request asks for status or doctor, route to `adapter-health` and keep
  allowed actions `read-only`.
- If the request only returns to an issue, backlog item, report, or discussion,
  or asks for status, analysis, a plan, or what comes next, keep the operation
  read-only. Do not reuse implementation, commit, or push authorization from a
  completed task.
- If the request is unclear, show only the two or three closest operations and
  ask for the smallest missing decision.
- Use `.ai/assistant/context-profiles.md` only when routing rationale,
  ambiguity, conflict, or adapter repair requires human-readable detail.
- Use `.ai/assistant/module-profile.md` only when module state is missing from
  the packet, disputed, or under repair.
- Load `.ai/assistant/operation-index.json` for an exact operation ID or alias.
  Load the full catalog only for bare `Alatyr`, ambiguity, or operation repair.
- For support changes, start with support-state delta evidence. Load only
  changed support owners, selected relationship shards, and affected target
  source owners; hashes locate change and do not prove semantics.
- Before edits, apply `.ai/assistant/policies/action-authorization.json` to the
  newest request and current logical scope.

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
Use when: accepted behavior, architecture, data, runtime, or a public contract may change.
Flow: `.ai/assistant/flows/blueprint-driven-change.flow.md`
Minimum input: change intent, non-goals, and approval constraints.

Common shortcuts:

- `Alatyr architecture` (`architecture-assistance`)
- `Alatyr diagram` (`diagram-discussion`)
- `Alatyr team status`
- `Alatyr support diff`, `Alatyr impact`, `Alatyr change cost`
- `Alatyr glossary`, `Alatyr dependencies`, `Alatyr modes`
- `Alatyr evidence`, `Alatyr knowledge`, `Alatyr debug status`
- `propose comment style`, `document code`, `Alatyr test first`
- `alatyr-ai-inventory`, `alatyr-suggest-ai`, `alatyr-adaptation`

Detailed operations and aliases are in
`.ai/assistant/help-reference.md`.

## Minimal Request Shape

```text
Use the installed Alatyr adapter in this repository.

Operation type: `{OPERATION_TYPE}`
Goal: `{GOAL}`
Non-goals: `{NON_GOALS}`
Known context: `{KNOWN_CONTEXT}`
Current user authorization: `{INSPECT_MODIFY_COMMIT_PUBLISH_OR_LIVE_EXTERNAL}`
Allowed actions: `{READ_ONLY_DOCS_ONLY_ADAPTER_ONLY_CODE_AND_TESTS_OR_FULL_WITH_APPROVAL}`
Expected final evidence: `{EXPECTED_FINAL_EVIDENCE}`
```

## When Unsure

1. Say which parts of the request are ambiguous.
2. Show the two or three closest options.
3. Ask for the smallest missing decision.
4. Avoid repository edits until the operation is selected.
5. Ask before any `modify`, `commit`, `publish`, or `live-external` phase that
   the newest current-scope request did not explicitly authorize.
