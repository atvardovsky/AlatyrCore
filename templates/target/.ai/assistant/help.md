# Alatyr Help

Alatyr is used here through assistant requests over the installed Markdown
adapter. It is not a universal CLI command unless `{PROJECT_NAME}` defines a
local command in `{TARGET_VALIDATION_OR_LOCAL_COMMANDS}`.

These aliases are chat/request shortcuts, not shell commands.

Full operation reference: `.ai/assistant/help-reference.md`.
Compact operation index: `.ai/assistant/operation-index.json`.
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
- If the request only returns to an issue, backlog item, report, or discussion,
  or asks for status, analysis, a plan, or what comes next, keep the operation
  read-only. Do not reuse implementation, commit, or push authorization from a
  completed task.
- Use `.ai/assistant/context-router.json` to choose task context before
  expanding the reading set, and use `.ai/assistant/context-profiles.md` when
  human rationale or conflict resolution is needed.
- Use `.ai/assistant/module-profile.md` to avoid routing to blocked or
  disabled optional modules.
- When `workspace-modes` is enabled, read its compact catalog before selecting
  task profile or project area. Prefer an explicit accepted mode, select
  automatically only on one unambiguous match, and ask before edits otherwise.
- Load `.ai/assistant/operation-index.json` for an exact operation ID or alias.
  Load the full catalog only for the bare `Alatyr` entry, ambiguity, or
  operation/adapter repair.
- Show `.ai/assistant/templates/pre-change-preview.md` before edits only when
  semantic or protected risk, boundary crossing, external effects, or unclear
  allowed-action scope triggers it.
- Add the `large-or-resumable` task-scale overlay only for multi-workstream,
  cross-boundary, budget-exceeding, or resumable work. Small tasks should not
  create operation packets.
- In an enabled team project, check the compact active-work index before a
  state-changing operation. Expand `team-active` only for explicit team work,
  a selected task/branch match, possible logical overlap, or unresolved index
  evidence. Keep unrelated tasks and team history out of context.
- Before completing material semantic, architectural, or non-obvious repair
  work, apply the lazy durable engineering-evidence gate. Small local work may
  skip with a specific reason; do not load unrelated evidence records.
- When the optional `debug-mode` module is enabled, activate it only from an
  explicit current-task or current-session request. Load only its compact index
  and active record, checkpoint material events rather than conversation turns,
  and expire activation when the logical scope ends.

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

Operation: `workspace-mode`
Use when: the user asks to list, suggest, inspect, select, define, accept,
update, disable, deprecate, remove, or review workspace modes.
Flow: `.ai/assistant/flows/workspace-mode.flow.md`
Minimum input: mode action or workspace-role question; mode ID and explicit
user decision for accepted-state changes.

Use `Alatyr architecture` for project pattern and architecture discussion. Use
`Alatyr diagram` for a capability-checked diagram view, `Alatyr team status`
for the compact team view, and `Alatyr set actor <actor-id-or-name>` to select
local attribution. These route to `architecture-assistance` and
`diagram-discussion`. When `code-documentation` is enabled, use
`propose comment style`, `document code`, `generate code docs`, or
`review code documentation`; the assistant selects a bounded accepted profile.
When `project-vocabulary` is enabled, use `Alatyr glossary`, `Alatyr define
term`, or `check terminology`; the assistant starts from the compact catalog.
Use `Alatyr enable test-first` to assess and configure the optional policy, or
`Alatyr test first` for an enabled policy. The assistant may suggest this once
when defect, invariant, contract, refactor, or recurring-regression evidence
supports it; a suggestion is not mandatory unless target policy says so.
Use `Alatyr extensions` to list compact state, `Alatyr inspect extension
<source>` for read-only source review, and `Alatyr add/update/disable/remove
extension <source-or-id>` for an approval-aware lifecycle request. These are
chat shortcuts, not shell commands. `Alatyr suggest extensions <scope>` remains
read-only and does not fetch or install a package.
When `dependency-knowledge` is enabled, use `Alatyr dependencies` for compact
state, `Alatyr sync dependencies` to compare and update only the reviewed
project projection, `Alatyr explain dependency <package>` for selected current
facts, or `Alatyr dependency impact <package-or-change>` for bounded impact.
These requests never activate nested adapters or update software packages.
When `workspace-modes` is enabled, use `Alatyr modes` for compact state,
`Alatyr suggest modes` for evidence-bound proposals, `Alatyr mode <id>` for a
per-task selection preview, `Alatyr define mode` to draft a mode, or `Alatyr
accept mode <id>` for an explicit acceptance request. Suggestions remain
proposed, and a mode never grants permissions or activates nested adapters.
Use `Alatyr evidence` to inspect compact historical evidence, `Alatyr capture
evidence` to request capture for the current task, or `Alatyr explain decision
<evidence-id>` to reconstruct why a prior change was made. These records store
normalized conclusions and references, never raw assistant reasoning.
When `debug-mode` is enabled, use `Enable Alatyr Debug Mode for this task` to
start explicit task-local observation, `Alatyr debug status` for read-only
state, `Alatyr debug checkpoint` for a material event checkpoint, `Alatyr debug
summary` to finalize or summarize, and `Disable Alatyr Debug Mode` to stop.
Debug records measure Alatyr and supervision; they are not architecture
authority and never grant code, commit, publish, or live-action permission.
Detailed team, blueprint, integrity, update, documentation, vocabulary,
test-first, extension, dependency-knowledge, workspace-mode, and
AI-infrastructure operations and aliases are in
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
