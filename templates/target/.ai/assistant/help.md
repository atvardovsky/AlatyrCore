# Alatyr Help

Use this file in `{PROJECT_NAME}` when a programmer asks for Alatyr help,
available actions, commands, or gives an unclear request.

Replace placeholders with target facts before accepting installation.

Alatyr is used here through assistant requests over the installed Markdown
adapter. It is not a universal CLI command unless `{PROJECT_NAME}` defines a
local command in `{TARGET_VALIDATION_OR_LOCAL_COMMANDS}`.

## Operation Menu

| Operation | Use When | Flow | Minimum Input |
| --- | --- | --- | --- |
| `help` | The user asks what Alatyr can do or the request is unclear. | `.ai/assistant/flows/operation-routing.flow.md` | Goal or suspected task area. |
| `create-project-blueprint` | Create, repair, or recheck blueprint-equivalent source-of-truth docs from target evidence. | `.ai/assistant/flows/project-blueprint-creation.flow.md` | Blueprint scope and non-goals. |
| `recheck-after-installation` | Verify the installed adapter after initial installation. | `.ai/assistant/flows/adapter-recheck.flow.md` | Installation note or known gaps. |
| `recheck-after-framework-update` | Check whether an Alatyr Core update requires target adapter migration. | `.ai/assistant/flows/adapter-recheck.flow.md` | Update source or changed framework baseline. |
| `product-change` | Change accepted project behavior, architecture, data, runtime, or public contract. | `.ai/assistant/flows/blueprint-driven-change.flow.md` | Change intent, non-goals, and approval constraints. |
| `logical-integrity-review` | Review whether code, docs, tests, diagrams, prompts, skills, gates, and bridges agree. | `.ai/assistant/flows/logical-integrity-review.flow.md` | Changed fact, suspected drift, or files to inspect. |
| `skill-adaptation` | Import, adapt, or review skills, prompts, wrappers, or third-party assistant infrastructure. | `.ai/assistant/flows/skill-adaptation.flow.md` | Skill source, intended use, and permissions. |
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
- Known adapter gaps: `{KNOWN_GAPS}`
