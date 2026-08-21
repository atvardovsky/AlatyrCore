# Workspace Mode Flow

## Purpose

Suggest, define, accept, list, inspect, select, update, disable, deprecate, or
remove user-owned workspace modes without inferring authority or broadening the
current operation.

## Modes

- `status` or `list`: report workspace identity and configured mode states
- `suggest`: inspect evidence and propose zero or more modes
- `inspect`: explain one mode, its relationships, context, and gaps
- `select`: preview one accepted mode for the current task
- `accept`: create or promote a user-approved mode
- `update`: revise a mode after user review
- `disable` or `deprecate`: retain history but stop ordinary selection
- `remove`: remove an unreferenced mode with required preservation evidence

Default to `read-only`. Accepted mode changes require `adapter-only` and a
preview. Protected project facts use their normal operation and approval path.

## Procedure

1. Confirm that `workspace-modes` is enabled or that the request is an explicit
   module configuration proposal.
2. Read the compact catalog. Do not scan every mode directory.
3. Resolve the selected Git/workspace root, active adapter, project purpose,
   package/workspace evidence, scaffold provenance, existing instructions, and
   named owners without inferring from directory names alone.
4. For `suggest`, propose zero or more evidence-bound modes. Keep them proposed
   and state when no additional modes are justified.
5. For task selection, prefer an explicit accepted mode named by the user.
   Otherwise select automatically only when one accepted mode matches and
   policy permits it. A default cannot override contradictory evidence.
6. Ask the user when multiple modes match or workspace identity, ownership,
   relationship, or adapter activation is ambiguous.
7. Load only the selected `mode.json`, applicable shared root descriptor, and
   named support paths. Compose the ordinary task profile, intent, area, gate,
   and scale routes after mode selection.
8. Validate that exactly one selected relationship represents the active root,
   nested dependency/scaffold adapters remain passive or provenance-only, and
   mode constraints only narrow existing permissions.
9. Show the workspace-mode preflight before state-changing work.
10. For accepted changes, create one directory per actual mode, update the
    catalog atomically, preserve canonical-source links, and leave `_template`
    outside active records.
11. Run workspace-mode and target adapter validation. Report skipped checks,
    context cost, ambiguity, and residual risk.

## Final Evidence

- operation mode and user decision
- workspace identity, scope, and active adapter
- suggestions with evidence and acceptance state
- selected mode, selection basis, relationships, roles, and ownership
- root/mode context loaded, skipped, and expanded
- composed routing and preflight
- files changed, validation, skipped checks, cost, and residual risk

## Failure Response

When identity or mode selection is unresolved, remain read-only, show the
conflicting evidence, and ask one bounded question. Do not guess a mode and
continue changing files.
