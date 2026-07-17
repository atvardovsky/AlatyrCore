# AI Infrastructure Recommendation Flow

Use this flow in `{PROJECT_NAME}` when the programmer asks what AI
infrastructure should be added or how an existing skill, prompt, gate, checker,
flow, tool/MCP configuration, bridge, wrapper, or template should change.

Aliases include `alatyr-suggest-ai {RECOMMENDATION_SCOPE}` and
`alatyr-improve-ai {AI_INFRASTRUCTURE_ITEM_ID}`. These are chat/request
shortcuts, not shell commands.

Recommendation is read-only. Do not fetch, install, execute, edit, remove,
activate, or change permissions during this flow.

## Base Target Sources

- Compact bootstrap, with `AGENTS.md` treated as preloaded
- Framework recommendation guidance:
  `.ai/framework/ai-infrastructure-recommendations.md`
- Framework routing guidance: `.ai/framework/ai-infrastructure-routing.md`
- AI infrastructure router: `.ai/assistant/ai-infrastructure-router.json`
- Project contour: `.ai/project/contour.md`
- Source-of-truth registry: `.ai/project/source-of-truth-registry.md`
- Target assistant contour: `.ai/assistant/contour.md`
- Target gates: `.ai/assistant/gates/checklist.md`
- Recommendation report template:
  `.ai/assistant/templates/ai-infrastructure-recommendation.md`
- Target validation or manual review: `{TARGET_VALIDATION}`

## Conditional Sources

- Current inventory report or
  `.ai/assistant/flows/ai-infrastructure-inventory.flow.md` when relevant item
  coverage is unknown
- Selected project-area source of truth: `{SELECTED_PROJECT_AREA_OWNER}`
- Selected existing item source: `{SELECTED_AI_ITEM_CANONICAL_SOURCE}`
- Existing adaptation record: `{SELECTED_AI_ITEM_ADAPTATION_RECORD}`
- Existing item validation and output evidence:
  `{SELECTED_AI_ITEM_EFFECTIVENESS_EVIDENCE}`
- Maturity, adapter-recheck, large-task, incident, rework, or effectiveness
  evidence only when it supports the observed problem
- Framework adaptation guidance: `.ai/framework/skill-adaptation.md` only when
  describing an accepted recommendation's next operation

Do not load source-access or prompt-injection policy during ordinary
recommendation. Load it later if an accepted proposal moves to external source
review or canonical integration.

## Steps

1. Select the `recommend` route and the smallest project area, problem scope,
   and existing item-ID set.
2. Load a current bounded inventory or inspect only relevant router-declared
   items. Do not scan all item content when router evidence is sufficient.
3. Identify the project-contour owner for the need, constraint, or expected
   outcome. Record missing or anecdotal evidence explicitly.
4. Cluster repeated tasks, review failures, incidents, skipped checks,
   consistency gaps, context expansions, or unsupported assistant behavior by
   the outcome they affect.
5. Compare existing item purpose, triggers, context, permissions, gates,
   validation, output contract, assistant surfaces, and observed results with
   that project evidence.
6. Classify each candidate as `add-new`, `improve-existing`, `consolidate`,
   `replace`, `retire`, `keep`, or `unresolved`. Evaluate existing-item changes
   before `add-new`.
7. Choose the narrowest item type: skill for recurring specialized reasoning,
   prompt/template for stable I/O, gate for human decisions, checker for
   deterministic invariants, flow/checklist for ordered work, tool/MCP only for
   missing execution capability, or bridge/wrapper for assistant compatibility.
8. Record expected quality effect, acceptance criteria, context-load effect,
   implementation and maintenance cost, permissions, safety, compatibility,
   validation, rollback or retirement path, and residual risk. Label estimates
   and do not invent measurements.
9. Reject speculative, duplicate, one-off, ownerless, or untestable candidates.
   Keep unresolved evidence unresolved.
10. Write or report a bounded recommendation using
    `.ai/assistant/templates/ai-infrastructure-recommendation.md` only when the
    requested allowed actions permit adapter evidence changes.
11. Do not change project contour facts. They justify the need and expected
    outcome; recommendation and item mechanics remain assistant-contour owned.
12. For an accepted candidate, name but do not start the next route:
    `adapt-import`, `gate-checker-change`, `tool-mcp-change`, or
    `bridge-wrapper-change`. That later operation performs normal approval,
    source-access, prompt-injection, permission, and validation checks.

## Final Evidence

Report:

- recommendation scope, project area, and canonical owner
- selected route, inventory source, existing item IDs, and surfaces inspected
- observed problem, recurrence or high-impact exception, and evidence quality
- recommendation kind and proposed item type
- proposed contract change and non-goals
- expected quality effect and measurable acceptance criteria
- expected context-load, implementation, and maintenance cost
- permissions, safety, compatibility, approval, and validation impact
- rejected or unresolved candidates and reasons
- recommendation status and next operation
- actions explicitly not taken and residual risk

## Rejection Criteria

Reject or revise recommendation work that:

- proposes an item without project-contour evidence or a target-owned outcome
- recommends `add-new` without checking relevant existing items and overlap
- treats estimates as measured quality, token, duration, or cost improvement
- uses a prompt where a deterministic checker is required, or a tool where a
  repository workflow is sufficient
- fetches, installs, edits, removes, activates, or broadens permissions during
  recommendation
- moves assistant workflow mechanics into the project contour
- cannot name acceptance criteria, maintenance ownership, or residual risk
