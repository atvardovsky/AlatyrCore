# Agent Instructions

This repository uses Alatyr Core. Resolve placeholders from target evidence.

## Compact Bootstrap

Treat this file as host-preloaded context; do not reread it. Load only:

- `.ai/alatyr.yaml`
- `.ai/README.md`
- `.ai/assistant/context-router.json`

Select smallest profile/areas. Load `.ai/assistant/context-profiles.md` only
for ambiguity, conflict, or repair. Record context receipt on expansion.

Route exact IDs/aliases through `.ai/assistant/operation-index.json`; use
profile candidates for clear requests. Load
`.ai/assistant/operation-catalog.json` only for bare `Alatyr`, ambiguity, or
repair. Status/doctor is read-only.

Activate task-scale overlays only on their trigger. Load only selected
workstream/task evidence.

## Session Recovery

Do not rely on prior chat for adapter state. After installation/update or
unclear state, use the note/message named by `.ai/README.md`.

## Target Evidence

- Project/areas: `{PROJECT_NAME}`, `{TARGET_STACK_AND_AREA_MAP}`.
- Fact registry: `{TARGET_SOURCE_OF_TRUTH_REGISTRY}`.
- Checks: `{TARGET_VALIDATION}`.
- Security/live services: `{TARGET_SECURITY_POLICY}`.
- Diagrams/artifacts: `{TARGET_DIAGRAM_POLICY}`.
- AI infrastructure: `.ai/assistant/ai-infrastructure-router.json` and its
  source-access and prompt-injection policies.

## Canonical Rules

Use canonical owners for `ALATYR-CONTEXT-001`, `ALATYR-SOURCE-001`,
`ALATYR-RISK-001`, `ALATYR-APPROVAL-001`, `ALATYR-SAFETY-001`,
`ALATYR-SAFETY-002`, `ALATYR-INTEGRITY-001`, `ALATYR-CHANGE-001`,
`ALATYR-ADAPTER-001`, `ALATYR-MODULE-001`, `ALATYR-OPERATION-001`,
`ALATYR-DIAGRAM-001`, `ALATYR-TEAM-001`, and `ALATYR-EVIDENCE-001`. Project
facts belong under the project contour; local
flows, gates, prompts, skills, bridges, checkers, and commands belong under the
assistant contour. Do not invent facts or copy policy into bridges.

For semantic changes, re-derive target invariants and reconcile related review
items by shared fact or contract. Use the consistency map when enabled. For AI
infrastructure, select one route and the smallest item-ID set before loading
item-specific context. Run only validation that exists.

Routing selects a flow; it does not grant approval or broaden allowed actions.
A preview is not approval and becomes stale when material risk or scope
changes.

## Protected Changes

Apply target approval policy before architecture, accepted behavior, security,
permission, dependency, destructive, live, spend, production, imported-
infrastructure, or weakened-gate changes. When path scope matters, use an
explicit JSON approval record bound to the Git diff base and reject uncovered
or excluded paths.

## Final Evidence

Report profile/areas, changed facts/files, invariant/integrity result,
reconciled reviews, synchronized surfaces, validation/skips, approval scope,
context expansion, optional task-scale or AI-item evidence, preview state, and
residual risk.
